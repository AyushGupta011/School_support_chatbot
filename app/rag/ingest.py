import hashlib
import os

from langchain_core.embeddings import Embeddings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.erp import Chunk, Document
from app.rag.chunking import chunk_markdown


async def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

async def ingest_documents(session: AsyncSession, embeddings: Embeddings, docs_dir: str):
    for filename in os.listdir(docs_dir):
        if filename.endswith(".md"):
            with open(os.path.join(docs_dir, filename), "r", encoding="utf-8") as f:  # noqa: ASYNC230
                content = f.read()
        elif filename.endswith(".pdf"):
            try:
                from langchain_community.document_loaders import PyMuPDFLoader
                loader = PyMuPDFLoader(os.path.join(docs_dir, filename))
                content = "\\n".join(doc.page_content for doc in loader.load())
            except ImportError:
                content = "PDF loading requires pymupdf"
        else:
            continue
                
        # Upsert document
            stmt = select(Document).where(Document.title == filename)
            result = await session.execute(stmt)
            doc = result.scalar_one_or_none()
            
            if not doc:
                doc = Document(title=filename, content=content)
                session.add(doc)
                await session.flush()
                
            chunks = chunk_markdown(content, source=filename)
            
            for chunk in chunks:
                chunk_hash = await compute_hash(chunk['content'])
                chunk['metadata']['hash'] = chunk_hash
                
                # Check if chunk exists
                stmt_chk = select(Chunk).where(Chunk.metadata_json['hash'].astext == chunk_hash)
                res_chk = await session.execute(stmt_chk)
                if not res_chk.scalar_one_or_none():
                    emb = embeddings.embed_query(chunk['content'])
                    new_chunk = Chunk(
                        document_id=doc.id,
                        content=chunk['content'],
                        embedding=emb,
                        metadata_json=chunk['metadata'],
                    )
                    session.add(new_chunk)
                    
            await session.commit()
            
            # Post-process tsvector
            await session.execute("UPDATE chunks SET tsv = to_tsvector('english', content) WHERE tsv IS NULL")
            await session.commit()
