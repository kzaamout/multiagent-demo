# Quickstart: Event spine and stubbed loop (S1)

## Prerequisites

- Python 3.13 and uv 0.9 on the path
- git (for the build stamp)
- Chromium for Playwright: `uv run playwright install chromium` (screenshot tests only)
- No model credentials are needed. `.env` may be absent.

## Setup

```
uv sync
```

## Run the application

```
set PYTHONUTF8=1
uv run uvicorn app.main:app --port 8000
```

Open http://localhost:8000/demo at 1920 by 1080.

## Validate end to end

1. Choose `01 · Clean run`, press Run. Watch the loop strip, feed, meters, and raw drawer. Press Approve on the termination card. The card closes with your decision and the raw drawer's last line is `run.terminated`.
2. Choose `02 · Planted inconsistency`, press Run. The run pauses on the waiting-on-you banner with two questions. Submit. Watch the Review to Work arrow fire, the retry badge tick to 1 of 2, and the pass. Approve.
3. Choose `03 · Missing sheet`, press Run. The blocker card appears. Press Escalate. The termination card lists the missing sheet.
4. Choose `05 · Not ready`, press Run. The run stops in seconds listing the deadline and the specification.
5. Choose `06 · Prospect own`, press Run. Intake completes and the run ends with exit `dry_intake`.
6. Press Replay at 4x on any dataset. The same events arrive with the same ids.
7. Click any agent message's prompt toggle. Click any Orchestrator note to see its reason.

## Quality gates

```
uv run python scripts/check.py
```

Runs, in order: ruff, mypy (schema and orchestrator at minimum), pytest, the em-dash lint over tracked files and `runs/`, and the `.env` leak test. Exit code is non-zero on the first failure.

## Golden logs

Regenerate all six from the stubs (only when a stub is deliberately changed):

```
uv run python scripts/regen_golden.py
```

The replay-and-compare suite is `tests/integration/test_golden_compare.py`.

## Screenshot comparison and browser tests

```
uv run playwright install chromium              # once
uv run python scripts/capture_export.py         # re-renders the export bundles to tests/visual/reference/
uv run pytest -m visual                         # screenshot comparison and end-to-end clicks in Chromium
```

Reference captures live under `tests/visual/reference/` and are committed. Diff overlays are written to `tests/visual/output/`. Masks for regions deferred to later slices are listed with reasons in `tests/visual/masks.py`.

## Page parameters for inspection

- `/demo?golden=<dataset>&upto=<seq>` renders a fixed state from the committed golden log.
- `/demo?run=<run_id>` renders a recorded run from `runs/<run_id>/events.jsonl`.
- `/demo?pin=export` starts runs with the export's names (Oscar, Anna, Elena, Pavel, Willa, Rafael) instead of random ones.
- `/demo?dataset=<dataset>` preselects a dataset.
