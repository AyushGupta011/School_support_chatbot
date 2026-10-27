import asyncio
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.db import AsyncSessionLocal
from app.core.llm import get_llm
from app.graph.builder import build_graph


async def main(question: str):
    class DummyEmbeddings:
        def embed_query(self, text): return [0.1]*1536
        def embed_documents(self, texts): return [[0.1]*1536 for _ in texts]
        
    llm = get_llm()
    key = os.environ.get("OPENAI_API_KEY")
    embeddings = OpenAIEmbeddings() if key and not key.startswith("your_") else DummyEmbeddings()
    
    async with AsyncSessionLocal() as session:
        graph = build_graph(llm, embeddings)
        config = {
            "configurable": {
                "session": session,
                "student_id": 41
            }
        }
        initial_state = {
            "messages": [HumanMessage(content=question)],
            "student_id": 41,
            "role": "student"
        }
        result = await graph.ainvoke(initial_state, config=config)
        print(f"\nQ: {question}\nA: {result.get('final_answer')}\n")

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "What is the attendance policy?"
    asyncio.run(main(q))
