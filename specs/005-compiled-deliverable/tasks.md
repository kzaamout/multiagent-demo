---

description: "Task list for slice S4, compiled deliverable and provenance"
---

# Tasks: Compiled deliverable and provenance (S4)

**Input**: Design documents from `specs/005-compiled-deliverable/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/compile.md, quickstart.md

**Tests**: every change carries its test task, as in S3 (owner rule "include tests with each change"; CLAUDE.md rule 8 for goldens). Tests that need Typst or pandoc carry `pytest.mark.compiler` and skip by tool name when it is absent.

**Live runs**: every live verification run starts from the Demo page with the server under `COST_CEILING=1.00` and is checked with `scripts/compare_run.py`. Golden logs are never edited to fit a run.

**Parallel S5 branch**: `app/main.py`, `app/web/static/js/render.js`, `app/web/static/js/reducer.js`, `app/web/static/css/app.css` and `app/schema/events.py` are touched only through new functions, new routes and new selectors. `events.py` is not touched at all in this slice.

**Organization**: phases follow the plan's delivery order (pipeline, engine, page, live verification, closeout). Story labels map to spec.md: US1 pages appear and refresh, US2 provenance markers, US3 Reviewer on pages, US4 Handoff actions, US5 brand on the cover, US6 interims removed and record whole.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)

---

## Phase 1: Setup

- [x] T001 Create packages `app/compile/__init__.py`, `tests/unit/s4/__init__.py`, `tests/integration/s4/__init__.py`; add `compiler` to `[tool.pytest.ini_options].markers` in `pyproject.toml` with the text "needs Typst and pandoc on the path"
- [x] T002 [P] Add `tools_available() -> dict[str, str | None]` in `app/compile/pipeline.py` (runs `typst --version` and `pandoc --version` with a 10 s timeout, returns version strings or None) and a `pytest_collection_modifyitems` extension in `tests/conftest.py` that skips `compiler` items with reason "compiler missing: <tool>" when either is None; test in `tests/unit/s4/test_tools.py` that the reason names the tool
- [x] T003 [P] Write the shared fixture draft `app/agents/stubs/fixtures/draft-fixture.md`: the markdown template sections filled with synthetic figures, at least eight `{{value|src:...}}` tags whose source ids match the stub specialists' short ids, one table with a tagged cell, a heading with a tag, and no em dash; test in `tests/unit/s4/test_fixture.py` that every tag parses with `app.tools.template.find_tags`
- [x] T004 [P] Record Typst 0.15.1, pandoc 3.10.2 and the reused career-hub pipeline in `docs/dependencies.md` with the problem solved and the cost of doing without (plan Verified versions table)

---

## Phase 2: Foundational (the pipeline)

- [x] T005 Write `templates/rfp-response.typ` as a pandoc Typst template: `#set page(paper: "us-letter")`, single column, a cover block using `$prospect-name$`, `$logo-path$` (image when non-empty, else a wordmark: the prospect name set large in `$primary-colour$`), `$primary-colour$` on headings, and the marker function `#let prov(n, src) = [#super(text(size: 7pt, fill: rgb("$primary-colour$"))[#n])#context [#metadata((n: n, src: src, page: here().page(), x: here().position().x.pt(), y: here().position().y.pt()))<prov>]]`; body at `$body$`; no em dash in any literal
- [x] T006 [P] Write `templates/run-timeline.typ`: Letter, single column, title "Run timeline" with `$run-id$` and `$dataset$`, body at `$body$`, table style for the event rows
- [x] T007 Write `app/compile/markers.py`: `prepare_markdown(markdown, sources) -> tuple[str, list[MarkerDraft]]` replaces each `{{value|src:id}}` (regex `app.tools.template.TAG`) in document order with `value` followed by the raw inline `` `#prov(n, "id")`{=typst} ``, numbering from 1; `MarkerDraft(n, source_id, source_event_id | None)` resolved through `sources` (short id to event id), unresolved when absent; `appendix(markers, headlines) -> str` renders the "Provenance" section rows "n. source id, headline" with "unresolved" for missing sources; tests in `tests/unit/s4/test_markers.py` for a tag inside a table cell, inside a heading, two tags on one line, and an unresolved id
- [x] T008 [P] Write `app/compile/brand.py`: `read_brand(dataset_folder) -> Brand` reading `brand.yaml` (`prospect_name` required; `logo_path` resolved inside the dataset folder and set to "" when the file is missing; `primary_colour` must match `^#[0-9A-Fa-f]{6}$`, else the template default `#1F3A5F` with `Brand.assumptions` carrying "brand primary_colour is not a six-digit hex colour; the template default was used"); tests in `tests/unit/s4/test_brand.py` for a missing logo, a bad colour, a missing name (ValueError)
- [x] T009 Write `app/compile/pipeline.py` `compile_draft(run_folder, version, markdown, brand, sources, template=templates/rfp-response.typ) -> Compiled`: create `artifacts/v<N>/`; run `pandoc -f markdown-smart -t typst --template <template> -V prospect-name=... -V logo-path=... -V primary-colour=... -o draft-v<N>.typ` on the prepared markdown; `typst compile draft-v<N>.typ draft-v<N>.pdf`; `typst compile --format png --ppi 150 draft-v<N>.typ "page-{0p}.png"`; `typst query draft-v<N>.typ "<prov>" --field value` (fallback `typst eval` when query exits non-zero with the deprecation error) to `markers.json` with `x`, `y` converted to pixels (points times 150 divided by 72) and `source_event_id` from the MarkerDraft list; page text per page through pypdfium2 to `pages.json`; write `compiled.json` (`version`, `pdf_path`, `page_images`, `marker_count`, `unresolved`, `page_count`, `elapsed_ms`, `tool_versions`) with run-relative paths; raise `CompileError(first error line)` on any non-zero exit, with a 60 s timeout per step; all subprocess calls without a shell
- [x] T010 Tests for T009 in `tests/unit/s4/test_pipeline.py` (`compiler` marked): the fixture draft compiles; `page_images` count equals `page_count`; every marker's page is within range and its pixel position inside the image bounds (read PNG size with pypdfium2's rendered size or PIL if present, else parse the PNG header); `pages.json` has one text per page and page 1 contains the prospect name; a malformed table raises `CompileError` naming the line; `compiled.json` paths are run-relative; the wordmark path is exercised with a brand whose logo is missing
- [x] T011 [P] Write `app/compile/timeline.py`: `compile_timeline(run_folder, events) -> Path` builds a markdown table (time from run start as mm:ss, stage, actor name and role, event type, one-line summary: `reason` for Orchestrator events, `headline` or `message` for agent events, `exit` for termination) and runs the pipeline with `templates/run-timeline.typ` to `artifacts/timeline.pdf`, regenerating only when `events.jsonl` is newer; test in `tests/unit/s4/test_timeline.py` (`compiler` marked) on the Clean run golden that the PDF exists and its page text contains every event type
- [x] T012 Export the public API in `app/compile/__init__.py` (`compile_draft`, `compile_timeline`, `tools_available`, `read_brand`, `CompileError`, `Compiled`) and add a lint test `tests/lint/test_compiled_no_em_dash.py` (`compiler` marked) that compiles the fixture draft and fails on an em dash in any page's text

**Checkpoint**: the pipeline turns the fixture draft into pages, markers and page text; the engine and the page can proceed.

---

## Phase 3: User Story 1 - The proposal appears as pages and refreshes in place (Priority: P1)

**Goal**: every `draft.committed` is followed by `artifact.compiled` with real paths, in live, stub and replay; the panel shows the pages.

**Independent test**: a stub run of Clean run produces `artifacts/v1/` and the browser shows the pages with "v1"; a replay with the datasets folder removed shows them again.

- [x] T013 [US1] Give stub scenarios the run folder: `app/runs/registry.py` `start_run` passes `run_folder` to the scenario factory, `app/agents/stubs/__init__.py` stores it, and `app/agents/stubs/_common.py` `draft(...)` writes `drafts/draft-v<N>.md` from `fixtures/draft-fixture.md` (with the note appended as a sentence in the executive summary on v2 so versions differ) and calls `compile_draft` with the dataset's brand before yielding `draft.committed`; the stub's `provenance_tags` are rebuilt from the fixture's real tags; test in `tests/integration/s4/test_stub_compile.py` (`compiler` marked) that a stub Clean run leaves `artifacts/v1/compiled.json` and that `draft.committed.provenance_tags` matches the fixture's tags
- [x] T014 [US1] Orchestrator emission: in `app/orchestrator/orchestrator.py` `_assemble`, after relaying `draft.committed`, read `artifacts/v<N>/compiled.json` from the run folder and emit `artifact.compiled` with its `pdf_path` and `page_images`; keep `self.latest_compiled` for Handoff; raise `RuntimeError` naming the version when the record is missing; test in `tests/integration/s4/test_orchestrator_compiled.py` that the emitted payload matches the record and follows the commit before any Reviewer dispatch
- [x] T015 [US1] Refuse to start without the tools: `app/runs/registry.py` `start_run` raises `LiveUnavailable(["compiler missing (typst)"])` or `(pandoc)` when `tools_available()` reports None, for stub and live runs alike; `app/main.py` already maps it to 409; test in `tests/integration/s4/test_registry_tools.py` with the tool lookup patched
- [x] T016 [US1] Re-record the nine golden logs with `uv run python scripts/regen_golden.py` (commit the stub changes first; the script refuses otherwise) and confirm `tests/integration/test_api.py` and the replay-and-compare suite pass; goldens now carry `artifact.compiled` with real paths after every `draft.committed`
- [x] T017 [US1] Panel pages: in `app/web/pages/demo.html` replace the `draft-page` block with a `pages` list container and keep `artifact-empty`, `artifact-title`, `artifact-version`; in `app/web/static/js/reducer.js` add `view.latestCompiled` (`version`, `pdf_path`, `page_images`, `runId`, `eventId`) from the last `artifact.compiled` in a new case branch; in `app/web/static/js/render.js` add `renderPages(view, ui)` that renders one `<img loading="lazy">` per page from `/api/runs/<id>/files/<path>`, replaces images in place by index (same node, new `src`) so the scroll offset is kept, sets the version label "v<N>", and shows the empty message "This recording predates compiled pages" when a run has a draft but no compiled event with paths; remove the call to the text renderer; delete `app/web/static/js/draft.js` and its script tag
- [x] T018 [US1] Styles for the page list in `app/web/static/css/app.css` (new selectors `.pages`, `.page-img`, `.page-num` only): pages stacked with the export's gap, image width 100 percent of the panel, a thin border in the export's line colour, page number caption in the meta text style
- [x] T019 [US1] Browser tests in `tests/visual/test_e2e_ui.py` (`compiler` and `dataset` marked): a stub Clean run shows page images with "v1" and the count matches `page_images`; on Planted inconsistency, scroll the panel to page 2 during Review and assert after v2 that the `scrollTop` is unchanged and no empty message flashed (poll `#artifact-empty.hidden` every frame during the swap); a replay served from a run folder copied to a temp runs dir with no datasets shows the same pages

**Checkpoint**: pages appear live, on stubs and in replay.

---

## Phase 4: User Story 2 - Every figure has a paper trail on the page (Priority: P1)

**Goal**: markers on the pages are hover targets that highlight the source message.

**Independent test**: replay Planted inconsistency, hover every marker, assert the highlighted card's event id equals the marker's `source_event_id`.

- [x] T020 [US2] Marker layer: in `app/web/static/js/render.js` add `renderMarkers(view, ui)` that fetches `artifacts/v<N>/markers.json` once per compiled event (cache on `ui.markers[eventId]`), and for each marker places an absolutely positioned `<button class="marker" data-source-event="...">` over the page image at `x` times (displayed width over natural width) and `y` likewise, recomputed on image load and on window resize; an unresolved marker gets `data-unresolved="true"` and no target
- [x] T021 [US2] Hover wiring in `app/web/static/js/demo.js`: `mouseenter` on a marker adds `is-source` to the feed card whose `data-event` or `data-card` resolves to the source event (extend `buildCard` in `render.js` to set `data-event-id` on agent-message and specialist-thread cards from the thread's completed or last event) and scrolls it into view with `block: "center"`; `mouseleave` removes the class; nothing on click
- [x] T022 [US2] Styles in `app/web/static/css/app.css` (new selectors `.marker`, `.marker[data-unresolved]`, `.card.is-source`): a 22 px circle in the brand ink with the number in the mono font, visible at three metres; the highlighted card gets the export's active border and a soft background, no animation
- [x] T023 [US2] Browser test in `tests/visual/test_e2e_ui.py` (`compiler`, `dataset`): replay Planted inconsistency at 4x to termination, iterate every `.marker` on every page, hover, and assert exactly one `.card.is-source` whose event id equals the marker's `data-source-event`; assert the count of markers equals `marker_count` in `compiled.json`; assert zero markers carry `data-unresolved`
- [x] T024 [US2] Provenance appendix: the Writer's markdown template `templates/rfp-response.md` keeps its `{{provenance_appendix}}` slot; `app/compile/markers.py` `appendix` output replaces the slot content at compile time (`app/compile/pipeline.py`) so the printed appendix lists marker numbers and source headlines from the run's specialist `task.completed` events; unit test that the appendix lists every marker once

---

## Phase 5: User Story 3 - The Reviewer judges the pages (Priority: P1)

**Goal**: the Reviewer's bundle carries page images and page text; the markdown path is gone.

**Independent test**: scripted Reviewer records its bundle; assert `images` non-empty and no markdown material.

- [x] T025 [US3] `app/schema/bundles.py`: add `images: list[str] = []` to `PromptBundle` and a sixth section "Pages" listing the paths in `sections()`; `app/live/seat_call.py` builds the first user message with an image content block per path (`{"image": {"format": "png", "source": {"bytes": ...}}}`, the same shape `vision_read_drawing` uses) read from the run folder, only when `seat_model.model.image_input` is true, else raises `LiveUnavailable` naming the seat before the call; unit test in `tests/unit/s4/test_bundle_images.py` for the section and the refusal
- [x] T026 [US3] `app/live/materials.py` reviewer materials: replace the `Draft v<N>` text material with one material per page "Page <n> text" from `artifacts/v<N>/pages.json` (source label `page-<n>`), and return the page image paths for the bundle; `app/live/source.py` `review` passes them as `images`; `app/live/source.py` `assemble` calls `compile_draft` after `commit_draft` and, on `CompileError`, records the reply as rejected with reason `compile_failed` and the compiler's message for the second attempt, then the existing twice-invalid path; integration tests in `tests/integration/s4/test_reviewer_pages.py` and `test_compile_failure.py` on the scripted model (`compiler` marked)
- [x] T027 [P] [US3] Seat wording: `config/electrical-bid/seats/reviewer.md` says the Reviewer sees the brief, the compiled page images with their page text, and the criteria, and cites page numbers and marker numbers in evidence; the Reviewer row in `config/electrical-bid/seats/README.md` follows; lint passes
- [x] T028 [US3] Interim removal check: `tests/unit/s4/test_no_interim.py` asserts `app/web/static/js/draft.js` does not exist, `render.js` contains no `S1Draft`, and `materials.py` contains no `Draft v` material (SC-007)

---

## Phase 6: User Story 4 - Handoff: approve, edit once, reject, download (Priority: P2)

**Goal**: the package is populated and all five Handoff actions work.

**Independent test**: drive a stub run to Handoff in the browser and exercise each control.

- [x] T029 [US4] Package: `app/orchestrator/orchestrator.py` `_handoff` fills `pdf_path` and `page_images` from `self.latest_compiled`; test in `tests/integration/s4/test_handoff_package.py` that they match the last compiled event
- [x] T030 [US4] Edit path: `app/main.py` `DecisionRequest` gains `markdown: str = ""`; `app/orchestrator/orchestrator.py` `submit_decision("edit", notes, markdown)` validates non-empty markdown, writes `drafts/draft-v<N+1>.md`, runs `compile_draft`, and on success queues the edit so `_handoff` emits `draft.committed` with `actor` the human (recomputed `provenance_tags` via `find_tags`), `artifact.compiled`, then `human.approved` decision `edit`, then terminates with the Handoff exit; on `CompileError` raises `ValueError(message)` which the route returns as 400 and the run stays at Handoff; tests in `tests/integration/s4/test_edit.py` (`compiler` marked) for the event sequence, the actor, and the 400 path
- [x] T031 [US4] Timeline route: `app/main.py` new `GET /api/runs/{run_id}/timeline.pdf` returning `FileResponse` from `compile_timeline` (409 before termination, 503 naming the tool when missing, works for recordings through `registry.read_recording`); test in `tests/integration/s4/test_timeline_route.py` (`compiler` marked)
- [x] T032 [US4] Handoff controls in `app/web/pages/demo.html`: enable Edit, Reject, Download PDF, Download run timeline with ids `btn-edit`, `btn-reject`, `btn-download-pdf`, `btn-download-timeline`; add the edit area (`<textarea id="edit-area">` in the export's input style, Save and Cancel in the pill and outline styles) and the reject notes area (same text input style) hidden by default; in `app/web/static/js/render.js` add `renderHandoffActions(view, ui)` enabling the five controls only when `view.handoffPending` and live mode (downloads also after termination for exits `reviewer_pass` and `retry_exhausted`), never in Single-model or replay; in `app/web/static/js/demo.js` wire Edit (load `drafts/draft-v<N>.md` through the files route into the text area, Save posts `decision: edit` with `markdown`, Cancel restores pages, a 400 shows the message above the area and keeps it open), Reject (notes then `decision: reject`), and the two downloads (anchor to the files route and the timeline route)
- [x] T033 [US4] Browser tests in `tests/visual/test_e2e_ui.py` (`compiler`, `dataset`): stub Clean run to Handoff, Edit one word, Save, assert one more `draft.committed` with actor `human`, one more `artifact.compiled`, `human.approved` decision `edit`, and termination; a second run, Reject with notes, assert the decision and notes and termination; after termination the PDF link returns `application/pdf` and the timeline link returns a PDF; Edit and Reject are absent in replay
- [x] T034 [US4] Family-consistency review of Edit, Reject, the edit area and the marker against the export's component families, recorded as S4 decisions in `docs/design-deviations.md`; screenshot comparison for the terminated state re-captured with pages on screen and masks updated in `tests/visual/masks.py` only where the export shows the old text panel

---

## Phase 7: User Story 5 - The cover carries the prospect's brand (Priority: P2)

**Goal**: page 1 shows name, logo or wordmark, and brand colour for every dataset.

**Independent test**: compile the fixture draft against every dataset's brand file.

- [x] T035 [US5] Brand assumption on the run: when `read_brand` returns assumptions, `app/live/source.py` and the stub path record them through the existing `assumption.accepted` flow before the first commit (question id `brand_colour`); test in `tests/integration/s4/test_brand_assumption.py`
- [x] T036 [P] [US5] Test in `tests/unit/s4/test_brand_covers.py` (`compiler`, `dataset`): for every dataset folder, compile the fixture draft with its brand and assert page 1 text contains `prospect_name`; for a dataset without a logo file assert the wordmark path was taken (`Compiled.tool_versions` untouched, `Brand.logo_path == ""`)
- [x] T037 [P] [US5] Long-name wordmark: unit test that a 60-character prospect name compiles and page 1 text contains it whole (the template wraps the wordmark)

---

## Phase 8: User Story 6 - Live verification and the record (Priority: P3)

**Goal**: the slice is proven on live runs and recorded.

- [ ] T038 [US6] Live run from the Demo page on Clean run under `COST_CEILING=1.00`: record the run id, the seconds from `draft.committed` to `artifact.compiled`, the Reviewer verdict citing a page, and the spend; `scripts/compare_run.py` MATCH
- [ ] T039 [US6] Live run on Planted inconsistency: v1 and v2 pages, version swap observed, every marker hovered on v2, Edit exercised once at Handoff; compare and record
- [ ] T040 [US6] Live run on Clean run ending in Reject with notes and both downloads opened; record
- [ ] T041 [US6] Roadmap S4 status entry in `docs/roadmap.md` with the run ids, timings, spend, and the evidence list; `docs/model-performance.md` refreshed with `uv run python scripts/model_report.py --write`

---

## Phase 9: Closeout

- [ ] T042 Gates: `uv run python scripts/check.py`, `uv run pytest -m visual`, `uv run pytest -m compiler`; fix anything red
- [ ] T043 Publication check on the branch (no prospect names, no client files, no credentials), push `005-compiled-deliverable`, and message the S5 session (multiagent-demo-6c) that 005 is pushed and lists the shared-file functions it added, so 006 can rebase

---

## Dependencies

- Phase 2 blocks everything after it. T005 blocks T009. T007 and T008 block T009. T009 blocks T010, T011, T012.
- US1 (T013 to T019) blocks US2, US3, US4 and US5 in the engine; T017 blocks T020 and T032 on the page.
- US2 (T020 to T024) depends on T017; T024 depends on T007.
- US3 (T025 to T028) depends on T013 and T014; T025 blocks T026.
- US4 (T029 to T034) depends on T014 and T017; T030 depends on T009; T031 depends on T011.
- US5 (T035 to T037) depends on T008 and T013.
- US6 (T038 to T041) depends on every earlier phase and on a machine with Ollama, AWS keys and the tools.
- Closeout depends on everything.

## Parallel execution examples

- After T001: T002, T003, T004 together.
- After T005: T006, T007, T008 together.
- After T009: T010, T011, T012 together.
- Within US1: T015 and T018 beside T013 and T014; T017 and T018 together.
- Within US2: T022 beside T020; T024 beside T021.
- Within US3: T027 beside T025 and T026.
- Within US5: T036 and T037 together after T035.

## Implementation strategy

MVP is Phase 2 plus US1: the fixture draft compiles and pages appear on stubs, live and replay, with goldens re-recorded. US2 and US3 make the slice true to the spec (hover provenance, Reviewer on pages). US4 and US5 complete the Handoff beat and the brand. US6 records the evidence. Each phase ends in a state the presenter could show.
