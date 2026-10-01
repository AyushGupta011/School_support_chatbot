import asyncio
import os
import sys

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.db import AsyncSessionLocal
from app.graph.builder import build_graph


async def main(question: str):
    class DummyEmbeddings:
        def embed_query(self, text): return [0.1]*1536
        
    class DummyLLM:
        def invoke(self, msgs):
            class Msg:
                content = "Fake answer [source, section/page]"
            return Msg()

    embeddings = OpenAIEmbeddings() if os.environ.get("OPENAI_API_KEY") else DummyEmbeddings()
    llm = ChatOpenAI(temperature=0) if os.environ.get("OPENAI_API_KEY") else DummyLLM()
    
    async with AsyncSessionLocal() as session:
        graph = build_graph(session, embeddings, llm)
        result = await graph.ainvoke({"question": question, "student_id": 1, "role": "student", "chunks": [], "answer": ""})
        print(f"Q: {question}\nA: {result['answer']}")

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "What is the attendance policy?"
    asyncio.run(main(q))
