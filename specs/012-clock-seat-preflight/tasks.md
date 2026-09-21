---

description: "Task list for 012: presenter clock and seat-aware pre-flight"
---

# Tasks: Presenter clock and seat-aware pre-flight

**Input**: Design documents from `specs/012-clock-seat-preflight/`

**Prerequisites**: plan.md, spec.md, research.md (D1 to D14), data-model.md, contracts/http-api.md, contracts/ui.md, quickstart.md

**Tests**: Included. The spec's success criteria name browser tests, route tests, and a marker test (constitution XIII, XVI, XVII).

**Organization**: One phase per user story in priority order. User Story 1 (the clock) and User Story 2 (the dot) share no code and can be built in either order. User Story 3 (the recheck) builds on User Story 2's stored result and header policy.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1 to US3)
- Paths are relative to the repository root

## Path Conventions

Single web application: `app/` (engine, API, static pages), `tests/` (unit, integration, visual, fixtures), `docs/` and `.specify/memory/` (controlled documents).

---

## Phase 1: Setup (controlled documents first, constitution X)

**Purpose**: The documents that govern behaviour change before any code (principles X and XIX, research D13).

- [X] T001 Amend `.specify/memory/constitution.md` to 1.3.0: add to principle II the sentence "The Demo page's Elapsed figure is the one display-only clock: it advances between events from the working time the events give, freezes while the run waits on the human, stops at `run.terminated`, and no state, event, or other figure depends on it."; replace the Sync Impact Report with one for 1.2.0 to 1.3.0 (MINOR, owner decision 1 of 2026-09-21, principle II, no template change); set **Version** 1.3.0 and **Last Amended** 2026-09-21
- [X] T002 [P] In `CLAUDE.md` working rule 3, append "The one exception is the display-only Elapsed clock (constitution II)."
- [X] T003 [P] In `docs/spec-input.md` move to Version 0.8: add a "Changes from 0.7" paragraph (owner decisions of 2026-09-21: the Elapsed working-time clock and its holds, the termination card showing working time, one pre-flight row per model probed at the same time, the new Introduction recording, replays and family rows, the seat-aware dot with its red and amber lists, the recheck on a seat change; supersedes two S7 decisions: a seat swap no longer leaves the stored result alone, and a laptop may go green without a login pair); rewrite the meters strip sentence in 2.2 to say "elapsed working time, ticking each second while the run works, held while the run waits on the human, stopped at termination"; rewrite 2.4 to the per-model rows and the red, amber, green, and grey rules of research D8
- [X] T004 [P] Create `tests/unit/s12/__init__.py` and `tests/integration/s12/__init__.py`

---

## Phase 2: Foundational

None. The stories share no code, and each phase below carries its own prerequisites.

---

## Phase 3: User Story 1 - Elapsed ticks like a clock (Priority: P1) 🎯 MVP

**Goal**: `#elapsed` counts each second of working time in live runs and replays, holds during human waits, stops at the end, and the termination card shows the same figure.

**Independent Test**: `uv run pytest tests/visual/test_e2e_clock.py tests/integration/s12/test_run_clock.py -q` passes (quickstart, Story 1).

### Implementation for User Story 1

- [X] T005 [US1] In `app/orchestrator/clock.py` add `Clock.now_ts() -> str` returning `self.ts(self.elapsed_offset_ms())`; `VirtualClock` inherits it and so returns `ts(0)`
- [X] T006 [US1] In `app/main.py` add a helper `run_clock(orchestrator) -> dict[str, Any]` returning `{"now": orchestrator.clock.now_ts(), "pace": orchestrator.clock.pace}`; add it as `clock` to the `POST /api/runs` reply, and add `live_run_clock` to `/api/meta` (the helper's value when `registry.is_live()` and `registry.live`, else `None`) per `contracts/http-api.md`
- [X] T007 [P] [US1] Create `app/web/static/js/clock.js` exposing `window.S1Clock.valueAt(clock, anchor, nowMs)`: with no anchor or `!clock.running` return `clock.workMs`; live anchor `{kind:'live', runNowMs, pace, receivedAt}` returns `clock.workMs + Math.max(0, anchor.runNowMs + (nowMs - anchor.receivedAt) * anchor.pace - clock.lastTsMs)`; replay anchor `{kind:'replay', arrivedAt, speed}` returns `clock.workMs + Math.max(0, (nowMs - anchor.arrivedAt) * anchor.speed)`; no timer, no DOM, no state (data model, "Clock anchor")
- [X] T008 [US1] In `app/web/pages/demo.html` load `/static/js/clock.js` after `reducer.js` and before `render.js`
- [X] T009 [US1] In `app/web/static/js/reducer.js` replace `view.elapsedMs` with `view.clock = { workMs, lastTsMs, running, ended, workAtHandoffMs }` worked out from the events by the hold table in `data-model.md`: holds `ask:<event_id>` (open at `clarification.asked` without `blocker`, closed by the `clarification.answered` that answers the last of its `question_ids`), `blocker:<blocker_id>` (open at `clarification.asked` with `blocker`, closed by `clarification.answered` whose `question_id` is the blocker id), `pause` (`run.paused` to `run.resumed`), `handoff` (`handoff.ready` to `human.approved`); held time is the union of open intervals; `run.terminated` closes every hold; `workMs` never decreases between events; keep the reducer free of timers and update its header comment to say the clock view is derived here and advanced only by `clock.js`
- [X] T010 [US1] In `app/web/static/js/render.js` write `#elapsed` from `F.fmtClock(ui.clockShownMs)` (set by `demo.js`, T011) instead of `view.elapsedMs`; in `terminationCard` set `eyebrowMs` to `view.clock.workMs` when terminated and to `view.clock.workAtHandoffMs` while Handoff waits, and stop reading `summary.elapsed_ms` there
- [X] T011 [US1] In `app/web/static/js/demo.js` hold the clock anchor and `shownMs` in presentation state: on `startRun` take `data.clock` as a live anchor (`runNowMs = F.tsMs(clock.now)`, `receivedAt = performance.now()`); on attach to `meta.live_run_id` take `meta.live_run_clock`; in `onEvent` during a replay, and in `playPublic` for each event it plays, set a replay anchor with `arrivedAt = performance.now()` and the chosen speed; `?golden=` and `?run=` views set no anchor; `resetView` clears the anchor and `shownMs`; one `setInterval` of `250 / speed` ms (250 ms for a live run) runs only while the latest `view.clock.running` is true and an anchor exists, computes `Math.max(shownMs, S1Clock.valueAt(...))`, and writes `#elapsed` only when the shown second changes; clear the interval on `run.terminated` and on reset; on `visibilitychange` recompute at once; expose `window.__s1.clock = { anchor, shownMs }` (`contracts/ui.md`)

### Tests for User Story 1

- [X] T012 [P] [US1] Create `tests/integration/s12/test_run_clock.py`: `POST /api/runs` on a stubbed dataset returns `clock.now` in the event `ts` format and `clock.pace == settings.stub_pace`; `/api/meta` carries `live_run_clock` during that run and `null` when no run is live; `Clock.now_ts()` advances with `pace` and `VirtualClock.now_ts()` is `ts(0)`
- [X] T013 [US1] Create `tests/visual/test_e2e_clock.py` (marker `visual`, Playwright `page.clock.install()`): (a) for every dataset's golden log, load `/demo?golden=<id>` and assert through `S1Reducer.reduce` in the page that `view.clock.workMs` at each prefix matches a Python reimplementation of the hold table in the test, and that the final `workMs` equals the termination card's elapsed text (SC-011); (a2) feed `S1Reducer.reduce` hand-built event lists and assert `workMs`: a Pause alone, a Pause during an open question batch (the union is counted once), a blocker answered, a blocker escalated, and Handoff then `human.approved` then closing work; (b) replay `planted-inconsistency` at 1x with `page.clock.run_for(1000)` steps and assert `#elapsed` changes every second of run time, never decreases, and holds for the whole clarification wait, then resumes (SC-001, SC-002, FR-007); (c) the same at 4x advances four per second; (d) after `run.terminated` the text is unchanged after `run_for(10000)` (SC-003); (e) a stubbed live run reloaded mid-run shows a value within one second of the run's working time and keeps ticking (FR-009); (f) `?golden=` states do not change after `run_for(5000)`; (g) the Introduction's public replay (`/demo?public=1&run=<pinned>`) ticks between events and ends on the recording's working time
- [X] T014 [US1] Run `uv run pytest -m visual -k "demo_running or demo_terminated or replay_matches"`; where the `demo-running` or `demo-terminated` capture's elapsed text or termination eyebrow now differs beyond tolerance, add a `Rect` for that region in `tests/visual/masks.py` with reason "Elapsed shows working time, holds excluded (owner decisions 2 and 10, 2026-09-21)" and slice "012"

**Checkpoint**: The clock ticks, holds, and stops in live runs and replays; the termination card matches it.

---

## Phase 4: User Story 2 - The header dot reflects only what would hurt this demo (Priority: P1)

**Goal**: One row per model, the new recordings and family rows, schema 2 storage, and one header policy that every page uses against the seats in force.

**Independent Test**: `uv run pytest tests/unit/s12 tests/integration/s12/test_preflight_api.py -q` passes (quickstart, Story 2).

### Implementation for User Story 2

- [X] T015 [US2] Rewrite `app/preflight/result.py` to schema 2 (data model, "Stored pre-flight result"): `CheckResult(id, name, status, detail, elapsed_ms=0, checked_at="", subject=field(default_factory=lambda: {"kind": "fixed"}))`; `PreflightResult(run_mode, ran_at: str | None, checks: tuple[CheckResult, ...])` with no overall status and no counts; `SCHEMA = 2` and "Any other value fails to load; the page reads 'not run yet'"; `merge(result | None, rows, run_mode) -> PreflightResult` replacing rows by `id`, keeping `ran_at`, and creating a result with `ran_at: None` when none is stored; keep `load_result`, `save_result`, `format_stamp`; move `HeaderState` and `header_state` out to `app/preflight/header.py` (T017)
- [X] T016 [US2] Rewrite the row set in `app/preflight/checks.py` (research D6, D9): replace `provider_checks` with `model_checks(ctx)`, one `Check` per registry model in registry order with id `model:<key>`; a cloud row probes that model with `strands_probe` under `PROVIDER_TIMEOUT_S`, is `skip` with "No key in .env for <provider label>" (or "No AWS credentials" for Bedrock) when the provider is not available, names the row "<label> answers" and the detail "<short label> answered in <n> ms" or "<short label> did not answer (<ExceptionClass>)"; a local row is "<model_id> pulled in Ollama", reads the tags that the `ollama` row stored in `ctx.scratch`, fails with "not pulled" or "Ollama not reachable", and is `skip` in Cloud mode; the `ollama` row checks reachability only in Laptop mode and stores the tag set in `ctx.scratch`, and in Cloud mode keeps today's rule (fail naming the seats still on local models, else `skip` with `CLOUD_MODE_SKIP`) (spec FR-013); `check_env` records `subject = {"kind": "env", "login_missing": [...], "keys_missing": {provider: name}}` for every non-Ollama provider, never a value; add `check_intro_recording` (id `intro-recording`, "Introduction recording present") and `check_replays` (id `replays`, "Every dataset has a replay", naming any dataset with neither a recording nor a golden log) through two injectables on `CheckContext`, `intro_recording_present: Callable[[], bool]` and `datasets_without_replay: Callable[[], list[str]]`; every row sets `checked_at`; `checks_for` returns cloud model rows, `ollama`, local model rows, `typst`, `png`, `tunnel`, `disk`, `env`, `intro-recording`, `replays`
- [X] T017 [US2] Create `app/preflight/header.py`: `HeaderState(status, glyph, title)`; `family_row(config) -> CheckResult` (id `family`, "Reviewer and Writer on different model families", fails with the registry's `SHARED_FAMILY_WARNING` text when `family_of` matches); `env_on_read(row, config, run_mode) -> CheckResult` per data model "The env row on read"; `seats_on_model(config) -> dict[model_key, list[seat]]`; `header_state(result, config, run_mode) -> HeaderState` implementing research D8 exactly: red list, amber list (`tunnel`, `family`, `intro-recording`, `replays`), grey when nothing red or amber and no pre-flight has run or a seat model has no row, green otherwise with the count of failed rows that do not matter; titles in the four forms of research D8 with the stamp of the newest deciding `checked_at`; no credential in any title
- [X] T018 [US2] Rewrite `app/preflight/runner.py`: `run_preflight(ctx)` runs the cloud model checks with `asyncio.gather` alongside one sequential task for `ollama`, local rows, `typst`, `png`, `tunnel`, `disk`, `env`, `intro-recording`, `replays`, each through `_run_one`, then stores `PreflightResult(run_mode, ran_at=now, rows in checks_for order)`; `payload(result, config, run_mode, running) -> dict` per `contracts/http-api.md` (stored rows with the env row replaced by `env_on_read`, then `family_row`, `seats` on model rows, `passed` and `applicable` counted over every payload row including `family`, `stamp`, `header`); the pending payload lists every row `pending` with detail "Pending" and `header.status == "pending"`
- [X] T019 [US2] In `app/main.py` add `current_header() -> HeaderState` calling `header_state(load_result(cfg.runs_dir), registry.effective_config(), cfg.run_mode)` and use it in `page()`, `introduction_page()`, and `/api/meta`'s `preflight`; `build_preflight_context()` passes `intro_recording_present=lambda: bool(registry.events_for(cfg.public_run_id))` and `datasets_without_replay=lambda: [d for d in registry.datasets if registry.replay_source(d) is None]`; `GET /api/preflight` and `POST /api/preflight/run` return `payload(...)`
- [X] T020 [P] [US2] In `app/web/static/js/preflight.js` set the page's dot status, glyph, and title from `result.header`; delete `headerTitle` and `HEADER_GLYPH`; the confirmation still shows when `passed === applicable` and `applicable > 0`
- [X] T021 [P] [US2] Update `app/preflight/__init__.py` docstring and exports for schema 2, `header.py`, `payload`, and `merge`

### Tests for User Story 2

- [X] T022 [P] [US2] Create `tests/unit/s12/test_header_policy.py`: one case per line of research D8: an unused cloud model failing gives green with "1 unused model failed" (SC-004); a seat model failing gives red naming the model and seat; Laptop mode with no login pair is not red, Cloud mode is red (US2 scenarios 3, 4); a seat provider key missing is red naming the key only (US2 scenario 5); `typst`, `png`, `disk` red whatever the seats (US2 scenario 6); `ollama` failing is red only with a local seat in Laptop mode; a local seat in Cloud mode is red; each of `tunnel`, `family`, `intro-recording`, `replays` alone is amber and never red (SC-010); a seat model with no row gives grey naming it (US2 scenario 8); the same stored rows give different states for different seat configurations (US2 scenario 7)
- [X] T023 [P] [US2] Create `tests/unit/s12/test_preflight_rows.py`: model rows in registry order with ids `model:<key>`; a cloud model without a key is `skip` with the key-less line; a probe failure carries the exception class, never the message; local rows read one tags call; `env` subject lists names only; `intro-recording` and `replays` pass and fail through their injectables; schema 2 round trip; a schema 1 file loads as `None`; `merge` replaces by id and keeps `ran_at`; `run_preflight` starts every cloud probe before the first finishes (probes that wait on a shared `asyncio.Event`)
- [X] T024 [US2] Create `tests/integration/s12/test_preflight_api.py` with injected checks: the payload shape of `contracts/http-api.md`; with an unused model failing and everything else passing, the dot is green on `/demo`, `/settings`, `/preflight`, and `/introduction` and `/api/meta.preflight == "pass"` (SC-004); moving a seat onto that model through `POST /api/seats/{seat}` makes the next page load red without a rerun; Laptop mode with no login pair and a failing unused Gemini row is green (SC-009); a planted `.env` marker appears in no route body, page, or `runs/preflight.json` (SC-008)
- [X] T025 [US2] Update the S7 tests that assert schema 1, `essential`, `provider:<name>` rows, or `result.status` to the schema 2 shape, keeping each test's intent: `tests/unit/s7/test_preflight_checks.py`, `tests/unit/s7/test_preflight_runner.py`, `tests/integration/s7/test_preflight_api.py`, and `tests/unit/s7/test_run_mode.py` where it reads the Ollama row
- [X] T026 [US2] Rewrite `tests/fixtures/preflight-all-pass.json` and `tests/fixtures/preflight-one-fail.json` at schema 2 (research D12): two cloud model rows carrying the export's provider row names and detail texts, then `ollama`, `typst`, `png`, `tunnel`, `disk`, `env`, with the added rows after them; in the visual suite's server fixture that captures the `preflight-*` states (the module that calls `capture()` with `prepare`), build the app with an injected `model_config` whose seats are on those two models; run the three `preflight-*` visual states and add a `Rect` in `tests/visual/masks.py` over the rows below the export's last row with reason "rows added for every model, recordings, and model families (owner decisions 6 and 11, 2026-09-21)" and slice "012"

**Checkpoint**: The dot is green for this demo when only unused rows fail; red and amber follow research D8 on every page.

---

## Phase 5: User Story 3 - A seat change rechecks the chosen model (Priority: P2)

**Goal**: After a swap in Settings, the chosen model and the env row are rechecked, stored, and shown in the status line and the Settings dot without a reload.

**Independent Test**: `uv run pytest tests/integration/s12/test_recheck.py tests/visual/test_e2e_ui.py -k recheck -q` passes (quickstart, Story 3).

### Implementation for User Story 3

- [X] T027 [US3] In `app/preflight/runner.py` add `recheck(ctx, model_key) -> tuple[CheckResult, ...]`: for a cloud model its row; for a local model the `ollama` row then its pulled row; then the `env` row; each through `_run_one`; merge into the stored result with `merge` and save; raise `ValueError(f"unknown model {model_key}")` for a key not in the registry
- [X] T028 [US3] In `app/main.py` add `POST /api/preflight/recheck` with body model `RecheckRequest(model: str)`: holds the shared `asyncio.Lock` (waits for a running full pre-flight or recheck, FR-024), replies `{ "checks": [rows as in the payload], "header": current_header() }`, 400 on an unknown key; change `POST /api/preflight/run` to refuse with 409 only while `app.state.preflight_running` (a full run) is set, and otherwise wait for the lock; the recheck emits no event and touches no run (FR-023)
- [X] T029 [US3] In `app/web/static/js/settings.js` after a successful swap set the status line to "Applied: the next run uses <label>. Checking <label>." (or the live-run form), then post `/api/preflight/recheck` with the model key; on the reply replace the second sentence with the model row's detail and, when it failed, " Pre-flight is red." when `header.status === 'fail'`; set `[data-part="preflight-indicator"]` status, glyph, and title from `header`; on a failed request write "The pre-flight recheck did not run: <error>."; the last reply wins; no timer (`contracts/ui.md`)

### Tests for User Story 3

- [X] T030 [P] [US3] Create `tests/integration/s12/test_recheck.py` with injected probes: a swap then recheck to a failing cloud model stores its failed row with a new `checked_at`, leaves every other row unchanged, and replies with a red header (US3 scenario 1); back to a passing model returns the reply's header to the state the other rows give (scenario 2); a local model rechecks `ollama` and its pulled row, not a probe (scenario 3); the env row is rechecked (scenario 4); a recheck started during a full run finishes after it (scenario 6); an unknown key is 400; during a stubbed live run a recheck adds no event, no `meter.update`, and nothing under the run's folder (scenario 5, SC-007); the reply carries no `.env` marker
- [X] T031 [US3] In `tests/visual/test_e2e_settings_recheck.py` (its own module, so its server can script the probes) add `test_settings_recheck_updates_the_dot_in_place`: with an app whose probe fails for one model, open `/settings`, move the Estimator to it, and assert the status line names the failure and the header dot's `data-status` becomes `fail` without a navigation; move it back and assert the dot leaves `fail` (SC-005)

**Checkpoint**: A seat change keeps the dot honest between full pre-flights.

---

## Phase 6: Polish and cross-cutting concerns

- [X] T032 [P] In `docs/design-deviations.md` replace the elapsed meter entry (the elapsed meter now ticks working time between events; the termination eyebrow shows working time) and add the pre-flight rows added below the export's rows, each with the masks from T014 and T026
- [X] T033 [P] In `README.md` rewrite the Pre-flight section's row table and dot paragraph to the per-model rows, the recordings and family rows, the red, amber, green, and grey rules, and the recheck on a seat change; remove "a provider no seat uses" from the orange list and say the login pair counts only in Cloud mode
- [X] T034 Run `uv run python scripts/check.py` and read its exit code on its own, not through a pipe; fix every red gate, including the em dash lint over the new files
- [X] T035 Run `uv run pytest -m visual` and fix every failure; confirm the golden replay suite passes unchanged (SC-007)
- [X] T036 Run one full pre-flight on the presenter laptop through `POST /api/preflight/run` and confirm it ends within 60 s with one row per model (SC-006) and a green dot in Laptop mode while the Gemini 2.5 Pro row and the login pair fail (SC-009); leave the live team run on the projector to the owner (quickstart, Story 1 live)

---

## Phase 7: Owner follow-up of 2026-09-21 (decisions 12 and 13)

**Goal**: Compute time on the Compare strip, the comparison line, and the run timeline, the same working time the clock shows.

**Independent Test**: `uv run pytest tests/unit/s12/test_working_time.py tests/integration/s12/test_comparison_time.py -q` and `uv run pytest -m visual tests/visual/test_e2e_clock.py` pass.

- [X] T037 [US1] Create `app/runs/working_time.py` with `working_times(events) -> list[int]` and `working_ms(events) -> int` implementing the hold table of `data-model.md` exactly as `reducer.js`'s `WorkClock` does, with timestamps taken to whole milliseconds without floating point
- [X] T038 [US1] In `app/runs/comparison.py` add `"working_ms": working_ms(events)` to `_figures`; keep `elapsed_ms`
- [X] T039 [US1] In `app/web/static/js/render.js` make the Compare strip summary, the Single-model line, and the comparison line read `working_ms`, falling back to `elapsed_ms` for a figure without it
- [X] T040 [US1] In `app/compile/timeline.py` print each event's working time from `working_times` in the Time column
- [X] T041 [P] [US1] Create `tests/unit/s12/test_working_time.py`: the hand-built cases of T013 (a2) give the same values in Python; the timeline's Time column shows working time after a clarification wait
- [X] T042 [P] [US1] Create `tests/integration/s12/test_comparison_time.py`: a recorded planted inconsistency Team run's comparison figures carry `working_ms` equal to `working_ms(events)` and shorter than `elapsed_ms` by the clarification and approval waits (SC-012)
- [X] T043 [US1] In `tests/visual/test_e2e_clock.py` check the page's reducer against `app.runs.working_time.working_times` instead of the test's own copy of the rule, and add a case that sets a comparison with `working_ms` and asserts the comparison line prints it
- [X] T044 Update `docs/design-deviations.md` (012 decision 2 covers the Compare strip and the timeline) and run `scripts/check.py` and the visual suite

## Dependencies and execution order

- **Setup (T001 to T004)**: first. T001 before any code (principle X).
- **US1 (T005 to T014)**: after Setup. T005 before T006; T007 and T009 before T010 and T011; T013 and T014 after T011.
- **US2 (T015 to T026)**: after Setup, independent of US1. T015 before T016 and T017; T016 and T017 before T018; T018 before T019; tests after T019.
- **US3 (T027 to T031)**: after US2 (it uses `merge`, `header_state`, and the payload rows).
- **Polish (T032 to T036)**: after the stories it documents or gates.

## Parallel opportunities

- T002, T003, T004 alongside each other after T001.
- In US1: T007 (clock.js) alongside T009 (reducer); T012 alongside T013.
- In US2: T020 and T021 alongside T019; T022 and T023 alongside each other.
- US1 and US2 as a whole alongside each other; they touch different files except `app/main.py` (T006 and T019 edit different functions).
- T032 and T033 alongside each other.

## Implementation strategy

1. **MVP**: Setup, then US1. The clock is what the prospect sees. Demonstrable on its own from the Demo page with any replay.
2. **Increment 2**: US2. The dot means "this demo will work". Demonstrable from the Pre-flight page and any header.
3. **Increment 3**: US3. The dot stays honest after a seat change. Demonstrable from Settings.
4. Polish and gates, then the owner's live checks.
