# Monsieur Français — web

Next.js (App Router) front end. It is UI only: every request goes to the FastAPI backend through
the `/api/*` rewrite in `next.config.ts` (`API_URL`, default `http://localhost:8000`).

```bash
pnpm install
pnpm dev            # http://localhost:3000, backend must be running
pnpm gen:api        # regenerate lib/api/schema.d.ts after backend schema changes
pnpm lint && pnpm typecheck && pnpm test
pnpm e2e            # needs a freshly seeded database; see `make e2e` at the repo root
```
