---

description: "Task list for slice S3, failure paths and presenter controls"
---

# Tasks: Failure paths and presenter controls (S3)

**Input**: Design documents from `specs/003-failure-paths-controls/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/controls.md, quickstart.md

**Tests**: requested by the owner ("include tests with each change"); every change carries its test task.

**Live runs**: every live verification run starts from the Demo page with the server started under `COST_CEILING=1.00`, and is checked with `scripts/compare_run.py`. Golden logs are never edited to fit a run.

**Organization**: phases follow the plan's delivery order (engine, page, datasets, live verification, review and records). Story labels map to spec.md: US1 Planted inconsistency, US2 Missing sheet, US3 Not ready, US4 Missing price, US5 Pause and Stop, US6 Dry intake, US7 Cost ceiling, US8 derived datasets.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)

---

## Phase 1: Setup

- [x] T001 Create test packages `tests/integration/s3/__init__.py` and `tests/unit/s3/__init__.py`
- [x] T002 [P] Write `scripts/compare_run.py`: take a run id, read `runs/<run_id>/events.jsonl`, find the dataset from the `run.started` payload, compare with `datasets/<dataset>/golden-events.jsonl` through `app.runs.golden.compare`, print transitions, exit, retries, clarifications asked, blockers raised, and estimated cost, and exit 1 on a mismatch; test it in `tests/unit/s3/test_compare_run.py` on a deterministic stub run written to a temporary runs folder

---

## Phase 2: Foundational

- [x] T003 The registry hands each run's asyncio task to its Orchestrator (`attach_task`) so Stop can cancel it, in `app/runs/registry.py` and `app/orchestrator/orchestrator.py`; test that the task is attached in `tests/integration/s3/test_controls.py`

**Checkpoint**: controls and datasets can proceed.

---

## Phase 3: User Story 5 - Pause and Stop a live run (Priority: P1)

**Goal**: the presenter pauses, resumes, and stops any run, and each action is an Orchestrator event or the termination.

**Independent Test**: start a slow stub run, pause during Work, check no dispatch while paused, resume, stop; exit `stopped` within 5 s; last event is `run.terminated`.

- [x] T004 [US5] Tests in `tests/integration/s3/test_controls.py`: pause emits `run.paused` with payload `{"by": "human"}` and a reason; no `task.dispatched` between `run.paused` and `run.resumed`; resume emits `run.resumed` with `{"by": "human"}`; pause is ignored while waiting on a human, at Handoff, and after termination; Stop during a scripted seat call that never yields ends with exit `stopped` within 5 s and no event after `run.terminated`; Stop while waiting on a clarification ends `stopped` with no `clarification.answered`
- [x] T005 [US5] Emit `run.paused` and `run.resumed` through the serialised emitter from `pause()` and `resume()`, ignoring pause while `pending_human` is set or the run has ended, in `app/orchestrator/orchestrator.py` (research D2); add reasons `paused` and `resumed` to use
- [x] T006 [US5] Stop cancels the attached run task and the work stage's child tasks; `run()` catches the cancellation that follows a stop request, terminates with `stopped` under `asyncio.shield`, and late results are discarded, in `app/orchestrator/orchestrator.py` (research D1)
- [x] T007 [P] [US5] API tests for `POST /api/runs/{id}/pause`, `/resume`, `/stop` returning 202 and producing the events of `contracts/controls.md`, in `tests/integration/s3/test_controls_api.py`
- [x] T008 [US5] Enable Pause and Stop per the control-state table in `data-model.md`: Pause reads Resume while paused by the presenter; both disabled when idle, waiting on a human (Pause only), ended, or in replay and fixed states; wire the buttons to the routes; in `app/web/pages/demo.html`, `app/web/static/js/demo.js`, `app/web/static/js/render.js`
- [x] T009 [US5] Browser test in `tests/visual/test_e2e_controls.py`: a slow stub run; Pause shows the paused note and the Resume label; Resume continues; Stop ends with the stopped termination card; buttons disabled after the end and in a replay
- [x] T010 [US5] Run `uv run pytest -m visual` and confirm the screenshot comparison still passes with controls disabled in fixed states

**Checkpoint**: US5 works on stubs and in the browser.

---

## Phase 4: User Story 8 - Four failure datasets derived from Clean run (Priority: P1)

**Goal**: scenarios 2 to 5 have real inputs with one documented planted change each.

**Independent Test**: `tests/integration/s3/test_failure_datasets.py` passes and each dataset reports `mode: live` from `/api/datasets`.

- [ ] T011 [US8] Planted inconsistency: copy `datasets/clean-run/source/` to `datasets/planted-inconsistency/source/`; in `E-002.typ` change the header to "Main: 200 A main breaker" and remove schedule note 3; in `E-001.typ` remove note 2 ("Ratings on this diagram agree"); compile all PDFs into `datasets/planted-inconsistency/inputs/`; copy the Clean run price list to `fixtures/`; rewrite `README.md` with E-002 200 A against E-001 225 A, the expected sequence, exit `reviewer_pass` with retry count 1, presenter note, build commands
- [ ] T012 [P] [US8] Missing sheet: copy the sources to `datasets/missing-sheet/source/`; add panel LP-2 (30-circuit, 100 A, surface, staff workroom, fed from LP-1 by a 100 A three-pole breaker and "Feeder, 4C plus ground, 100A in EMT", schedule "see E-003") to `E-001.typ`; list E-003 "Panel Schedule LP-2" in the `E-000.typ` index and add "30-circuit panelboard, 100A, surface", "Feeder, 4C plus ground, 100A in EMT", and "100A 3-pole breaker" to its materials schedule; in `E-002.typ` put the LP-2 feeder breaker on circuits 14, 16, 18 and leave circuit 8 as lobby receptacles only; in `E-102.typ` tag the four program room receptacles LP-2-1; do not create E-003; compile into `inputs/`; copy the price list; rewrite `README.md` naming LP-2 and the absent E-003, exit `blocker_escalated`
- [ ] T013 [P] [US8] Missing price: copy Clean run sources and compiled inputs unchanged; write `datasets/missing-price/fixtures/supplier-prices.csv` without the `Exit sign, LED` row; rewrite `README.md` naming the removed item, exit `reviewer_pass` with retry count 0 and a possible minor finding
- [ ] T014 [P] [US8] Not ready: copy the sources; in `invitation-to-tender.typ` remove the closing date and time from section 3 and the date from section 6, keeping section 2's reference to the Division 26 specification; compile the invitation and the drawings into `datasets/not-ready/inputs/` without `division-26-specification.pdf`; copy the price list; rewrite `README.md`, exit `not_ready`
- [ ] T015 [US8] Integrity tests in `tests/integration/s3/test_failure_datasets.py`: each dataset is curated and legible with no em or en dashes; Planted inconsistency has 200 A main breaker on E-002 and 225 A on E-001 and otherwise the Clean run schedule; Missing sheet names LP-2 on E-001 and E-000 with no E-003 file; Missing price lacks exactly `Exit sign, LED`; Not ready has no closing date and no specification file while its invitation lists the specification
- [ ] T016 [US8] Update `datasets/README.md` curation checklist for the four derived datasets

**Checkpoint**: datasets ready for live verification.

---

## Phase 5: User Story 3 - A request that is not ready stops in seconds (Priority: P1)

**Goal**: Not ready ends before Plan with both items listed.

**Independent Test**: live run from the Demo page matches the golden log; card lists deadline and specification.

- [ ] T017 [US3] Live run of Not ready from the Demo page; `uv run python scripts/compare_run.py <run_id>`; confirm the card lists the submission deadline and the Division 26 specification and that no specialist was dispatched; on a mismatch, diagnose from the recording and fix within the documented rules, then rerun
- [ ] T018 [P] [US3] Confirm the existing browser test for the not_ready card still passes in `tests/visual/test_e2e_ui.py`

---

## Phase 6: User Story 2 - A blocker pauses the run and asks (Priority: P1)

**Goal**: Missing sheet pauses on a blocker; Escalate ends with the missing list; Answer resumes.

**Independent Test**: live Escalate run matches the golden log; live Answer run resumes Work.

- [ ] T019 [US2] Scripted tests in `tests/integration/s3/test_blocker_live.py`: an Estimator blocker needing a human pauses with the blocker attached; Answer reaches only the Estimator's rework context and is not appended to the knowledge store; Escalate ends `blocker_escalated` with the description in the summary's missing list; a first route back to Intake reruns Intake and a second becomes a blocker
- [ ] T020 [US2] Live run of Missing sheet from the Demo page, press Escalate; `scripts/compare_run.py`; confirm the card names the LP-2 schedule; fix and rerun on a mismatch
- [ ] T021 [US2] Live run of Missing sheet, answer the blocker instead; confirm the run resumes at Work, record its exit, and confirm the knowledge file gained no entry

---

## Phase 7: User Story 1 - The Reviewer sends work back and the second draft passes (Priority: P1)

**Goal**: Planted inconsistency fails v1, routes to the Estimator, reworks, and passes v2.

**Independent Test**: live run matches the golden log with one backward Review to Work change and retry count 1.

- [ ] T022 [US1] Scripted tests in `tests/integration/s3/test_review_routing_live.py`: a fail routed to the Estimator dispatches only the Estimator with the findings in its bundle, then the Writer, then a passing review, matching the Planted inconsistency golden transitions; a fail routed to Assemble dispatches only the Writer; three fails end `retry_exhausted` with the unresolved findings
- [ ] T023 [US1] Live run of Planted inconsistency from the Demo page; `scripts/compare_run.py`; on a mismatch diagnose from the recording (Estimator concern, draft text, Reviewer finding and route) and adjust within documented rules; up to three runs, reporting how many matched

---

## Phase 8: User Story 4 - A missing price is disclosed, not invented (Priority: P2)

**Goal**: Missing price passes with the unpriced item disclosed.

**Independent Test**: live run matches the golden log; draft lists the exclusion.

- [ ] T024 [US4] Live run of Missing price from the Demo page; `scripts/compare_run.py`; confirm Pricing's unpriced exception for `Exit sign, LED`, the draft's exclusion, and any minor finding on the card

---

## Phase 9: User Story 6 - Dry intake before a meeting (Priority: P2)

**Goal**: the composer toggle ends a run after Intake with exit `dry_intake`.

**Independent Test**: toggle on, run Clean run; exit `dry_intake` with the verdict on the card.

- [x] T025 [US6] Add `dry_intake: bool = False` to `RunRequest` in `app/main.py`; `Registry.start_run(dataset_id, names, dry_intake)` sets the agent source's `dry_intake` for live and stub runs in `app/runs/registry.py`; tests in `tests/integration/s3/test_dry_intake.py` for a stub and a scripted live run ending `dry_intake` with the readiness verdict in the summary
- [x] T026 [US6] Enable the Dry intake toggle while idle and lock it while a run is live; send `dry_intake` with Run; in `app/web/pages/demo.html`, `app/web/static/js/demo.js`, `app/web/static/js/render.js`; browser test in `tests/visual/test_e2e_controls.py`
- [ ] T027 [US6] Live Dry intake run on Clean run from the Demo page; confirm exit `dry_intake` and the verdict on the card

---

## Phase 10: User Story 7 - A cost ceiling stops a run before it overspends (Priority: P2)

**Goal**: a breach ends the run with the spend shown.

**Independent Test**: ceiling below one Estimator call ends `cost_ceiling` with no dispatch after the breach.

- [x] T028 [US7] Termination card for `cost_ceiling` shows "Estimated spend" against the ceiling from `/api/meta` in `app/web/static/js/render.js`; browser test with a stub run at a low ceiling in `tests/visual/test_e2e_controls.py`
- [x] T029 [P] [US7] Scripted live test in `tests/integration/s3/test_cost_ceiling_live.py`: priced scripted seat usage passes the ceiling after the first Estimator call; exit `cost_ceiling`; no `task.dispatched` after the breach
- [ ] T030 [US7] Live check: restart the server with `COST_CEILING=0.02`, run Clean run from the Demo page, confirm exit `cost_ceiling` and the spend line; restart with `COST_CEILING=1.00`

---

## Phase 11: Polish and records

- [ ] T031 Live Pause, Resume, and Stop on Clean run from the Demo page: pause during Work, confirm no new thread while paused, resume, stop; confirm exit `stopped` within 5 s
- [ ] T032 Family-consistency review: capture the blocker card from the Missing sheet golden log, the paused composer, and the Dry intake toggle switched on at 1920 by 1080; review against the export's card and composer families; record findings and fixes in `docs/design-deviations.md`; update the Dry intake mask reason in `tests/visual/masks.py`
- [ ] T033 [P] Update `README.md` scenario notes and the quickstart if live runs changed anything
- [ ] T034 Update `docs/roadmap.md` S3 status with run ids, matches, and estimated spend; mark tasks done in this file
- [ ] T035 Run `uv run python scripts/check.py` and `uv run pytest -m visual`; commit
- [ ] T036 Show the slice in the browser: leave the verified runs viewable with `/demo?run=<id>` and report them to the owner

---

## Dependencies and execution order

- Setup (T001, T002) and Foundational (T003) come first.
- US5 (T004 to T010) depends on T003.
- US8 (T011 to T016) is independent of US5 and blocks US1 to US4 live runs.
- US6 (T025, T026) is independent of US8; T027 needs a live server.
- US7 (T028, T029) is independent; T030 needs a live server.
- Live verification order: T017, T020, T021, T023, T024, T027, T030, T031.
- Polish (T032 to T036) comes last.

## Parallel opportunities

- T002 alongside T003.
- T012, T013, T014 alongside T011 (different dataset folders).
- T007 alongside T005 and T006 once T004 exists.
- T018 alongside T017; T029 alongside T028.

## Implementation strategy

1. Engine and page controls (US5, US6 code, US7 card) with tests on stubs and the scripted model: no spend.
2. Derive and test the four datasets (US8): no spend.
3. Live verification, cheapest first: Not ready, Dry intake, cost ceiling, Stop and Pause, Missing price, Missing sheet, Planted inconsistency.
4. Review, records, gates, and the browser showing.

MVP: US5 plus US8 plus US3 shows the controls and the first failure path live at no model cost.
