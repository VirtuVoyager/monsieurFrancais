.PHONY: up down obs logs dev-api dev-web migrate seed reset-db grade-pending test lint typecheck check gen-api e2e

up:            ## Build and start db, api and web in Docker (OrbStack)
	docker compose up -d --build

down:
	docker compose down

obs:           ## Start with the Grafana/Loki/Tempo observability stack on :3001
	MF_OTEL_ENDPOINT=http://obs:4318 docker compose --profile obs up -d --build

logs:
	docker compose logs -f api web

dev-api:       ## Run the API locally with reload (needs Postgres on :5432)
	cd api && uv run alembic upgrade head && uv run python -m app.jobs.seed && uv run uvicorn app.main:app --reload --port 8000

dev-web:
	cd web && pnpm dev

migrate:
	cd api && uv run alembic upgrade head

seed:
	cd api && uv run python -m app.jobs.seed

grade-pending: ## Retry writing submissions deferred by a budget cap or grader outage
	cd api && uv run python -m app.jobs.grade_pending

reset-db:      ## Drop and recreate the local schema, then migrate and seed
	cd api && uv run alembic downgrade base && uv run alembic upgrade head && uv run python -m app.jobs.seed

test:
	cd api && uv run pytest -q
	cd web && pnpm test

lint:
	cd api && uv run ruff check . && uv run ruff format --check .
	cd web && pnpm lint && pnpm format:check

typecheck:
	cd api && uv run mypy app
	cd web && pnpm typecheck

check: lint typecheck test

gen-api:       ## Regenerate the typed web client from the API's OpenAPI schema
	cd web && pnpm gen:api

e2e: reset-db  ## Browser tests against a freshly seeded database (API and web must be running)
	cd web && pnpm e2e
