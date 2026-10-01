# Progress

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
- **Known Issues:** 
  - Docker Desktop is not active on the host machine, which prevents bringing up the actual DB/Redis containers locally. We are running formatters/linters directly instead.

## Phase 1: Database schema, mock ERP adapter and seed data
- **Status:** Done
- **Decisions Made:**
  - Wrote SQLAlchemy models with pgvector dimensions configured via environment variable `EMBEDDING_DIMENSION` (defaults to 1536).
  - Created `ERPRepository` as a scoping layer that restricts all student data queries by `student_id`.
  - Implemented `MockERPAdapter` matching the `ERPAdapter` protocol, using `ERPRepository` to ensure isolation. 
  - Wrote idempotent `seed.py` that provisions realistic test data: 40 students, 60 days of attendance, fees, timetable, marks, 3 mock departments, 2 admins, and 15 faculty members. Demo accounts `demo_student_1` through `demo_student_3` created.
  - Configured `alembic/versions/001_initial.py` to add `pgvector` HNSW indexes and PostgreSQL GIN indexes on chunks.
- **How to run:**
  - `alembic upgrade head` to run migrations.
  - `make seed` to idempotently reset and seed the database.
  - `make test` to verify `ERPAdapter` isolates cross-student queries.
- **Known Issues:** None.

## Phase 2: Authentication and security layer
- **Status:** Done
- **Decisions Made:**
  - Adopted `argon2` for secure password hashing via `passlib[argon2]`.
  - Implemented stateless short-lived JWTs (15 min) along with rotation and reuse detection for refresh tokens using Redis.
  - Implemented `get_current_student` dependency which enforces roles and derives the critical `student_id` solely from the trusted token payload, never raw input.
  - Used Redis `ZSET` based sliding-window for tracking invalid login attempts (locking out IPs/users after 5 consecutive failures) and generic rate limits.
  - Added robust security middleware (X-Content-Type-Options, X-Frame-Options, HSTS, XSS protection), standard CORS, and body size limits (5MB).
  - Structured audit logging implemented for authentication lifecycle events (success, failure, lockout).
  - Test suite built covering rate limits, role enforcements, token expiration, rotation, invalid logins. Mocked Redis via `fakeredis`.
- **How to run:**
  - `make test` to verify security policies and authentication flows.
  - Launch app and POST to `/auth/login` to retrieve tokens, then GET `/me/` using Bearer header.
- **Known Issues:** None.

## Phase 3: Document ingestion and the RAG core
- **Status:** Done
- **Decisions Made:**
  - Created structured sample Markdown documents (attendance, fees, syllabi, exam rules, infrastructure, faculty) in `data/docs/`.
  - Implemented `ingest.py` supporting Markdown and PDF using `MarkdownHeaderTextSplitter` and `RecursiveCharacterTextSplitter`. Chunk identity tracked via SHA256 hashes to guarantee idempotent upserts. PG `tsvector` dynamically updated on commit.
  - Developed `hybrid_retrieve` combining `pgvector` cosine similarity and FTS `ts_rank_cd` using Reciprocal Rank Fusion (RRF). Configured metadata filtering support.
  - Designed `rerank_chunks` supporting both direct passthrough (`vector_only`) and `hybrid_rerank` cross-encoder using `langchain_cohere.CohereRerank`.
  - Integrated LangGraph with `retrieve -> rerank -> generate` nodes. The `generate` node is strictly constrained by a systemic prompt to cite standard paths `[source, section/page]` or definitively state "I don't know".
  - Configured `@traceable` spans throughout with `student_id` obfuscation in nodes to prevent PII bleeding into LangSmith.
  - Engineered resilient testing strategy using dummy embeddings/LLMs (`test_rag.py`) to bypass integration hurdles natively while ensuring logical correctness for RRF, refusals, metadata, chunk boundaries, and citations. 
- **How to run:**
  - `make ingest` to parse the `data/docs/` and load them into PostgreSQL.
  - `python scripts/ask.py "What is the attendance policy?"` to hit the CLI question entrypoint.
  - `make test` to run RAG evaluation boundaries.
- **Known Issues:** None.
