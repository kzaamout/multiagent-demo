# Implementation Plan: Compiled deliverable and provenance (S4)

**Branch**: `005-compiled-deliverable` | **Date**: 2026-09-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-compiled-deliverable/spec.md`

## Summary

Compile every committed draft to a PDF and page images through the career-hub pipeline shape (pandoc to Typst with a template, Typst to PDF, Typst to PNG at 150 ppi) wrapped as a Python module, with the intermediate Typst source kept. Provenance tags become numbered markers whose positions Typst reports, so the artifact panel overlays hover hotspots on the page images and jumps the feed to the source message. The Reviewer receives the page images and the extracted page text instead of markdown. Handoff gains Edit (one recompile as the human), Reject with notes, Download PDF and Download run timeline (a PDF rendered from the event log through the same pipeline). Stub runs compile a fixture draft for real so every golden log regains `artifact.compiled`. The S2 and S3 text interims are removed.

## Verified versions and names (2026-09-17)

| Item | Verified | Source |
|---|---|---|
| Typst | 0.15.1; `typst query` still works and warns that `typst eval 'query(<label>)'` is the successor | `typst --version`, `typst query --help`, a two-page probe returned page and position in points for each marker |
| pandoc | 3.10.2; `-t typst` emits headings, tables as `#figure(table(...))`, and passes `{{value|src:id}}` through as text | `pandoc --version`, probe on a draft fragment |
| pypdfium2 | already a dependency, used by `app/tools/prepare.py` for page text and page images | `pyproject.toml`, `app/tools/prepare.py` |
| Career-hub script | `compile-to-pdf.sh` and `.ps1`: pandoc `-t typst --template`, `typst compile`, `typst compile --format png --ppi 150 "<stem>-p{p}.png"`, intermediate `.partial.typ` retained | owner's path, read 2026-09-17 |
| Reviewer model | Gemma 4 12B, `image_input: true` in `config/models.yaml` | registry |

No Python dependency is added. Two external tools (Typst, pandoc) are recorded in `docs/dependencies.md`. Details in [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.13; vanilla JavaScript in the static page

**Primary Dependencies**: FastAPI, Pydantic, Strands Agents, pypdfium2; Typst 0.15.1 and pandoc 3.10.2 as external tools invoked by subprocess

**Storage**: files under `runs/<run_id>/artifacts/v<N>/` per compiled version; templates under `templates/`; brand under `datasets/<id>/brand.yaml`

**Testing**: pytest (unit on the pipeline with fixture markdown, integration with the scripted model and the stubs), Playwright browser tests, golden re-record, live verification under `COST_CEILING=1.00`; tests that need the tools carry `pytest.mark.compiler` and skip naming the missing tool

**Target Platform**: presenter laptop, Windows 11, Chrome; the same tools on the reference machine

**Project Type**: web application (FastAPI server with a static page)

**Performance Goals**: pages in the panel within 10 s of `draft.committed` (measured on the probe: pandoc under 0.5 s, Typst PDF and PNG under 3 s for ten pages, query under 1 s); version swap with no empty frame; hover response immediate

**Constraints**: event schema 1.1.0 frozen (the four payloads used as written; marker positions and page text are files, not fields); the page renders only from events and the files they name; no em dashes, including in the compiled PDF; the Orchestrator is the only emitter; shared files with the parallel S5 branch touched only through new functions and routes

**Scale/Scope**: one compile module with four parts, two Typst templates, one Orchestrator change, one live source change, one stub change, one materials change, three API additions, one panel rewrite, nine golden re-records, one dependency record, one deviation entry

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | S4 compliance | Status |
|---|---|---|
| I Demo, not product | Compile serves the presenter's screen and the leave-behind; no document management, no batch export, no editor beyond one text area | Pass |
| II Events only | `draft.committed`, `artifact.compiled`, `handoff.ready`, `human.approved` as frozen; the panel renders from `artifact.compiled` and the files it names; markers and page text are files beside the images | Pass |
| III One owner of state | The Orchestrator emits `artifact.compiled` after reading the compile result, populates the package, and terminates after Edit or Reject; the compile module writes files and returns a record, it never emits | Pass |
| IV One door | Edit and Reject go through the existing decision route to the Orchestrator | Pass |
| V Roles are real | The Reviewer's scope changes from draft text to page images plus page text, still the brief and the criteria, never the sources; recorded in the seat README | Pass |
| VI Design for the failure | A compile failure follows the twice-invalid reply path; no new exit; a failed human edit keeps the previous pages and the run open | Pass |
| VII Provenance | Every tag becomes a marker resolved to a message or listed unresolved; the Writer's validation stays in front of the commit | Pass |
| VIII Reliability | Every version's files stay in the run folder; Replay shows pages from the folder with no compiler and no datasets | Pass |
| IX Writing rules | The em-dash lint covers templates and the compiled PDF's text (extracted per page) | Pass |
| X, XI Controlled sources | Behaviour from spec-input 0.7 sections 2.2, 2.6, 3, 6, 8; appearance from the export's artifact panel; Edit and Reject additions recorded as deviations | Pass |
| XII Vertical slices | Builds on S3b; no schema change | Pass |
| XIII Acceptance recorded | Golden re-record, screenshot comparison, browser tests, live runs | Pass |
| XIV Projector | Page images at 150 ppi; markers sized to be visible at distance; hover only | Pass |
| XV Dependencies | Typst and pandoc recorded with rationale and cost of doing without | Pass |
| XVI Quality gates | Unit, integration, browser, lint; compiler tests skip by name when the tools are absent | Pass |
| XVII Credentials | None involved | Pass |
| XVIII Design wired, not redesigned | Panel keeps the export's layout; Edit and Reject use the outlined button family the export already has; the text area uses the export's input style | Pass |
| XIX Approval | Eight owner decisions of 2026-09-17 recorded in the spec | Pass |
| Non-goals | Provenance stays hover only; Reject terminates; nothing sent externally | Pass |

Re-check after Phase 1 design: no new violation. The bundle gains an `images` list for the Reviewer's call; bundles are recorded files, not events, so the frozen schema is untouched.

## Project Structure

### Documentation (this feature)

```text
specs/005-compiled-deliverable/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── compile.md
├── checklists/
│   └── requirements.md
└── tasks.md             # from /speckit-tasks
```

### Source Code (repository root)

```text
app/compile/__init__.py            public entry points: compile_draft, compile_timeline, tools_available, read_brand
app/compile/pipeline.py            pandoc to .typ, typst to PDF and PNG, query markers, extract page text, write compiled.json
app/compile/markers.py             tag to marker preprocessing, provenance appendix, unresolved handling
app/compile/brand.py               brand.yaml to template variables, wordmark fallback, colour validation
app/compile/timeline.py            event log to timeline markdown, then the pipeline with the timeline template
templates/rfp-response.typ         pandoc Typst template: Letter, single column, cover, brand colour, marker function
templates/run-timeline.typ         pandoc Typst template for the timeline table
app/orchestrator/orchestrator.py   _assemble reads compiled.json and emits artifact.compiled with real paths; _handoff fills the package; edit path (human commit, compile, terminate)
app/live/source.py                 assemble: compile after commit, compile failure as a rejected reply
app/live/materials.py              reviewer materials: page images and page text instead of the draft text
app/live/seat_call.py              images on the bundle reach the model as image content
app/schema/bundles.py              PromptBundle.images (list of run-relative paths), default empty
app/agents/stubs/_common.py        stub draft writes the fixture markdown and compiles it
app/runs/registry.py               start_run refuses when a needed tool is missing
app/main.py                        DecisionRequest.markdown for edit; GET /api/runs/{id}/timeline.pdf; files route unchanged
app/web/pages/demo.html            artifact panel: pages list, marker layer, edit area, Reject notes, download links
app/web/static/js/render.js        renderArtifact rewritten (new functions); handoff actions; hover highlight
app/web/static/js/demo.js          edit, reject, download wiring; marker hover handlers
app/web/static/js/draft.js         removed
app/web/static/css/app.css         page list, marker, edit area, highlight styles (new selectors only)
config/electrical-bid/seats/reviewer.md   scope wording: page images and page text
config/electrical-bid/seats/README.md     Reviewer scope row
datasets/*/golden-events.jsonl     re-recorded with artifact.compiled
docs/dependencies.md               Typst, pandoc, career-hub pipeline
docs/design-deviations.md          S4: Edit, Reject, markers, edit area
docs/roadmap.md                    S4 status
tests/unit/s4/                     pipeline, markers, brand, timeline (compiler marked)
tests/integration/s4/              orchestrator emits real paths; reviewer bundle; edit and reject; compile failure; stub compile
tests/visual/test_e2e_ui.py        pages appear, swap keeps scroll, hover highlights, handoff actions (new tests)
tests/lint/                        em dashes in compiled page text
```

**Structure Decision**: extend the existing single project with one new package `app/compile/` and two templates; the engine and page changes are confined to the functions named above so the parallel S5 branch rebases cleanly.

## Delivery order

1. Pipeline: `app/compile/` with the two templates, unit tests on fixture markdown (markers, positions, brand fallback, timeline), the compiler skip marker, the dependency record.
2. Engine: stub compile, live compile with the rejected-reply path, Orchestrator emission and package, Reviewer materials and bundle images, seat README; integration tests on the scripted model; golden re-record for all nine datasets.
3. Page: panel rewrite with pages, markers, hover, version swap, Edit, Reject, downloads; browser tests; screenshot comparison; deviations.
4. Live verification from the Demo page on Clean run and Planted inconsistency under `COST_CEILING=1.00`; Edit and Reject exercised once each; timeline downloaded.
5. Interim removal check (SC-007), roadmap S4 status, gates, push, message to the S5 session.

## Complexity Tracking

No constitution violations to justify.
