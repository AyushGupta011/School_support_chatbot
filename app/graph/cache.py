import hashlib
import json

import numpy as np
from langchain_core.embeddings import Embeddings

from app.core.redis import get_redis


# Robust semantic cache using redis scan + cosine similarity
async def semantic_search_cache(query: str, embeddings: Embeddings, threshold: float = 0.9):
    try:
        redis = get_redis()
        # Scan with match rather than blocking keys()
        keys = []
        cur = "0"
        while True:
            res = await redis.scan(cursor=cur, match="semcache:*", count=100)
            if isinstance(res, (list, tuple)) and len(res) == 2:
                cur, batch = res
                keys.extend(batch)
            else:
                break
            if str(cur) == "0":
                break
                
        if not keys:
            return None
            
        raw_emb = embeddings.embed_query(query)
        query_emb = np.array(raw_emb, dtype=np.float32)
        norm_q = np.linalg.norm(query_emb)
        if norm_q == 0 or np.std(query_emb) < 1e-4:
            # Skip semantic cache if embeddings are dummy/constant
            return None
        
        best_score = -1.0
        best_answer = None
        
        for key in keys:
            data = await redis.get(key)
            if data:
                entry = json.loads(data)
                emb = np.array(entry["embedding"], dtype=np.float32)
                if np.std(emb) < 1e-4:
                    continue
                norm_e = np.linalg.norm(emb)
                if norm_e > 0:
                    score = float(np.dot(query_emb, emb) / (norm_q * norm_e))
                    if score > best_score:
                        best_score = score
                        best_answer = entry["answer"]
                        
        if best_score >= threshold:
            return best_answer
        return None
    except Exception:
        # Cache lookup should fail gracefully without failing chat request
        return None

async def store_in_cache(query: str, answer: str, embeddings: Embeddings, ttl_seconds: int = 86400 * 7):
    try:
        raw_emb = embeddings.embed_query(query)
        query_emb = np.array(raw_emb, dtype=np.float32)
        if np.std(query_emb) < 1e-4:
            # Do not cache dummy/constant embeddings
            return
        redis = get_redis()
        raw_emb = embeddings.embed_query(query)
        if hasattr(raw_emb, "tolist"):
            raw_emb = raw_emb.tolist()
            
        # Deterministic SHA256 key
        key_hash = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()
        key = f"semcache:{key_hash}"
        
        entry = {
            "query": query,
            "answer": answer,
            "embedding": raw_emb
        }
        await redis.setex(key, ttl_seconds, json.dumps(entry))
    except Exception:
        pass

async def invalidate_cache():
    try:
        redis = get_redis()
        cur = "0"
        while True:
            res = await redis.scan(cursor=cur, match="semcache:*", count=100)
            if isinstance(res, (list, tuple)) and len(res) == 2:
                cur, batch = res
                if batch:
                    await redis.delete(*batch)
            else:
                break
            if str(cur) == "0":
                break
    except Exception:
        pass
