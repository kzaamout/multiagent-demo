---

description: "Task list for lettered provenance markers"
---

# Tasks: Lettered provenance markers

**Input**: Design documents from `specs/013-lettered-markers/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/markers.md, quickstart.md

**Tests**: every change carries its test task, as in every slice before this one. Tests that need Typst or pandoc carry `pytest.mark.compiler`; browser tests carry `pytest.mark.visual`.

**Where**: all work happens in the worktree `C:\Users\Khobaib\OneDrive\Desktop\code\multiagent-demo-markers` on branch `013-lettered-markers` (owner decision 9a). Recorded runs are read, never written, from `C:\Users\Khobaib\OneDrive\Desktop\code\multiagent-demo\runs\`.

**Organization**: story labels map to spec.md: US1 a figure on the page reads as the figure, US2 every surface names the marker the same way, US3 recordings made before the change replay correctly, US4 the Reviewer is not thrown by the letters.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)

---

## Phase 1: Setup

- [X] T001 In the worktree root, run `uv sync`, confirm `typst --version` (0.15.1) and `pandoc --version` (3.10.2), and run `uv run python scripts/check.py` on the untouched branch, capturing its exit code separately from any pipe; record the baseline result in `specs/013-lettered-markers/evidence.md` under a "Baseline" heading

---

## Phase 2: Foundational

**Purpose**: the controlled records change first (constitution X), then the one function every surface takes its label from.

- [X] T002 [P] Add decision 36 to `docs/roadmap.md` after decision 35: "Provenance markers are letters" (2026-09-21, owner decisions 1a, 2a, 3b, 4a, 5a, 6a, 7a, 8a, 9a, 10b; `specs/013-lettered-markers/spec.md`), stating why (a superscript number reads as another digit of the amount), the rule (a to z, then aa, ab as spreadsheet columns count, all 26 letters), the four surfaces, that marker numbers, tag ids and payloads stay so no golden is re-recorded, and that recordings made before it keep their numbers; no em dash
- [X] T003 [P] Reword item 2 under the S4 heading in `docs/design-deviations.md`: the printed marker is a small superscript lowercase letter in the brand colour (a, b, c in reading order, aa after z), and the panel's 22 px circle shows the same letter, or the number for a recording made before 2026-09-21; keep the rest of the item
- [X] T004 Add `marker_label(n: int) -> str` to `app/compile/markers.py`: lowercase letters counted as spreadsheet columns ("1 a, 26 z, 27 aa, 28 ab, 52 az, 53 ba, 702 zz, 703 aaa"), all 26 letters, `ValueError` for `n` below 1; one-line docstring naming the rule
- [X] T005 Tests for T004 in `tests/unit/s4/test_markers.py`: the listed pairs, `ValueError` for 0 and -1, and 1 to 1000 giving 1000 distinct labels made only of the letters a to z

**Checkpoint**: the label rule exists in one place and is tested.

---

## Phase 3: User Story 1 - A figure on the page reads as the figure (Priority: P1)

**Goal**: the compiled PDF and page images print a letter after each tagged figure.

**Independent Test**: compile a draft with tagged figures; the displayed page shows a, b, c and no superscript digit.

- [X] T006 [US1] In `app/compile/markers.py`, add `label: str` to `MarkerDraft` (after `value`), set it with `marker_label(n)` in `prepare_markdown`, and write the raw call as `#prov(n, "label", "source_id")`, as in `` 36860.5`#prov(1, "a", "pricing")`{=typst} ``; update the module docstring to say the template renders a small superscript letter
- [X] T007 [US1] In `templates/rfp-response.typ`, change the marker function to `#let prov(n, label, src)`: the displayed compile prints `label` inside the same `super(text(size: 6.5pt, fill: brand, weight: 600)[...])`, the metadata keeps `(n: n, src: src, page, x, y)` unchanged; update the comment above it to say letter, keeping the history of why the text compile exists; no dollar sign in the comment (the file is a pandoc template)
- [X] T008 [US1] Update the expected strings in `tests/unit/s4/test_markers.py` (`#prov(1, "a", "pricing")`, `#prov(4, "d", "pricing")`) and its module docstring; add a test that the four markers of the existing table test carry labels a to d
- [X] T009 [US1] Add a compiler test in `tests/unit/s4/test_pipeline.py`: a draft with 30 tagged figures compiles; the `.typ` holds `#prov(27, "aa",` and `#prov(30, "ad",`; `markers.json` labels run y, z, aa to ad at the end; the text extracted from the displayed PDF (`app.live.documents.parse_pdf`) holds the first and last tagged prices and no tagged figure followed directly by an extra digit

**Checkpoint**: the displayed pages carry letters (SC-001).

---

## Phase 4: User Story 2 - Every surface names the marker the same way (Priority: P1)

**Goal**: the page, the overlay, the Provenance table and the Reviewer's page text show the same label for each marker.

**Independent Test**: compile a draft and compare, marker by marker, the four surfaces.

- [X] T010 [P] [US2] In `app/compile/markers.py` `appendix`, print `m.label` in the Marker column; update `test_appendix_lists_every_marker_and_names_unresolved_sources` and `test_with_appendix_extends_the_provenance_section_or_adds_it` in `tests/unit/s4/test_markers.py` to expect `| a | takeoff | ...` and `| b | ghost | unresolved |`
- [X] T011 [US2] In `app/compile/pipeline.py`, add `label: str` as the last field of `Marker` and set it from `d.label` in `_typst_markers`, so `markers.json` carries it after `y` (contract section 3); update the docstring of `_page_texts` to say the marker is written " [a]"
- [X] T012 [US2] In `templates/rfp-response.typ`, the text compile (`markers=text`) writes ` \[#label\]`; update `test_a_marker_is_never_read_as_part_of_its_figure` in `tests/unit/s4/test_pipeline.py` to expect "$79,063.75 [a]", "$79,063.75 [c]" and "45 troffers [b]", and assert no bracketed digit such as " [1]" remains
- [X] T013 [US2] Extend `test_every_tag_has_a_marker_inside_its_page` in `tests/unit/s4/test_pipeline.py`: every `markers.json` entry has `label == marker_label(n)`, and the prepared markdown's Provenance table lists the same labels in the same order
- [X] T014 [P] [US2] In `app/web/static/js/render.js` `placeMarkers`, set the button text to `m.label` when it is a non-empty string, else `String(m.n)`; keep `data-marker` as `String(m.n)`; update the comment above `loadMarkers` if it describes the number
- [X] T015 [P] [US2] Reword the first paragraph of `config/electrical-bid/seats/reviewer.md` per research R6: a small superscript letter in the page image and the same letter in square brackets in the page text, as in $79,063.75 [a]; $79,063.75 with marker a and with marker b are the same price; cite the page number and, for a figure, its marker letter; no em dash
- [X] T016 [US2] Add a browser test in `tests/visual/test_e2e_ui.py` (`compiler`): a Clean run stub run reaches its pages; every `.marker` button's text equals the `label` of the `markers.json` entry with the same `data-marker`, and every text is lowercase letters

**Checkpoint**: one label per marker across the four surfaces (SC-002).

---

## Phase 5: User Story 3 - Recordings made before the change replay correctly (Priority: P2)

**Goal**: an overlay over numbered pages shows numbers; the golden suite passes untouched.

**Independent Test**: serve a recording whose `markers.json` has no `label`; the buttons show the numbers.

- [X] T017 [US3] Extend the browser test of T016 in `tests/visual/test_e2e_ui.py`: copy the finished run into a second runs folder, rewrite its `markers.json` without `label` (as every recording before this change is), serve it with `_serve` as `test_pages_appear_for_a_stub_run_and_replay_without_datasets` does, open `/demo?run=<id>`, and assert each button's text equals its `data-marker`
- [X] T018 [US3] Run `uv run pytest tests/integration/test_golden_compare.py -q` and the golden replay browser test `test_every_marker_highlights_its_source_message`; both pass with no file under `datasets/` changed (`git status` shows nothing there, the datasets being local); record in `specs/013-lettered-markers/evidence.md`

**Checkpoint**: old recordings stay consistent with their own pages (SC-003).

---

## Phase 6: User Story 4 - The Reviewer is not thrown by the letters (Priority: P2)

**Goal**: 5 recorded reviews replayed on lettered pages, compared with what the Reviewer said the first time.

**Independent Test**: the replay record in `evidence.md` meets SC-004.

- [X] T019 [US4] Select 5 first reviews per research R7 from `C:\Users\Khobaib\OneDrive\Desktop\code\multiagent-demo\runs\`: recorded on or after 2026-09-19, Reviewer on `gemma4 12b, local`, a recorded `review.verdict` present, together covering a pass and a fail, two datasets, and one draft with more than 26 markers; list run id, dataset, draft version, marker count and recorded verdict in `specs/013-lettered-markers/evidence.md`
- [X] T020 [US4] Write the replay script in the session scratchpad (not committed): for each selected review, recompile that run's committed draft with `app.compile.compile_draft` into a scratch run folder with the dataset's brand, rebuild the recorded bundle with the page text materials replaced by the new `pages.json`, the system instruction from the new `reviewer.md` through `load_instructions`, and the new page images, then call `SeatCall` with the recorded model and parse with `parse_reply("reviewer", ...)`; check `runs/_sweep/` and Ollama's loaded models first and do not run while a sweep is in flight
- [X] T021 [US4] Run the replay; record in `specs/013-lettered-markers/evidence.md` for each review the recorded and replayed verdict, every marker each finding cites, whether any finding reads a letter as part of a figure or cites a marker by number, and the reason for any verdict that differs, found by reading the reply

**Checkpoint**: SC-004 met, or the failure recorded and the owner told before merging.

---

## Phase 7: Polish and closeout

- [X] T022 [P] In `docs/seat-flow.md` (Reviewer "Sees" row) write the example as $79,063.75 [a]; in `docs/seat-deep-dive.md` (Reviewer input) say each marker is written as its letter in brackets after its figure
- [X] T023 [P] Update comments that describe a marker as a number: `app/compile/__init__.py` module docstring ("numbered markers"), `app/compile/pipeline.py` module and `_page_texts` docstrings if not already done in T011
- [X] T024 Search tracked files for descriptions of markers as numbers (`superscript number`, `numbered marker`, `marker number`, `[1]` beside a price) and fix any current description found outside historical records; history in `docs/roadmap.md` decisions before 36, `specs/001` to `specs/012` and past evidence stays as written
- [X] T025 Run `uv run python scripts/check.py` (exit code captured on its own) and `uv run pytest -m visual`; both green; record the results in `specs/013-lettered-markers/evidence.md`
- [X] T026 Mark every task done in this file; confirm the branch is `013-lettered-markers` and `git status` shows only files this work changed; stage them by name; commit with the attribution line
- [X] T027 Merge `013-lettered-markers` into `main` with `--no-ff` from the worktree (main is not checked out elsewhere), after confirming `main` has not moved past `7a75a68` or merging its new commits cleanly; do not push

---

## Dependencies and execution order

- Phase 1 first. Phase 2 before any story: T006 needs T004.
- US1 (T006 to T009) before US2: T011 and T012 build on the new `#prov` signature and `MarkerDraft.label`.
- US3 (T017) extends the test of T016, so it follows US2. T018 can run any time after T012.
- US4 needs US1 and US2 done (it replays on the new pages and the new instruction).
- Phase 7 after all stories; T026 and T027 last.

## Parallel opportunities

- T002 and T003 (two documents) alongside T004.
- In US2: T010, T014 and T015 touch three different files.
- In Phase 7: T022 and T023.

## Implementation strategy

US1 alone makes the page right but leaves the table, overlay and Reviewer saying numbers, so US1 and US2 ship together as the minimum. US3 is a fallback that costs one expression and one test. US4 is a check, not a change: it gates the merge.
