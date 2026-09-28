# Monsieur Français

Exam-first French app for TCF Canada (target NCLC 7), A1 → C2. The full plan is in
[docs/PLAN.md](docs/PLAN.md); read the relevant section before changing a feature.

## Layout

- `api/`: FastAPI + SQLAlchemy 2 + Alembic, Python 3.12, managed with `uv`.
  - `app/domain/`: pure logic (scoring, coverage, cost, exercises). No I/O.
  - `app/services/`: use cases; the only place that touches the DB session and providers.
  - `app/routers/`: thin HTTP layer; `app/presenters.py` maps domain state to schemas.
  - `app/models/`: catalogue tables (shared, no `user_id`) and personal tables (always `user_id`).
- `web/`: Next.js 16 App Router, TypeScript, Tailwind v4. UI only; all data via `/api/*`.
  Read `web/AGENTS.md` first: this Next.js version differs from older training data.
- `content/`: the course catalogue (YAML/Markdown/CSV), `pricing.yaml`, `exam_scales.yaml`.

## Commands

`make check` (lint + typecheck + tests), `make dev-api`, `make dev-web`, `make reset-db`,
`make gen-api` after any API schema change, `make e2e`, `make up` for Docker (OrbStack).
Backend tests need Postgres with pgvector on :5432 and a `mf_test` database.

## Rules

- Clean, idiomatic, small: SOLID where it pays, DRY, KISS, YAGNI. No speculative abstractions,
  no base classes or service locators. Plain functions when there is no state.
- Comments explain *why* (exam rules, scoring, pricing choices), never *what*. No docstrings that
  restate a signature.
- Layering: routers → services → DB. `domain/` stays pure and fully unit-tested.
- Every paid call (Azure OpenAI, Speech) goes through `services.metering.run_metered`, which
  reserves against the budget cap first. Never construct a provider client anywhere else.
- Catalogue content is never generated at request time. Generation belongs to the content
  pipeline and must check the media hash / generation cache first.
- Live items are immutable: edits create a new version (handled by `services.content.seed`).
- Exam scales and prices live in versioned YAML under `content/`, never in code.
- Skill bars only use timed, exam-condition evidence. Lesson exercises and module checks never
  feed them.
- French text: accents matter in answer checking; render with `fr()` typography and `lang="fr"`.
- Strict typing both sides (`mypy --strict`, `tsc --strict`); ruff/eslint/prettier clean.
- Schema changes only through Alembic migrations (autogenerate, then review).
