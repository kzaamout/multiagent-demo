---

description: "Task list for slice S6, Introduction tab and public replay"
---

# Tasks: Introduction tab and public replay (S6)

**Input**: Design documents from `specs/007-introduction-replay/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/introduction.md, quickstart.md

**Tests**: every change carries its test task. Tests that compile carry `pytest.mark.compiler`; tests that need the pinned recording carry `pytest.mark.dataset` and use a recording copied into a temp runs folder.

**Parallel S7 branch**: `app/main.py` gains routes and one page flag only; `app.css` appended rules only; `demo.js` gains a public mode branch only; nothing in `preflight.html`, `login.html` or any auth code is touched.

**Organization**: phases follow the plan's delivery order (content, diagrams, team, PDF; the page; the public replay; closeout). Story labels map to spec.md: US1 sections, US2 diagrams, US3 team, US4 public replay, US5 PDF, US6 name check.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)

---

## Phase 1: Setup

- [ ] T001 Create `app/intro/__init__.py`, `tests/unit/s6/__init__.py`, `tests/integration/s6/__init__.py`; add `public_run_id: str` to `Settings` in `app/config.py` read from `PUBLIC_RUN_ID` with the default named in research R7; add the setting to `.env.example` with a comment
- [ ] T002 [P] [US6] Record the service name check in `specs/007-introduction-replay/research.md` R1 (done) and in the roadmap status at closeout; no content change

---

## Phase 2: Foundational (content, diagrams, team, PDF)

- [ ] T003 [US1] Write `app/intro/content.py`: `Section` dataclass (id, eyebrow, title, blocks, diagram, text); `sections(folder=content/intro) -> list[Section]` reading the seven files in order with the export's ids and eyebrows; a block parser for headings, paragraphs, ordered and bulleted lists, a pipe table, inline `**bold**` and `_italic_`, HTML comments dropped, a diagram slot read from the comment (`diagram: architecture|loop|demo-vs-production`); `render_blocks(blocks) -> str` escaping text; `plain_text(section) -> str`; tests in `tests/unit/s6/test_content.py`: seven sections in order, every paragraph of every file present in `plain_text`, comments absent, the table has eight rows, no em dash, the diagram slots are architecture, loop and demo-vs-production on files 02, 03 and 06
- [ ] T004 [P] [US2] Write `app/intro/diagrams.py`: one band description of the architecture (renderers Web UI and Slack "future" greyed; the event stream bus; the Orchestrator box with a six-node strip and a retry badge; six agent cards with initials and colours from `F.seatColor` equivalents in `app/orchestrator/roster.py`; tool boxes under Estimator, Pricing and Writer only; five providers with dotted lines; the human figure right of the Orchestrator with the "one door" arrow) and `architecture_svg(badges=None)`, `demo_vs_production_svg()` (two copies with laptop and AgentCore badge sets, Runtime, Gateway, Memory, Observability, Identity on the boxes the content table maps), `loop_svg()` (six lit pills with the Demo strip's labels and glyph, forward arrows, three red backward arrows labelled Review to Work, Review to Assemble, Work to Intake, human icons on Intake, Work and Handoff, the retry badge on Review, an exits card off Handoff listing the four narrative exits with Not ready branching off Intake); `Diagram(name, svg, text)`; the SVGs use `viewBox`, the export's colours and sizes, and `font-family` Inter with sans-serif fallback; tests in `tests/unit/s6/test_diagrams.py`: each SVG parses as XML, contains the named parts as text, and has no em dash
- [ ] T005 [P] [US3] Write `app/intro/team.py`: `TeamCard` and `team_cards(registry) -> list[TeamCard]` for the six seats (name pair and blurb parsed from `content/intro/04-the-team.md`'s bold lines, role from the roster, model label from the registry's current seat models, owns from the seat file's first paragraph, sees from `SEAT_DEFINITIONS` kinds in plain words, tools from the definition) plus the two appraisal cards from the content file's last paragraph with "swaps in for the appraisal workflow"; tests in `tests/unit/s6/test_team.py`: eight cards, order, the Reviewer's tools are none and its sees names the brief, pages and criteria, the appraisal cards carry the note
- [ ] T006 [P] [US5] Write `templates/introduction.typ` (Letter, single column, ink headings in the response template's family, tables in the same style, images full width) and `app/intro/pdf.py`: `render_pdf(settings) -> Path` writing `runs/_intro/introduction.md` (sections with `![](name.svg)` at each diagram slot and a team list), the three SVG files, then `app.compile.render_markdown` to `introduction.pdf`, skipping when the PDF is newer than every source; `scripts/intro_pdf.py` with `--out`; tests in `tests/unit/s6/test_pdf.py` (`compiler` marked): the PDF exists, its page text carries every section heading and every paragraph's first sentence, three images embedded (the `.typ` names three `image(` calls), regeneration only when a source is newer

**Checkpoint**: content, diagrams, team and the PDF exist without a page.

---

## Phase 3: User Story 1 and 2 - The page (Priority: P1)

- [ ] T007 [US1] Flatten the export: write `app/web/pages/introduction.html` from the decoded bundle (header without the selector, Introduction current, the eight sections with their ids, max widths, paddings and eyebrows, slots `{{SECTION:<id>}}`, `{{DIAGRAM:<name>}}`, `{{TEAM}}`, `{{REPLAY}}`) and append `.intro-*` rules to `app/web/static/css/app.css` copied from the export's inline styles (48 px Space Grotesk headings, 18 px body, FAQ item rule, team card, detail grid, replay frame shell)
- [ ] T008 [US1] `app/intro/__init__.py` `render_page(settings, registry) -> str` fills the slots; `app/main.py` `GET /introduction` returns it with the build stamp; test in `tests/integration/s6/test_introduction_route.py`: 200, seven section ids in order, the build stamp, no workflow selector, Introduction marked current; the nav on the other three pages links to `/introduction` (edit `demo.html`, `settings.html`, `preflight.html` nav anchors from disabled to `href="/introduction"`)
- [ ] T009 [US2] Inline the three SVGs at their slots; test in `tests/integration/s6/test_introduction_route.py` that the page carries three `<svg` with the diagram names as `data-diagram`
- [ ] T010 [US1] Content diff test `tests/integration/s6/test_content_diff.py`: for each section, the rendered HTML's text (tags stripped, whitespace collapsed) equals `plain_text` of the file; and the em-dash lint covers the rendered page (`tests/lint/test_intro_no_em_dash.py`)
- [ ] T011 [US1] Screenshot comparison: add the Introduction reference capture from the export bundle to `tests/visual/capture_app.py` and `tests/visual/test_screenshots.py` (top of the page, 1920 by 1080), masks in `tests/visual/masks.py` for the replay frame and the build stamp; the loop section is compared (the export has text there; mask it with the recorded reason)

---

## Phase 4: User Story 3 - The team grid (Priority: P2)

- [ ] T012 [US3] Render the eight cards into the `{{TEAM}}` slot with the export's team card markup, `data-part="team-card"`, the detail grid hidden until clicked; `app/web/static/js/intro.js` toggles `data-open` on click and nothing else; browser test in `tests/visual/test_e2e_intro.py`: eight cards, click expands and collapses, the six seats' model labels equal `/api/seats` labels

---

## Phase 5: User Story 4 - The public replay (Priority: P1)

- [ ] T013 [US4] Public routes in `app/main.py`: `/public/run/{run_id}/events`, `/files/{path}`, `/prompts/{prompt_ref}`, `/meta`, each refusing any id but `cfg.public_run_id` with 404 before touching the disk; reuse the private routes' readers; tests in `tests/integration/s6/test_public_run.py` (`dataset` marked, recording copied into a temp runs folder): the pinned id answers, another recorded id is 404 on every route, a path outside the folder is 404, `meta` carries dataset id, exit and `has_pages`
- [ ] T014 [US4] Demo page public mode: `app/web/static/js/demo.js` reads `public=1`, `run` and `speed`; in public mode it fetches events, files and prompts through the public routes (a `base` prefix used by the existing fetches), hides `.composer`, the run controls, `#handoff-actions`, the header nav links and the banner, keeps the loop strip, feed, pages, markers, meters and raw drawer, plays the events as a replay at the given speed without a stream, and never posts; `app/web/pages/demo.html` gains `data-public` on the frame for the CSS to hide the parts; test in `tests/visual/test_e2e_intro.py`: `/demo?public=1&run=<pinned>&speed=4` plays to termination, the hidden parts are absent, pages and markers appear, no request goes to `/api/runs`
- [ ] T015 [US4] The frame on the Introduction: the `{{REPLAY}}` slot renders the export's frame shell with the caption from `/public/run/{id}/meta` (dataset and exit), the 1x and 4x controls switching the iframe's `speed`, and an iframe to `/demo?public=1&run=<pinned>&speed=1`; when the pinned recording is missing the shell shows one sentence and no iframe; browser test: the iframe plays the pinned run, the 4x control reloads it at 4x, no anchor inside the frame leaves it
- [ ] T016 [US4] Set `PUBLIC_RUN_ID`'s default in `app/config.py` to the pinned recording (research R7), copy that run folder's id into `.env.example` as the example, and record in the roadmap which run is pinned

---

## Phase 6: User Story 5 - The PDF route (Priority: P2)

- [ ] T017 [US5] `app/main.py` `GET /introduction.pdf` serving `render_pdf` (503 naming the missing tool); test in `tests/integration/s6/test_introduction_pdf_route.py` (`compiler` marked): 200 `application/pdf`, `%PDF-` prefix, a second request does not regenerate when nothing changed

---

## Phase 7: Closeout

- [ ] T018 Family-consistency review and S6 entries in `docs/design-deviations.md` (loop diagram drawn; SVG bands; real replay frame; caption from the pinned run; Introduction link enabled in every header)
- [ ] T019 Roadmap S6 status in `docs/roadmap.md` with the pinned run, the content diff, screenshot and PDF results, and the name check record
- [ ] T020 Gates (`check.py`, `pytest -m visual`), publication sweep, push `007-introduction-replay`, message the S7 session with the public route list from the contract

---

## Dependencies

- T003, T004, T005, T006 after T001; T006 depends on T003 and T004.
- Phase 3 depends on T003 and T004; T008 blocks T009 and T010; T011 depends on T007.
- T012 depends on T005 and T007.
- T013 blocks T014; T014 blocks T015; T016 any time after T013.
- T017 depends on T006 and T008.
- Closeout after everything.

## Parallel execution examples

- After T001: T003, T004, T005 together, then T006.
- After T008: T009, T010, T011 together, with T012 beside them.
- After T013: T014 then T015, with T016 and T017 beside them.

## Implementation strategy

MVP is Phases 2 and 3: the page with its copy and diagrams. Phase 5 makes it the proof the copy promises. Phase 6 gives S7 its leave-behind. Each phase ends with the page in a state a salesperson could open.
