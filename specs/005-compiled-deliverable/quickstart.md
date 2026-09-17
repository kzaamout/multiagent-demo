# Quickstart: verify S4

Prerequisites: S3b setup, Typst 0.15.1 and pandoc 3.10.2 on the path (`typst --version`, `pandoc --version`), Ollama running with the seat models, AWS keys and `COST_CEILING=1.00` in `.env`. In the S4 worktree, `.env` also carries `DATASETS_DIR` and `RUNS_DIR` pointing at the main checkout.

## Gates

```
uv run python scripts/check.py
uv run pytest -m visual
uv run pytest -m compiler
```

The compiler tests skip, naming the tool, on a machine without Typst or pandoc.

## Pipeline alone

```
uv run python -c "from app.compile import tools_available; print(tools_available())"
uv run pytest tests/unit/s4 -q
```

Expected: both tools report a version; the fixture draft compiles to a PDF, page images, `markers.json` with one marker per tag and positions inside the page bounds, `pages.json` with one text per page, and the cover shows the wordmark for a dataset without a logo file.

## Stub run and goldens

```
uv run python scripts/regen_golden.py
uv run pytest tests/integration -q
```

Expected: every dataset's golden carries `artifact.compiled` with real paths after every `draft.committed`; the replay-and-compare suite passes on stage sequence and exit.

## From the Demo page

```
$env:PYTHONUTF8 = "1"
uv run uvicorn app.main:app --port 8000
```

Open http://localhost:8000/demo.

1. **Pages appear.** Choose 01 Clean run, press Run. Expected: after the Writer commits, the artifact panel shows the pages with "v1" within ten seconds; markers are visible beside figures.
2. **Hover.** Hover a marker. Expected: the feed scrolls to the specialist message and highlights it; the highlight clears on leaving.
3. **Version swap.** Choose 02 Planted inconsistency, press Run, scroll the panel to page 2 during Review. Expected: after the rework, v2 replaces v1 in place with the scroll kept and no empty frame.
4. **Reviewer on pages.** Open the prompt toggle on the Reviewer's message. Expected: a Pages section listing the page images and the page text; no markdown section.
5. **Edit.** At Handoff press Edit, change one word, press Save. Expected: one more draft commit and one more compiled event with actor You, pages refresh, exit reviewer_pass, termination card shows the decision edit.
6. **Reject.** Run 01 again to Handoff, press Reject, enter notes. Expected: decision reject recorded with the notes, same exit, run terminated.
7. **Downloads.** After termination, press Download PDF and Download run timeline. Expected: the final PDF and a timeline PDF with one row per event.
8. **Replay.** Press Replay on 02. Expected: pages appear at the same moments as in the live run; with the datasets folder renamed away and Typst removed from the path, the replay still shows pages.

## Evidence to record

Run ids, elapsed time from `draft.committed` to `artifact.compiled`, spend per run, the screenshot comparison result, and the roadmap S4 status line.
