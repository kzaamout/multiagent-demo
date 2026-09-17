# Quickstart: validating S5

Run from the worktree root on branch `006-seats-single-chat`. The `.env` there points `RUNS_DIR` and `DATASETS_DIR` at the main checkout.

## Prerequisites

- `uv sync` done; Chromium for Playwright installed (`uv run playwright install chromium`).
- At least the Clean run dataset present under the datasets folder.
- For live checks: Ollama running with the seat models pulled; `COST_CEILING=1.00` in `.env`.

## Gates

```
uv run python scripts/check.py
uv run pytest -m visual
```

Expected: all gates green; the visual suite passes for the seven existing states plus `settings-dropdown` and `demo-terminated-chat`.

## Story 1, swap a seat

Scripted: `uv run pytest tests/integration/s5/test_model_swap.py -q`. Expected: a `model.changed` event between two dispatches, the next bundle on the new model, later actors carrying it, and a warning when the Reviewer joins the Writer's family.

Live: start the app, open `/settings`, move the Estimator to another available model during a Clean run. Expected: the row, the feed cards, and the meter change within a second; the Estimator's next prompt toggle shows the new model.

## Story 2, Single-model run

Scripted: `uv run pytest tests/integration/s5/test_single_run.py -q`. Expected: mode single, four stage changes, one dispatch and one completion, exit `single_complete`, the run replays, and the comparison route lists it.

Live: switch the composer to Single model, run Clean run, approve nothing (the run ends on its own). Expected: Plan and Review render bypassed, the Compare strip fills, and the comparison line shows both runs after a Team run exists.

## Story 3, meters

Open any agent meter on a terminated run. Expected: calls, tokens in and out, cost, wall time, latency, last event.

## Story 4, chat

Scripted: `uv run pytest tests/integration/s5/test_chat.py -q`. Expected: a reply from the scripted model using the seat's bundle, a 409 on an unpaused live run, and an identical digest of the run folder before and after.

Live: after a run, click Elena's card and ask why she chose a rating. Expected: an answer in the panel, the footer showing the chat's tokens and cost, the meters unchanged; close and reopen shows an empty panel.

## Evidence to record

Run ids and spend for one Team run and one Single-model run on the same dataset, in the roadmap S5 status entry; refresh `docs/model-performance.md` with `uv run python scripts/model_report.py --write`.
