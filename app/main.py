import logging

from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine

from app.api import admin, auth, chat, me, ui
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import setup_middlewares

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="School Support Chatbot")
setup_middlewares(app)
app.include_router(auth.router)
app.include_router(me.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(ui.router)

async def get_db_health():
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.connect():
            return "ok"
    except Exception as e:  # noqa: BLE001
        logger.error(f"Postgres health check failed: {e}")
        return "error"
    finally:
        await engine.dispose()

async def get_redis_health():
    try:
        redis = Redis.from_url(settings.redis_url)
        await redis.ping()
        return "ok"
    except Exception as e:  # noqa: BLE001
        logger.error(f"Redis health check failed: {e}")
        return "error"
    finally:
        if 'redis' in locals():
            await redis.close()

@app.get("/health")
async def health_check():
    pg_status = await get_db_health()
    redis_status = await get_redis_health()
    
    return {
        "status": "ok" if pg_status == "ok" and redis_status == "ok" else "error",
        "postgres": pg_status,
        "redis": redis_status,
    }
