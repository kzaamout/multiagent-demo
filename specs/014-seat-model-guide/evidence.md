# Evidence: Seat model guide on Settings

## Baseline

2026-09-21, worktree `multiagent-demo-guide` on `014-seat-model-guide` at `aa3e7d4` before any code change, `DATASETS_DIR` pointed at the main checkout's local datasets. `uv run python scripts/check.py` exit 0: ruff and format clean, mypy clean on 219 source files, pytest 549 passed, 1 skipped, the em dash lint and the `.env` leak test green. The main checkout's `runs/` held 389 run folders.

## Load time (SC-004)

`Registry.seat_table()` on the main checkout's `runs/` (391 folders, 390 runs that called a model), on the presenter laptop: first call 0.101 s, then 0.012 s, 0.013 s and 0.013 s with nothing changed, the cost of listing and statting the folders. The first call read every folder; the next three read none (`tests/unit/guide/test_guide.py::test_the_guide_rereads_only_folders_that_changed` pins that behaviour). In Chromium at 1920 by 1080 on the same runs, the guide lines were on screen 0.32 s after navigation on a fresh server and 0.11 s after a reload, against the 1 second target. The first call's 0.101 s benefits from the operating system's file cache; the research measured 0.36 s for a cold read of 389 folders.

## Page and report (SC-002)

`uv run python scripts/model_report.py --write` with `RUNS_DIR` at the main checkout's `runs/` and that checkout's `.env` loaded into the one process (so the model table's Available column says what the laptop can reach; it records presence, never a value). The CSV's header row is byte for byte the committed one. In one process, at one moment, the report's "Top models per seat" and `Registry.seat_table()` on the same 390 runs:

| Seat | Top open model (page and report) | Top proprietary model (page and report) |
|---|---|---|
| orchestrator | qwen3.5 9b, local, 98% (394 of 401) | no runs yet |
| intake | qwen3.5 9b, local, 56% (218 of 386) | no runs yet |
| estimator | qwen3.5 9b, local, 44% (155 of 349) | claude-sonnet-5 via Bedrock, 94% (31 of 33) |
| pricing | qwen3.5 9b, local, 94% (214 of 228) | no runs yet |
| writer | qwen3.5 9b, local, 40% (100 of 250) | no runs yet |
| reviewer | gemma4 12b, local, 98% (197 of 200) | no runs yet |

Every pick, percentage and count agreed. Another session was recording runs in the main checkout while this was measured, and a page load a few minutes earlier read the Intake at 219 of 386 over the same number of runs. The cause of that one-reply difference was not traced; the likely one is a run of that session counted from its event log before it ended (FR-012). The comparison above, made in one process at one moment, is the one that stands.

## Quickstart

- **Step 2, the page on the real runs.** Served in-process on the main checkout's `runs/` (390 runs), captured at 1920 by 1080 to `settings-guide.png`. The line under the title reads "Instruction accuracy is the share of a seat's replies the Orchestrator accepted the first time it checked them against the seat's instructions. Figures from 390 recorded runs." Every seat shows both lines; only the Estimator has a proprietary pick (claude-sonnet-5 via Bedrock, 94%, 31 of 33 replies). The Writer's button read "qwen3.5 9b, local 40% (100 of 250)"; moved to gemma4 12b it read "gemma4 12b, local 0% (0 of 12)" with the status line "Applied: the next run uses gemma4 12b, local.", and moved back it read 40% again. The Case Manager and Market Analyst rows carry no guide. The foot note names both measures and says neither looks at the price.
- **Step 3, page and report.** See "Page and report" above.
- **Step 4, a new run without a restart.** Three finished run folders copied to an empty scratch folder: the page read "Figures from 3 recorded runs." with one request to the API; a fourth folder copied in and the page reloaded read "Figures from 4 recorded runs." with one request; in 5 idle seconds the page made no request.
- **Step 5, nothing touched a run.** See "Gates" below and `git diff --stat main`.

## Gates

`uv run python scripts/check.py` exit 0 after the change, with `DATASETS_DIR` at the main checkout's datasets: ruff and format clean, mypy clean on 224 source files, pytest 574 passed, 1 skipped (549 at the baseline; the 25 new tests are in `tests/unit/guide/`, `tests/integration/guide/` and `tests/unit/sweep/test_report_sections.py`), the em dash lint and the `.env` leak test green.

`uv run pytest -m visual` exit 0 in 410 s: 35 selected, 35 passed, including `test_page_matches_export[settings]` and `[settings-dropdown]` against the export with the guide's additions hidden, and `test_e2e_ui.py::test_settings_names_the_top_models_beside_each_seat`. A first full run failed on that new test alone: it started its own Playwright while the module's page fixture held one, which Playwright refuses on one thread. It now opens a fresh context on the fixture's browser. After that change ruff, format, mypy (224 files) and the em dash lint (406 files) were rerun clean.

## What changed and what did not

`git diff --stat main` names only the files in plan.md. Nothing under `app/schema/`, `docs/schema/`, `config/electrical-bid/seats/` or any golden log changed, and no file from `runs/` or `datasets/` is tracked. No model was called and no run was started for this work. The regenerated CSV gained rows for runs recorded since its last refresh, including 6 on the `prospect-a` dataset id, which carry run metadata only.
