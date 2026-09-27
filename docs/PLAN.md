# Monsieur Français — Build Plan

An exam-first French app for TEF Canada / TCF Canada (target: NCLC 7 in all four skills).
It is not a travel-phrase app. Every screen should earn exam points.

## 1. Product principles

1. **The exam is the curriculum.** Content is ordered by the grammar sequence and task types of TCF/TEF, and scored on the real scales (TCF /699 and /20, TEF "Équivalence ancien score").
2. **Your weakest skill decides your level.** IRCC takes the lowest of the four skills, so the app does too. The home screen always leads with your weakest skill.
3. **Listening, speaking and writing get most of the time.** About 70% of each daily session goes to these three skills. Reading and grammar review fill the rest.
4. **Make learners produce French, not just recognise it.** Cards go English → French and you answer out loud. Answering by recognition alone is not the default.
5. **Accuracy is its own score.** Every writing and speaking attempt is graded on four criteria: task fulfilment, coherence, vocabulary range and grammatical accuracy. Feedback shows only the top 2–3 fixes, then you rewrite. No walls of corrections.
6. **Engagement comes from quick wins.** Short sessions, visible progress, streaks and quests keep you coming back. Everything uses these patterns except timed mocks, which have to feel like the real exam.

## 2. Feature map

| Area | What the user gets |
|---|---|
| **Learn** | Grammar concepts in the order the exam strategy uses (pronouns → articles → adjectives → verbs/negation/questions → tenses → conditional/subjunctive). Each concept has a short explanation, examples, common mistakes and a mastery check. |
| **Practice** | Short exercises per concept: fill-in, transform, dictation, error spotting and sentence building. They are spaced-repetition-driven and mixed across concepts. |
| **Drills** | One exam task at a time, timed: CO/CE MCQ sets, EE tasks 1–3 (TCF) or sections A/B (TEF), EO tasks 1–3 (TCF) or 1–2 (TEF). |
| **Mocks** | Full or half mocks in the exact exam structure. Results show a score table per skill, the gap to the NCLC 7 floor, the change since the last mock, and a verdict: *on track / at risk / off track*. |
| **Speaking studio** | Live voice conversation with an AI examiner who plays roles (a landlord, an employer). Includes a Task 1 answer bank with shadowing loops, and a post-session rubric score with a transcript and flagged errors. |
| **Listening lab** | Audio clips in France and Québec accents, dictation, and shadowing mode. Before a practice drill you can skim the transcript first ("priming"); mocks are always cold. Single play enforced in TCF mode. |
| **Writing desk** | Timed editor with a word counter and templates you can open during practice (hidden in mocks). Your personal list of recurring errors appears as a proofread checklist before you submit. |
| **Library (revision)** | Everything you've learned, searchable and filterable: **words** (with gender, colour-coded), **sentences**, **grammar concepts**, **templates**, **errors**. Each item shows its spaced-repetition status and a "review now" button. |
| **Notes inbox** | Paste or sync your day-wise tutor notes. The app pulls out words, sentences and grammar points and adds them to the Library, with a review step before anything is saved. |
| **Progress** | A predicted NCLC band per skill, a readiness ladder, hours logged per phase, and trends from mock to mock. |

## 3. Gamification

Kept simple and pointed at the exam:

- **XP** for completed work, weighted by skill. Listening, speaking and writing earn 1.5× so the effort goes where the exam is hardest.
- **Daily quests** (3 per day), generated from your weakest skill and the spaced-repetition queue. Example: "1 EO Task 2 roleplay, 20 dictation lines, 15 card reviews."
- **Streak**, with one freeze earned per 7-day run.
- **NCLC ladder:** each skill climbs NCLC 4 → 7+. The overall rank is the lowest of the four, which makes the bottleneck visible.
- **Achievements** tied to real milestones: "First 250-word EE3", "10 EO3 attempts past 4 min", "Mock verdict: on track".
- **Boss fights:** a weekly half-mock unlocks after the week's quests are done.
- No leagues or social features in v1. It's a single-user app first.

## 4. Architecture

```
 Browser (Next.js PWA)
   │  REST/JSON + SSE           WebRTC (audio, ephemeral token)
   ▼                                   ▼
 FastAPI backend  ─────────────►  Realtime voice model (speech-to-speech)
   │  services / domain
   ├── Claude API (grading, feedback, content generation, notes extraction)
   ├── TTS / STT (listening audio, transcripts)
   ├── Postgres 16 + pgvector (local)
   ├── Local media store (./media, generated audio)
   └── MCP server (learner data for Claude Desktop / claude.ai)
```

### 4.1 Stack decisions

| Layer | Choice | Why |
|---|---|---|
| Frontend | **Next.js (App Router) + TypeScript + Tailwind + shadcn/ui + Framer Motion**, TanStack Query | A polished component base out of the box, smooth motion for the game feel, and a PWA installs on phone and desktop. Next.js serves the UI only; no business logic lives there. |
| Backend | **Python 3.12 + FastAPI**, Pydantic v2, SQLAlchemy 2 + Alembic, `uv` | Python has the best tooling for LLMs, audio and LangGraph. FastAPI gives typed APIs and generated OpenAPI docs, which the frontend uses to generate a type-safe client. |
| DB | **Postgres 16 + pgvector** (local) | One store for relational data, spaced-repetition state and semantic search (dedupe notes, find similar errors). |
| Spaced repetition | **FSRS** (`fsrs` package) | The current best scheduler, and simpler than hand-rolled SM-2. |
| Text LLM | **Claude (`claude-opus-5`)** with structured outputs and server-side refusal fallbacks enabled | Rubric grading, error explanations, exercise generation and notes extraction all need strict JSON and careful French grammar judgment. Running bulk content generation on a cheaper model is your call later (cost vs quality). |
| Voice-to-voice | **OpenAI Realtime API over WebRTC**, behind a `VoiceProvider` interface (Gemini Live as the alternative) | Claude's API has no speech-to-speech endpoint. Live examiner roleplay needs a native realtime speech model for low latency and natural turn-taking. The browser connects directly using a short-lived token minted by the backend, so audio never passes through our server. |
| Speaking grading | Session transcript + audio → **STT** → **Claude rubric grader** | Keeping the conversation model separate from the grader means the examiner stays in character and the scoring stays strict. |
| Pronunciation (optional, phase 4) | Azure Speech pronunciation assessment (`fr-FR`) | Scores each phoneme and word; use it for shadowing feedback. |
| TTS for listening | A realtime-provider or Azure neural voice, with France and Québec voices; audio pre-generated and cached | Mocks need consistent audio that can be replayed exactly, not audio generated on the fly. |
| Runtime | **Docker Compose** (`db`, `api`, `web`) on this machine | One command to start everything locally. |

### 4.2 Agentic or not?

**Mostly not.** Most of the app is deterministic: scheduling, scoring conversion, XP, quests, the Library. Those are plain services. An LLM is used only where judgment is needed, and each of those uses is a **single structured-output call**:

- `grade_writing(task, text) → RubricScore + top fixes + error tags`
- `grade_speaking(task, transcript) → RubricScore + top fixes + error tags`
- `extract_from_notes(markdown) → words / sentences / grammar points`
- `generate_items(concept | task, n) → exercises`, followed by a second validation call that rejects items with bad grammar or ambiguous answers

**LangGraph comes in phase 3, for exactly two stateful flows:**

1. **Coach:** a weekly plan and a post-mock review. It reads mock history and your error list, proposes the next week's quest mix, and pauses for your approval. The Postgres checkpointer and pause-for-approval support earn their keep here.
2. **Content pipeline:** generate → validate → dedupe (pgvector) → human review → publish, with the review step as a pause.

**DeepAgents: not now.** It's built for long, open-ended tasks with planning and a filesystem. Nothing here needs that in v1. Revisit only if the Coach grows into a multi-week planner that uses tools across many sources.

**A2A: no.** There's one app and one team of agents, with nothing to talk to across organisations. It would add cost and no value.

**MCP: yes, one small server (phase 3).** It exposes `search_library`, `add_vocab`, `get_error_fingerprint`, `log_tutor_note` and `get_progress` over your Postgres data. This lets your existing TEF/TCF skill and your notes chat in Claude read and write the same learner data the app uses. It's cheap to build (FastMCP, about 150 lines) and ties the app into the way you already study.

## 5. Data model (first cut)

```
users(id, exam: TCF|TEF, target_date, daily_minutes, created_at)
concepts(id, slug, phase, order, title, body_md, level)
lexemes(id, lemma, pos, gender, en, example_fr, example_en, audio_path)
sentences(id, fr, en, concept_id?, source, audio_path)
templates(id, exam, task, kind: opener|connector|closer|frame, text_fr, text_en)
exercises(id, kind, concept_id?, payload jsonb, answer jsonb, status: draft|live)
drills(id, exam, section, task, payload jsonb, timing_s)   -- one exam task item
mocks(id, exam, structure jsonb)

cards(id, user_id, item_type, item_id, direction, fsrs_state jsonb, due_at)
attempts(id, user_id, target_type, target_id, response jsonb, score jsonb, duration_s, created_at)
speaking_sessions(id, user_id, drill_id, transcript jsonb, audio_path, rubric jsonb)
writing_submissions(id, user_id, drill_id, text, word_count, rubric jsonb, rewrite_of?)
mock_results(id, user_id, mock_id, per_skill jsonb, verdict, created_at)
error_tags(id, user_id, tag, example, count, last_seen)   -- personal error list; top 5 shown
notes(id, user_id, taken_on, raw_md, extracted jsonb, status)

xp_events(id, user_id, source, amount, created_at)
streaks(user_id, current, longest, freezes, last_active_on)
quests(id, user_id, day, spec jsonb, progress jsonb, done_at)
achievements(id, code, title), user_achievements(user_id, achievement_id, earned_at)
```

Score-to-NCLC conversion tables live in versioned config (`exam_scales.yaml`) with a "verified as of" date, never in code.

## 6. Repository layout

```
api/
  app/
    main.py
    config.py
    db.py
    domain/          # pure logic: fsrs wrapper, nclc mapping, xp, quests, streaks
    models/          # SQLAlchemy models
    schemas/         # Pydantic I/O
    repositories/    # DB access only
    services/        # use cases: grading, library, drills, notes, voice tokens
    llm/             # Claude client, prompts, structured output schemas
    voice/           # VoiceProvider protocol + openai_realtime impl
    routers/         # thin FastAPI routes
    mcp/             # MCP server (phase 3)
  migrations/
  tests/
web/
  app/               # routes: (home) learn practice drills mocks speak listen write library progress
  components/        # ui (shadcn), game (xp, streak, quest), exam (timer, mcq, recorder)
  lib/               # api client (generated), hooks, audio utils
content/
  concepts/*.md      # grammar concepts as reviewed markdown, seeded into DB
  templates/*.yaml
  exam_scales.yaml
docker-compose.yml
CLAUDE.md            # coding rules for agents working in this repo
```

## 7. Code quality rules

These go into `CLAUDE.md` and are enforced by tooling:

- **Python:** `ruff` (lint + format), `mypy --strict`, `pytest`. **TS:** `eslint` + `prettier`, `tsc --strict`, `vitest`, `playwright` for 3–4 critical flows. All run in `pre-commit` and CI (GitHub Actions).
- **Layering:** routers → services → repositories. Domain logic stays pure and free of I/O, so it's trivially testable. Routes contain no SQL and services contain no HTTP.
- **SOLID where it pays:** `VoiceProvider`, `TtsProvider` and `LlmGrader` are small interfaces because they genuinely have more than one implementation (or a test fake). Nothing else gets an abstraction until a second use exists (YAGNI).
- **DRY:** one rubric schema shared by writing and speaking. One `Timer`/`ExamShell` component shared by all drills and mocks. The OpenAPI-generated client removes hand-written fetch code.
- **KISS:** no repository base classes, service locators or event buses. Plain functions over classes when there's no state.
- **Comments** only explain *why* (for example, exam rules). Names carry the *what*. No docstrings that just restate a signature.
- **Prompts** live as versioned files under `llm/prompts/`, with a small golden set per grader (real graded samples) run as tests, so prompt changes can't silently regress scoring.
- Small PRs, conventional commits, one feature per branch.

## 8. Delivery phases

| Phase | Scope | Done when |
|---|---|---|
| **0. Foundations** (≈1 wk) | Repo skeleton, Docker Compose, Postgres + migrations, FastAPI health, Next.js shell with design system (theme, typography, dark mode), CI, `CLAUDE.md`. | `docker compose up` shows the app shell; CI green. |
| **1. Learn + Library + SRS** (≈2 wks) | Grammar concepts (seed the 6 blocks), exercises, FSRS cards (production direction), Library with words/sentences/concepts/errors, XP + streak + daily quests. | You can study a concept, review cards daily and browse everything learned. |
| **2. Writing + Listening** (≈2–3 wks) | Writing desk with EE tasks, Claude rubric grading, top-3 fixes, rewrite loop, error list. Listening lab with TTS audio, MCQ drills, dictation, shadowing. Notes inbox (paste markdown → extract → review → Library). | A writing submission gets an exam-scale score and fixes; listening drills run timed with single play. |
| **3. Speaking + Coach + MCP** (≈3 wks) | Realtime examiner (EO tasks, roleplays), recording, transcript, rubric grading. Task 1 answer bank with shadowing loop. LangGraph Coach (weekly plan + post-mock review). MCP server. | A full EO3 debate with the AI examiner, graded afterwards; Claude Desktop can query your Library. |
| **4. Mocks + polish** (≈2 wks) | Full/half mocks in exact structure for your exam, verdicts, predicted NCLC, achievements, boss fights, pronunciation scoring, PWA install, performance pass. | A full mock end-to-end with a per-skill scoring table and verdict. |

Build order follows the risk: grading quality and voice latency are the hardest parts, so each gets a spike (1–2 days) at the start of its phase before any UI work.

## 9. Content strategy

- Items are **original, generated in the exam format**. No copying from *Réussir le TCF/TEF* or paid mock banks. Your own practice with those books stays outside the app, and the results come in through the Notes inbox.
- Every generated item passes a validation call (grammar, one correct answer, level fit) and sits in `draft` until approved. Approval is one click in an admin view.
- Grammar concept pages are written once, reviewed (by you, and optionally your tutor), and stored as markdown in `content/`.

## 10. Risks

| Risk | Mitigation |
|---|---|
| LLM scores drift from real examiner scores | Golden set of tutor-graded samples; compare after every prompt change; show scores as a band, not a single point. |
| Voice latency or cost | Browser connects directly over WebRTC; cap session length at exam length; track token/minute use per session. |
| Wrong French in generated content | Two-pass generation + validation, draft/review gate, tutor spot checks. |
| Exam format changes | Formats and scales are in versioned config with "verified as of" dates. |
| Scope creep | Phases ship usable slices; leagues, social features and multi-user stay out until after phase 4. |

## 11. Open decisions

1. **Hosting / "Obsidian":** Obsidian is a notes app, not a server. The plan assumes the app runs on this machine via Docker Compose, and that your Obsidian vault is a **notes source**: the Notes inbox syncs a vault folder of day-wise notes as Markdown. Confirm or correct.
2. **Exam:** TCF Canada or TEF Canada? The default is TCF unless your speaking/writing scores swing by more than a band between attempts. Both will be supported; the choice sets the default mock structure and scales.
3. **API budget:** which providers you're willing to pay for: Anthropic for grading and content, OpenAI or Google for realtime voice, and optionally Azure for pronunciation.
4. **Users:** just you for now, or a small group (tutor access, friends)? This affects auth (none/local vs. magic-link).
