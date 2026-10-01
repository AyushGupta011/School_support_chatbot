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

## Phase 4: Complete the LangGraph assistant
- **Status:** Done
- **Decisions Made:**
  - Added full graph logic representing `messages`, `intent`, `retrieved_docs`, `confidence`, `tool_results`, `retry_count`, `cache_hit`, and `final_answer`.
  - Segregated control flow via intent classification: `personal_data`, `knowledge`, `chitchat`, and `unknown`.
  - Set up `guardrails_in` analyzing inputs for excessive length or prompt injection keywords.
  - Created `guardrails_out` checking the final answer for leaked system prompts or cross-student ID boundaries (rejects outputs containing STUXXX of other users).
  - Setup `Redis` caching via `semantic_search_cache` keyed by semantic similarity for queries.
  - Wrote strict `tool_agent` nodes where the tool schema does *not* expose `student_id` to the LLM (bypassing injection capabilities), and it relies entirely on server-side state config. 
  - LangSmith tracing enriched with hashed tags (`intent_pending`, `env_prod`, `route_chat`) and Postgres checkpointer config logic placed in endpoint.
  - Tests covering prompt injections, knowledge routes, cross-student leaks logic built against fake environments seamlessly. 
- **How to run:**
  - Invoke `POST /chat/` using the student bearer token and a `{"message": "string"}` payload.
  - Returns Server-Sent Events (SSE) `application/x-ndjson` streaming response containing tokens and final outputs.
- **Known Issues:** None.

## Phase 5: HTTP API and a minimal web UI
- **Status:** Done
- **Decisions Made:**
  - Upgraded `/chat` to utilize SSE (`sse-starlette`) correctly iterating through `astream_events` from the LangGraph run. It emits distinct events for `run_id`, streamed `token` instances, and finally `done` containing the `final_answer`.
  - Built `POST /chat/feedback` to ingest ratings. It pushes directly to the underlying `Feedback` Postgres schema and mirrors standard interactions to `langsmith` using `create_feedback(run_id, key="user_score", score=score)`.
  - Added `POST /admin/ingest` requiring strict `admin` JWT capabilities. Spins up an asynchronous background task resolving `app.rag.ingest`.
  - Implemented `app/core/middleware.py::RequestIDMiddleware` which generates and attaches an `X-Request-ID` across the lifecycle.
  - Integrated a minimal Web UI hosted natively via `app/api/ui.py` at `/`. It leverages local storage to handle the bearer token transparently and consumes the SSE stream while displaying realtime outputs. Interactive feedback (👍/👎) controls unlock upon completion.
  - Authored isolated suite `test_api.py` validating strict role segmentation via token checks, hitting explicit `chat` SSE endpoints using `httpx-sse`, and validating proper rate limits (`HTTP 429` on 20+ operations/min).
- **How to run:**
  - Access `http://localhost:8000/` via browser. 
  - Authenticate using `demo_student_1` and `demopass`.
  - Input prompts to see streaming SSE answers parsing natively in the vanilla JS wrapper. Provide feedback via appended buttons.
- **Known Issues:** None.

## Phase 6: Evaluation harness using LangSmith and RAGAS
- **Status:** Done
- **Decisions Made:**
  - Created `evals/dataset.jsonl` encapsulating 80 hand-crafted interactions split across `english`, `hinglish`, `adversarial`, `out_of_scope` and `personal_data` domains mapped directly to expected nodes/tools.
  - Formatted `evals/setup_dataset.py` mapping `.jsonl` directly to `langsmith.Client().create_dataset(...)` allowing distinct metadata attributes per node.
  - Devised `evals/evaluators.py` introducing bespoke rulesets for `tool_correctness`, `leakage_prevention` (analyzing STUxxx leakage against contextual IDs), and `routing_accuracy`. Designed wrappers embedding RAGAS models via `LangchainLLMWrapper` calculating asynchronous `faithfulness` and `relevancy` scores strictly on the knowledge slice.
  - Orchestrated `evals/run_eval.py` exploiting LangSmith's robust `aevaluate` targeting the `vector_only` and `hybrid_rerank` matrices, dumping local telemetry.
  - Authored `evals/ci_gate.py` implementing strict minimum threshold gates enforcing zero leakage parameters alongside minimum contextual precision expectations (`sys.exit(1)` upon failure). Output formatted perfectly to markdown tables inside `evals/results/report.md`.
  - Built explicit synthetic `evals/generate_testset.py` drafting candidates strictly to a review file rather than polluting production evals. 
- **How to run:**
  - Use `python evals/setup_dataset.py` to push to LangSmith.
  - Call `python evals/run_eval.py --mode [vector_only | hybrid_rerank]` executing the metrics workload across the evaluation array. 
  - `python evals/ci_gate.py` returns CI exit statuses corresponding to regression tests.
- **Known Issues:** 
  - Host environment continues failing to orchestrate `asyncpg` bindings requiring pure-python bypasses where necessary.
