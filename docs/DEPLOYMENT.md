# Monsieur Français — Deployment Plan

How the app goes from one learner on a laptop to a hosted app that a tutor (and later other
examiners or learners) can use, without anyone but the owner spending money. Status: **planned,
not started.** Read with [PLAN.md](PLAN.md) §§ 9, 11 and 17.5.

## 1. What costs money at runtime

Everything is free except work that depends on one learner's own output.

| Feature | Paid call | Who gets it |
|---|---|---|
| Live speaking examiner | gpt-realtime-mini | Owner; others only if granted, with a cap |
| Speaking transcription and grading | Azure STT + gpt-5.4-mini | Owner; otherwise saved ungraded for a human examiner |
| Writing grading | gpt-5.4-mini (two passes) | Same as speaking |
| Notes: extraction, glossary, word audio | gpt-5.4-mini + TTS | Owner only |
| Semantic search | One embedding per query (tiny) | Everyone; keyword-only fallback when a user has no budget |

Free for everyone, from the pre-generated catalogue: lessons, exercises (checked in code), listening
and reading drills and mocks with stored audio, reviews, Library, hover glossary.

**Enforcement already exists:** every paid call goes through `run_metered`, which refuses once the
user's cap is reached, so a user with caps of 0 cannot spend. What is missing is entitlements (so
the UI hides what the user can't use) and an app-wide ceiling as a second net.

## 2. Multi-user foundation (prerequisite)

Today `services.users.get_or_create_learner` ("the first user") is used in `routers/auth.py`,
`mcp_server.py`, the `build_glossaries`, `generate_audio` and `embed_pending` jobs and the
scheduler's `_embed`. Anyone who logged in would become the owner.

- **Roles:** `owner` (everything), `examiner` (content review, grading, later authoring),
  `learner` (free features unless granted more).
- **Invite-only accounts:** the owner creates an invite link, the invitee sets a passphrase.
  No public sign-up.
- **Entitlements** on the user (`speaking`, `ai_grading`, `notes`), checked in services, not only
  hidden in the UI. Paid features default to off and caps to 0.
- **App-wide monthly ceiling**, checked by `run_metered` alongside the user's caps.
- **Notes are owner-only** at the router and the job level.
- **Jobs iterate users** instead of taking the first one. The scheduler runs as a single
  replica guarded by a Postgres advisory lock, so a job never runs twice.

## 3. Media in Azure Blob Storage

Media sits on local disk under `media/`, which does not survive container restarts.

- **`MediaStore` protocol** (`put`, `get`, `url`, `exists`) with two implementations: local disk
  (dev, tests, CI) and Azure Blob (hosted). The audio, speaking and notes services call it instead
  of touching paths. Keys stay the same, so content addressing and the manifest are unchanged.
- **Two containers:**
  - `catalog`: content-addressed audio. Public-read behind a CDN; immutable and holds nothing
    personal.
  - `users`: speaking recordings and note uploads. Private; served through the API (owner check)
    or short-lived SAS links. Voice recordings are personal data.
- **Access by managed identity**, never a storage key.
- **One-time sync:** `azcopy` the catalogue and note audio already generated locally.
  `content/media_manifest.csv` stays in git as the record of what exists.

## 4. Tutor review (first features for the tutor)

1. **Flag or comment on any item** (lesson, exercise, mock question): "wrong answer", "unnatural
   French", "wrong level", plus a note. The owner gets a queue; fixes go through the existing item
   versioning (`services.content.seed`).
2. **Human grading queue:** the examiner sees the owner's writing and speaking submissions
   (recording + transcript) and scores them on the same rubric. Each pair of human and AI scores
   joins the golden set (`content/golden/`), the check that the AI grader stays calibrated.

## 5. Examiner module (tutor-set timed assessments)

- **Copyright:** only the examiner's own material. Official TCF papers belong to France Éducation
  international and are never uploaded.
- **Authoring first:** a structured editor for task, questions, timing and answer key. Then
  import: upload PDF/DOCX → gpt-5.4-mini drafts the structure → the examiner corrects it →
  publish. The draft is an authoring-time call, metered against the examiner's budget and cached
  by file hash, never generated at request time.
- **Listening audio:** the examiner uploads recordings, or gives a script that the content
  pipeline turns into TTS once (hash-cached).
- **Delivery:** assigned to a learner with an availability window, run in `ExamShell` (timing,
  locked navigation, no glossary).
- **Scoring:** CO/CE multiple choice auto-scored (free); EE/EO graded by the examiner, or by AI
  only for learners with `ai_grading`.
- **Skill bars:** tutor tests aren't calibrated to the TCF scale, so results are a separate
  "Tutor assessments" record and do not feed the bars (at most at reduced weight, opt-in).
- **Versioning:** published assessments are immutable; edits create a version, past attempts stay
  valid.

## 6. Hosting on Azure

Same region as the existing Azure OpenAI and Speech resources.

| Piece | Choice |
|---|---|
| API, web | Azure Container Apps (web may scale to zero; API min 1 replica) |
| Scheduler | Container Apps scheduled jobs, or one always-on replica with the advisory lock |
| Database | Postgres Flexible Server, Burstable B1ms, `vector` extension allow-listed |
| Media | Blob Storage (§ 3) |
| Secrets | Key Vault + managed identity; no keys in env files on servers |
| Build and deploy | GitHub Actions → Azure Container Registry → deploy on merge to `virtuvoyager_dev`; `alembic upgrade head` runs before the new revision takes traffic |
| Domain and TLS | Custom domain with a managed certificate. HTTPS is mandatory: browsers only open the microphone on secure origins |

- **Realtime needs nothing extra:** WebRTC goes browser → Azure directly; the API only mints the
  ephemeral token and records usage.
- **Cheaper alternative:** one small VM with `docker compose` and Caddy for TLS. Fine for a
  tutor-only stage; patching and backups are then manual.
- **Rough fixed cost** (verify in the Azure pricing calculator): Container Apps + Postgres about
  $25–50 per month, Blob about $1. Paid calls on top, bounded by the caps.
- **Safety nets:** Azure budget alert on the resource group, on top of the in-app caps.
- **Backups:** Postgres automated backups with point-in-time restore (7–14 days); soft delete on
  the `users` container.

## 7. Phases

| Phase | Scope | Done when |
|---|---|---|
| **D0. Ready to host** | `MediaStore` (local + Blob), production Dockerfiles, health checks, config cleanup | Runs locally exactly as today, on either store |
| **D1. Multi-user** | Roles, invites, entitlements, caps 0 by default, app-wide ceiling, owner-only notes, jobs per user | A second account can use the free parts and cannot spend |
| **D2. Deploy** | Azure resources, CI/CD, domain, backups, budget alert, media sync, smoke test | The tutor logs in on the hosted app |
| **D3. Tutor review** | Item flags and comments, human grading queue, golden set | The tutor reviews content and grades the owner's work |
| **D4. Examiner module** | Authoring, document import, assignment, timed delivery | A tutor-set test runs end to end |

## 8. Open questions

1. Container Apps or a single VM; which domain.
2. The tutor's role: content review, grading, or setting tests (decides D3 vs D4 priority).
3. Whether other students will use it (stricter privacy and account deletion in D1; the copyright
   rule becomes firm).
4. Whether the tutor's papers are their own material.
