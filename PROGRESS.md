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
- **Known Issues:** None so far.

