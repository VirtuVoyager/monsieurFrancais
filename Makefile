.PHONY: up down obs logs dev-api dev-web migrate seed reset-db grade-pending embed audio note-audio glossary mcp test lint typecheck check gen-api e2e

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

embed:         ## Embed knowledge-base entries that are new or changed (also runs every minute in the API)
	cd api && uv run python -m app.jobs.embed_pending

audio:         ## Generate missing catalogue audio (each clip once; set MF_SPEECH_PROVIDER=azure for real voices)
	cd api && uv run python -m app.jobs.generate_audio

note-audio:    ## Generate audio for approved class-note words and phrases (also runs every 5 minutes in the API)
	cd api && uv run python -m app.jobs.note_audio

glossary:      ## Build hover glossaries for changed modules (set MF_GLOSSARY_PROVIDER=azure for real ones)
	cd api && uv run python -m app.jobs.build_glossaries

mcp:           ## Run the read-only MCP server on stdio (for Claude Desktop and other clients)
	cd api && uv run python -m app.mcp_server

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
	cd api && MF_GLOSSARY_PROVIDER=fake uv run python -m app.jobs.build_glossaries
	cd web && pnpm e2e
