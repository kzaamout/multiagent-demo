# Quickstart: validate the seat model guide

Run from the worktree `multiagent-demo-guide`. The recorded runs live in the main checkout, so point `RUNS_DIR` there (the worktree has no `runs/` of its own).

## 1. Gates

```powershell
uv run python scripts/check.py; echo "exit $LASTEXITCODE"
uv run pytest -m visual
```

Read the exit code on its own line; do not pipe the gate into another command.

## 2. The page on real runs

```powershell
$env:RUNS_DIR = "C:\Users\Khobaib\OneDrive\Desktop\code\multiagent-demo\runs"
uv run uvicorn app.main:app --port 8010
```

Open `http://127.0.0.1:8010/settings` (log in if `DEMO_USERNAME` is set) and check:

- Under the title, the line defining instruction accuracy gives the number of recorded runs (385 or more on 2026-09-21).
- Every seat shows "Top open model" and "Top proprietary model". With the runs of 2026-09-21: Orchestrator qwen3.5 9b 98% (390 of 397 replies); Intake qwen3.5 9b 57%; Estimator qwen3.5 9b 44% and claude-sonnet-5 via Bedrock 94% (29 of 31 replies); Pricing qwen3.5 9b 94%; Writer qwen3.5 9b 40%; Reviewer gemma4 12b 98%. Every proprietary slot but the Estimator's reads "no runs yet".
- Each model button shows its model's figure after the name, for example "qwen3.5 9b, local 40% (100 of 248)" at the Writer.
- Move the Writer to gemma4 12b: the button reads "gemma4 12b, local 0% (0 of 12)". Move it back.
- The note at the foot says what instruction accuracy and behaviour accuracy measure and that neither looks at the price.
- Reload twice: the figures are the same, and the second load is instant.

## 3. Page and report agree

```powershell
$env:RUNS_DIR = "C:\Users\Khobaib\OneDrive\Desktop\code\multiagent-demo\runs"
uv run python scripts/model_report.py --write
```

In `docs/model-performance.md`, the "Top models per seat" table names the same models with the same percentages and counts as the page. No table heading says "First time" or a bare "Accuracy"; they read "Instruction accuracy" and "Behaviour accuracy". `docs/model-performance-runs.csv` keeps its column names (`git diff --stat` shows only new rows since the last refresh, no header change).

## 4. A new run shows up without a restart

Copy three finished run folders from the main `runs/` into an empty scratch folder, start a second server on it (`$env:RUNS_DIR` set to the scratch folder, `--port 8011`), and load Settings: the line under the title says 3 recorded runs. Copy a fourth folder in and reload: it says 4, with no restart. No timer runs on the page; the browser's network panel shows one `GET /api/seats` per load. A stub run adds nothing, because no seat in it made a model call.

## 5. Nothing touched a run

`git diff main --stat` shows no change under `app/schema/`, `datasets/`, `docs/schema/`, or `config/electrical-bid/seats/`, and the golden replay tests pass in step 1.
