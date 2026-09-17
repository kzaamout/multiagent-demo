# Implementation Plan: Seats, single model, and chat (S5)

**Branch**: `006-seats-single-chat` | **Date**: 2026-09-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-seats-single-chat/spec.md`

## Summary

Make the model a visible runtime attribute of every seat. Settings reads the provider registry and writes an in-memory per-seat override that the next dispatch uses, with `model.changed` emitted into the live run so every card follows. Add a Single-model run: one actor, one instructions file, the team's deterministic tools, four stage changes, exit `single_complete`, recorded and replayable like any run. Fill the Compare strip and the comparison line from the latest recordings of each mode. Complete the meters with provider latency and the comparison line. Add a read-only chat endpoint that answers from a seat's recorded prompt bundle and leaves the run folder untouched. Keep every edit to shared files additive so the S4 branch rebases cleanly.

## Verified versions and names (2026-09-16)

| Item | Verified | Source |
|---|---|---|
| Schema | 1.1.0, frozen; `model.changed`, `meter.update.latency_ms`, `stage.changed` in a Single-model run, `single_complete` all already typed | `app/schema/events.py`, `docs/schema/events-v1.1.0.md` |
| Registry | `config/models.yaml`: providers bedrock, google, xai, ollama; seat defaults on local Ollama models with the Estimator on Bedrock | `app/live/providers.py` |
| Meters UI | Detail row and ceiling bar already rendered from `meter.update`; the comparison line is static text | `app/web/static/js/render.js` |
| Export switches | `mode`, `chatOpen` on Demo; `openDropdown` on Settings; references `demo-terminated-chat.png` and `settings-dropdown.png` already captured | `scripts/capture_export.py`, `tests/visual/reference/` |

No dependency is added. Details in [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.13; vanilla JavaScript in the static pages

**Primary Dependencies**: FastAPI, Pydantic, Strands Agents 1.55.1 (a fresh Agent with no tools for chat), pypdfium2 (unchanged)

**Storage**: files: `runs/<run_id>/` recordings (source of the comparison), `config/models.yaml` (read only), in-memory seat overrides on the registry, chat history held in the browser panel only

**Testing**: pytest with the scripted model for swaps, Single-model runs, and chat; the byte-identical run folder test; Playwright visual comparison for Settings closed and open and Demo with the chat panel; live verification runs under the cost ceiling

**Target Platform**: presenter laptop, Windows 11, Chrome, projector at 1920 by 1080

**Project Type**: web application (FastAPI server with static pages)

**Performance Goals**: a swap reaches every card within 1 s (the event is emitted on the API call and streamed at once); a chat reply within the model's own latency; the comparison loads with the page

**Constraints**: schema 1.1.0 frozen; the page renders only from events (the comparison and chat are read from recordings and an out-of-band endpoint, never from run state); no em dashes; credentials only in `.env`; shared files touched additively (S4 in parallel); the workflow id, event types, and agent ids stay stable apart from the added `single` seat

**Scale/Scope**: one new seat, one new instructions file, five new API routes, two new page scripts (Settings, chat), one stub scenario, one comparison reader, two visual states added to the comparison

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | S5 compliance | Status |
|---|---|---|
| I Demo, not product | Settings lists what `.env` allows; no credential entry, no persistence of swaps | Pass |
| II Events only | The swap is visible as `model.changed`; the Single-model run is a run of events; the comparison reads recordings; chat is declared out of band by the spec and touches nothing the page renders from events | Pass |
| III One owner of state | The Orchestrator emits `model.changed` and every Single-model event; the registry only holds the override | Pass |
| IV One door | Chat is not the human door; it cannot answer a question or a blocker | Pass |
| V Roles are real | The label is always the live model: Settings, cards, meters, and the API read the same roster; the Single-model actor is its own seat, not a disguised team seat | Pass |
| VI Design for the failure | `single_complete` is a control exit; the cost ceiling still applies to a Single-model run | Pass |
| VII Provenance | The Single-model output carries none, and the strip says so | Pass |
| VIII Reliability | A Single-model run records and replays from its folder; chat is not recorded because it is not part of the run | Pass |
| IX Writing rules | New copy and `single.md` lint-checked | Pass |
| X, XI Controlled sources | `models.yaml` is never written; the override is memory only | Pass |
| XII Vertical slices | Schema unchanged; adds a seat and routes | Pass |
| XIII Acceptance recorded | Scripted tests per story, the byte-identical test, the Settings and chat captures, one recorded Single-model run | Pass |
| XV Dependencies | None added | Pass |
| XVI Quality gates | Existing gates plus new unit and integration folders | Pass |
| XVII Credentials | Availability is a boolean and a reason; no value leaves the server | Pass |
| XVIII Design wired, not redesigned | Settings dropdown, Single model switch, model dropdown, Compare body, and chat panel follow the export's markup and styles; the Settings labels differ from the export by design (deviation recorded) | Pass |
| XIX Approval | Ten owner decisions of 2026-09-16 recorded in the spec | Pass |
| Non-goals | Providers from the UI: no. Changing instructions mid-run: the swap changes the model only. Leaderboard: one comparison line from two recordings | Pass |

Re-check after Phase 1 design: no new violation. The Reviewer and Writer family guard is a warning, as the owner decided; constitution VI's rule is kept by the defaults and surfaced when the presenter departs from it.

## Project Structure

### Documentation (this feature)

```text
specs/006-seats-single-chat/
  plan.md
  research.md
  data-model.md
  quickstart.md
  contracts/http-api-s5.md
  checklists/requirements.md
  tasks.md              (from /speckit-tasks)
```

### Source Code (repository root)

```text
app/
  live/providers.py            registry: availability once at startup, per-seat override, effective spec, chat model
  live/source.py               single(): the one-call Single-model step; swap_seat_model()
  live/chat.py                 new: out-of-band chat call from a recorded prompt bundle
  live/replies.py              SingleReply shape
  orchestrator/orchestrator.py mode, run_single(), change_model()
  orchestrator/roster.py       seat "single"
  runs/registry.py             overrides, start_run(mode, model), comparison(dataset_id)
  runs/comparison.py           new: latest terminated recording per mode and its figures
  agents/stubs/single_run.py   new: stub Single-model scenario for any dataset
  seats/definitions.py         seat "single" (tools union, scopes)
  main.py                      new routes only: /api/seats, /api/seats/{seat}, /api/datasets/{id}/comparison, /api/chat; RunRequest.mode and model
  web/pages/settings.html      rows rendered by settings.js from /api/seats
  web/pages/demo.html          composer switch live, model dropdown, chat panel skeleton
  web/static/js/settings.js    new
  web/static/js/chat.js        new
  web/static/js/demo.js        mode switch, model dropdown, comparison fetch, chat open (new functions)
  web/static/js/render.js      new functions: renderComparison, renderChat, latency in the detail row
  web/static/js/reducer.js     model.changed applied to the roster; mode from run.started
  web/static/css/app.css       appended rules only (chat body, compare body, model menu)
config/electrical-bid/seats/single.md   new
config/models.yaml             unchanged
tests/
  unit/s5/                     registry override, comparison reader, single reply shape, chat bundle lookup
  integration/s5/              swap mid-run, Single-model run and replay, chat byte-identical, API routes
  visual/                      settings-dropdown and demo-terminated-chat states added to the comparison
```

**Structure Decision**: single web application as before. New behaviour lands in new modules (`chat.py`, `comparison.py`, `single_run.py`, `settings.js`, `chat.js`) and in new routes and functions in the shared files, so the S4 branch's edits to the artifact panel and compile pipeline do not overlap.

## Delivery order

1. Registry: availability at startup, overrides, effective config, `/api/seats` (US1 backend).
2. `model.changed` in the Orchestrator and live source; reducer applies it to the roster; Settings page live (US1 complete, Settings captures).
3. Seat `single`, `single.md`, `SingleReply`, `run_single()`, stub scenario, `RunRequest.mode`; composer switch and model dropdown (US2 engine).
4. Comparison reader and route; Compare strip and comparison line; latency in the detail row (US2 and US3 complete).
5. Chat endpoint, panel, byte-identical test, chat capture (US4).
6. Gates, visual suite, one live Single-model run, roadmap and deviations entries.

## Complexity Tracking

No constitution violation to justify.
