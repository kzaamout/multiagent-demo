# Implementation Plan: Seat model guide on Settings

**Branch**: `014-seat-model-guide` | **Date**: 2026-09-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/014-seat-model-guide/spec.md`

## Summary

Beside each seat, the Settings page names the top open model and the top proprietary model with their instruction accuracy and counts, shows the current model's own figure in its model button, defines the figure under the title, and explains instruction accuracy and behaviour accuracy at the foot. Instruction accuracy is the report's existing first-time figure (`accepted_first_time / replies` from each run's `metrics.json`), summed per seat and model label over every recorded run. A new module, `app/runs/guide.py`, owns the run reading (moved from the report), the figure, the Wilson lower bound, the 5-run threshold and the picks; the registry holds one cached instance per runs folder that re-reads only changed folders, and `GET /api/seats` carries the result. Each model in `config/models.yaml` states `weights: open` or `weights: proprietary`. The performance report uses the same module for a new "Top models per seat" section and relabels "First time" as "Instruction accuracy" and "Accuracy" as "Behaviour accuracy". No event, schema, golden, seat instruction or model call changes.

## Technical Context

**Language/Version**: Python 3.13; vanilla JavaScript and one CSS file for the flattened Settings page

**Primary Dependencies**: FastAPI, PyYAML (both present). No new dependency.

**Storage**: none new. Reads `runs/<id>/metrics.json` and `runs/<id>/events.jsonl`; `config/models.yaml` gains one key per model.

**Testing**: pytest (unit and integration); Playwright under `-m visual` for the page and the screenshot comparison; `scripts/check.py` runs the gates (ruff, mypy, pytest, em dash lint)

**Target Platform**: the demo laptop (Windows 11), Chrome on the projector

**Project Type**: web application (FastAPI serving static pages) with report scripts

**Performance Goals**: Settings shows its figures within 1 second with about 400 recorded runs (SC-004). Measured: a cold read of 389 folders takes 0.36 s, a folder scan 0.025 s (research D7).

**Constraints**: no timer or polling on the page (constitution II, FR-012); no stored file of figures (rule 15, FR-011); CSV column names unchanged (rule 13); the export's row layout and column widths unchanged (XVIII); no em dashes (IX)

**Scale/Scope**: 6 seats, 12 registry models, about 400 run folders growing by tens per sweep

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I Demo, not product | The guide answers the question a prospect asks the presenter at the Settings page, "why that model?", from evidence the project already collects. Nothing is built for unattended use. | Pass |
| II Schema first, events only | No event type, payload or schema version changes. The picks are configuration advice beside the model menu, like its availability notes, not run state; the Demo page's rendering of a run is untouched. No timer or poll: figures arrive as the reply to the page's own request. | Pass |
| III One owner of state, IV One door | Untouched: the guide reads recordings and changes nothing. | Pass |
| V Roles are real | The seat's card and model menu go on showing the live model. The figure in the button follows the model's name without altering it, and the picks are labelled as picks (FR-009, FR-010). | Pass |
| VI Design for the failure | Exits, goldens and planted defects unchanged. | Pass |
| VII Provenance | Not touched. | Pass |
| VIII Reliability on demo day | Reading is cached per folder; an unreadable folder is skipped, so the page always renders. No network call. | Pass |
| IX Writing rules | New copy, report text and comments carry no em dash; the lint covers them. | Pass |
| X Controlled sources of truth | `docs/spec-input.md` 2.3 defines the Settings page. It is amended first, with a changelog line, to add the guide; the layout addition is recorded in `docs/design-deviations.md` and the owner's decisions as roadmap decision 37. | Pass |
| XI Reconcile before building | The export's Settings has no guide. The case is recorded with its decision in `docs/design-deviations.md` (research D9, D10). | Pass |
| XII Vertical slices | Demonstrable on the Settings page with the recorded runs; no layer is built ahead of its use. | Pass |
| XIII Acceptance testable | Unit tests for the figure, bound, threshold, picks and cache; an API test on a seeded runs folder; a report test that the page and the report agree; a Playwright test for the rendered text; the screenshot comparison still runs on everything but the additions (research D10). | Pass |
| XIV Built for a projector | The guide lines use the export's meta text size, as the page's existing sub line and status line do; the model's name in the button keeps its 15 px. The guide is read up close by the presenter; the names the audience reads are unchanged. | Pass |
| XV Dependencies | None added; a filesystem watcher was rejected (research D7). | Pass |
| XVI Quality gates | `scripts/check.py` and `pytest -m visual` green before the commit. | Pass |
| XVII Credentials | Not touched; availability stays a boolean and a reason. | Pass |
| XVIII Export wired, never redesigned | The additions reuse the export's `.page-sub` and `.menu-note` styles; the three columns and their widths stay. | Pass |
| XIX Human approval | The owner requested the feature and gave ten decisions and two clarifications on 2026-09-21, recorded in the spec. The report relabelling was the owner's answer B. | Pass |
| Non-goal: a model leaderboard | Two names per seat plus the current model's figure, on the existing page. No page of its own, no ranked list, no history, no sorting, no figures in the menu options (decision 1a). | Pass |
| Non-goal: providers or credentials from the UI | Nothing new can be changed from the page; the `weights` field is edited by hand in the registry file. | Pass |

**Post-design re-check (after Phase 1)**: unchanged. The design adds one registry key, one module, keys to an existing response, and page elements in existing styles; no gate moves.

## Project Structure

### Documentation (this feature)

```text
specs/014-seat-model-guide/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── seats-guide.md   # registry field, /api/seats additions, page elements and copy, report section
├── checklists/
│   └── requirements.md
├── evidence.md          # written during implementation: baseline, load time, page and report, gates, quickstart
├── settings-guide.png   # the Settings page on the real runs, captured during implementation
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/runs/
├── guide.py             # NEW: metrics_of (moved), instruction_accuracy, whole_percent, wilson_lower,
│                        #      MIN_RUNS_FOR_BEST, SeatRecord, SeatPick, records(), picks(), SeatGuide cache
└── registry.py          # holds a SeatGuide; seat_table() adds row["guide"] and table["guide"]

app/live/
└── providers.py         # ModelSpec.weights, validated in ModelConfig.load

app/seats/
└── definitions.py       # needs_image_input(agent_id), moved from the report's seat table

app/web/
├── pages/settings.html  # guide-note line under the title, guide-foot paragraph
└── static/
    ├── js/settings.js   # select-fig in the button, seat-guide block, guide-note run count
    └── css/app.css      # .select-fig, .seat-guide, .guide-line, .guide-kind, .guide-value, .settings-foot

config/
└── models.yaml          # weights: open | proprietary on all 12 models

scripts/
└── model_report.py      # imports the guide module; "Top models per seat" section; label renames

docs/
├── spec-input.md                 # 2.3 amended, changelog line
├── model-performance.md          # regenerated
├── model-performance-columns.md  # regenerated
├── model-performance-runs.csv    # regenerated, same columns
├── design-deviations.md          # new section for this change
└── roadmap.md                    # decision 37

CLAUDE.md                # one pointer to the guide module

tests/
├── unit/guide/support.py                      # NEW: write_run() seeds a synthetic run folder for the guide tests
├── unit/guide/test_guide.py                   # NEW: figure, bound, threshold, kinds, needs, ties, statuses, cache
├── unit/guide/test_registry_weights.py        # NEW: weights parsing and the real registry's values
├── integration/guide/test_seats_guide_api.py  # NEW: /api/seats on a seeded runs folder, live run left out
├── unit/sweep/test_report_sections.py         # label renames; report section agrees with the guide
├── visual/masks.py                            # the additions hidden in the Settings captures, with reason
├── visual/capture_app.py                      # applies the hidden additions
└── visual/test_e2e_ui.py                      # the guide renders with its text on a seeded runs folder
```

**Structure Decision**: The existing single-project layout. The shared calculation lives in `app/runs/`, beside `metrics.py` whose rows it reads, so both the server and the report script import it; the report stops owning `metrics_of`. Tests for the new module sit in new `tests/unit/guide/` and `tests/integration/guide/` folders, following the per-feature folders already there.

## Merge notes

Branch `012-clock-seat-preflight` is not on `main` yet and touches some of the same files: `app/web/static/js/settings.js` (the swap handler and a recheck; this work changes the row rendering), `app/runs/registry.py` (two lines), `tests/visual/masks.py`, `docs/design-deviations.md`, `CLAUDE.md`, and the version line and changelog of `docs/spec-input.md` (it moves to 0.8). Whichever merges second keeps both changes; if 012 merges first, this work's spec-input change becomes 0.9.

## Complexity Tracking

No constitution violations to justify.
