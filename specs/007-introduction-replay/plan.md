# Implementation Plan: Introduction tab and public replay (S6)

**Branch**: `007-introduction-replay` | **Date**: 2026-09-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-introduction-replay/spec.md`

## Summary

Flatten the export's Introduction bundle into a static page that renders the seven content files at request time, draws the three diagrams as inline SVG generated from one Python module (so the PDF embeds the same drawings), shows eight expandable team cards from the roster and seat definitions, and embeds a read-only replay of one pinned run through a public endpoint that serves that run id only. A script and a route produce the Introduction PDF through the S4 pipeline. The service names in the copy were checked against current documentation and are correct.

## Verified versions and names (2026-09-17)

| Item | Verified | Source |
|---|---|---|
| AgentCore components | Runtime, Gateway, Memory, Identity, Observability exist as named; Policy, Evaluations, Browser and Code Interpreter also exist and are not in the copy | AWS AgentCore developer guide overview and observability pages; AWS What's New, general availability October 2025 |
| Strands Agents | Open-source AWS SDK, Python and TypeScript, built to deploy on AgentCore Runtime; the copy's sentence stands | strandsagents.com; AWS Machine Learning blog on the SDK |
| Export bundle | `design/Introduction.html`, 78,926 character page template, 20 assets; sections what-it-is, architecture, agentic-loop, the-team, how-agents-differ, aws, faq, replay; the architecture figure is HTML bands plus one inline SVG for the provider lines and one SVG asset (the human figure); the replay frame is a static mock; the loop section is text only | decoded with `scripts/extract_design_assets.load_bundle` |
| Existing pieces | `page()` helper and static mount in `app/main.py`; `/demo?run=<id>` loads a recording read-only; the files and prompt routes serve a run folder; `pandoc` and Typst from S4 | `app/main.py`, `app/web/static/js/demo.js` |

No dependency is added. Details in [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.13; vanilla JavaScript; one CSS file

**Primary Dependencies**: FastAPI, Pydantic; pandoc and Typst through `app.compile` for the PDF; the standard library's markdown handling is not enough, so the page renderer is a small in-house converter for the subset the content uses (headings, paragraphs, bold and italic, numbered and bulleted lists, one pipe table, HTML comments dropped), the same subset `app/web/static/js/draft.js` handled before S4

**Storage**: content in `content/intro/*.md` (read at request time); diagram SVGs generated in memory for the page and written to `runs/_intro/` for the PDF; the PDF under `runs/_intro/introduction.pdf`; the pinned run id in `.env` as `PUBLIC_RUN_ID`

**Testing**: pytest (renderer unit tests with a content diff; route tests with the TestClient; the public endpoint refusal test), Playwright browser tests (page renders, cards expand, frame plays the pinned run), screenshot comparison against the export's partial capture, PDF text test (`compiler` marked)

**Target Platform**: presenter laptop and any browser a prospect uses, including phone width

**Project Type**: web application

**Performance Goals**: page render under 200 ms server side; PDF under 10 s; the frame plays the pinned run at 4x as the Demo does

**Constraints**: copy never rewritten in code; no login exists yet, so nothing added may need one; the public endpoint must not leak other recordings; event schema untouched; no em dashes in page, SVG or PDF text

**Scale/Scope**: one page, one renderer module, one diagram module, two routes plus a public run endpoint, one Typst template, one script, a read-only flag on the Demo page, tests, deviations, roadmap status

## Constitution Check

| Principle | S6 compliance | Status |
|---|---|---|
| I Demo, not product | One public page and one pinned run; no run browser, no analytics, no comments | Pass |
| II Events only | The frame is the Demo renderer on the recording's events; the page itself is static content | Pass |
| III, IV | No run is started, changed or asked anything | Pass |
| V Roles are real | Seat cards read the roster names and the seat definitions' tools and scopes | Pass |
| VIII Reliability | The frame plays from the run folder alone; the endpoint reads files, never providers | Pass |
| IX Writing rules | Content files are the copy; lint covers the page, the SVG text and the PDF text | Pass |
| X, XI Controlled sources | Copy from `content/intro/`; appearance from the export; the loop diagram, the SVG bands and the real replay frame are recorded deviations with the export's decisions | Pass |
| XII Vertical slices | Builds on S4 and S5; no schema change | Pass |
| XIII Acceptance recorded | Content diff, screenshot comparison, endpoint test, browser replay, PDF test | Pass |
| XIV Projector | Not the page's audience; the export's 18 px body and 48 px headings are kept | Pass |
| XV Dependencies | None added | Pass |
| XVI Quality gates | Existing gates plus the new tests; compiler tests skip by tool name | Pass |
| XVII Credentials | None involved; the public endpoint reads no `.env` value but the run id | Pass |
| XVIII Design wired, not redesigned | The export's section layout, typography, card and frame styles are flattened as they are; the diagrams keep the export's band layout as SVG; additions are recorded | Pass |
| XIX Approval | Seven owner decisions of 2026-09-17 in the spec | Pass |
| Non-goals | No multi-user viewing, no dashboard; one pinned run, read-only | Pass |

Re-check after Phase 1 design: no new violation. The read-only flag on the Demo page hides controls; it adds no state and no route that changes a run.

## Project Structure

### Documentation (this feature)

```text
specs/007-introduction-replay/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── introduction.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
app/intro/__init__.py              render_page, render_pdf, sections, diagrams
app/intro/content.py               reads content/intro/*.md in order; markdown subset to HTML; plain text for the diff and the lint
app/intro/diagrams.py              architecture, loop, demo-versus-production as SVG strings from one description of the bands
app/intro/team.py                  eight team cards from the roster, the seat definitions and the content file's appraisal names
app/intro/pdf.py                   markdown for the PDF with the SVG files, through app.compile.render_markdown with templates/introduction.typ
app/web/pages/introduction.html    flattened from the export: header without the selector, the eight sections with slots, the replay frame shell
app/web/static/js/intro.js         team card expand and the frame's speed control; nothing else
app/web/static/css/app.css         appended .intro-* rules copied from the export's inline styles
app/web/static/js/demo.js          public flag: hide the composer, controls and Handoff actions; load the pinned run through the public endpoint
app/main.py                        GET /introduction, GET /introduction.pdf, GET /public/run/{run_id}/events, /public/run/{run_id}/files/{path}, /public/run/{run_id}/prompts/{ref}, and the Demo page's public mode
app/config.py                      Settings.public_run_id from PUBLIC_RUN_ID
templates/introduction.typ         Letter, single column, ink colour headings, the same family as the response template
scripts/intro_pdf.py               writes the PDF and prints its path
content/intro/*.md                 unchanged unless a name check finds an error (none did)
tests/unit/s6/                     content renderer and diff, diagrams, team cards
tests/integration/s6/              routes, public endpoint refusal, PDF route and script
tests/visual/                      Introduction screenshot comparison and browser tests (page, cards, frame)
tests/visual/masks.py              Introduction masks for the frame and the loop section
docs/design-deviations.md          S6 decisions
docs/roadmap.md                    S6 status
```

**Structure Decision**: extend the single project with one new package `app/intro/`; the Demo page gains a public flag rather than a second renderer, so the frame stays the real thing.

## Delivery order

1. Content renderer and diff test; team cards; diagrams module with SVG snapshot tests; the Typst template and the PDF script and route.
2. The page: flatten the export's markup and styles, wire the sections, cards, diagrams and header; screenshot comparison against the partial capture.
3. The public endpoint and the Demo page's public mode; the frame; the pinned run setting; browser tests.
4. Deviations, roadmap status, gates, push, message to the S7 session (it needs the public route list for its login guard).

## Complexity Tracking

No constitution violations to justify.
