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
