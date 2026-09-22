# Implementation Plan: Lettered provenance markers

**Branch**: `013-lettered-markers` | **Date**: 2026-09-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/013-lettered-markers/spec.md`

## Summary

Provenance markers are labelled a, b, c instead of 1, 2, 3 on every surface a person or the Reviewer reads: the superscript on the compiled pages, the overlay button in the Deliverable panel, the Marker column of the printed Provenance table, and the bracketed marker in the Reviewer's page text. One Python function turns a marker's number into its label, counting as spreadsheet columns do. The compile passes that label to the Typst template and writes it into `markers.json` as a new `label` field, which the overlay shows, falling back to the number for recordings that have no label. The marker's integer number, the tag ids and every event payload stay as they are, so the schema and the golden logs do not move. The Reviewer's seat instruction is reworded for letters, and 5 recorded Reviewer requests are replayed on the recompiled, lettered pages before the work is merged.

## Technical Context

**Language/Version**: Python 3.13; vanilla JavaScript in the flattened Demo page; Typst template language

**Primary Dependencies**: pandoc 3.10 and Typst 0.15 for the compile (unchanged); Strands Agents with Ollama for the replay check (unchanged). No new dependency.

**Storage**: files under `runs/<id>/artifacts/v<N>/`: `markers.json` gains one field, `pages.json` changes its bracketed marker text

**Testing**: pytest (`-m compiler` for tests that run Typst, `-m visual` for Playwright browser tests); `scripts/check.py` runs the gates

**Target Platform**: the demo laptop (Windows 11), Chrome on the projector

**Project Type**: web application (FastAPI serving static pages) with a compile pipeline

**Performance Goals**: none new. A compile still takes about a third of a second.

**Constraints**: event types, payloads, the schema version and golden logs unchanged (FR-009); recorded runs replay unchanged (FR-007); no em dashes (IX)

**Scale/Scope**: up to 45 markers per draft on record; the label function has no upper limit

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I Demo, not product | The change is what the prospect sees on the projector and in the PDF. Nothing is added for unattended use. | Pass |
| II Schema first, events only | No event type or payload changes. `markers.json` is a compile artifact beside the pages, not an event, and the UI still renders only what the run produced. | Pass |
| III One owner of state, IV One door | Untouched. | Pass |
| V Roles are real | The Reviewer's instructions change wording only: letters instead of numbers. Tools, scope and model are unchanged. | Pass |
| VI Design for the failure | The Reviewer's input changes, so its ability to fail a planted defect is checked by replaying recorded reviews before merging (spec User Story 4). Exits and goldens are unchanged. | Pass |
| VII Provenance | Every tagged figure still carries a marker that resolves to its source; only the label changes. | Pass |
| VIII Reliability on demo day | A recording made before the change replays with its own numbers (FR-007), so replay stays faithful. | Pass |
| IX Writing rules | No em dashes; the lint covers the template, prompts and generated pages. | Pass |
| X Controlled sources of truth | `docs/spec-input.md` 2.6 says nothing about how a marker is labelled. The numbered label is recorded in `docs/design-deviations.md` (S4 item 2) and the S4 status in `docs/roadmap.md`. Those records change first, with a roadmap decision entry for the owner's ten decisions. | Pass |
| XI Reconcile before building | The design export shows tags as underlined figures; the recorded deviation already covers markers, and it is updated to say letters. | Pass |
| XII Vertical slices | Demonstrable from the Demo page: compile a run, see letters on the pages and the overlay. | Pass |
| XIII Acceptance testable | Unit tests for the label, compile tests for the pages and `markers.json`, a browser test for the overlay and its fallback, the golden compare suite, and the replay record. | Pass |
| XIV Built for a projector | The overlay button keeps its 22 px size; two letters at its 11 px monospace font fit inside it. | Pass |
| XV Dependencies | None added. | Pass |
| XVI Quality gates | `scripts/check.py` must be green before the commit. | Pass |
| XVII Credentials | Not touched. The replay uses local Ollama and needs no key. | Pass |
| XVIII Export wired, never redesigned | The overlay element, its size and colours are unchanged; only its text changes. | Pass |
| XIX Human approval | This changes a recorded decision (S4 decision 2a, numbered markers). The owner requested it and gave ten decisions on 2026-09-21, recorded in the spec. | Pass |
| Non-goals | "Provenance beyond hover-to-highlight": nothing is added to provenance; hover is unchanged (FR-010). | Pass |

**Post-design re-check (after Phase 1)**: unchanged. The design adds one field to an artifact file and one argument to a template function; no gate moves.

## Project Structure

### Documentation (this feature)

```text
specs/013-lettered-markers/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── markers.md       # the label rule, the template call, markers.json, the Reviewer's page text
├── checklists/
│   └── requirements.md
├── evidence.md          # written during implementation: the Reviewer replays and the gate results
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/compile/
├── markers.py           # marker_label(n); MarkerDraft carries its label; the #prov call and the appendix use it
└── pipeline.py          # Marker carries label into markers.json; comments say letter

templates/
└── rfp-response.typ     # #prov(n, label, src) prints the label, superscript or " [label]" in text mode

app/web/static/js/
└── render.js            # overlay shows m.label, falling back to String(m.n)

config/electrical-bid/seats/
└── reviewer.md          # markers are letters; cite a figure by its marker letter

docs/
├── roadmap.md           # decision entry for this change
├── design-deviations.md # S4 item 2 says letters
├── seat-flow.md         # Reviewer "Sees" row example says [a]
└── seat-deep-dive.md    # Reviewer input says the marker is a letter in brackets

tests/
├── unit/s4/test_markers.py      # label rule, #prov call, appendix letters
├── unit/s4/test_pipeline.py     # page text "[a]", markers.json label (compiler)
└── visual/test_e2e_ui.py        # overlay shows the label; a label-less markers.json shows the number
```

**Structure Decision**: The existing single-project layout. All changes sit in the compile package, the response template, the Demo page renderer and the Reviewer's seat file, with their tests beside the existing S4 tests.

## Complexity Tracking

No constitution violations to justify.
