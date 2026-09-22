# Quickstart: Lettered provenance markers

How to see and check the change. The marker rules are in [contracts/markers.md](contracts/markers.md).

## Prerequisites

- `uv sync` done; pandoc and Typst on the path (Pre-flight shows both); Chromium for Playwright installed.
- The scenario datasets present locally under `datasets/` for the golden replay tests.

## 1. The gates

```text
uv run python scripts/check.py
uv run pytest -m visual
```

Expected: both green. `check.py` includes the label rule, the compile tests (page text reads `[a]`, `markers.json` carries `label`), the golden compare suite and the em dash lint. The browser tests include the overlay showing letters on a fresh run and numbers on a golden replay.

## 2. See it on the Demo page

```text
uv run uvicorn app.main:app --port 8000
```

Set `AGENT_MODE=stub` first for a run in seconds; a live run shows the same thing. Open `/demo`, choose 01 · Clean run, press Run. When the pages appear:

- every figure on the page image has a small superscript letter after it, a, b, c in reading order, and no superscript digit;
- each round button over a marker shows the same letter, and hovering it highlights the source message in the feed;
- the Provenance table at the end lists a, b, c in its Marker column;
- Download PDF shows the same letters.

## 3. See an old recording keep its numbers

Choose 02 · Planted inconsistency and press Replay. Its pages were compiled before this change: the pages show numbers and the buttons over them show the same numbers.

## 4. The Reviewer's page text

In the run folder of step 2, open `runs/<id>/artifacts/v1/pages.json`. Each tagged figure reads with its letter in brackets, as in `$79,063.75 [a]`. Open the Reviewer's prompt with the prompt toggle: its instructions describe the markers as letters.

## 5. The Reviewer replay record

`evidence.md` beside this file records the 5 replayed Reviewer requests: which runs, the recorded verdict against the replayed one, and the markers each finding cites.

## The Introduction's pinned recording

The Introduction frame replays the run in `PUBLIC_RUN_ID`, by default `21b86b66`, recorded on 2026-09-21 with lettered markers (it replaced `f2dda488` from S4, whose pages show numbers). To pin another, set `PUBLIC_RUN_ID=<run id>` in `.env`, or change the default in `app/config.py` in its own commit, then open `/introduction` and check the frame shows letters.
