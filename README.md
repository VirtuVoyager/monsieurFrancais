# Monsieur Français

An exam-first French app for **TCF Canada** (target NCLC 7), taking one learner from A1 to C2.
Read the [implementation plan and roadmap](docs/PLAN.md) for the why; [CLAUDE.md](CLAUDE.md)
has the layout and coding rules.

## Run it (OrbStack or any Docker)

```bash
cp .env.example .env        # optional until Azure is connected
make up                     # db + api + web on http://localhost:3000
make obs                    # same, plus Grafana (logs, traces, metrics) on http://localhost:3001
```

The first visit asks you to choose a passphrase. `MF_PROVIDERS=fake` (the default) never calls a
paid service: grading uses a deterministic stand-in and listening uses the browser's voice.

## Develop

```bash
make dev-api                # needs Postgres 16 with pgvector on :5432
make dev-web
make check                  # lint + types + unit tests, both sides
make e2e                    # browser tests against a freshly seeded database
make gen-api                # after any API schema change
```

## Use your data from Claude (MCP)

`make mcp` runs a read-only MCP server over stdio with `search_kb`, `get_skill_levels`,
`get_error_fingerprint` and `get_progress`. For Claude Desktop, add to
`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "monsieur-francais": {
      "command": "uv",
      "args": ["--directory", "/path/to/monsieurFrancais/api", "run", "python", "-m", "app.mcp_server"],
      "env": { "MF_DATABASE_URL": "postgresql+psycopg://mf:mf@localhost:5432/mf" }
    }
  }
}
```
