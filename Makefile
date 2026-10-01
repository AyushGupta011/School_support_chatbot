up:
	docker compose up -d --build

down:
	docker compose down -v

test:
	docker compose exec -T app pytest

lint:
	docker compose exec -T app ruff check .
	docker compose exec -T app mypy .

seed:
	docker compose exec -T app python scripts/seed.py

ingest:
	docker compose exec -T app python scripts/ingest_docs.py

eval:
	docker compose exec -T app python evals/run.py
