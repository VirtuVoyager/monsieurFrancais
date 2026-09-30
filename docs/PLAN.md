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

- Every counted EE/EO attempt is graded by the GPT grader on the TCF 0–20 scale against four criteria: **task fulfilment, coherence and cohesion, vocabulary range, grammatical accuracy**.
  - Each criterion is graded **separately**, and the grader must quote evidence from your answer for each one.
  - The prompt includes the CEFR descriptors for each band and 2–3 graded example answers, taken from a *golden set* that includes samples your tutor has graded.
  - **Two independent grading passes.** If they disagree by more than 1 point, a third pass runs and the median is taken. This cuts down random swings in the score.
- **Objective signals** are measured directly and given to the grader:
  - Errors per 100 words, from error tagging.
  - Word count against the target, and whether the attempt finished within time.
  - For speaking: speech rate, pause ratio and filled pauses (*euh*), taken from word timestamps. Also Azure's **pronunciation accuracy and fluency** scores for fr-FR/fr-CA.
- **Time is part of the score.** Writing runs on the exam clock with a word counter. Speaking runs on the task's clock, and silences and hesitations are measured.
- The skill estimate is a **recency-weighted mean** of the counted scores, with uncertainty from their spread. It converts to CEFR/NCLC using the TCF bands (/20: 4–5 A2, 6–9 B1, 10–13 B2, 14–15 C1, 16–20 C2; NCLC 7 = 10–11).
- The grader is checked against the golden set in CI (§ 16). A prompt change that shifts the average error by more than 1 point fails the build.

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

### 4.6 Your settings drive the plan

Onboarding and **Settings** hold:
- exam date and target NCLC (default 7)
- study minutes per day and days off
- preferred accent mix for listening (France / Québec)
- timezone (default Asia/Kolkata)

These settings drive:
- the mock cadence (monthly → weekly in the final 4 weeks);
- the *on track / at risk / off track* verdict;
- two reminders from the exam strategy:
  - a **"book by" date**, 8 weeks before the exam, because test centres fill 6–8 weeks ahead;
  - a **retake window**: TCF needs a 30-day gap, so the first sitting should leave room for one retake before your target draw.

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
| **Speaking studio** | Live voice conversation with an AI examiner (Task 2 roleplays, Task 3 debate follow-ups). Task 1 answer bank with a shadowing loop. After each session: rubric score, transcript with errors marked, pronunciation feedback. The examiner speaks only French, keeps to exam register, and answers a switch to English with an in-French repair phrase, never by switching language. |
| **Listening lab** | France and Québec voices; dictation; shadowing. The pre-listening transcript skim is available in practice only, never in timed work. |
| **Writing desk** | Exam-clock editor with word count. Templates are visible in practice and hidden in assessments. Your top-5 recurring errors appear as a proofread checklist before you submit. |
| **Library** | Everything learned: **words** (with gender), **sentences**, **grammar concepts**, **templates**, **your errors**. Searchable, with spaced-repetition review on demand. |
| **Notes inbox** | Point it at your Obsidian vault's tutor-notes folder (read-only). New day notes are extracted into words, sentences and grammar points, shown for your approval, then added to the Library. |
| **Progress** | The two progress bars, assessment history, trends. Nothing else. |
| **Content studio** (settings area) | Review queue for generated items: preview (with audio), approve, reject or edit (creates a new version), bulk-approve by module. Golden-set manager for tutor-graded samples. |
| **Export** (settings area) | Download all your data (JSON/CSV); vocabulary and sentences as an Anki deck. |
| **Budget** (settings area) | Live Azure spend vs your monthly caps, spend per feature, Speech free allowance left, reconciliation with Azure's bill (§ 9). |

## 8. Cloud and models: Azure only, OpenAI GPT models only

### 8.1 What the app needs from AI services

1. A **text model** for rubric grading, error tagging, feedback, content generation and notes extraction. It must output strict JSON.
2. A **speech-to-speech realtime model** for the live examiner, in French, with low latency.
3. **Speech-to-text** with word timestamps (fr-FR, fr-CA), for speaking transcripts and fluency signals.
4. **Pronunciation assessment** in French.
5. **Neural text-to-speech** with France **and Québec** voices, to produce listening audio.

Azure is the only one of the big three clouds that covers all five on one bill. French pronunciation assessment has no equivalent on Google Cloud or AWS.

### 8.2 Model choices (cheapest option that meets the quality bar)

| Job | Default | Escalation | Notes |
|---|---|---|---|
| Grading, error tagging, feedback, notes extraction, content generation and validation | **GPT-5.4 mini** (Azure OpenAI in Foundry, Global Standard) | **GPT-5.4**, only for writing/speaking grading, and only if mini fails the golden-set bar | Responses API with strict JSON schema output. Mini costs roughly 1/3 as much as the full model. The golden-set eval (§ 4.3) decides: if mini's average grading error on the /20 scale stays ≤ 1 point, it stays everywhere. |
| Live examiner | **gpt-realtime-2.1-mini** | gpt-realtime, only if mini's French or role-play quality is noticeably worse in the phase-3 spike | WebRTC audio straight between the browser and Azure; the API exchanges the SDP offer using a short-lived token, so the browser never holds a credential. Mini's audio rates are about 1/3 of the full model's. Plays the examiner only, never grades. |
| Transcripts and fluency signals | **Azure Speech STT** (fr-FR / fr-CA), word timestamps | — | Also used for dictation checks. The browser records Opus/WebM; the API converts it with `ffmpeg` to 16 kHz mono WAV for Speech and keeps the Opus file as your recording. |
| Pronunciation | **Azure Speech pronunciation assessment** (fr-FR / fr-CA) | — | Accuracy, fluency and completeness. Prosody and content scoring are English-only, so grammar and vocabulary come from the GPT grader. |
| Listening audio | **Azure neural TTS**, France and Québec voices, SSML for pace and pauses | — | Generated once and cached, so replays cost nothing. |

Model names and versions move fast. The app reads deployment names from config, and prices from `content/pricing.yaml` (§ 9). Moving to a newer mini model means changing config, not code.

The backend uses the official `openai` Python SDK against the Azure endpoint, with `Grader`, `Examiner` and `SpeechService` as the only abstractions.

### 8.3 Free credits for the build phase

| What | Details | Catch |
|---|---|---|
| **Azure free account** | **US$200 credit for 30 days** plus a set of always-free services | Free-trial subscriptions get **zero quota for Azure OpenAI models**. You have to **upgrade to Pay-As-You-Go** to deploy GPT models. The upgrade keeps the unspent credit for its 30 days, and you pay only for usage beyond it. |
| **Azure Speech free tier (F0)** | **5 audio hours of STT per month** and **0.5 M neural TTS characters per month** (≈ 10 h of audio), **never expires** | One F0 resource per subscription; limits can't be raised. Pronunciation-assessment support on F0 gets checked in the phase-0 spike. On the paid tier it's a +US$0.30/hour add-on for real-time use. |
| **After the credit runs out** | GPT and realtime usage is billed per token; Speech stays free up to the F0 limits | Hard monthly budgets in the app (§ 9) keep this bounded. |

**How to use them:**
1. Create the free account and upgrade to Pay-As-You-Go on day 1, so GPT models can be deployed.
2. Spend the $200 in the first 30 days on the expensive, one-off work:
   - generating and validating the A1–A2 question bank;
   - the grading golden-set comparison (mini vs full);
   - the realtime examiner spike.
3. Keep Speech on **F0 permanently** during the build, and generate TTS audio in batches so it stays under 0.5 M characters a month.
4. Set an Azure-side budget alert as a safety net from day 1 (§ 9.4).

**Rough running cost after the build** (estimates, to be replaced by real metered numbers in the first month): grading one writing task with mini costs well under US$0.01. A 5-minute examiner session with gpt-realtime-mini is roughly US$0.10–0.25, because realtime re-bills the growing conversation every turn. Speech stays inside F0 for one learner. A study month with daily practice and weekly speaking sessions should land in the **low single-digit US$**. The budget screen will show the real number.

## 9. Budget and cost tracking

Paid usage comes from two places: **Azure OpenAI** (GPT-5.4 mini and gpt-realtime-mini) and **Azure Speech**. The app meters every paid call itself, stores usage and cost in Postgres, and enforces **hard monthly caps** before a call is made.

### 9.1 Why the app meters locally

- Azure Cost Management data **arrives late**: 8–24 h on some subscription types, up to 72 h on Pay-As-You-Go. It is also aggregated per resource, not per request.
- **Azure budgets only send alerts.** They never stop spending.
- So a real-time view and a hard stop both have to live in the app. Azure's own numbers are pulled in nightly as the check on the app's numbers.

### 9.2 Metering

- **One path for every paid call.** Each goes through `metered(service, feature, call)`, which reads usage from the provider's response and writes a `usage_events` row.
  - **GPT (Responses API):** the `usage` block (input, cached input and output tokens).
  - **Realtime:** each `response.done` event carries text/audio input/output tokens. With WebRTC these events reach the browser, which forwards them to `POST /speaking/sessions/{id}/usage` as they happen.
  - **STT and pronunciation assessment:** audio seconds (from the audio's own duration, rounded the way Azure bills).
  - **TTS:** billable characters of the SSML sent.
- **Prices** live in `content/pricing.yaml`: per model and meter, with an effective-from date. Every usage row stores its units, computed cost and `price_version`, so history stays correct when prices change.
- **Free allowance:** Speech F0 limits (5 h STT, 0.5 M TTS characters a month) are tracked the same way. The screen shows how much free allowance is left, and those units cost 0.
- **Feature tags** (`grading`, `examiner`, `content_gen`, `notes`, `tts_listening`, `stt_speaking`, `pronunciation`) show what the money was spent on.

### 9.3 Hard budgets

- **Budget month** = calendar month in your timezone. Azure's billing period may not start on the 1st, so reconciliation compares day by day, not by billing period.
- **Caps:** a monthly cap per service (Azure OpenAI, Speech) plus an overall cap, all editable on the budget screen. Alerts at 50%, 80% and 100%.
- **Check before every call:** `BudgetGuard.reserve(service, estimated_cost)` compares month-to-date spend plus open reservations plus the estimate against the cap. If it would exceed the cap, the call is **refused** and the UI says which cap was hit. After the call, the reservation is replaced by the actual cost.
- **Realtime sessions:**
  - Before a session starts, the guard reserves the **worst-case** cost for the task's maximum duration: exam task length plus a small buffer, at the highest per-minute rate.
  - The token needed to connect is only issued if that reservation fits.
  - The browser ends the session when the reserved time runs out, or earlier if the forwarded usage reaches the reservation. The API hangs the call up itself when usage reaches the reservation, and a job hangs up any session a minute past its deadline.
  - At the end, the reservation is released; the per-response usage events are the actual cost.
  - Because the reservation is worst-case, the cap can't be overshot by more than one session's buffer.
- **Offline work stays free:** the Library, spaced-repetition reviews, cached audio and past results keep working when a cap is hit. Only new grading, generation and voice sessions stop.

### 9.4 Checking against Azure, and Azure-side safety nets

- **Nightly reconciliation job:** pulls actual cost per meter for the app's resource group from the **Cost Management Query API**. It stores it in `cost_reconciliations` and shows metered cost vs Azure-billed cost and the drift %.
  - Azure's realtime meters are known not to match `response.done` usage exactly. So a rolling 30-day correction factor per service (billed ÷ metered) is applied to projections and worst-case reservations.
- **Safety nets in Azure itself**, in case the app is bypassed:
  1. An **Azure Budget** on the resource group, with email alerts at 80% and 100%.
  2. A low **tokens-per-minute quota** on each GPT deployment, so a runaway loop can't burn much per hour. Content generation uses its own deployment with a higher quota, raised only while a batch runs. All callers handle `429` with backoff. Speech F0's low concurrency limit is respected by a small client-side rate limiter.
  3. Speech on **F0**, which stops by itself at its limits.

### 9.5 Budget screen

- Month-to-date spend vs cap, per service and in total. These bars are for money, not learning progress.
- Spend by feature (grading, examiner, TTS…), with daily burn rate and a month-end projection.
- Speech free allowance remaining.
- Cap editor and alert thresholds.
- A table of recent usage events (time, feature, model, units, cost), filterable.
- The reconciliation panel: metered vs billed, drift %, date of the last Azure sync.
- Displayed in USD (Azure list prices), with an optional INR display rate in settings. Reconciliation uses whatever currency Azure bills in.

## 10. Logging and observability (free, self-hosted)

The whole stack is open source, runs locally in Docker, and has no per-GB bill. Azure Monitor / Application Insights is deliberately left out, because it charges for data ingested beyond its free allowance.

| Concern | Tool | Notes |
|---|---|---|
| App logs | **structlog** (JSON) → stdout | Every line carries `request_id`, plus `run_id` / `session_id` where relevant. Levels via config. Docker log rotation caps disk use. |
| Traces and metrics | **OpenTelemetry** SDK with auto-instrumentation for FastAPI, SQLAlchemy, httpx and the `openai` client | GPT calls come out as spans with model, token counts and latency. Prompt/response capture is behind a flag, on in dev. |
| Storage and UI | **`grafana/otel-lgtm`**, one container with Grafana, Loki (logs), Tempo (traces) and Prometheus (metrics) | Full-featured and free; about 1 GB RAM. Runs under a Compose profile (`docker compose --profile obs up`) so it's optional day to day. 30-day local retention. |
| Frontend errors | Browser errors and slow-interaction reports → `POST /client-logs` → same pipeline | No third-party error-tracking SaaS. |
| Dashboards | Provisioned from `observability/` in the repo: API latency, error rate, GPT latency and tokens, realtime session durations, budget guard refusals | Version-controlled. |

Logs are for debugging. **Usage and cost live in Postgres** (§ 9), which is the durable record. Audio recordings and your writing are never written to logs.

## 11. Content storage: generate once, reuse for every learner

**Rule: the course is a shared catalogue produced ahead of time, and learners only read it.** Lessons, questions, model answers, audio and images are generated, validated and approved once in the content pipeline, then stored permanently. A new user, or a fresh install, loads the catalogue and makes **zero** AI or Speech calls for it. Only work that is personal to a learner costs money at runtime.

### 11.1 What is shared and what is personal

| | Examples | Generated | Stored in | Cost per new user |
|---|---|---|---|---|
| **Shared catalogue: text** | Module outlines, grammar pages, vocab, sentence banks, templates, CO/CE questions and transcripts, EE/EO prompts, model answers, explanations | Once, by the content pipeline | **Git, under `content/`** (YAML / Markdown / CSV), the version-controlled source of truth; loaded into Postgres by an idempotent seed | **0** |
| **Shared catalogue: audio** | Listening clips, dictation lines, word and sentence pronunciations, model-answer audio for shadowing | Once per unique (text, voice, settings) | **Content-addressed media store** (§ 11.2) | **0** |
| **Shared catalogue: images** | A1–A2 picture-based listening questions, module cover illustrations (few, optional) | Once, only where the exam format needs a picture | Same media store | **0** |
| **Personal data** | Your answers, writing, recordings, transcripts, grades, skill estimates, notes, cards | At runtime, by you | Postgres rows keyed by `user_id`; files under `media/users/<user_id>/` | Grading, the examiner and notes extraction only; unavoidable because they depend on the learner's own output |

Every personal table gets a `user_id` from the start, even though there's only one user today. It costs one column now and saves a painful migration later.

### 11.2 Content-addressed media store

- Every generated file is named by the **hash of everything that produced it**:
  - For audio: `sha256(engine + voice + rate + SSML text)`.
  - For images: `sha256(model + prompt + size)`.
- Files live at `media/catalog/<kind>/<ab>/<cd>/<hash>.<ext>`. Audio is **Opus at 48 kbps mono**, about 22 MB per hour. Images are **WebP**.
- **Before any TTS or image call, the pipeline checks whether the hash already exists.** If it does, nothing is billed. So re-running the pipeline, rebuilding the DB, or two modules needing the same sentence never costs twice.
- A **manifest** (`content/media_manifest.csv`: hash, kind, source text or prompt, voice, duration, bytes) is committed to git. It records exactly what exists, without committing the binaries themselves.
- The app reads files through a small `MediaStore` interface:
  - Today: the local-filesystem implementation.
  - If the app is ever hosted for other users: an Azure Blob implementation, with the same keys and the same manifest, served through a CDN. No other code changes.

### 11.3 Text generation cache and prompt caching

- **Generation cache:** every pipeline call is keyed by `sha256(prompt template version + inputs + model)` in a `generation_cache` table. If the pipeline crashes halfway, or a batch is re-run, finished calls are reused instead of paid for again.
- Approved items are **immutable**. An edit creates a new version, so past answers always point to exactly what was shown, and each question keeps its own difficulty estimate.
- **Azure OpenAI prompt caching** gives a discount on repeated prompt prefixes of 1,024+ tokens. Grading prompts put the fixed part first (rubric, band descriptors, example answers) and the learner's answer last, so most grading input is billed at the cached rate.
- **Repair sets** draw from the existing question bank first. New questions are generated only when the bank has too few for that error, and anything generated joins the shared catalogue for everyone.

### 11.4 Size, portability and backups (all free)

- **Rough size:** text under 50 MB; audio for A1–C2 about 1–2 GB (roughly 50–80 hours of clips); images under 200 MB.
- **Content pack:** `make content-pack` bundles `media/catalog/` into a versioned archive (`content-pack-vX.Y.tar.zst`) and uploads it as a **GitHub Release asset** (free, up to 2 GB per file).
  - `make content-pull` on a new machine downloads and unpacks it, checked against the manifest. Only hashes missing from the pack would ever be generated again.
- **Backups:** a nightly `pg_dump` plus an rsync of `media/` (catalogue and personal data) to an external drive or a synced folder. There's no cloud storage bill, so Azure costs stay limited to OpenAI and Speech.

## 12. Knowledge base and "Ask" assistant

**Yes to a searchable knowledge base and a chatbot. No to a separate vector database. No to nightly-only embedding.**

### 12.1 Why pgvector in the existing Postgres, not Qdrant / Weaviate / Milvus / Chroma

- **The corpus is small.** The full A1–C2 catalogue is roughly 15–25k entries (concept sections, words, sentences, questions, templates). Personal data adds a few thousand a year. pgvector with an HNSW index handles millions of vectors, so this is nowhere near its limits.
- **The useful questions are joins.** "What have *I* learned about the subjunctive?" means vector search **filtered by** your covered modules, your cards, your error tags and the CEFR level. In Postgres that's one SQL query. With a separate vector DB, those filters have to be copied into it and kept in sync.
- **One fewer thing to run.** A second store means writing to both and keeping them consistent, plus another backup and another container. It would add complexity without adding capability at this size.
- **Swap later if ever needed.** Search sits behind one `KnowledgeBase` service. If a hosted multi-user version outgrows pgvector, only that service changes.

### 12.2 When things get embedded: on change, not nightly

A nightly batch would leave today's lesson or note unsearchable until tomorrow. Instead:

- **Catalogue content** is embedded **once, when it's approved** in the content pipeline, keyed by content hash plus embedding model. Embeddings for approved catalogue content ship in the **content pack** (§ 11.4), so a new install or new user never re-embeds the catalogue.
- **Personal content** (approved note items, error tags, graded writing and speaking feedback) goes into an `embedding_queue` table in the same transaction that creates it. A background worker drains the queue every minute in batches.
- A **nightly sweep** remains only as a safety net. It picks up anything the queue missed, and it handles a re-embed when the embedding model changes (entries store their `embedding_model`).

### 12.3 What gets indexed

Natural units instead of arbitrary text chunks. One entry per:
- grammar concept section
- word (lemma, gender, meaning, example)
- sentence
- template
- question, with its transcript and explanation
- model answer
- approved note item
- error tag, with examples of your mistakes
- piece of grading feedback

Each entry carries `kind`, `module_id`, `cefr`, `user_id` (null for catalogue), `source_ref` (a deep link into the app), `content_hash` and `embedding_model`.

**Hybrid search:** pgvector similarity plus Postgres full-text search with the `french` dictionary and `unaccent`, plus `pg_trgm` for typo-tolerant word lookup. Results are merged by reciprocal rank fusion, a simple standard way to combine ranked lists. Keyword search matters here: exact grammar words like *dont*, *lequel* or *subjonctif* are where embeddings alone are weakest.

### 12.4 Embedding model and cost

- **Azure OpenAI `text-embedding-3-small`**, same provider and bill, reduced to 512 dimensions. It costs a few cents per million tokens. The whole catalogue is a few million tokens, so the one-off cost is well under US$1, and personal content costs almost nothing. Every call goes through `metered()` + `BudgetGuard`.
- If you'd rather pay nothing: a local open-source multilingual model (e.g. `bge-m3`) in its own container works, at the cost of ~2 GB RAM and slower indexing. It's not the default.

### 12.5 The "Ask" assistant (phase 4)

- A chat panel reachable from anywhere. It answers questions like:
  - "What did I learn about *en* vs *y*?"
  - "Which words from the housing module do I keep missing?"
  - "Explain why it's *que je sois* here."
  - "Give me 5 sentences using *dont* from my lessons."
- **One tool-calling loop** on GPT-5.4 mini (Responses API with function tools). It doesn't need LangGraph. Tools:
  - `search_kb(query, scope: learned|catalogue|mine, kind?, cefr?)`
  - `get_progress()`
  - `get_error_fingerprint()`
  - `lookup_word(lemma)`
  - `start_practice(item_ids)`: turns an answer into a mini drill.
- **Grounded and cited:** answers come from retrieved entries and link back to the lesson, card or feedback they came from. Explanations use exam-register French. General grammar questions outside the course are allowed but labelled as such.
- Conversations are saved per user (`chat_threads`, `chat_messages`). Cost is budget-checked like every other call, typically a fraction of a cent per question.
- The **MCP server** exposes the same `search_kb`, so the Claude app, where your TEF/TCF skill lives, can query the knowledge base too.

### 12.6 Same index, other uses

The index also powers:
- dedupe in the content pipeline
- clustering similar errors for repair sets
- "related lessons" links
- global search in the Library

## 13. Architecture

```
 Browser (Next.js PWA)
   │  REST/JSON + SSE              WebRTC audio (short-lived token, budget-checked)
   ▼                                        ▼
 FastAPI backend ───────────────────►  Azure OpenAI gpt-realtime-mini (examiner)
   │
   ├── Azure OpenAI GPT-5.4 mini (grading, feedback, content, notes)
   ├── Azure Speech (STT, pronunciation assessment, TTS)
   ├── BudgetGuard + usage metering ──► Postgres (usage_events, budgets)
   ├── Nightly job: Azure Cost Management reconciliation
   ├── Postgres 16 + pgvector (local, Docker)
   ├── media/ (catalog/: shared generated audio + images, content-addressed; users/: recordings)
   ├── Obsidian vault folder (read-only notes source)
   ├── MCP server (your learning data, for any MCP client)
   └── OpenTelemetry ──► grafana/otel-lgtm (logs, traces, metrics)
```

| Layer | Choice |
|---|---|
| Frontend | Next.js (App Router) + TypeScript + Tailwind + shadcn/ui + Framer Motion, TanStack Query, type-safe client generated from the API's OpenAPI spec. UI only, no business logic. |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic, `uv`, official `openai` SDK (Azure endpoint), Azure Speech SDK. |
| DB | Postgres 16 + pgvector (HNSW) + full-text search (`french`, `unaccent`) + `pg_trgm`: relational data and the knowledge base in one store. |
| Scoring | Rasch ability estimate for listening and reading, recency-weighted rubric aggregate for writing and speaking. Pure functions in `domain/`. |
| Spaced repetition | FSRS (`fsrs` package) for Library reviews. |
| Jobs | APScheduler inside the API process for the nightly reconciliation and content jobs. No separate queue until one is needed. |
| Runtime | Docker Compose on this machine: `db`, `api`, `web`, plus optional `obs`. Single user, so no auth beyond a local passphrase. |

### 13.1 Agentic or not?

**Mostly not.** The path, coverage, scoring, budgets and scheduling are deterministic code. The AI is used only where judgment is needed, and each use is a **single structured-output call**: `grade_writing`, `grade_speaking`, `tag_errors`, `extract_from_notes`, `generate_items` + `validate_items`.

- **LangGraph (phase 3), two flows only:**
  - **Repair-set builder** after a failed level-exam section: read the error clusters → pick modules and lessons → generate targeted items → pause for your review.
  - **Content pipeline:** generate → validate → dedupe → review → publish.
  Both benefit from saving state in Postgres and pausing for approval. Nothing else does.
- **DeepAgents: no.** Nothing here is a long, open-ended planning task.
- **A2A: no.** There's one app and no outside agents to talk to.
- **MCP: yes, one small server.** It exposes `search_kb`, `get_skill_levels`, `get_error_fingerprint`, `add_note_items`. Any MCP client, including the Claude app where your TEF/TCF skill and notes chat live, can read and write the same data the app uses. It's about 150 lines with FastMCP and adds no cloud cost.

## 14. Data model (first cut)

```
users(id, display_name, passphrase_hash, settings jsonb, created_at)   -- exam date, target NCLC, daily minutes, accent mix, timezone

levels(id, cefr, order)
blocks(id, level_id, order)
modules(id, block_id, order, slug, theme, title, summary)
lessons(id, module_id, order, kind: grammar|vocab|sentences|listening|reading|writing|speaking, payload jsonb)
concepts(id, module_id, slug, title, body_md)
lexemes(id, module_id, lemma, pos, gender, en, example_fr, example_en, audio_hash)
sentences(id, module_id, fr, en, audio_hash)
templates(id, task, kind, text_fr, text_en, introduced_at_level)

items(id, version, supersedes_id?, skill: CO|CE|EE|EO, task, cefr, difficulty, payload jsonb, answer jsonb, audio_hash?, content_hash, status: draft|live|retired)
assessments(id, kind: module_check|checkpoint|level_exam|mock|placement|drill, scope_id, structure jsonb)
assessment_runs(id, user_id, assessment_id, started_at, finished_at, result jsonb, verdict)
responses(id, run_id, item_id, skill, answer jsonb, correct?, rubric jsonb?, time_ms, timed_out)
recordings(id, response_id, audio_path, transcript jsonb, pronunciation jsonb)

module_progress(user_id, module_id, lessons_done, check_score, status: locked|open|covered|placed, covered_at)
skill_estimates(id, user_id, skill, theta?, score, se, cefr, nclc, evidence_count, computed_at)   -- history, one row per recompute
error_tags(id, user_id, tag, example, count, last_seen)
cards(id, user_id, item_type, item_id, fsrs_state jsonb, due_at)
notes(id, user_id, source_path, taken_on, raw_md, extracted jsonb, status)

media_assets(hash pk, kind: audio|image, path, source jsonb, duration_ms?, bytes, created_at)   -- mirrors content/media_manifest.csv
generation_cache(key pk, template_version, model, output jsonb, created_at)

kb_entries(id, user_id?, kind, module_id?, cefr?, source_ref, text, tsv tsvector, embedding vector(512), embedding_model, content_hash)
embedding_queue(id, kb_entry_id, enqueued_at, processed_at?, error?)
chat_threads(id, user_id, title, created_at), chat_messages(id, thread_id, role, content jsonb, citations jsonb, created_at)

usage_events(id, user_id?, occurred_at, service: openai|speech, model, feature, units jsonb, cost_usd, free_units jsonb, price_version, request_id, run_id?)
budgets(id, user_id, month, service: openai|speech|total, cap_usd, alert_pcts int[])
budget_reservations(id, service, feature, estimated_usd, created_at, settled_at?, usage_event_id?)
cost_reconciliations(id, day, service, meter, billed_amount, billed_currency, metered_usd, synced_at)
```

Catalogue tables (`levels` … `items`) are shared and have no `user_id`. Every personal table does. Catalogue rows reference audio by `audio_hash` into `media_assets`, never by path.

Exam formats, timings and score tables live in versioned `content/exam_scales.yaml`. Prices live in `content/pricing.yaml`. Both carry a "verified as of" date and never live in code.

## 15. Repository layout

```
api/
  app/
    main.py  config.py  db.py  observability.py
    domain/        # pure: rasch.py, skill_estimate.py, coverage.py, scales.py, cost.py, fsrs wrapper
    models/        # SQLAlchemy
    schemas/       # Pydantic I/O
    repositories/  # DB access only
    services/      # path, lessons, assessments, grading, library, notes, budget (guard + metering), voice tokens
    llm/           # Azure OpenAI client, prompts/, output schemas, golden-set runner
    speech/        # Azure STT, pronunciation, TTS
    jobs/          # reconcile_costs.py, content jobs
    routers/       # thin FastAPI routes
    mcp/           # MCP server
  migrations/
  tests/
web/
  app/             # path, module/[slug], assess/[id], drill, speak, listen, write, library, progress, budget
  components/      # ui (shadcn), exam (ExamShell, Timer, Mcq, Recorder, WordCounter), progress (CoverageBar, SkillBar), budget
  lib/             # generated API client, hooks, audio utils
content/
  modules/<level>/<nn-slug>/   # module.yaml, concepts/*.md, vocab.csv, sentences.csv
  templates/*.yaml
  exam_scales.yaml
  pricing.yaml
  golden/                      # graded writing and speaking samples for grader evals
  media_manifest.csv           # every generated audio/image: hash, source, voice, duration
media/                         # gitignored; catalog/ restored via `make content-pull`, users/ is personal
observability/                 # Grafana dashboards + datasource provisioning
docker-compose.yml
CLAUDE.md
```

## 16. Code quality rules

These go into `CLAUDE.md` and are enforced by tooling:

- **Python:** `ruff` (lint + format), `mypy --strict`, `pytest`. **TypeScript:** `eslint` + `prettier`, `tsc --strict`, `vitest`, `playwright` for the critical flows (lesson → module check, full checkpoint, budget cap refusal). All run in `pre-commit` and GitHub Actions.
- **Layering:** routers → services → repositories. `domain/` is pure and has no I/O. Routes contain no SQL and services contain no HTTP.
- **No catalogue content is generated at request time.** Learner-facing code only reads the catalogue; generation lives in the pipeline and always checks the media hash / generation cache first.
- **No paid call bypasses `metered()` + `BudgetGuard`.** A test fails if the Azure clients are constructed anywhere else.
- **SOLID where it pays:** small interfaces only where a second implementation or a test fake exists (`Grader`, `SpeechService`, `RealtimeTokenIssuer`). No speculative abstractions.
- **DRY:** one rubric schema for writing and speaking, one `ExamShell` for every timed experience, one generated API client, one metering path.
- **KISS:** plain functions over classes when there's no state. No base repositories, no event bus, no service locator.
- **Comments** explain *why* only (exam rules, scoring and pricing choices). No docstrings that restate the signature.
- **Grader evals as tests:** `content/golden/` samples are scored (on demand, and weekly in CI, within a small budget). The build fails if the grader's average error rises above 1 point on the /20 scale.
- **AI-dependent code is tested without Azure:** `Grader`, `SpeechService` and `RealtimeTokenIssuer` have in-memory fakes, and parsing is tested against recorded response fixtures. Regular CI never calls Azure. Only the budgeted grader eval does.
- **Git workflow:** `main` is protected and always releasable. Work happens on short-lived feature branches off `virtuvoyager_dev` and is merged via PR with CI green. Conventional commits.

## 17. Non-functional requirements (baseline)

Context: one learner, running locally in Docker Compose on a mid-range laptop or desktop, with Azure as the only external dependency. Every number here is a **target with a named way of checking it**: CI tests, Playwright traces, OpenTelemetry metrics in Grafana, or a scripted check.

### 17.1 Performance

| Area | Target | Verified by |
|---|---|---|
| Page load, first visit (local) | LCP < 1.5 s, JS < 200 KB gzipped per route | Lighthouse CI on key routes |
| Interaction responsiveness | INP < 200 ms; route transitions p95 < 200 ms | Playwright traces, web-vitals → OTel |
| Non-AI API endpoints | p95 < 150 ms, p99 < 400 ms | OTel histograms |
| Knowledge-base hybrid search | p95 < 150 ms at 100k entries | Benchmark test with synthetic data |
| Skill-estimate recompute (Rasch + rubric aggregate) | < 500 ms per assessment | Unit benchmark |
| Cached audio playback start | < 300 ms | Playwright |
| Writing grading (two passes run in parallel) | p95 < 20 s, progress shown | OTel span on `grade_writing` |
| Speaking post-session grading (STT + pronunciation + grading) | p95 < 45 s for a 4.5-min task | OTel span |
| Ask assistant | first token < 3 s p95, streamed | OTel |
| Realtime examiner | voice-to-voice turn latency < 1.2 s p95 (depends on network and Azure region; region chosen in the phase-3 spike) | Client-side timing from WebRTC events |

### 17.2 Exam fidelity

- **Timers:** the server is the source of truth for start and end times. The client timer drifts < 100 ms per 10 min and survives a page reload. A section ends on the server even if the tab is closed.
- **TCF rules enforced:** listening audio plays once, you can't go back, no hints, templates hidden. Covered by Playwright tests for every assessment type.
- **Reliable scores:**
  - Grader average error ≤ 1.0 point on /20 against the golden set. The build fails if it's exceeded.
  - The two grading passes agree within 1 point in ≥ 85% of cases.
  - Listening/reading ability uncertainty ≤ ±30 on the /699 scale after one full checkpoint.

### 17.3 Reliability, durability, availability

- **No lost work:**
  - Every answer is saved as it's given.
  - Writing autosaves every 5 s.
  - Recordings are written to disk before any upload or grading.
  - An interrupted assessment resumes where it stopped.
- **Graceful degradation:** if Azure is unreachable or a budget cap is hit, the Library, reviews, cached audio, lessons and **listening/reading assessments keep working fully**, because their scoring is local. Writing and speaking submissions are **queued and graded later**, never dropped. Only the live examiner and Ask are unavailable.
- **Retries:** paid calls retry with exponential backoff (max 3). Grading jobs are idempotent: a retry never double-charges, thanks to the generation cache and budget reservations.
- **Backups:** RPO ≤ 24 h (nightly `pg_dump` + `media/` rsync); RTO < 30 min (`make restore` + `make content-pull`). A restore drill is scripted and run monthly.
- **Availability:** there's no SLA for a local app. The target is that the stack comes back automatically after a reboot (`restart: unless-stopped`), with health checks on every container.

### 17.4 Cost

- Monthly caps are never exceeded by more than **one realtime session's buffer** (≤ US$0.50).
- **100% of paid calls** produce a `usage_events` row. This invariant is tested: Azure clients can't be constructed outside the metering layer.
- Metered vs Azure-billed drift < 10% after the correction factor, shown on the budget screen.
- Catalogue content (text, audio, images, embeddings) costs **0** for any new user or install.

### 17.5 Security and privacy

- **Network exposure:**
  - The app binds to `localhost` by default.
  - Using it from a phone on your LAN goes through Caddy with a local TLS certificate (browsers only allow the microphone over HTTPS or on localhost), behind the passphrase login.
  - Postgres and Grafana are never exposed outside the Docker network.
- **Secrets:**
  - Azure keys live in `.env` (gitignored), with `gitleaks` in pre-commit and CI.
  - Keys never reach the browser. The API mints a **short-lived session token** per session, only after the budget check, and uses it for the SDP exchange itself.
- **Sessions:** the passphrase is hashed with Argon2id. Session cookies are HttpOnly, SameSite=Strict and Secure over TLS. Login attempts are rate-limited.
- **MCP server:** runs over stdio for local clients, or on `localhost` HTTP with a bearer token. It's never exposed on the LAN.
- **Dependencies:** Dependabot, `pip-audit` and `npm audit` in CI. No known high or critical vulnerabilities on the main branch.
- **Input handling:** everything is validated with Pydantic, SQL goes only through SQLAlchemy, and the notes importer reads the Obsidian folder **read-only** and sanitises Markdown before rendering. Content from notes or the knowledge base is passed to the LLM as data, never as instructions.
- **Privacy:**
  - Recordings, writing and grades stay on your machine.
  - Azure OpenAI doesn't use API data for training.
  - Speech data logging stays off.
  - Recordings and your writing are never written to logs.

### 17.6 Accessibility, compatibility, localisation

- **WCAG 2.2 AA.** Fully keyboard-operable, including `ExamShell`. Visible focus. Respects `prefers-reduced-motion`. Colour is never the only signal (word gender uses a colour **and** a label). `axe` checks in Playwright.
- **Browsers:** latest two versions of Chrome, Edge, Firefox and Safari, including mobile Safari and Chrome as an installed PWA. Layouts work from 360 px wide.
- UI in English, content in French.
- **Correct French typography:** non-breaking spaces before `; : ! ?` and inside « guillemets », proper apostrophes, UTF-8 throughout. French text is always tagged with `lang="fr"` so screen readers pronounce it correctly.

### 17.7 Maintainability and operability

- **Static checks:** `mypy --strict` and `tsc --strict` with zero errors; ruff and eslint with zero warnings; function complexity ≤ 10 (ruff C901).
- **Test coverage:** ≥ 90% line coverage on `domain/` (scoring, budgets, coverage), ≥ 75% on the backend overall, and Playwright on the critical flows.
- **CI:** under 10 minutes on every PR. Grader evals run weekly and on prompt changes, within a fixed budget.
- **Setup:** one command (`make up`) on Linux, macOS or WSL2, with Docker as the only prerequisite. Schema changes only through Alembic migrations, tested up and down.
- **Observability:** 100% of API requests traced; structured logs with request IDs; 30-day local retention; dashboards version-controlled.

### 17.8 Capacity and footprint

- **Designed for 1 learner.** The schema is multi-user-ready (`user_id` everywhere) and the API is stateless, so scaling out later means adding instances, not redesigning. Load beyond a single user isn't a target and isn't tested.
- **RAM:** idle, the core stack (`db`, `api`, `web`) uses < 1.5 GB; `obs` adds about 1 GB.
- **Disk:** about 3 GB for the full catalogue (audio, images, embeddings) plus about 1 GB a year of your recordings (Opus).

## 18. Delivery phases

| Phase | Scope | Done when |
|---|---|---|
| **0. Foundations** (~1 wk) | Skeleton, Docker Compose (+ `obs` profile), Postgres + migrations, FastAPI health, Next.js shell and design system, CI, `CLAUDE.md`. Azure: free account → Pay-As-You-Go, resource group, Azure OpenAI deployments (GPT-5.4 mini, gpt-realtime-mini) with low TPM quotas, Speech F0, Azure Budget alert. **Metering + BudgetGuard + `pricing.yaml` from day 1.** | `docker compose up` shows the shell; CI green; one GPT call and one TTS call are metered into `usage_events` and visible in Grafana. |
| **1. Path + modules + coverage + budget screen** (~2–3 wks) | Level/block/module model, lesson player, module checks, coverage bar, Library + FSRS, A1–A2 content (16 modules, generated with the free credit), budget screen, nightly reconciliation. | You can work through A2 modules and see coverage move; budget screen shows live and reconciled spend. |
| **2. Assessment engine + receptive skills** (~3 wks) | Knowledge-base index (hybrid search, embedding queue, embeddings in content pack), `ExamShell`, question bank with difficulty, Rasch estimator, CO/CE skill bars, placement test, block checkpoints (CO/CE parts), TTS listening audio. **Golden set + mini vs full grader comparison.** | Placement sets real CO/CE estimates; a checkpoint moves the bars. |
| **3. Writing + speaking** (~3–4 wks) | Writing desk + rubric grading (two passes), error tagging; realtime examiner with budget-checked sessions; STT + pronunciation; EE/EO skill bars; level exams + gate + repair sets (LangGraph); Notes inbox from Obsidian; MCP server. | A full level exam with all four skills produces four skill bars and a gate decision, within budget. |
| **4. Mocks + B1–B2 content + Ask + polish** (~3–4 wks) | "Ask" assistant over the knowledge base, full TCF mocks, verdicts, monthly/weekly cadence tied to exam date, B1–B2 content (16 modules), performance and accessibility pass, PWA install. | A full 2 h 47 mock end-to-end, scored against NCLC 7. |
| **5. C1–C2** (later) | Remaining 16 modules and higher-level question bank. | Complete A1–C2 path. |

## 19. Content strategy

- All questions and texts are **original, written in exam format**. Nothing is copied from *Réussir le TCF* or paid mock banks.
- Each generated item goes through a validation pass (grammar, single correct answer, CEFR level fit, difficulty estimate). It stays in `draft` until you approve it (one click).
- Content generation is a one-off cost per item. Most of the A1–B1 bank should be generated within the first 30 days to use the free credit.
- Grammar pages and module outlines live as markdown/YAML in `content/`, reviewed by you and optionally your tutor.
- Your tutor's graded corrections go into `content/golden/`. This is what keeps the writing and speaking bars honest.

## 20. Risks

| Risk | Mitigation |
|---|---|
| Writing/speaking scores drift from real examiners | Golden set with tutor-graded samples, two grading passes, eval check on error; show uncertainty bands, not single points. |
| GPT-5.4 mini grades French writing less strictly than needed | Golden-set comparison against GPT-5.4 before phase 3; escalate grading only (not generation) if needed. |
| Listening/reading difficulty estimates are rough with one user | Start difficulty from authored CEFR levels (a strong prior); refine only after enough answers; widen uncertainty when evidence is thin; cross-check against full mocks. |
| Realtime cost surprises | Worst-case reservation before the connection token is issued, session time caps, correction factor from reconciliation, low TPM quotas, Azure budget alert. |
| Wrong French in generated content | Generate-then-validate, draft/approve gate, tutor spot checks. |
| Exam format or price changes | Versioned `exam_scales.yaml` and `pricing.yaml`. |
| Azure retires a model version | Deployment names in config; watch retirement notices; switch deployment, rerun the golden-set eval, update `pricing.yaml`. |
| Build takes ~4 months while you're already studying | Phases ship usable slices early: A1–A2 modules and Library by week ~4, listening/reading measurement by ~week 7, speaking/writing by ~week 11. Your tutor sessions continue in parallel, and the Notes inbox brings that work into the app. |

## 21. Out of scope for now

- Access from outside your home network. If you want it later, a free personal Tailscale tailnet is the simplest option and needs no code changes.
- TEF Canada structure and scales (the design supports it; add the scales and task formats later).
- Multiple users, accounts, and hosting on Azure (schema and `MediaStore` are ready; auth and Blob storage would be added).
- Native mobile apps (the installable PWA covers phone use).
- Offline use away from the home machine (the PWA needs the local server).

## 22. Decided

- **Exam:** TCF Canada (TEF support can be added later by adding its scales and structure).
- **Obsidian:** read-only notes source only.
- **Cloud:** Microsoft Azure only. **Azure OpenAI** (GPT-5.4 mini, gpt-realtime-mini) and **Azure Speech** (F0). No Claude.
- **Budgets:** metered locally in Postgres, hard monthly caps enforced in the app, reconciled nightly with Azure Cost Management.
- **Content storage:** shared catalogue generated once (text in git, audio/images in a content-addressed local store backed up as a GitHub Release content pack); only personal work (grading, examiner, notes) costs money per learner.
- **Knowledge base:** pgvector + French full-text search in the existing Postgres (no separate vector DB); embedded on approval/creation via a queue, nightly sweep as safety net; "Ask" assistant in phase 4.
- **Logging:** structlog + OpenTelemetry → self-hosted `grafana/otel-lgtm`. No paid observability.
- **Users:** single user; local passphrase, no accounts.
- **No gamification:** no XP, streaks, quests or badges. Two progress bar types only (the budget screen's spend bars are a separate admin view).
