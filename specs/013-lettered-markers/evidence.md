# Evidence: Lettered provenance markers

## Baseline

2026-09-21, worktree `multiagent-demo-markers` on `013-lettered-markers` at `7a75a68` before any code change, `DATASETS_DIR` pointed at the local datasets. Typst 0.15.1, pandoc 3.10.2. `uv run python scripts/check.py` exit 0: ruff, format, mypy clean on 217 source files, pytest 535 passed, 1 skipped, em dash lint and the `.env` leak test green.

## Pages, table, overlay and old recordings (SC-001 to SC-003)

- `tests/unit/s4/test_markers.py`: the label rule (1 a, 26 z, 27 aa, 52 az, 53 ba, 702 zz, 703 aaa), 1,000 distinct lowercase labels, `ValueError` below 1, the `#prov(n, "label", "src")` call, labels past z, and letters in the Provenance table.
- `tests/unit/s4/test_pipeline.py` (Typst): every `markers.json` entry carries `label == marker_label(n)`; the printed Provenance table lists the same labels in the same order; the Reviewer's page text reads `$79,063.75 [a]` with no bracketed number; a 30 marker draft prints `aa` to `ad`, and the text of the displayed PDF shows no tagged figure followed by an extra digit.
- `tests/visual/test_e2e_ui.py::test_marker_buttons_show_letters_and_an_older_recording_its_numbers`: a fresh Clean run shows on every button the letter `markers.json` stores; the same run served with `label` removed from `markers.json`, as every recording before this change is, shows the numbers.
- `test_every_marker_highlights_its_source_message` replays the Planted inconsistency golden, whose pages were compiled before the change: every marker still highlights its source message. `tests/integration/test_golden_compare.py`: 22 passed. No golden was re-recorded and no event payload or schema file changed.

## Reviewer replay (SC-004)

**Method.** A scratch script, not committed, took each recorded first review, compiled the recorded draft again with this branch's code (the dataset's brand, the recorded headlines and client), put the new page text in place of the recorded page text in the recorded context, replaced only the marker paragraph of the recorded instruction with the new one, and sent the new page images to the recorded model, `gemma4 12b, local`, at the recorded settings (temperature 0.2, `num_ctx` 16384, thinking off), through `SeatCall` and the seat's own parser. The recompiled pages matched the recorded ones word for word apart from the marker labels and one line that wrapped earlier because a letter is narrower than a number. All reviews were recorded on 2026-09-19 or 2026-09-20, after the bracketed page text (decision 26) and with the verified note in the context. Ollama had no other work; no sweep was running.

**The five chosen reviews (owner decision 8a).**

| Run | Dataset | Markers | Recorded | Replayed with letters |
|---|---|---|---|---|
| 860daf39 | planted-inconsistency | 33 | fail, the planted rating | pass |
| 3a08a493 | planted-inconsistency | 9 | fail, the planted rating | fail, the planted rating |
| f6d3fa2b | planted-inconsistency | 28 | pass | pass |
| 4430b85d | missing-price | 19 | pass | pass |
| a509601c | clean-run | 24 | pass | pass |

**The one difference, read and measured.** 860daf39's recorded failure is the demo's planted defect: the Assumptions name 225 A on the single-line diagram and 200 A on the panel schedule but do not list it as a clarification. The Assumptions passage carries no marker at all, so the letters change nothing the finding rests on. At temperature 0.2 the model is effectively deterministic for a given input, so the question was whether letters matter or whether this review turns on any change to its input:

| 860daf39, what was sent | Replays | Verdict |
|---|---|---|
| the recorded request, unchanged | 4, then 5 with seeds 1 to 5 | fail every time |
| letters: new instruction, page text and images | 4 | pass every time |
| only the new marker paragraph, numbered pages | 3 | pass every time |
| only the lettered page text, numbered images and instruction | 3 | pass every time |
| only the lettered page text and images, recorded instruction | 3 | pass every time |
| the recorded request with "specific, no em dashes" written "specific. No em dashes." | 2 | pass every time |
| the recorded request with the serial comma dropped from "praise, fix, or explain" | 2 | pass every time |

Two edits that have nothing to do with markers flip it the same way. This review's catch turns on the exact input, not on how markers are written.

**The planted defect across every comparable review.** To see whether letters move the catch rate rather than one review, all 12 recorded Planted inconsistency first reviews with both ratings on the page and the verified note were replayed as recorded and with letters. The recorded replays reproduced every recorded verdict.

| Run | Markers | Numbers (as recorded) | Letters |
|---|---|---|---|
| 03e79c7e | 13 | caught | caught |
| 0697dd53 | 4 | caught | caught |
| 0bc11b13 | 9 | caught | caught |
| 3a08a493 | 9 | caught | caught |
| 860daf39 | 33 | caught | missed |
| 999a7df6 | 4 | caught | caught |
| c034877b | 8 | caught | caught |
| 06739c94 | 12 | missed | missed |
| 4842da4f | 7 | missed | missed |
| 812f6764 | 18 | missed | missed |
| f6d3fa2b | 28 | missed | missed |
| fa5cd5ff | 45 | missed | caught |
| **Caught** | | **7 of 12** | **7 of 12** |

Ten verdicts are identical and two moved in opposite directions. The letters neither help nor hurt the catch; the Reviewer catching the planted defect in about 58 percent of first reviews is the standing fact, recorded here because the Planted inconsistency scenario depends on it.

**SC-004.** In every lettered replay with findings, the seven catches above, each finding is the planted rating, quoted from the Assumptions section. Zero findings read a letter as part of a figure, zero cite a marker by number, and none cites a marker at all, so no cited letter can be missing from its page. Met.

## Found along the way

The only app server running on this machine during the work, on port 8000, was started on 2026-09-17 12:42 without reload, so it serves code from before decision 26. Run 767e9d18, recorded today from it, handed the Reviewer page text with glued markers, such as a tender price read as $20,727.731, and the Reviewer context had no bracketed marker. With letters the same fallback would read $20,727.73a, which cannot be taken for a digit. The server needs a restart to serve current code.

## Gates

`uv run python scripts/check.py` exit 0 after the change: ruff, format and mypy clean on 217 source files, pytest 549 passed, 1 skipped, em dash lint and the `.env` leak test green. `uv run pytest -m visual` exit 0: 35 passed, none skipped, including the screenshot comparisons against the design export.

## The Introduction's pinned run

At the owner's request the same day, a fresh Planted inconsistency run was recorded on this branch's code and pinned. It was driven through the Demo page's API from a second server started in this worktree over the shared `runs/`, `datasets/` and `knowledge/` folders, because the restarted server on port 8000 serves the other session's branch, which does not carry this change. Seats on their committed defaults, `COST_CEILING=1.00`.

Run `21b86b66`: exit `reviewer_pass` on the first review, approved at Handoff, 89 events, 3.0 minutes, an estimated 0.31 USD. It asked no question, the knowledge file already holding the answer. Three pages and ten markers, a to j, all resolved; `markers.json` stores the labels; the Reviewer's page text carries ten bracketed letters and no bracketed number. The draft discloses the 225 A against 200 A discrepancy in its Assumptions and the Reviewer passed it, the same shape as the run it replaces, `f2dda488`. Played in the public frame at 4x, every button showed its letter.

It is now the default `public_run_id` in `app/config.py`; `.env` sets no `PUBLIC_RUN_ID`, so the default applies wherever this code runs.
