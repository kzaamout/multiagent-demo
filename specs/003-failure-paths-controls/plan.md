# Implementation Plan: Failure paths and presenter controls (S3)

**Branch**: `003-failure-paths-controls` | **Date**: 2026-09-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-failure-paths-controls/spec.md`

## Summary

Make the S1 engine's failure paths work live and hand the presenter control of a run. Derive four failure datasets from the Clean run Typst sources, each with one planted change. Emit pause and resume as Orchestrator events, make Stop cancel a run in flight, add Dry intake to the run request, and enable Pause, Stop, and the Dry intake toggle in the composer for live runs. Show the spend on the cost ceiling card. Verify each scenario with a live run from the Demo page against its golden log, review the new controls for family consistency, and keep every gate green.

## Verified versions and names (2026-09-15)

| Item | Verified | Source |
|---|---|---|
| strands-agents | 1.55.1 pinned; PyPI lists 1.56.0 | PyPI JSON, installed metadata |
| Ollama | 0.34.1 | local `GET /api/version` |
| Typst | 0.15.1 | `typst --version` |
| Seat models | Qwen 3.5 9B (Orchestrator, Intake, Pricing, Writer), Claude Sonnet 5 on Bedrock with thinking off (Estimator), Gemma 4 12B (Reviewer) | `config/models.yaml`, roadmap decisions 13 to 15 |

No dependency is added. Details in [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.13; vanilla JavaScript in the static page

**Primary Dependencies**: FastAPI, Pydantic, Strands Agents 1.55.1, pypdfium2; Typst 0.15.1 for authoring dataset PDFs

**Storage**: files: `datasets/`, `runs/<run_id>/` recordings, `knowledge/` per client

**Testing**: pytest (unit, integration with the scripted model, lint), Playwright visual and browser tests, live verification runs with a per-run cost ceiling

**Target Platform**: presenter laptop, Windows 11, 12 GB graphics card, Chrome

**Project Type**: web application (FastAPI server with a static page)

**Performance Goals**: Stop ends a run within 5 s in every state; Not ready ends within 2 minutes of Run; Escalate ends within 5 s

**Constraints**: event schema v1.0.0 frozen; the page renders only from events; no em dashes anywhere; credentials only in `.env`; live runs under `COST_CEILING=1.00`

**Scale/Scope**: four derived datasets, three composer controls, two engine changes, one card detail, one evidence command

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | S3 compliance | Status |
|---|---|---|
| I Demo, not product | Controls serve a presenter on stage; no unattended-use features | Pass |
| II Events only | Pause and resume become events; cards render from events; Stop is visible only through `run.terminated` | Pass |
| III One owner of state | Only the Orchestrator emits pause, resume, and termination; controls call the Orchestrator | Pass |
| IV One door | Blocker questions and answers go through the Orchestrator's card | Pass |
| V Roles are real | No change to scopes or tools; rework context carries only the routed findings | Pass |
| VI Design for the failure | The slice itself: four narrative exits plus the control exits, nothing else | Pass |
| VII Provenance | Unchanged; the Writer's provenance check stays on the rework path | Pass |
| VIII Reliability on demo day | Stop cancels in flight; every live run has a cost ceiling | Pass |
| IX Writing rules | Dataset text, READMEs, and card copy lint-checked for em dashes | Pass |
| X, XI Controlled sources, reconcile | Golden logs are not edited to fit live runs; mismatches are reported | Pass |
| XII Vertical slices | Builds on S2 without changing the frozen schema | Pass |
| XIII Acceptance recorded | Evidence command and recorded live runs per scenario | Pass |
| XV Dependencies | None added | Pass |
| XVI Quality gates | Existing gates plus dataset integrity tests and control tests | Pass |
| XVII Credentials | No change | Pass |
| XVIII Design wired, not redesigned | Blocker card, Pause control, and Dry intake toggle reviewed against the export families; findings recorded | Pass |
| XIX Approval | Owner approved S3 and dataset derivation on 2026-09-15; any seat instruction tuning found necessary is reported | Pass |
| Non-goals | Reject re-entering the loop: not built. Editing prompts mid-run: Pause freezes dispatch only | Pass |

Re-check after Phase 1 design: no new violation. The Stop cancellation keeps the Orchestrator as the only emitter of the termination.

## Project Structure

### Documentation (this feature)

```text
specs/003-failure-paths-controls/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── controls.md
├── checklists/
│   └── requirements.md
└── tasks.md             # from /speckit-tasks
```

### Source Code (repository root)

```text
app/orchestrator/orchestrator.py   pause and resume events; Stop cancels the run task and child tasks
app/runs/registry.py               start_run(dry_intake); keeps the run task for Stop
app/main.py                        RunRequest.dry_intake
app/live/source.py                 unchanged unless live verification needs it
app/web/pages/demo.html            Pause, Stop, Dry intake controls enabled per state
app/web/static/js/demo.js          control wiring, Pause and Resume toggle, Dry intake flag on Run
app/web/static/js/render.js        control states; cost ceiling spend on the termination card
datasets/planted-inconsistency/    source/, inputs/, fixtures/, README.md
datasets/missing-sheet/            source/ with LP-2 and no E-003, inputs/, fixtures/, README.md
datasets/missing-price/            source/, inputs/, fixtures/ without Exit sign, LED, README.md
datasets/not-ready/                source/ without deadline, inputs/ without specification, fixtures/, README.md
scripts/compare_run.py             recorded run against its golden log
tests/integration/s3/              dataset integrity, controls, dry intake, stop cancellation, cost ceiling
tests/visual/                      browser tests for Pause, Stop, Dry intake, blocker Escalate
docs/design-deviations.md          S3 family-consistency review
docs/roadmap.md                    S3 status
```

**Structure Decision**: extend the existing single project; S3 adds datasets, tests, and one script and changes a handful of existing modules.

## Delivery order

1. Engine: pause and resume events, Stop cancellation, Dry intake flag, with tests on the scripted model and stubs.
2. Page: controls and the cost ceiling card detail, with browser tests.
3. Datasets: derive the four, integrity tests, READMEs.
4. Live verification from the Demo page: Not ready, Missing price, Missing sheet with Escalate and with Answer, Planted inconsistency, then Stop, Pause, Dry intake, and the cost ceiling on Clean run.
5. Family-consistency review, deviations, roadmap status, gates.

## Complexity Tracking

No constitution violations to justify.
