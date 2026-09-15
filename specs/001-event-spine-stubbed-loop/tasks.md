# Tasks: Event spine and stubbed loop (S1)

**Input**: Design documents from `specs/001-event-spine-stubbed-loop/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/events-v1.0.0.md, contracts/http-api.md, quickstart.md

**Tests**: Requested. The spec's completion evidence is the replay-and-compare suite, the screenshot comparison, and the quality gates (constitution XIII and XVI), so test tasks are included and are part of the deliverable.

**Organization**: Grouped by user story in priority order. US1 (stubbed loop), US2 (replay), and US3 (golden logs and suite) are P1 and form the MVP together; US4 (Demo page fidelity) and US6 (quality gates) are P2; US5 (static pages) is P3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 to US6 from spec.md
- Paths are repository-relative per plan.md

---

## Phase 1: Setup

**Purpose**: Project skeleton, dependency pins, gates wiring, design asset extraction

- [ ] T001 Create `pyproject.toml` with the uv project, Python 3.13, exact pins from research.md (fastapi 0.141.1, uvicorn 0.53.0, pydantic 2.13.5, pyyaml 6.0.3, python-dotenv 1.2.3; dev: pytest 9.1.1, pytest-asyncio 1.4.0, httpx 0.28.1, mypy 2.3.1, ruff 0.16.7, playwright 1.62.0, pillow 12.3.0), ruff and mypy config (strict on `app/schema` and `app/orchestrator`), pytest markers (`visual`), and run `uv sync` to produce `uv.lock`
- [ ] T002 [P] Create the package skeleton with empty `__init__.py` files: `app/`, `app/schema/`, `app/orchestrator/`, `app/agents/`, `app/agents/stubs/`, `app/runs/`, `app/web/pages/`, `app/web/static/{css,js,fonts,img}/`, `tests/{unit,integration,visual,lint}/`, `scripts/`
- [ ] T003 [P] Write `scripts/lint_em_dash.py`: scans git-tracked text files plus everything under `runs/` and any paths given as arguments, fails on U+2014 with path and line, exit code 1; reconfigures stdout to UTF-8
- [ ] T004 [P] Write `scripts/extract_design_assets.py`: decodes each `design/*.html` bundle manifest, writes the 20 woff2 fonts to `app/web/static/fonts/<family>-<weight>-<range>.woff2` and the human-figure SVG to `app/web/static/img/person.svg`, never writes under `design/`, and prints a manifest table; run it once and commit the assets
- [ ] T005 [P] Write `app/config.py`: settings dataclass loaded from environment and `.env` (python-dotenv) with `RUNS_DIR` (default `runs`), `DATASETS_DIR`, `RETRY_BUDGET` (2), `COST_CEILING` (5.00), `STUB_PACE` (4.0), `WORKFLOW` (`electrical_rfp`); no credentials read in S1
- [ ] T006 [P] Write `app/buildinfo.py`: returns `{hash, date}` from `git rev-parse --short HEAD` and `git log -1 --format=%cs`, or `{hash: "no-git", date: today}` when git is absent
- [ ] T007 Write `scripts/check.py`: runs `ruff check .`, `ruff format --check .`, `mypy app`, `pytest -m "not visual"`, `python scripts/lint_em_dash.py`, and `pytest tests/lint/test_env_leak.py` in order; stops on first failure; documented in quickstart.md

**Checkpoint**: `uv run python scripts/check.py` runs (tests may be empty) and the fonts and icon exist under `app/web/static/`

---

## Phase 2: Foundational (blocking)

**Purpose**: The frozen schema and the Orchestrator core that every story depends on

- [ ] T008 Copy `specs/001-event-spine-stubbed-loop/contracts/events-v1.0.0.md` to `docs/schema/events-v1.0.0.md` with a header line stating it is frozen and the amendment procedure
- [ ] T009 Write `app/schema/events.py`: `Stage`, `Exit`, `Direction`, `Verdict`, `Severity`, `Decision`, `ReadinessVerdict` literal types; `Model`, `Agent` models; `Actor` union (Agent, `"human"`, `"system"`); one payload model per event type exactly as in the contract (including `Summary`, `Finding`, `Subtask`, `ChecklistItem`, `Blocker`, `HandoffPackage`); `Event` envelope with a `type`-discriminated payload validator; validators: `reason` required for Orchestrator-seat actors, `prompt_ref` required on the listed agent message types, `stage` null on `run.started` and `run.terminated`; `SCHEMA_VERSION = "1.0.0"`
- [ ] T010 [P] Write `app/schema/bundles.py`: `PromptBundle` model (`prompt_ref`, `system`, `context_slice`, `task`, `tools`, `model`)
- [ ] T011 [P] Write `app/schema/export.py`: builds the JSON Schema for `Event` and `PromptBundle` and a `main()` that writes `docs/schema/events-v1.0.0.json`; run it and commit the file
- [ ] T012 [P] Write `tests/unit/test_schema.py`: every event type validates with a minimal valid payload; wrong payload for a type fails; Orchestrator event without `reason` fails; agent message without `prompt_ref` fails; `run.started` with a stage fails; all eight exit values accepted; `readiness_verdict` accepted on the summary
- [ ] T013 [P] Write `tests/unit/test_schema_export.py`: regenerating the JSON Schema equals the committed `docs/schema/events-v1.0.0.json` byte for byte (normalised line endings)
- [ ] T014 [P] Write `app/orchestrator/roster.py`: seat table (`orchestrator`, `intake`, `estimator`, `pricing`, `writer`, `reviewer`, `case`, `market`) with role labels, the two names per seat from spec 4.3, colours from the export, default model objects with the export's labels (`claude-sonnet via Bedrock`, `claude-sonnet via Bedrock (vision)`, `llama3.1 8b, local`, `gemini-2.5-pro via Google`), `build_roster(seed, names_override)` returning `Agent` objects for the electrical RFP workflow (six seats), and `human_actor()`
- [ ] T015 [P] Write `tests/unit/test_roster.py`: same seed gives same names; both names appear across seeds; override applies; every Agent has provider, model_id, label
- [ ] T016 Write `app/orchestrator/state.py`: `RunState` dataclass per data-model.md and pure transition functions `can_enter(stage)`, `on_review_fail(route_to)` returning `rework | retry_exhausted`, `on_route_back_to_intake()` returning `allowed | blocker`, `on_meter(delta)` returning `ok | cost_ceiling`, plus the six-stage order constant
- [ ] T017 [P] Write `tests/unit/test_state_machine.py`: forward path; Review fail twice within budget then third fail is `retry_exhausted`; Work to Intake once allowed, second time blocker; cost ceiling breach detected after the breaching delta; pause flag blocks dispatch predicate; every exit value reachable through the rules
- [ ] T018 Write `app/agents/base.py`: `Emit` step (seat, type, offset_ms, payload, bundle, meter delta), `Wait` markers, `StubScenario` protocol with `dataset_id`, `steps`, `plan` (subtasks), `human_script`, and `EventSink` protocol the Orchestrator passes to stubs
- [ ] T019 Write `app/runs/bus.py`: `StreamBus` with per-stream event lists, subscriber queues, `publish(stream_id, event_dict)`, `subscribe(stream_id, since_seq)` async generator that first yields backlog after `since_seq` then live items, `close(stream_id)`
- [ ] T020 Write `app/runs/recorder.py`: `Recorder` creating `runs/<run_id>/`, appending events to `events.jsonl` as they are published, writing `prompts/<ref>.json`, `meta.json` on start and on termination, and `knowledge.md`
- [ ] T021 Write `app/orchestrator/knowledge.py`: copy `datasets/<id>/knowledge.seed.md` to the run folder if present else create empty; `append(entries)` writes a dated section; returns the entries for `knowledge.appended`
- [ ] T022 Write `app/orchestrator/orchestrator.py`: `Orchestrator(run_id, dataset, scenario, roster, config, bus, recorder, clock)`; emits `run.started`; runs Intake by calling the stub; batches blocking `clarification.needed` into one `clarification.asked` and pauses on a human gate (asyncio.Event) with non-blocking ones producing `assumption.accepted`; on answers emits `knowledge.appended`; handles `not_ready` and dry intake exits; emits `plan.created` from the scenario plan; dispatches tasks with `task.dispatched`, gathers independent tasks concurrently and waits for dependencies; relays stub emissions with envelope filling (seq, ts from start plus offset, actor from roster, prompt_ref) and sleeps `offset delta / STUB_PACE`; handles `blocker.raised` (needs_human: `clarification.asked` with blocker and pause; Answer resumes; Escalate terminates `blocker_escalated` with `missing`; route_back_to intake with cap); Assemble and Review stages; review routing with `retry.incremented`; Handoff with `handoff.ready` then waits for `human.approved` then `run.terminated`; pause and resume and stop methods; cost ceiling check after every `meter.update`; guarantees `run.terminated` last with a structured summary (event_count, elapsed_ms, est_cost, retries, missing, unresolved_findings, readiness_verdict, human_decision); all emitted events validated through `Event` before publish
- [ ] T023 [P] Write `tests/unit/test_stubs_emit_only_agent_events.py`: for every registered stub scenario, every `Emit` step type is in the agent event set and never an Orchestrator or human type
- [ ] T024 Write `app/runs/registry.py`: dataset discovery in spec order with labels `01 · Clean run` etc. (from a fixed table keyed by folder name), `brand.yaml` load, golden and recording detection, latest recording lookup by `meta.json.started_at`, live run registry (one at a time), `start_run(dataset_id, names)`, `get_run`, `human_answers`, `human_decision`, `pause`, `resume`, `stop`

**Checkpoint**: `pytest tests/unit` green; the Orchestrator can be driven in-process by a test with a scripted human

---

## Phase 3: User Story 1 - Run a stubbed scenario and watch the loop (Priority: P1) MVP

**Goal**: All six datasets run end to end from stubs through the Orchestrator, recorded, with the human touchpoints working, and the Demo page rendering every element from events.

**Independent Test**: With no credentials, run each dataset from the Demo page to its README exit, acting at each touchpoint; every element traces to an event in the raw drawer.

### Stubs (agent side)

- [ ] T025 [P] [US1] Write `app/agents/stubs/planted_inconsistency.py` from the export's sample transcript: Intake readiness `ready_with_assumptions` with the 9-item checklist (7 pass, bid validity assumed, service voltage blocking), one non-blocking clarification (bid validity, default 60 days) and two blocking ones (service voltage 208Y/120 V, LED alternate no), plan of three sub-tasks (takeoff, price after 1, assemble after 1 and 2), Estimator progress replies and tool calls at the export offsets (01:19, 01:28, 01:35, 02:02) with the 200 A vs 225 A flag, Pricing waiting then `46 of 47 lines priced, 1 long-lead exception`, Writer draft v1 at 02:41 with 31 tags, Reviewer fail at 03:12 (major to Estimator, minor to Writer), Estimator rework at 03:31, draft v2 at 03:48, Reviewer pass at 04:05 with one minor note, meter deltas summing to the export's terminated totals (tokens 6200, 18400, 61000, 9100, 24700, 31500; cost 0.05, 0.09, 0.42, 0, 0.16, 0.11), prompt bundles from the export's three sample bundles plus minimal ones for the rest; `human_script`: answer both defaults, approve
- [ ] T026 [P] [US1] Write `app/agents/stubs/clean_run.py`: minimal fixture text marked `[fixture]`; readiness `ready_with_assumptions` with one non-blocking default; Estimator, Pricing (waits), Writer v1, Reviewer pass with no findings; `human_script`: approve
- [ ] T027 [P] [US1] Write `app/agents/stubs/missing_sheet.py`: Intake ready; Estimator raises `blocker.raised` with `needs_human` describing the absent panel schedule sheet; `human_script`: escalate; also a secondary script `answer` path that continues to a pass (used by a unit test only)
- [ ] T028 [P] [US1] Write `app/agents/stubs/missing_price.py`: Pricing completes with one exception (exit signs unpriced); Writer discloses; Reviewer pass with one minor finding; `human_script`: approve
- [ ] T029 [P] [US1] Write `app/agents/stubs/not_ready.py`: readiness `not_ready` with deadline and Division 26 specification failed; no further steps; `human_script`: none
- [ ] T030 [P] [US1] Write `app/agents/stubs/prospect_own.py`: dry intake flag on the scenario; readiness `ready_with_assumptions`; `human_script`: none
- [ ] T031 [US1] Write `app/agents/stubs/__init__.py`: registry by dataset id, deterministic `prompt_ref` allocation `pb-<dataset>-<nn>`, `bundle_for(prompt_ref)` lookup across scenarios
- [ ] T032 [US1] Write `tests/integration/test_orchestrator_scenarios.py`: drives each scenario in-process with its `human_script`; asserts the exit per dataset README, `run.terminated` last, `seq` contiguous, Planted inconsistency has one backward Review to Work and `retry.incremented` count 1, Missing sheet `missing` lists the sheet, Not ready `missing` lists two items, Prospect own exit `dry_intake` with `readiness_verdict`, Clean run `knowledge.appended` absent (no blocking question) and Planted inconsistency `knowledge.appended` present with two entries, Pricing dispatched only after Estimator completed
- [ ] T033 [US1] Write `tests/integration/test_recording.py`: a run writes `events.jsonl`, `meta.json`, `prompts/`, `knowledge.md`; the file matches the published events; a partial run has a valid prefix

### API and stream

- [ ] T034 [US1] Write `app/main.py` API routes per contracts/http-api.md: `GET /api/meta`, `GET /api/datasets`, `POST /api/runs` (409 when live), `GET /api/runs/{id}`, `GET /api/runs/{id}/events`, `POST /api/runs/{id}/answers`, `POST /api/runs/{id}/decision` (approve only in S1), `POST /api/runs/{id}/{pause|resume|stop}`, `GET /api/prompts/{ref}`, `GET /api/streams/{id}/events` (SSE with `id`, `event`, `data`, keepalive comment, `Last-Event-ID` and `since`, close after `run.terminated`), page routes with build-stamp substitution, static mount
- [ ] T035 [US1] Write `tests/integration/test_api.py` and `tests/integration/test_stream.py`: datasets list order and labels; start run; stream delivers events in order with `id` equal to `seq`; resume with `since` returns no duplicates; answers and decision endpoints advance the run; 409 on second run; prompt lookup works during a run

### Demo page (event-driven)

- [ ] T036 [US1] Write `app/web/static/css/app.css`: `@font-face` blocks for the extracted fonts (unicode ranges as in the export), body and keyframes (`nodePulse`, `arrowFire`, `dotBlink`), and one class per element of the Demo template with values copied verbatim: frame, header, nav, pre-flight dot states, workflow select, loop strip and nodes (idle, active, complete, paused), retry badge, forward arrow glyph, backward arrows SVG with fired variant, banner and question boxes, composer controls (dataset select, mode switch, Dry intake toggle, Run, Pause, Stop, Replay with speed segments), feed and every card kind (orchestrator note, agent message, assumption, question, human answer, plan card rows, specialist thread with replies and blinking dots, draft committed, verdict with pill and findings and severity variants, termination card, blocker card with 4px red left border), agent card sizes (40, 32, 24), prompt button and panel, artifact aside (compare strip, panel header, placeholder body, handoff actions including disabled Edit and Reject), meters strip (elapsed, agent meters, run total, comparison line, ceiling bar, detail row), raw drawer, chat panel; hover and active rules; `[disabled]` and `.is-disabled` at opacity 0.45
- [ ] T037 [US1] Write `app/web/pages/demo.html`: static skeleton of the Demo frame with header (product name, workflow select, nav with pre-flight dot pending and build stamp `{{BUILD_STAMP}}`), loop strip with six nodes and the three backward arrows and labels, banner container (hidden), composer, feed container with the idle message, artifact aside with compare strip empty state and placeholder text `Compiled output arrives in S4`, meters strip, raw drawer, chat panel (hidden, disabled); no sample data
- [ ] T038 [P] [US1] Write `app/web/static/js/events.js`: `EventStream(url, sinceSeq, onEvent, onClose)` using `EventSource`, tracks last `seq`, reconnects with `since`, ignores duplicates
- [ ] T039 [P] [US1] Write `app/web/static/js/reducer.js`: pure `reduce(events, runMeta)` producing the view model in data-model.md (node states, fired arrows, retry badge, cards with open threads, banner questions, blocker, termination, meters, elapsed, raw lines, roster map); `fmtTok`, `fmtUsd`, `fmtClock(ms)` matching the export
- [ ] T040 [US1] Write `app/web/static/js/render.js`: DOM builders for every card kind and page part from the view model, agent card builder at three sizes, prompt panel builder that fetches `/api/prompts/{ref}` on first open, why-on-click for Orchestrator notes, thread auto-expand and collapse, verdict pill and findings, termination card from `handoff.ready` and from `run.terminated`, blocker card with Answer and Escalate, banner with editable inputs and Resume button, meters with detail row on click, raw drawer toggle with JSON lines, in-place updates keyed by `event_id` so re-rendering does not flicker
- [ ] T041 [US1] Write `app/web/static/js/demo.js`: loads `/api/meta` and `/api/datasets`, fills the dataset dropdown, composer wiring (Run posts `/api/runs` and opens the stream; disabled controls stay disabled; Replay wiring added in US2), banner submit posts answers, blocker Answer and Escalate post answers, Approve posts decision, page reload rebuilds from `/api/runs/{id}/events` using `sessionStorage` for the current run id, feed auto-scroll to newest while active
- [ ] T042 [US1] Manual pass per quickstart.md steps 1 to 5 and 7 on all six datasets; fix defects; record the pass in `specs/001-event-spine-stubbed-loop/checklists/s1-manual.md`

**Checkpoint**: All six datasets run from the Demo page to their expected exits; every card kind has appeared

---

## Phase 4: User Story 2 - Replay a recorded run at 1x or 4x (Priority: P1)

**Goal**: Replay of the most recent recording (or the golden log) with original ids and scaled timing, identical display.

**Independent Test**: Run Clean run live, replay at 4x, final page states match and event lists match apart from timestamps.

- [ ] T043 [US2] Write `app/runs/replay.py`: `ReplaySession(dataset, speed, source)` resolving latest recording else golden log, publishing events on `StreamBus` under `session_id` with original fields, sleeping `gap / speed`, closing after `run.terminated`, writing nothing
- [ ] T044 [US2] Add `POST /api/replays` to `app/main.py` and `replay_source` to `GET /api/datasets`
- [ ] T045 [US2] Write `tests/integration/test_replay.py`: replay of a recorded run yields identical events (same `event_id`, `seq`, `ts`, payload); replay timing at speed 4 is one quarter of the recorded gaps within tolerance; golden fallback when no recording; no new folder under `runs/` after a replay; human events play without waiting
- [ ] T046 [US2] Wire Replay and speed in `app/web/static/js/demo.js`: speed segment toggle (1x default, 4x), Replay posts `/api/replays` and opens the session stream, human controls render read-only during replay (answers shown, buttons inert), Replay disabled while a live run is in progress and for datasets with no source (tooltip reason)
- [ ] T047 [US2] Manual check per quickstart step 6 on two datasets at both speeds; record in `checklists/s1-manual.md`

**Checkpoint**: Replay works from the page for every dataset that has a golden log

---

## Phase 5: User Story 3 - Golden logs and the replay-and-compare suite (Priority: P1)

**Goal**: Six committed golden logs and a suite that proves each stubbed run matches its golden stage sequence and exit.

**Independent Test**: Suite passes from a clean checkout; corrupting one stub fails that dataset with the divergence named.

- [ ] T048 [US3] Write `scripts/regen_golden.py`: for each dataset runs the scenario in-process with its `human_script` at a fixed start timestamp `2026-09-14T09:12:00Z`, fixed roster names (the export's), and writes `datasets/<id>/golden-events.jsonl`; refuses to run if the working tree has uncommitted stub changes unless `--force`
- [ ] T049 [US3] Run the regenerator and commit the six golden logs
- [ ] T050 [US3] Write `tests/integration/test_golden_compare.py`: for each dataset, run the scenario in-process, extract `[(from, to, direction)]` from `stage.changed` and the terminal `exit`, compare with the golden log, and on mismatch report the first differing transition index; also validate every golden event against `Event`, `seq` contiguity, last event `run.terminated`; assert Planted inconsistency has exactly one backward Review to Work and one `retry.incremented` with count 1; assert Missing sheet ends `blocker_escalated` with an `escalate` answer present
- [ ] T051 [US3] Write `tests/integration/test_golden_divergence.py`: monkeypatch one stub to skip a stage and assert the suite's comparison function fails naming the dataset and index

**Checkpoint**: `pytest tests/integration/test_golden_compare.py` green; golden logs committed

---

## Phase 6: User Story 4 - The Demo page matches the design export (Priority: P2)

**Goal**: Reference captures from the export for all four Demo states and the chat panel, and a passing comparison with declared masks.

**Independent Test**: Capture and compare; no visible difference at 1920 by 1080 outside declared deferred regions.

- [ ] T052 [US4] Write `scripts/capture_export.py`: copies each export bundle to the scratch folder, rewrites the `data-props` default for `state` (idle, running, paused, terminated), `chatOpen`, and `preflight`, renders with Playwright Chromium at 1920 by 1080, waits for the bundle loader to finish and fonts to load, disables animations at their end frame, saves `tests/visual/reference/demo-<state>.png`, `demo-terminated-chat.png`, `login.png`, `settings.png` (dropdown closed, `openDropdown -1`), `preflight-pending.png`, `preflight-all-pass.png`; never writes under `design/`
- [ ] T053 [US4] Run the capture script, compare `demo-terminated.png`, `login.png`, `settings.png`, `preflight-all-pass.png` against `design/screenshots/` by eye, record any drift in `design/README.md` under Screenshots, commit the references
- [ ] T054 [US4] Write `tests/visual/masks.py`: per-capture list of rectangles excluded in S1 with the slice that removes each: artifact panel body (S4), compare strip body and comparison line (S5), meter detail row (S5), Settings dropdown open state (S5)
- [ ] T055 [US4] Write `tests/visual/test_screenshots.py` (marker `visual`): starts the app on a free port with `STUB_PACE` high and fixed roster names, drives the page to each state (idle: load; paused: run Planted inconsistency until the banner; running: answer and wait until the Estimator thread shows the 01:35 reply; terminated: wait for `handoff.ready` then approve), captures at 1920 by 1080, compares with the reference using Pillow (channel difference over 24 counts; fail above 0.5 percent of unmasked pixels), writes diff images to `tests/visual/output/` on failure
- [ ] T056 [US4] Iterate on `app.css`, `demo.html`, and `render.js` until all Demo state comparisons pass; where the export and the spec cannot both be satisfied, record the case in `design/README.md`
- [ ] T057 [US4] Verify the additions in family by a side-by-side review (blocker card, Dry intake toggle, Edit and Reject, build stamp and pre-flight dot on every header); record in `checklists/s1-manual.md`

**Checkpoint**: `pytest -m visual` green for the four Demo states

---

## Phase 7: User Story 6 - Quality gates (Priority: P2)

**Goal**: Every gate green and the leak test in place.

**Independent Test**: `scripts/check.py` passes on a clean checkout; an inserted em dash fails the lint.

- [ ] T058 [P] [US6] Write `tests/lint/test_em_dash.py`: runs the lint function over the repo and over a temp file containing an em dash and asserts pass and fail respectively
- [ ] T059 [P] [US6] Write `tests/lint/test_env_leak.py`: writes a temp `.env` with `LEAK_MARKER=zq9-secret-marker`, loads config, runs Clean run in-process, and asserts the marker string appears in no event and no prompt bundle
- [ ] T060 [US6] Make `mypy app` strict-clean for `app/schema` and `app/orchestrator` and clean elsewhere; fix ruff findings; run `scripts/check.py` to green
- [ ] T061 [US6] Add `docs/dependencies.md` links from `plan.md` and `CLAUDE.md` pointers section; confirm every S1 dependency has an entry

**Checkpoint**: `uv run python scripts/check.py` exits 0

---

## Phase 8: User Story 5 - Login, Settings, and Pre-flight as static pages (Priority: P3)

**Goal**: Three static pages flattened from the export with the shared header and working nav.

**Independent Test**: Each page matches its capture; nav links work; Sign in reaches Demo.

- [ ] T062 [P] [US5] Write `app/web/pages/login.html`: form per the export, Sign in as a link to `/demo`, header not present (export has none), classes in `app.css`
- [ ] T063 [P] [US5] Write `app/web/pages/settings.html`: header with nav, pre-flight dot pending, build stamp; eight seat rows from the export's roster with inert model select (dropdown closed) and dependency notes; classes in `app.css`
- [ ] T064 [P] [US5] Write `app/web/pages/preflight.html`: header with nav, pre-flight dot pending, build stamp; title and disabled Run pre-flight button; eight check rows in the pending state; classes in `app.css`
- [ ] T065 [US5] Add the three captures to `tests/visual/test_screenshots.py` with masks for the build stamp text (hash differs per checkout) and run to green
- [ ] T066 [US5] Write `app/web/static/js/pages.js`: marks the active nav item and nothing else; include on all pages

**Checkpoint**: All seven captures compare green

---

## Phase 9: Polish and closure

- [ ] T067 Update `design/README.md` Screenshots section: list the new captures under `tests/visual/reference/` and note that `design/screenshots/` stays untouched
- [ ] T068 Update `docs/roadmap.md` S1 entry status line with the completion date and evidence paths
- [ ] T069 Write `README.md` at the repository root: what this is, quickstart pointer, gates command, pointer to `docs/roadmap.md`
- [ ] T070 Run `uv run python scripts/check.py` and `uv run pytest -m visual` one final time; run quickstart.md end to end; commit `feat(s1): event spine and stubbed loop`

---

## Dependencies and execution order

- Phase 1 first (T001 before T007; T002 to T006 in parallel).
- Phase 2 next: T008 to T013 (schema) before T022; T014 to T017 in parallel with the schema; T018 before T022; T019 to T021 in parallel; T022 before T024.
- US1 (Phase 3): stubs T025 to T030 in parallel after T018; T031 after them; T032 and T033 after T031; T034 after T024; T035 after T034; frontend T036 to T041 after T034 (T038 and T039 in parallel); T042 last.
- US2 (Phase 4) after US1's T034 and T041.
- US3 (Phase 5) after US1's T031 and T032; independent of the frontend.
- US4 (Phase 6) after US1's T041 and US3's T049 (fixed roster and timestamps).
- US6 (Phase 7) after US1's T034 (leak test runs a scenario); T058 and T059 in parallel.
- US5 (Phase 8) after T036 (shared stylesheet); T062 to T064 in parallel.
- Phase 9 last.

## Parallel examples

- Setup: T002, T003, T004, T005, T006 together.
- Foundation: T009 then T010, T011, T012, T013 together; T014, T015, T016, T017 together with the schema work.
- US1 stubs: T025 to T030 together.
- US1 frontend: T038 and T039 together while T036 and T037 are written.
- US6: T058 and T059 together.
- US5: T062, T063, T064 together.

## Implementation strategy

MVP is US1 plus US2 plus US3 (all P1): a demonstrable stubbed loop with replay and the evidence suite. Then US4 and US6 (P2) make the slice acceptable under constitution XIII and XVI. US5 (P3) completes the page set. The slice is complete only when T070 passes, per the roadmap's evidence list.

## Summary

- Total tasks: 70
- Setup 7, Foundational 17, US1 18, US2 5, US3 4, US4 6, US6 4, US5 5, Polish 4
- Parallel opportunities: 27 tasks marked [P]
