import os

from langsmith import traceable


@traceable(name="rerank_chunks")
async def rerank(query: str, chunks: list, mode: str = "vector_only"):
    if mode == "vector_only":
        return chunks
        
    if mode == "hybrid_rerank":
        try:
            from langchain_cohere import CohereRerank
            from langchain_core.documents import Document
            
            cohere_api_key = os.environ.get("COHERE_API_KEY", "")
            if not cohere_api_key:
                return chunks
                
            compressor = CohereRerank(cohere_api_key=cohere_api_key, top_n=3)
            
            docs = [Document(page_content=c.content, metadata=c.metadata_json) for c in chunks]
            compressed_docs = compressor.compress_documents(docs, query)
            
            return [{"content": d.page_content, "metadata_json": d.metadata} for d in compressed_docs]
        except Exception:  # noqa: BLE001
            return chunks
            
    return chunks
