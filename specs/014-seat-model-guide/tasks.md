---

description: "Task list for the seat model guide on Settings"
---

# Tasks: Seat model guide on Settings

**Input**: Design documents from `specs/014-seat-model-guide/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/seats-guide.md, quickstart.md

**Tests**: every change carries its test task, as in every slice before this one (constitution XIII). Browser tests carry `pytest.mark.visual`.

**Where**: all work happens in the worktree `../multiagent-demo-guide`, beside the main checkout, on branch `014-seat-model-guide`. Recorded runs are read, never written, from the main checkout's `runs/` by setting `RUNS_DIR` to that folder.

**Organization**: story labels map to spec.md: US1 see the best open and proprietary model beside each seat, US2 the figures do not overstate thin evidence, US3 the figures follow the runs without a restart, US4 the report says the same thing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)

---

## Phase 1: Setup

- [X] T001 In the worktree root, create the empty test packages `tests/unit/guide/__init__.py` and `tests/integration/guide/__init__.py`, run `uv sync` and `uv run python scripts/check.py`, capturing its exit code on its own line rather than through a pipe; create `specs/014-seat-model-guide/evidence.md` with a "Baseline" heading recording the result and the number of run folders under the main checkout's `runs/`

---

## Phase 2: Foundational

**Purpose**: the controlled records change first (constitution X), then the registry field, the seat needs, and the one calculation every surface takes its figures from.

- [X] T002 [P] Add decision 37 to `docs/roadmap.md` after decision 36: "Settings names the top open and proprietary model per seat" (2026-09-21, owner decisions 1a, 2b, 3a, 4a, 5c, 6a, 7a, 8a, 9a, 10a and clarifications B with a foot note and C; `specs/014-seat-model-guide/spec.md`), stating the figure (first attempts accepted over first attempts, every recorded run), the 5-run threshold, the Wilson ranking, the `weights` field, that the report's "First time" and "Accuracy" are relabelled "Instruction accuracy" and "Behaviour accuracy", and that no run, event or golden changes; no em dash
- [X] T003 [P] Amend `docs/spec-input.md`: set the version line to 0.8, add a "Changes from 0.7" paragraph for this feature (guide on Settings, the figure, the threshold, the ranking, the kind from the registry, the report relabelling), and append to section 2.3 two sentences saying that beside each seat the page names the top open and top proprietary model with its instruction accuracy and counts, shows the current model's figure in its model button, defines the figure under the title and explains both measures at the foot; no em dash
- [X] T004 [P] Add a section "Feature 014, seat model guide (2026-09-21)" at the end of `docs/design-deviations.md` with numbered items: the guide block under the model button and dependency note in the export's meta text style; the figure after the model's name in the button in the menu's note style, the button growing to two lines rather than cutting a long name; the second sub line under the title; the foot note; the unchanged column widths; and that the screenshot comparison hides these additions (research D10)
- [X] T005 [P] In `app/live/providers.py`, add `weights: str | None = None` to `ModelSpec` and read it in `ModelConfig.load`: absent gives `None`; a value other than `"open"` or `"proprietary"` raises `ValueError("model <key>: weights must be open or proprietary")`. In `config/models.yaml`, add `weights: proprietary` to bedrock-sonnet-5, bedrock-sonnet-4-6, bedrock-haiku-4-5, gemini-2-5-pro, gemini-3-8-flash and grok-4-6, and `weights: open` to llama3-1-8b, qwen3-5-9b, gemma4-12b, granite4-1-8b, qwen3-5-4b and deepseek-r1-14b, with one comment at the first use: "open: published weights anyone can run; proprietary: served only by its vendor (spec 014)"
- [X] T006 [P] Tests for T005 in `tests/unit/guide/test_registry_weights.py`: every model in the real `config/models.yaml` has `open` or `proprietary`; every `ollama` model there is `open` and every other is `proprietary`; a YAML written to `tmp_path` with `weights: shareware` raises the `ValueError` naming the model; a model without the key loads with `weights is None`
- [X] T007 [P] In `app/seats/definitions.py`, add `needs_image_input(agent_id: str) -> bool`: true for `single` and for any seat whose `sees` holds `DRAWING_PAGES` or `PAGE_TEXT`; one-line docstring saying the Estimator reads drawing pages and the Reviewer reads compiled pages as images. In `scripts/model_report.py`, make `seat_table()` call it instead of computing vision itself. Test in `tests/unit/guide/test_guide.py`: true for estimator, reviewer, single; false for orchestrator, intake, pricing, writer
- [X] T008 Create `app/runs/guide.py` with a module docstring naming spec 014 and rule 15. Move `metrics_of(folder)` from `scripts/model_report.py` unchanged in behaviour (event log required; `metrics.json` used when it has `golden_match` and `stopped_run` in every seat row, otherwise `run_metrics(read_events(...))`; `OSError`/`ValueError` give `None`) and make the report import it. Add `MIN_RUNS_FOR_BEST = 5` (the report imports it and drops its own), `Z95 = 1.959963984540054`, `instruction_accuracy(first_time, replies) -> float | None` (`None` when replies is 0), `whole_percent(first_time, replies) -> int | None` (`int(f"{share * 100:.0f}")`), `wilson_lower(first_time, replies, z=Z95) -> float | None`, a frozen `SeatRecord(agent_id, model, runs, replies, first_time)` with `share`, `percent` and `bound` properties, `records(runs: Iterable[dict]) -> dict[tuple[str, str], SeatRecord]` summing seat rows by `(agent_id, model or "unknown")` and counting a run only when the row has calls or replies, `runs_called(runs) -> int` counting runs in which some seat made a call or a reply, and `SEAT_ORDER = ("orchestrator", "intake", "estimator", "pricing", "writer", "reviewer")`
- [X] T009 In `app/runs/guide.py`, add the picks per data-model.md: a frozen `SeatPick(status, record=None, model_key=None)` where status is `"pick"`, `"no_runs"` or `"too_few_runs"`; `pick(seat, kind, recs, config) -> SeatPick` where a candidate is a record for the seat whose label matches a registry model's `label` with `weights == kind` and, when `needs_image_input(seat)`, `image_input` true; "a candidate qualifies when `runs >= MIN_RUNS_FOR_BEST` (5) and `replies > 0`"; choice by highest `bound`, then most `replies`, then earliest position in `config.models`; `too_few_runs` when candidates exist and none qualifies, `no_runs` when there is no candidate. Add `current(seat, recs, config) -> SeatRecord | None` for the seat's effective model (`config.seat_spec(seat).label`), `None` when its record is missing or has 0 replies, and `unclassified(config) -> list[str]` of labels without `weights`, in registry order
- [X] T010 Tests for T008 and T009 in `tests/unit/guide/test_guide.py`, with a helper module `tests/unit/guide/support.py` offering `write_run(runs_dir, run_id, seats, *, finished=True)` that writes `events.jsonl` (one `run.started` line, plus `run.terminated` when finished) and a current-format `metrics.json` whose seat rows carry `agent_id`, `role`, `model`, `provider`, `calls`, `replies`, `accepted_first_time`, `corrections`, `stopped_run`, `reasons`, `checks`, `settings`, `instructions`, `tokens_in`, `tokens_out`, `wall_ms`, `est_cost`, `tool_calls`. Cover: `instruction_accuracy(0, 0)` is `None`; `whole_percent(212, 226) == 94`, `(29, 31) == 94`, `(100, 248) == 40`; `wilson_lower(13, 13)` rounds to 0.772 and `(390, 397)` to 0.964; records sum across settings and instruction versions; a row with no calls and no replies adds no run; each pick status; the tie order; a label missing from the registry never picked; an unclassified model never picked and listed by `unclassified`; a text-only model never picked at the reviewer or the estimator; `current` returns `None` for 0 replies

**Checkpoint**: one calculation, tested, with the registry stating each model's kind.

---

## Phase 3: User Story 1 - See the best open and proprietary model beside each seat (Priority: P1)

**Goal**: Settings shows, per seat, the two picks, the current model's figure in its button, the defining line under the title and the foot note.

**Independent Test**: load Settings on a seeded runs folder and read each seat's two lines, the button figures, the run count and the foot note.

- [X] T011 [US1] In `app/runs/guide.py`, add `class SeatGuide` built with a runs folder, with `table(config, exclude_run=None) -> dict` returning `{"runs": runs_called, "min_runs": 5, "seats": {seat: {"current": ..., "open": ..., "proprietary": ...}}}` in the JSON shapes of contracts/seats-guide.md section 2 (a pick is `{"status": "pick", "model_key", "model", "runs", "replies", "first_time", "percent"}`, other statuses `{"status": ...}` only, `current` a record object or `None`). For now it reads every folder (skipping names starting with `_` and the `exclude_run` folder) with `metrics_of` on each call; the cache comes in T021
- [X] T012 [US1] In `app/runs/registry.py`, create `self.guide = SeatGuide(self.settings.runs_dir)` in `Registry.__init__`; in `seat_table()`, call `self.guide.table(config, exclude_run=self.live.run_id if self.is_live() and self.live else None)` once, add `row["guide"]` to each seat row from its seat entry and `"guide": {"runs": ..., "min_runs": ...}` to the returned table; leave every existing key as it is
- [X] T013 [P] [US1] In `app/web/pages/settings.html`, add `<p class="page-sub guide-note" id="guide-note" data-part="guide-note"></p>` after `#settings-note`, and after `#settings-status` add `<p class="settings-foot" data-part="guide-foot">` holding the paragraph of contracts/seats-guide.md section 4 word for word
- [X] T014 [US1] In `app/web/static/js/settings.js`: inside the model button, after the label span, add `<span class="select-fig" data-part="select-fig">` with `{percent}% ({first_time} of {replies})` from `row.guide.current`, or `no runs yet` when it is `null`; after the three existing columns of each row, append `<div class="seat-guide" data-part="seat-guide">` with two `<div class="guide-line" data-kind="open|proprietary">` each holding `<span class="guide-kind" data-part="guide-kind">` ("Top open model", "Top proprietary model") and `<span class="guide-value" data-part="guide-value">` (pick: `{model} · {percent}% ({first_time} of {replies} replies)`; `no_runs`: `no runs yet`; `too_few_runs`: `none with 5 runs on this seat yet`); in `render()`, set `#guide-note` to "Instruction accuracy is the share of a seat's replies the Orchestrator accepted the first time it checked them against the seat's instructions. Figures from {runs} recorded runs." (`1 recorded run` for one). The page never divides or rounds; update the file's header comment to say the guide comes from the same table
- [X] T015 [P] [US1] In `app/web/static/css/app.css`, beside the Settings rules: `.seat-guide { grid-column: 2 / -1; display: grid; grid-template-columns: max-content 1fr; gap: 2px 12px; font-size: 13px; color: #75758a; }`, `.guide-line { display: contents; }`, `.guide-value { color: #212121; }`, `.select-fig` in the `.menu-note` style (12px, #75758a, `white-space: nowrap`), the model button allowed to wrap its label and figure onto two lines (`height: auto; min-height: 44px` and a wrapping flex container for label and figure, the chevron kept at the right), `.guide-note { margin-top: -16px; }` so the two sub lines sit together, and `.settings-foot { font-size: 13px; color: #75758a; max-width: 900px; margin-top: 12px; }`; no change to `.seat-row`'s column widths
- [X] T016 [US1] Integration test `tests/integration/guide/test_seats_guide_api.py`: an app built with the real `config/models.yaml`, every provider available, and a runs folder seeded through `tests/unit/guide/support.py` so that pricing has qwen3.5 9b at 212 of 226 over 6 runs and the estimator has claude-sonnet-5 via Bedrock at 29 of 31 over 5 runs; `GET /api/seats` gives the pricing open pick with `percent` 94 and counts, the estimator proprietary pick, `current` for the pricing seat, `guide.runs` equal to the seeded runs, and still carries `seats`, `models` and `note`; after `POST /api/seats/writer {"model": "gemma4-12b"}` the writer row's `current` is gemma4 12b's record
- [X] T017 [US1] In `tests/visual/masks.py`, add `HIDDEN: dict[str, tuple[str, str]]` mapping `settings` and `settings-dropdown` to the selector list `.seat-guide, .select-fig, .guide-note, .settings-foot` and the reason "seat model guide added by spec 014: changes every row's height, so no rectangle can mask it; checked by test_e2e_ui" with removed_in "kept"; in `tests/visual/capture_app.py`, inject `{selectors}{display:none!important}` for a state listed in `HIDDEN` together with `FREEZE`; run `uv run pytest -m visual tests/visual/test_screenshots.py` and confirm the Settings comparisons pass
- [X] T018 [US1] Browser test in `tests/visual/test_e2e_ui.py` (`pytest.mark.visual`): serve an app on a runs folder seeded as in T016 plus a writer record for the seat's current model, open `/settings`, and assert the pricing row's open line reads "Top open model" and "qwen3.5 9b, local · 94% (212 of 226 replies)", the estimator's proprietary line names claude-sonnet-5 via Bedrock with "94% (29 of 31 replies)", the writer's button shows its model's label followed by its figure, `#guide-note` ends "Figures from {n} recorded runs.", the foot note mentions both "Instruction accuracy" and "Behaviour accuracy", each agent card's model line is the model's label alone with no figure, the open Estimator menu's options hold no `.select-fig` and no percentage, and the page's JS makes exactly one `GET /api/seats` on load

**Checkpoint**: User Story 1 is demonstrable on the Settings page (SC-001).

---

## Phase 4: User Story 2 - The figures do not overstate thin evidence (Priority: P1)

**Goal**: thin records never win, and a slot with no qualifying model says why.

**Independent Test**: seed the spec's thin-evidence folder and read the picks through the API and on the page.

- [X] T019 [US2] In `tests/integration/guide/test_seats_guide_api.py`, add a test on a runs folder (run counts scaled down from the spec's example, reply counts kept, every count at or above the 5-run threshold where it matters) with, at the orchestrator, gemma4 12b at 13 of 13 over 8 runs and qwen3.5 9b at 390 of 397 over 12 runs; at the intake, one proprietary model with 4 runs; at the reviewer, llama3.1 8b (text only) at 20 of 20 over 6 runs and gemma4 12b at 18 of 20 over 6 runs; and no proprietary run at the pricing seat. Assert: orchestrator open pick qwen3.5 9b with percent 98; intake proprietary `too_few_runs`; pricing proprietary `no_runs`; reviewer open pick gemma4 12b, never llama3.1 8b
- [X] T020 [US2] In `tests/visual/test_e2e_ui.py`, extend the T018 test or add one on the T019 folder: the intake proprietary line reads "none with 5 runs on this seat yet" and the pricing proprietary line "no runs yet", and no line names a model with fewer than 5 runs

**Checkpoint**: SC-003 holds on the page and in the API.

---

## Phase 5: User Story 3 - The figures follow the runs without a restart (Priority: P2)

**Goal**: a reload picks up new runs, re-reads only what changed, and leaves out the run this app is running.

**Independent Test**: load, add a folder, reload; reload again with nothing changed and count folder reads.

- [X] T021 [US3] In `app/runs/guide.py`, give `SeatGuide` the per-folder cache of data-model.md: on each `table()` call, list the runs folder, take each folder's signature `(file name, st_mtime_ns, st_size)` from `metrics.json` or, when absent, `events.jsonl`, reuse the cached seat rows when the signature is unchanged, read with `metrics_of` only new or changed folders, drop folders that disappeared, and when the set of `(folder, signature)` pairs less `exclude_run` equals the last call's, return the last aggregated records without summing again (the picks for the current config are still worked out, since a swap changes `current`); no timer, thread or watcher
- [X] T022 [US3] Tests for T021 in `tests/unit/guide/test_guide.py`, counting `metrics_of` calls with `monkeypatch`: the first call reads every folder; a second call with nothing changed reads none and returns equal figures; a new folder is read alone and raises `runs`; a rewritten `metrics.json` is re-read; a deleted folder leaves the figures; an unfinished folder (no `metrics.json`) is re-read when its `events.jsonl` grows; `exclude_run` leaves that folder out and it counts on the next call without it
- [X] T023 [US3] Test in `tests/integration/guide/test_seats_guide_api.py`: with the registry's `live` set to an orchestrator stand-in whose `run_id` names a seeded folder and whose state is not terminated, `GET /api/seats` does not count that folder; once it is terminated, the next request counts it
- [X] T024 [US3] Measure on the main checkout's runs with `RUNS_DIR` set: time `Registry.seat_table()` cold and warm (three warm calls) and record both, with the folder count, in `specs/014-seat-model-guide/evidence.md` under "Load time" against the 1 second target of SC-004

**Checkpoint**: SC-004 and SC-005 hold.

---

## Phase 6: User Story 4 - The report says the same thing (Priority: P2)

**Goal**: the report carries the same picks from the same code and names both measures without ambiguity.

**Independent Test**: generate the report and the seat table from one runs folder and compare every pick, percentage and count.

- [X] T025 [US4] In `scripts/model_report.py`, import `metrics_of`, `MIN_RUNS_FOR_BEST`, `instruction_accuracy` and `whole_percent` from `app.runs.guide`; make `Group.first_time_rate` return `instruction_accuracy(...) or 0.0`; make every instruction accuracy cell in `table`, `best_local_table`, `local_model_table` and `seat_performance_table` use `whole_percent`, keeping "n/a" for no replies
- [X] T026 [US4] In `scripts/model_report.py`, relabel per contracts/seats-guide.md section 6: in `TABLE_COLUMNS` "Accuracy" becomes "Behaviour accuracy" with its definition kept in meaning, and "First time" becomes "Instruction accuracy" defined as "share of the seat's replies the Orchestrator accepted on the first attempt, where a reply the run stopped on counts as not accepted; the figure the Settings page shows"; the headers of `best_local_table`, `local_model_table` and `seat_performance_table`; the `rank_key` docstring; the `columns_document` headings "How Behaviour accuracy is scored" and "What Behaviour accuracy does not measure, and the price tables that do" and the ranking paragraph; the Best local model and price section sentences in `report()`. No bare "Accuracy" label remains in any generated table or heading. CSV field names do not change
- [X] T027 [US4] In `scripts/model_report.py`, add `top_models_section(runs, config) -> list[str]` built on `SeatGuide`'s aggregation for the given runs (no live run excluded) and `pick`, rendering the table of contracts/seats-guide.md section 5 for the six Settings seats in `SEAT_ORDER`, a slot without a pick showing the page's wording ("no runs yet" or "none with 5 runs on this seat yet") with empty figure cells, a paragraph using the page's definition of instruction accuracy, the threshold, the Wilson ranking and the `weights` field, and the line "Models not classified as open or proprietary: " with the `unclassified` labels or "none"; place it in `report()` after "What the columns mean" and before "Best local model per seat"
- [X] T028 [US4] Update `tests/unit/sweep/test_report_sections.py` for the new labels (`cell(..., "Behaviour accuracy")`, `cell(..., "Instruction accuracy")`) and add: no table header in a generated report is a bare "Accuracy" or "First time"; the CSV header row is unchanged; on a runs folder seeded with `tests/unit/guide/support.py`, every pick, percentage and count in `top_models_section` equals `SeatGuide(runs_dir).table(config)` for the same folder (SC-002)
- [X] T029 [US4] With `RUNS_DIR` set to the main checkout's `runs/`, run `uv run python scripts/model_report.py --write` to refresh `docs/model-performance.md`, `docs/model-performance-columns.md` and `docs/model-performance-runs.csv`; confirm the CSV header is unchanged; record in `evidence.md` under "Page and report" the six seats' picks from the report beside those from `Registry.seat_table()` on the same folder

**Checkpoint**: SC-002 holds on the real runs.

---

## Phase 7: Polish and cross-cutting

- [X] T030 [P] Add a pointer to `CLAUDE.md` under Pointers: "Top open and proprietary model per seat, shown on Settings and in the report from one calculation: `app/runs/guide.py`; each model's open or proprietary kind is `weights` in `config/models.yaml`"; no em dash
- [X] T031 Run `uv run python scripts/check.py` and `uv run pytest -m visual`, each exit code read on its own; record both results in `evidence.md` under "Gates"; fix anything red before going on
- [X] T032 Walk quickstart.md steps 2 to 5 against the main checkout's runs on port 8010, capture a 1920 by 1080 screenshot of `/settings` to `specs/014-seat-model-guide/settings-guide.png`, note the time from navigation to the guide lines being on screen (SC-004, as the browser sees it), and record what was seen in `evidence.md` under "Quickstart"
- [X] T033 Run `git status` and `git diff --stat main` in the worktree and confirm only files named in plan.md changed, nothing under `app/schema/`, `docs/schema/`, `config/electrical-bid/seats/` or any golden log, and no file from `runs/` or `datasets/`; do not commit until the owner asks

---

## Dependencies and execution order

- **Setup (T001)** first.
- **Foundational (T002 to T010)**: T002, T003, T004, T005, T007 in parallel; T006 after T005; T008 after T007; T009 after T005 and T008; T010 after T009. Blocks every story.
- **US1 (T011 to T018)**: T011, then T012; T013 and T015 in parallel with T011; T014 after T013; T016 after T012; T017 after T014 and T015; T018 after T014.
- **US2 (T019, T020)**: after US1's T016 and T018 (it extends their files); the rules themselves were built in T009.
- **US3 (T021 to T024)**: T021 after T011; T022 after T021; T023 after T012; T024 after T021.
- **US4 (T025 to T029)**: after Foundational; T027 after T011; T028 after T025 to T027; T029 after T028. Independent of US1 to US3 on the page side.
- **Polish (T030 to T033)** last.

## Parallel examples

- Foundational: T002 roadmap, T003 spec input, T004 deviations, T005 registry field, T007 seat needs, all different files.
- US1: T013 page markup and T015 styles while T011 builds the table.
- US4 can proceed beside US2 and US3 once T011 exists.

## Implementation strategy

- **MVP**: Phases 1 to 3. The Settings page shows the two picks, the current model's figure, the definition and the foot note, from the rules built in Foundational.
- **Then**: US2's tests pin the thin-evidence behaviour, US3 adds the cache and the live-run exclusion, US4 brings the report into line and refreshes it on the real runs.
- Each checkpoint leaves the gates green.
