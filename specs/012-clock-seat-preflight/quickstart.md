# Quickstart: validating 012

Run from the repository root on branch `012-clock-seat-preflight`.

## Prerequisites

- `uv sync` done; Chromium for Playwright installed (`uv run playwright install chromium`).
- Typst and pandoc on the path (the compile rows).
- For the live checks: Ollama running with the seat models pulled, AWS credentials for Bedrock seats.

## Gates

```
uv run python scripts/check.py
uv run pytest -m visual
```

Expected: every gate green, the visual suite passes, the golden replay suite unchanged (SC-007).

## Story 1, the Elapsed clock

Scripted: `uv run pytest tests/visual/test_e2e_clock.py -q`. Expected, with Playwright's clock control:

- For every golden log, the reducer's working time at each event matches the hold rules in `data-model.md`, and the final value equals the termination card's figure (SC-011).
- A replay of the planted inconsistency log at 1x, then at 4x, changes `#elapsed` at every second of run time (four per second at 4x) and holds it through the clarification wait (SC-001, SC-002).
- A finished run keeps its final value for ten seconds (SC-003).
- A stubbed run reloaded mid-run shows the run's working time within one second and keeps ticking (FR-009).
- `?golden=` states never tick.

Live: start a live run on a dataset with a long Estimator call. Expected: Elapsed counts each second through the call, stops while the question banner is open, continues after Resume, stops at the termination card, and the card shows the same figure.

## Story 2, the header dot

Scripted: `uv run pytest tests/unit/s12 -q -k header` and `uv run pytest tests/integration/s12/test_preflight_api.py -q`. Expected: the policy table in research D8 holds case by case. An unused failing model leaves the dot green on Demo, Settings, Pre-flight, and Introduction (SC-004). Each amber condition alone gives amber (SC-010). The login pair counts in Cloud mode only. A schema 1 file reads as not run.

Live: on the presenter laptop in Laptop mode with no login pair, press Run pre-flight. Expected within 60 s (SC-006): one row per model in the Settings menu. If the Gemini 2.5 Pro entry still fails, its row is red with the error class, and the dot is green with a tooltip counting the unused failure (SC-009).

## Story 3, recheck on a seat change

Scripted: `uv run pytest tests/integration/s12/test_recheck.py -q`. Expected: a swap to a failing model moves the seat and stores the failed row with a new `checked_at`, and the reply's header is red. A swap to a local model rechecks `ollama` and the pulled row. A recheck during a full run waits for it. A recheck during a stubbed live run adds no event and no meter.

Live: in Settings move the Reviewer to a model whose probe fails. Expected: the status line says the model is being checked, then names the failure, and the dot turns red without a reload. Move it back: the dot returns to green. Move the Reviewer onto the Writer's family: the dot turns amber.

## Credentials

`uv run pytest tests/lint/test_env_leak.py tests/unit/s12 -q -k marker`. Expected: a planted marker in `.env` appears in no row, tooltip, stored result, or response (SC-008).
