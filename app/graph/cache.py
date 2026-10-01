import json

import numpy as np
from langchain_core.embeddings import Embeddings

from app.core.redis import get_redis


# Simple semantic cache using redis keys + cosine sim
async def semantic_search_cache(query: str, embeddings: Embeddings, threshold: float = 0.9):
    redis = get_redis()
    keys = await redis.keys("semcache:*")
    if not keys: return None
    
    query_emb = np.array(embeddings.embed_query(query))
    
    best_score = -1
    best_answer = None
    
    for key in keys:
        data = await redis.get(key)
        if data:
            entry = json.loads(data)
            emb = np.array(entry["embedding"])
            # cosine similarity
            score = np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb))
            if score > best_score:
                best_score = score
                best_answer = entry["answer"]
                
    if best_score >= threshold:
        return best_answer
    return None

async def store_in_cache(query: str, answer: str, embeddings: Embeddings):
    redis = get_redis()
    query_emb = embeddings.embed_query(query)
    
    # Check if exactly exists to avoid bloat
    key_hash = hash(query)
    key = f"semcache:{key_hash}"
    
    entry = {
        "query": query,
        "answer": answer,
        "embedding": query_emb
    }
    await redis.set(key, json.dumps(entry))
    
async def invalidate_cache():
    redis = get_redis()
    keys = await redis.keys("semcache:*")
    if keys:
        await redis.delete(*keys)
