import os

files = {
    "pyproject.toml": """[project]
name = "school-support-chatbot"
version = "0.1.0"
description = "University student assistant chatbot"
authors = [{name = "Antigravity", email = "ai@google.com"}]
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.142.2",
    "uvicorn>=0.54.0",
    "pydantic>=2.13.5",
    "pydantic-settings>=2.15.0",
    "sqlalchemy>=2.1.1",
    "asyncpg>=0.31.0",
    "redis>=8.1.0",
    "structlog>=26.1.0",
    "langchain>=1.4.3",
    "langchain-core>=1.4.3",
    "langchain-community>=1.4.3",
    "langgraph>=1.2.12",
    "langchain-postgres>=0.0.18",
    "langgraph-checkpoint-postgres>=3.1.2",
    "ragas>=0.4.3",
    "langsmith>=0.14.2",
    "psycopg2-binary>=2.9.9",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
]

[project.optional-dependencies]
dev = [
    "pytest>=9.1.1",
    "pytest-asyncio>=1.4.0",
    "httpx>=0.28.1",
    "ruff>=0.16.9",
    "mypy>=2.3.1",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
""",
    "Dockerfile": """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution and installation
RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system -e .[dev]

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
    "docker-compose.yml": """version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/school_chatbot
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: school_chatbot
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d school_chatbot"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
""",
    ".env.example": """# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/school_chatbot
# Redis
REDIS_URL=redis://redis:6379/0

# JWT Auth
JWT_SECRET=super_secret_key_change_me_in_prod
JWT_EXPIRY_MINUTES=60

# LLM Configuration
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-small
RERANKER_CHOICE=cohere

# LangSmith Tracing & Evals
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langchain_api_key
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_PROJECT=school_chatbot_dev
LANGCHAIN_EVAL_PROJECT=school_chatbot_eval

# RAG & Application settings
CACHE_SIMILARITY_THRESHOLD=0.9
RETRIEVAL_TOP_K=5
CONFIDENCE_THRESHOLD=0.75
EVAL_THRESHOLDS=0.8
""",
    "app/__init__.py": "",
    "app/core/__init__.py": "",
    "app/core/config.py": """from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/school_chatbot"
    redis_url: str = "redis://localhost:6379/0"
    
    jwt_secret: SecretStr = SecretStr("default_secret")
    jwt_expiry_minutes: int = 60
    
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"
    reranker_choice: str = "cohere"
    
    langchain_tracing_v2: bool = False
    langchain_api_key: SecretStr | None = None
    langchain_endpoint: str = "https://api.smith.langchain.com"
    langchain_project: str = "school_chatbot_dev"
    langchain_eval_project: str = "school_chatbot_eval"
    
    cache_similarity_threshold: float = 0.9
    retrieval_top_k: int = 5
    confidence_threshold: float = 0.75
    eval_thresholds: float = 0.8

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
""",
    "app/core/logging.py": """import logging
import structlog
import sys

def filter_secrets(logger, log_method, event_dict):
    \"\"\"Redact secrets from logs.\"\"\"
    sensitive_keys = {"password", "token", "email", "secret", "student_id"}
    for key in list(event_dict.keys()):
        if any(sens in key.lower() for sens in sensitive_keys):
            event_dict[key] = "***REDACTED***"
    return event_dict

def setup_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            filter_secrets,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
""",
    "app/main.py": """from fastapi import FastAPI, Depends
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from redis.asyncio import Redis
from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="School Support Chatbot")

async def get_db_health():
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.connect() as conn:
            return "ok"
    except Exception as e:
        logger.error(f"Postgres health check failed: {e}")
        return "error"
    finally:
        await engine.dispose()

async def get_redis_health():
    try:
        redis = Redis.from_url(settings.redis_url)
        await redis.ping()
        return "ok"
    except Exception as e:
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
""",
    "tests/__init__.py": "",
    "tests/test_health.py": """import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_health_check_returns_correct_format():
    # In a real test, we would mock DB/Redis or rely on test containers
    # For phase 0, we're just checking the endpoint structure
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "postgres" in data
        assert "redis" in data
""",
    "Makefile": """up:
\tdocker compose up -d --build

down:
\tdocker compose down -v

test:
\tdocker compose exec -T app pytest

lint:
\tdocker compose exec -T app ruff check .
\tdocker compose exec -T app mypy .

seed:
\tdocker compose exec -T app python scripts/seed.py

ingest:
\tdocker compose exec -T app python scripts/ingest_docs.py

eval:
\tdocker compose exec -T app python evals/run.py
""",
    ".gitignore": """.env
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/
""",
    "PROGRESS.md": """# Progress

## Phase 0: Project scaffold and infrastructure
- **Status:** Done
- **Decisions Made:**
  - Using `pyproject.toml` with `uv` for fast dependency management.
  - Used standard pinned versions for core stack components (FastAPI, SQLAlchemy, LangGraph, etc.).
  - Configured structured JSON logging with custom `structlog` filter to redact sensitive data (emails, passwords, tokens, student_ids).
  - Setup `.env.example` mapping all specified requirements.
  - Basic `/health` endpoint fully async checking Postgres and Redis connectivity.
- **How to run:**
  - `make up` to start all containers.
  - `make test` to run tests.
  - `make lint` to check format and types.
- **Known Issues:** None so far.

"""
}

# Create all files and directories
for path, content in files.items():
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

print("Files created successfully.")
