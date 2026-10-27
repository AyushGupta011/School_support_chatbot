from langchain_core.embeddings import Embeddings
from langsmith import traceable
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.erp import Chunk


def reciprocal_rank_fusion(vector_rows, fts_rows, top_k=5, k_rrf=60):
    scores = {}
    docs = {}
    
    for rank, row in enumerate(vector_rows):
        cid = row.id
        scores[cid] = scores.get(cid, 0) + 1.0 / (k_rrf + rank + 1)
        docs[cid] = row
        
    for rank, row in enumerate(fts_rows):
        cid = row.id
        scores[cid] = scores.get(cid, 0) + 1.0 / (k_rrf + rank + 1)
        docs[cid] = row
        
    sorted_cids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]
    return [docs[cid] for cid in sorted_cids]

@traceable(name="hybrid_retrieve")
async def retrieve_chunks(session: AsyncSession, query: str, embeddings: Embeddings, top_k: int = 5, filter_dict: dict | None = None):
    query_emb = embeddings.embed_query(query)
    
    # Vector Search
    vector_stmt = select(Chunk.id, Chunk.content, Chunk.metadata_json, Chunk.embedding.cosine_distance(query_emb).label("distance"))
    if filter_dict:
        for k, v in filter_dict.items():
            vector_stmt = vector_stmt.where(Chunk.metadata_json[k].astext == str(v))
    vector_stmt = vector_stmt.order_by(Chunk.embedding.cosine_distance(query_emb)).limit(top_k * 2)
    vector_res = await session.execute(vector_stmt)
    vector_rows = vector_res.all()
    
    # FTS Search
    import re
    words = [re.sub(r'\W+', '', w) for w in query.split() if len(re.sub(r'\W+', '', w)) > 1]
    if words:
        fts_query = " | ".join(words)
        fts_stmt = select(
            Chunk.id,
            Chunk.content,
            Chunk.metadata_json,
            func.ts_rank_cd(Chunk.tsv, func.to_tsquery('english', fts_query)).label("rank")
        ).where(Chunk.tsv.op("@@")(func.to_tsquery('english', fts_query)))
        if filter_dict:
            for k, v in filter_dict.items():
                fts_stmt = fts_stmt.where(Chunk.metadata_json[k].astext == str(v))
        fts_stmt = fts_stmt.order_by(func.ts_rank_cd(Chunk.tsv, func.to_tsquery('english', fts_query)).desc()).limit(top_k * 2)
        fts_res = await session.execute(fts_stmt)
        fts_rows = fts_res.all()
    else:
        fts_rows = []
        
    return reciprocal_rank_fusion(vector_rows, fts_rows, top_k=top_k)
