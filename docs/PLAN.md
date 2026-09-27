# Monsieur Français — Build Plan

An app that takes you from A1 to C2, built around TCF Canada (target: NCLC 7 in all four skills).
The French taught is the grammatically accurate, exam-register kind, not travel phrases.

## 1. Product principles

1. **Modules, not streaks.** Learning follows an ordered path from A1 to C2. There's no XP, no streaks, no quests, no badges.
2. **Only two kinds of progress bars.**
   - **Module coverage:** how much of the curriculum you have completed.
   - **Skill level:** one bar each for listening (CO), reading (CE), writing (EE) and speaking (EO). Each shows how well you perform that skill *under exam timing and pressure*.
3. **Skill bars are earned only under exam conditions.** Practice is for learning. Timed, unseen, exam-format work is what measures you. The two are never mixed.
4. **Your weakest skill sets your level,** as it does for IRCC. The app always shows which skill is holding you back.
5. **Accuracy is scored on its own.** Writing and speaking are graded on the TCF rubric. Feedback gives the top 2–3 fixes, then you rewrite.
6. **Listening, speaking and writing get extra time,** because they are the hardest sections. Every module gives them roughly 70% of its activity time.

## 2. Curriculum: levels → blocks → modules

```
Level (CEFR)  A1 ─ A2 ─ B1 ─ B2 ─ C1 ─ C2
Block         2 per level, each 4 modules          → Checkpoint after every block
Module        8 per level, ~6–8 h of study each    → Module check at the end
```

- **48 modules** in total. A1–B2 (32 modules) are built first; C1–C2 follow once the target level is within reach.
- Each **module** has a theme from the recurring exam topics (housing, work, health, environment, technology, education, immigration, culture…). It contains:
  - **Grammar:** 1–2 concepts, following the sequence pronouns → articles/nouns → adjectives → verbs/negation/questions → tenses → conditional/subjunctive at A1–B1, then B2+ structures (concordance des temps, participle agreement, relative pronouns *dont/lequel*, connectors, nominalisation).
  - **Vocabulary:** 40–60 words by theme, gender colour-coded, drilled English → French and spoken aloud.
  - **Sentence bank:** 20–30 model sentences in exam register.
  - **Skill lessons:** listening (dictation, gist and detail), reading, writing (the right task type for the level) and speaking (shadowing, answer bank, roleplay).
  - **Module check:** a short test of the module's own content.
- **Templates** (openers, connectors, question frames, opinion scaffold) are introduced at the level where the exam first needs them. Task 1 answer bank from A2, Task 2 question frames from B1, Task 3 debate scaffold from B1+.

## 3. Progress bar 1: module coverage

It is deliberately simple: it measures what you have done, not how good you are.

- A module is **covered** when all of its lessons are done **and** its module check is passed (≥ 80%).
- Coverage = covered modules ÷ total modules. It shows overall and per level, as one bar with level segments.
- Modules you skip by passing the placement test or a level exam count as covered and are marked *placed*.
- Spaced-repetition reviews of a module's vocabulary and sentences continue after it's covered. They don't change coverage.

## 4. Progress bar 2: skill level (one per skill)

This is the important one. It answers: *"If I sat the exam today, where would each skill land?"*

### 4.1 What counts as evidence

| Source | Counts? | Weight | Why |
|---|---|---|---|
| Lesson exercises, module checks | **No** | — | Untimed, hints and retries allowed, content you just studied. They measure short-term learning, not skill. |
| **Timed drills** (exam-conditions mode, unseen items, no hints, single play) | Yes | 0.5 | Real exam conditions, but short and self-chosen. |
| **Block checkpoints** (every 4 modules) | Yes | 1.0 | Timed, all four skills, includes items above your current level. |
| **Level exams** (every 8 modules) | Yes | 1.0 | Longer and cumulative. |
| **Full mocks** (exact TCF structure) | Yes | 1.0 | The closest thing to the real exam. |

Every piece of evidence loses weight over time, with a **half-life of 21 days**. A skill you haven't tested recently doesn't drop in score. Instead its uncertainty band widens and the bar is marked *stale*, prompting you to take a drill or checkpoint.

### 4.2 Listening and reading: an ability estimate from item difficulty

These sections are multiple choice, so they can be measured precisely.

- Every CO/CE question has a **difficulty**. It starts from the question's authored CEFR level (A1 easiest … C2 hardest), mirroring the TCF's progressive difficulty. It is refined as your answers come in: questions you consistently get right or wrong shift slightly.
- Ability is estimated with a **Rasch model**, the standard one-parameter scoring model from test theory. It uses every counted answer, weighted by recency and source. The result is an ability score plus an uncertainty. This is about 40 lines of numpy in `domain/`, with no framework.
- **Time pressure is part of the score.** Section timers match the exam's pace (TCF CO ≈ 54 s per question, CE ≈ 92 s). An unanswered question when time runs out counts as wrong, and TCF listening audio plays once.
- **Adaptive selection in checkpoints:** about 60% of questions near your current estimate, 20% one level above, and 20% review of earlier modules. This stops the estimate from maxing out at your current level and catches forgetting.
- The ability estimate converts to the **TCF /699 scale** using the official CEFR bands (A1 100–199, A2 200–299, B1 300–399, B2 400–499, C1 500–599, C2 600–699). NCLC is looked up from the listening and reading floors in `exam_scales.yaml` (NCLC 7: CO 458–502, CE 453–498).

### 4.3 Writing and speaking: rubric scores on the TCF /20 scale

- Every counted EE/EO attempt is graded by Claude on the TCF 0–20 scale against four criteria: **task fulfilment, coherence and cohesion, vocabulary range, grammatical accuracy**.
  - Each criterion is graded **separately**, and the grader must quote evidence from your answer for each one.
  - The prompt includes the CEFR descriptors for each band and 2–3 graded example answers, taken from a *golden set* that includes samples your tutor has graded.
  - **Two independent grading passes.** If they disagree by more than 1 point, a third pass runs and the median is taken. This cuts down random swings in the score.
- **Objective signals** are measured directly and given to the grader:
  - Errors per 100 words, from error tagging.
  - Word count against the target, and whether the attempt finished within time.
  - For speaking: speech rate, pause ratio and filled pauses (*euh*), taken from word timestamps. Also Azure's **pronunciation accuracy and fluency** scores for fr-FR/fr-CA.
- **Time is part of the score.** Writing runs on the exam clock with a word counter. Speaking runs on the task's clock, and silences and hesitations are measured.
- The skill estimate is a **recency-weighted mean** of the counted scores, with uncertainty from their spread. It converts to CEFR/NCLC using the TCF bands (/20: 4–5 A2, 6–9 B1, 10–13 B2, 14–15 C1, 16–20 C2; NCLC 7 = 10–11).
- The grader is checked against the golden set in CI (§ 10). A prompt change that shifts the average error by more than 1 point fails the build.

### 4.4 How the bar looks

```
Listening  A1 ──── A2 ──── B1 ────[██████▓▓░]── B2 ──|NCLC 7|── C1 ──── C2
           est. TCF 431 (±22) · NCLC 6 · last assessed 6 days ago
```

- Scale: A1 → C2, with a fixed **NCLC 7 target line**.
- **Solid fill** = your estimate. **Shaded** = the uncertainty band. The bar is dimmed with a *stale* label when the evidence is older than 21 days.
- Below it: estimated exam score, NCLC band, and date of the last counted evidence.
- The lowest of the four bars is highlighted. That's your real level.
- A trend line (click to expand) shows each checkpoint and mock over time.

### 4.5 Cold start

A **placement test** (about 40 min) runs at onboarding. It has adaptive CO/CE questions plus one short EE and one EO task. It sets the first skill estimates and marks modules below your level as *placed*. Since you already work with a tutor, you likely start around A2–B1 rather than A1.

## 5. Assessment cadence

| Assessment | When | Length | Content | Feeds |
|---|---|---|---|---|
| **Module check** | End of every module | 10–15 min | That module's grammar, vocab, a short listening and reading task, one production prompt | Coverage only |
| **Block checkpoint** | After every **4 modules** (mid-level) | 45–60 min | All four skills, timed, exam format scaled to the level, adaptive question selection, ~20% review from earlier blocks | Skill bars |
| **Level exam** | After every **8 modules** (end of level; replaces the 2nd checkpoint) | ~90 min | Cumulative for the level, all four skills, full exam timing per section | Skill bars + gate to the next level |
| **Full TCF mock** | From B1: **monthly**. In the final 4 weeks before your exam date: **weekly** | 2 h 47 | Exact TCF Canada structure: 39 CO, 39 CE, 3 EE tasks, 3 EO tasks | Skill bars + readiness verdict |
| **Timed drill** | Any time, your choice | 5–20 min | One exam task under exam conditions | Skill bars (0.5 weight) |

**Why every 4 modules and not 5:** a level has 8 modules, so 4 splits evenly into a mid-level checkpoint and an end-of-level exam. At 6–8 hours per module, 4 modules are about 3–4 weeks of study, so you get a new reading on all four skills roughly monthly. That's often enough to see progress and catch a lagging skill early. Assessments stay at about 10–15% of total study time, so they don't crowd out learning.

**Which tasks appear at each level** (EE/EO follow what the exam asks at that level):

| Level | CO/CE questions | Writing | Speaking |
|---|---|---|---|
| A1–A2 | A1–B1 difficulty | EE Task 1 (≈60 words) | EO Task 1 (personal interview) |
| B1 | A2–B2 difficulty | EE Tasks 1–2 | EO Tasks 1–2 (information exchange) |
| B2 | B1–C1 difficulty | EE Tasks 1–3 | EO Tasks 1–3 (debate, up to 4.5 min) |
| C1–C2 | B2–C2 difficulty | EE Tasks 1–3, higher bar | EO Tasks 1–3, higher bar |

**Level exam gate:** the next level unlocks when **every skill** reaches the current level's floor in the level exam. If one skill falls short, the app builds a **repair set** for that skill: targeted lessons from the modules where your errors cluster. You can retake just that section after 7 days. The other skills don't wait. You can keep practising them in the next level's free drills, but new modules stay locked. This is how the real exam works: one weak skill caps the whole result.

**After every checkpoint, exam and mock** you get:
- A score table per skill.
- The change since the last assessment.
- Your top 3 recurring errors.
- One suggested adjustment.
- From B1 onwards, a verdict: *on track / at risk / off track* against your exam date.

## 6. Keeping you coming back, without gamification

- **"Continue" is always one tap:** the home screen shows the next lesson in your current module and any vocab reviews that are due. No feed, no clutter.
- **Short, finishable lessons** (10–20 min), so any session ends with something completed.
- **Feedback worth coming back for:** precise rubric scores, your own sentences corrected, audio of your speaking attempt next to the model answer.
- **Real progress shown honestly:** the skill bars move only when your skill really moves, and that's the motivation.
- **Polished, calm UI:** good typography, smooth transitions, dark mode, fast. It should feel like a quality study tool, not a game.

## 7. Feature map

| Area | What you get |
|---|---|
| **Path** | Levels, blocks and modules on one screen; coverage bar; next lesson. |
| **Module** | Grammar → vocab → sentences → skill lessons → module check. |
| **Assessments** | Checkpoints, level exams, full mocks, placement. All run in the same `ExamShell`: timers, single-play audio, locked navigation, no hints. |
| **Timed drills** | Pick a skill and task type; runs under exam conditions and counts at half weight. |
| **Speaking studio** | Live voice conversation with an AI examiner (Task 2 roleplays, Task 3 debate follow-ups). Task 1 answer bank with a shadowing loop. After each session: rubric score, transcript with errors marked, pronunciation feedback. |
| **Listening lab** | France and Québec voices; dictation; shadowing. The pre-listening transcript skim is available in practice only, never in timed work. |
| **Writing desk** | Exam-clock editor with word count. Templates are visible in practice and hidden in assessments. Your top-5 recurring errors appear as a proofread checklist before you submit. |
| **Library** | Everything learned: **words** (with gender), **sentences**, **grammar concepts**, **templates**, **your errors**. Searchable, with spaced-repetition review on demand. |
| **Notes inbox** | Point it at your Obsidian vault's tutor-notes folder (read-only). New day notes are extracted into words, sentences and grammar points, shown for your approval, then added to the Library. |
| **Progress** | The two progress bars, assessment history, trends. Nothing else. |

## 8. Cloud and models: one provider, Microsoft Azure

### 8.1 What the app needs from AI services

1. A strong **text model** for rubric grading, error tagging, feedback, content generation and notes extraction. It must output strict JSON and judge French grammar carefully.
2. A **speech-to-speech realtime model** for the live examiner, in French, with low latency.
3. **Speech-to-text** with word timestamps (fr-FR, fr-CA), to get speaking transcripts and fluency signals.
4. **Pronunciation assessment** in French.
5. **Neural text-to-speech** with France **and Québec** voices, to produce listening audio.

### 8.2 Comparison

| Need | Azure (Microsoft Foundry + Azure Speech) | Google Cloud (Vertex AI) | AWS (Bedrock) |
|---|---|---|---|
| Claude for grading | **Yes:** Claude Opus 5 / Opus 5.5 / Sonnet 5, "Hosted on Azure", billed on the Azure invoice | Yes | Yes |
| Realtime speech-to-speech in French | **gpt-realtime** (Azure OpenAI in Foundry) | Gemini Live native audio | Nova Sonic (French added 2025) |
| STT with word timestamps, fr-FR + fr-CA | Yes | Yes | Yes |
| **Pronunciation assessment in French** | **Yes** (fr-FR, fr-CA: accuracy, fluency, completeness; prosody and content scoring are English-only) | No equivalent | No equivalent |
| Québec TTS voices | Several fr-CA neural voices | Some fr-CA voices | Few fr-CA voices |

**Decision: Azure.** It is the only one of the three that covers all five needs on one bill, including French pronunciation assessment and both Claude and a realtime speech model.

### 8.3 Model choices

| Job | Model / service | Notes |
|---|---|---|
| Grading, feedback, error tagging, content generation and validation, notes extraction | **Claude Opus 5** (`claude-opus-5`), Foundry deployment, Hosted on Azure, Global Standard | Best judgment on French grammar and rubrics, reliable structured outputs. Before phase 2 ships, run the golden-set eval against **Opus 5.5** (cheaper per token, also Hosted on Azure) and **Sonnet 5**, and pick the cheapest one that matches Opus 5's accuracy. That's your call once the numbers are in. |
| Live examiner | **gpt-realtime** (latest version in the Foundry catalog at build time), WebRTC from the browser with a short-lived token | Plays the examiner only. It never grades. |
| Transcripts and fluency signals | **Azure Speech STT** (fr-FR / fr-CA) with word-level timestamps | Also used for dictation checks. |
| Pronunciation | **Azure Speech pronunciation assessment** (fr-FR / fr-CA) | Feeds the speaking rubric and shadowing feedback. |
| Listening audio | **Azure neural TTS**, France and Québec voices, SSML for speed and pauses | Generated once and cached, so assessments replay identically. |

**Foundry constraints to design around:**
- No server-side refusal fallback: use the SDK's client-side fallback pattern.
- No Message Batches API: content generation runs as background jobs making ordinary calls.
- No Files API on Azure-hosted deployments: send content inline.

The Anthropic Python SDK connects with `AnthropicFoundry(resource=…)`, so the grading code stays standard Claude SDK code.

## 9. Architecture

```
 Browser (Next.js PWA)
   │  REST/JSON + SSE              WebRTC audio (short-lived token)
   ▼                                        ▼
 FastAPI backend ───────────────────►  Azure OpenAI gpt-realtime (examiner)
   │
   ├── Microsoft Foundry: Claude (grading, feedback, content, notes)
   ├── Azure Speech (STT, pronunciation assessment, TTS)
   ├── Postgres 16 + pgvector (local, Docker)
   ├── ./media (cached TTS audio, your recordings)
   ├── Obsidian vault folder (read-only notes source)
   └── MCP server (your learning data, for Claude Desktop / claude.ai)
```

| Layer | Choice |
|---|---|
| Frontend | Next.js (App Router) + TypeScript + Tailwind + shadcn/ui + Framer Motion, TanStack Query, type-safe client generated from the API's OpenAPI spec. UI only, no business logic. |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic, `uv`. |
| DB | Postgres 16 + pgvector (dedupe notes, find similar errors). |
| Scoring | Rasch ability estimate for listening and reading, recency-weighted rubric aggregate for writing and speaking. Pure functions in `domain/`. |
| Spaced repetition | FSRS (`fsrs` package) for Library reviews. |
| Runtime | Docker Compose on this machine: `db`, `api`, `web`. Single user, so no auth beyond a local passphrase. |

### 9.1 Agentic or not?

**Mostly not.** The path, coverage, scoring and scheduling are deterministic code. The AI is used only where judgment is needed, and each use is a **single structured-output call**: `grade_writing`, `grade_speaking`, `tag_errors`, `extract_from_notes`, `generate_items` + `validate_items`.

- **LangGraph (phase 3), two flows only:**
  - **Repair-set builder** after a failed level-exam section: read the error clusters → pick modules and lessons → generate targeted items → pause for your review.
  - **Content pipeline:** generate → validate → dedupe → review → publish.
  Both benefit from saving state in Postgres and pausing for approval. Nothing else does.
- **DeepAgents: no.** Nothing here is a long, open-ended planning task.
- **A2A: no.** There's one app and no outside agents to talk to.
- **MCP: yes, one small server.** It exposes `search_library`, `get_skill_levels`, `get_error_fingerprint`, `add_note_items`. Your TEF/TCF skill and notes chat in Claude can then read and write the same data the app uses. It's about 150 lines with FastMCP.

## 10. Data model (first cut)

```
levels(id, cefr, order)
blocks(id, level_id, order)
modules(id, block_id, order, slug, theme, title, summary)
lessons(id, module_id, order, kind: grammar|vocab|sentences|listening|reading|writing|speaking, payload jsonb)
concepts(id, module_id, slug, title, body_md)
lexemes(id, module_id, lemma, pos, gender, en, example_fr, example_en, audio_path)
sentences(id, module_id, fr, en, audio_path)
templates(id, task, kind, text_fr, text_en, introduced_at_level)

items(id, skill: CO|CE|EE|EO, task, cefr, difficulty, payload jsonb, answer jsonb, audio_path, status: draft|live)
assessments(id, kind: module_check|checkpoint|level_exam|mock|placement|drill, scope_id, structure jsonb)
assessment_runs(id, assessment_id, started_at, finished_at, result jsonb, verdict)
responses(id, run_id, item_id, skill, answer jsonb, correct?, rubric jsonb?, time_ms, timed_out)
recordings(id, response_id, audio_path, transcript jsonb, pronunciation jsonb)

module_progress(module_id, lessons_done, check_score, status: locked|open|covered|placed, covered_at)
skill_estimates(id, skill, theta?, score, se, cefr, nclc, evidence_count, computed_at)   -- history, one row per recompute
error_tags(id, tag, example, count, last_seen)
cards(id, item_type, item_id, fsrs_state jsonb, due_at)
notes(id, source_path, taken_on, raw_md, extracted jsonb, status)
```

Exam formats, timings and score conversion tables live in versioned `content/exam_scales.yaml` with a "verified as of" date. They never live in code.

## 11. Repository layout

```
api/
  app/
    main.py  config.py  db.py
    domain/        # pure: rasch.py, skill_estimate.py, coverage.py, scales.py, fsrs wrapper
    models/        # SQLAlchemy
    schemas/       # Pydantic I/O
    repositories/  # DB access only
    services/      # path, lessons, assessments, grading, library, notes, voice tokens
    llm/           # Foundry client, prompts/, output schemas, golden-set runner
    speech/        # Azure STT, pronunciation, TTS
    voice/         # realtime token minting
    routers/       # thin FastAPI routes
    mcp/           # MCP server
  migrations/
  tests/
web/
  app/             # path, module/[slug], assess/[id], drill, speak, listen, write, library, progress
  components/      # ui (shadcn), exam (ExamShell, Timer, Mcq, Recorder, WordCounter), progress (CoverageBar, SkillBar)
  lib/             # generated API client, hooks, audio utils
content/
  modules/<level>/<nn-slug>/   # module.yaml, concepts/*.md, vocab.csv, sentences.csv
  templates/*.yaml
  exam_scales.yaml
  golden/                      # graded writing and speaking samples for grader evals
docker-compose.yml
CLAUDE.md
```

## 12. Code quality rules

These go into `CLAUDE.md` and are enforced by tooling:

- **Python:** `ruff` (lint + format), `mypy --strict`, `pytest`. **TypeScript:** `eslint` + `prettier`, `tsc --strict`, `vitest`, `playwright` for the critical flows (lesson → module check, full checkpoint). All run in `pre-commit` and GitHub Actions.
- **Layering:** routers → services → repositories. `domain/` is pure and has no I/O. Routes contain no SQL and services contain no HTTP.
- **SOLID where it pays:** small interfaces only where a second implementation or a test fake exists (`Grader`, `SpeechService`, `RealtimeTokenIssuer`). No speculative abstractions.
- **DRY:** one rubric schema for writing and speaking, one `ExamShell` for every timed experience, one generated API client.
- **KISS:** plain functions over classes when there's no state. No base repositories, no event bus, no service locator.
- **Comments** explain *why* only (exam rules, scoring choices). No docstrings that restate the signature.
- **Grader evals as tests:** `content/golden/` samples are scored in CI, and the build fails if the grader's average error rises above 1 point on the /20 scale.
- Small PRs, conventional commits.

## 13. Delivery phases

| Phase | Scope | Done when |
|---|---|---|
| **0. Foundations** (~1 wk) | Skeleton, Docker Compose, Postgres + migrations, FastAPI health, Next.js shell and design system, CI, `CLAUDE.md`, Azure resources (Foundry, Speech). | `docker compose up` shows the shell; CI green; a Foundry Claude call and an Azure TTS call work. |
| **1. Path + modules + coverage** (~2–3 wks) | Level/block/module model, lesson player, module checks, coverage bar, Library + FSRS, content for A1–A2 (16 modules). | You can work through A2 modules and see coverage move. |
| **2. Assessment engine + receptive skills** (~3 wks) | `ExamShell`, question bank with difficulty, Rasch estimator, CO/CE skill bars, placement test, block checkpoints (CO/CE parts), TTS listening audio. **Grader spike + golden set + model comparison.** | Placement sets real CO/CE estimates; a checkpoint moves the bars. |
| **3. Writing + speaking** (~3–4 wks) | Writing desk + rubric grading (two passes), error tagging; realtime examiner; STT + pronunciation; EE/EO skill bars; level exams + gate + repair sets (LangGraph); Notes inbox from Obsidian; MCP server. | A full level exam with all four skills produces four skill bars and a gate decision. |
| **4. Mocks + B1–B2 content + polish** (~3 wks) | Full TCF mocks, verdicts, monthly/weekly cadence tied to exam date, B1–B2 content (16 modules), performance and accessibility pass, PWA install. | A full 2 h 47 mock end-to-end, scored against NCLC 7. |
| **5. C1–C2** (later) | Remaining 16 modules and higher-level question bank. | Complete A1–C2 path. |

## 14. Content strategy

- All questions and texts are **original, written in exam format**. Nothing is copied from *Réussir le TCF* or paid mock banks.
- Each generated item goes through a validation pass (grammar, single correct answer, CEFR level fit, difficulty estimate). It stays in `draft` until you approve it (one click).
- Grammar pages and module outlines live as markdown/YAML in `content/`, reviewed by you and optionally your tutor.
- Your tutor's graded corrections go into `content/golden/`. This is what keeps the writing and speaking bars honest.

## 15. Risks

| Risk | Mitigation |
|---|---|
| Writing/speaking scores drift from real examiners | Golden set with tutor-graded samples, two grading passes, CI check on error; show uncertainty bands, not single points. |
| Listening/reading difficulty estimates are rough with one user | Start difficulty from authored CEFR levels (a strong prior); refine only after enough answers; widen uncertainty when evidence is thin; cross-check against full mocks. |
| Realtime voice latency or cost | Browser connects directly over WebRTC; sessions capped at task length; cost logged per session. |
| Wrong French in generated content | Generate-then-validate, draft/approve gate, tutor spot checks. |
| Exam format changes | Everything in versioned `exam_scales.yaml`. |

## 16. Decided

- **Exam:** TCF Canada (TEF support can be added later by adding its scales and structure).
- **Obsidian:** read-only notes source only.
- **Cloud:** Microsoft Azure only (Foundry for Claude and gpt-realtime; Azure Speech).
- **Users:** single user; local passphrase, no accounts.
- **No gamification:** no XP, streaks, quests or badges. Two progress bar types only.
