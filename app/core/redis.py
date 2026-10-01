import time
import uuid

from redis.asyncio import Redis

from app.core.config import settings

# This will be replaced with fakeredis during testing
_redis_client: Redis | None = None

def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client

def set_redis(client: Redis):
    global _redis_client
    _redis_client = client

async def check_rate_limit(key: str, limit: int, window: int) -> bool:
    redis = get_redis()
    now = time.time()
    
    # Use sliding window rate limit via ZSET
    pipeline = redis.pipeline()
    pipeline.zremrangebyscore(key, 0, now - window)
    pipeline.zadd(key, {str(uuid.uuid4()): now})
    pipeline.zcard(key)
    pipeline.expire(key, window)
    results = await pipeline.execute()
    
    count = results[2]
    return count <= limit

async def mark_login_failure(ip: str, enrollment_no: str):
    redis = get_redis()
    now = time.time()
    key_ip = f"login_failures:ip:{ip}"
    key_user = f"login_failures:user:{enrollment_no}"
    
    for key in [key_ip, key_user]:
        await redis.zremrangebyscore(key, 0, now - 300) # 5 minutes window
        await redis.zadd(key, {str(uuid.uuid4()): now})
        await redis.expire(key, 300)

async def check_lockout(ip: str, enrollment_no: str) -> bool:
    redis = get_redis()
    now = time.time()
    key_ip = f"login_failures:ip:{ip}"
    key_user = f"login_failures:user:{enrollment_no}"
    
    for key in [key_ip, key_user]:
        await redis.zremrangebyscore(key, 0, now - 300)
        count = await redis.zcard(key)
        if count >= 5: # Lockout after 5 failures in 5 mins
            return True
    return False

async def clear_login_failures(ip: str, enrollment_no: str):
    redis = get_redis()
    key_ip = f"login_failures:ip:{ip}"
    key_user = f"login_failures:user:{enrollment_no}"
    await redis.delete(key_ip, key_user)

async def is_refresh_token_used(jti: str) -> bool:
    redis = get_redis()
    key = f"used_refresh:{jti}"
    return await redis.exists(key) > 0

async def mark_refresh_token_used(jti: str, expires_in: int = 86400 * 7):
    redis = get_redis()
    key = f"used_refresh:{jti}"
    await redis.setex(key, expires_in, "1")
