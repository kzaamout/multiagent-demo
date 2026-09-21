# Implementation Plan: Presenter clock and seat-aware pre-flight

**Branch**: `012-clock-seat-preflight` | **Date**: 2026-09-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/012-clock-seat-preflight/spec.md`

## Summary

The Demo page's Elapsed figure becomes a display-only clock. The reducer works out the run's working time from the events alone: time since `run.started`, less the human waits bracketed by events the schema already has. A small pure clock module adds the time since the latest event, read from the run's own clock for a live run and from the replay speed for a replay. One 250 ms interval rewrites `#elapsed` and nothing else. The termination card shows the same working time.

The pre-flight stores facts per row, not verdicts. It adds one row per model in the registry, probed at the same time, plus rows for the Introduction recording and the replays, and a family row worked out when read. One header policy function decides the dot on every read, from the stored rows, the seats in force, and the run mode: red for what stops this demo, amber for what harms it, green otherwise. A new recheck route, called by the Settings page after a successful swap, rechecks the chosen model and the env row and updates the Settings dot in place.

The constitution moves to 1.3.0 to allow the clock. `docs/spec-input.md` moves to 0.8. No event, schema version, or golden log changes.

## Verified versions and names (2026-09-21)

| Item | Verified | Source |
|---|---|---|
| Playwright clock control | `page.clock.install()`, `run_for()`, `fast_forward()` in the installed Playwright 1.62.0 | `uv run python -c "import importlib.metadata as m; print(m.version('playwright'))"` |
| Run clock | `Clock(start, pace)`: live team runs pace 1.0, stubbed runs `STUB_PACE` (4.0); `ts(offset)` and `elapsed_offset_ms()` | `app/orchestrator/clock.py`, `app/runs/registry.py` lines 428 and 431 |
| Hold events | `clarification.asked` (with or without `blocker`), `clarification.answered`, `run.paused`, `run.resumed`, `handoff.ready`, `human.approved`, `run.terminated` | `app/schema/events.py`, `docs/schema/events-v1.1.0.md` |
| Registry | 13 models: 3 Bedrock, 2 Google, 1 xAI, 7 Ollama; `family_of`, `family_warning` | `config/models.yaml`, `app/live/providers.py`, `app/runs/registry.py` |
| Replay sources today | all nine datasets have a recording or golden log; the pinned public run is on disk | `Registry.replay_source`, `Registry.events_for(public_run_id)`, checked 2026-09-21 |
| Dot styles | `.pf-dot[data-status]` pending, pass, warn (#e0730a), fail (#b30000) | `app/web/static/css/app.css` lines 90 to 93 |

No dependency is added.

## Technical Context

**Language/Version**: Python 3.13; vanilla JavaScript in the static pages

**Primary Dependencies**: FastAPI, Strands Agents (the existing one-word probe), httpx (Ollama tags), Playwright (tests only, already installed)

**Storage**: `runs/preflight.json` at schema 2; no other file

**Testing**: pytest with injected probes and a scripted seat model factory; httpx ASGI client for the routes; Playwright with clock control for the clock and the Settings recheck; the existing visual comparison, with masks recorded for added rows

**Target Platform**: presenter laptop, Windows 11, Chrome, projector at 1920 by 1080

**Project Type**: web application (FastAPI server with static pages)

**Performance Goals**: `#elapsed` within 250 ms of the true second; a full pre-flight under 60 s with every model probed at the same time; a recheck under 35 s; a page load works out the header in well under a millisecond (a file read and a loop over under 25 rows)

**Constraints**: schema 1.1.0 untouched; the reducer stays pure; the only timer is the Elapsed tick; no polling on Settings or Pre-flight; credentials never in a row, title, or response; no em dashes; machine identifiers stable (the new `model:<key>` ids are new, not renamed)

**Scale/Scope**: one new Python module (`app/preflight/header.py`), one new JS module (`clock.js`), one new route, fields added to two responses, schema 2 of one stored file, edits to four JS files and four Python files, three controlled documents amended

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Status |
|---|---|---|
| I Demo, not product | Everything serves the presenter on demo day: a clock that reads right on a projector, a dot that means "this demo will work". No unattended-use feature. | Pass |
| II Events only | **Amended to 1.3.0 by owner decision 1.** The clock is the one display-only exception: it adds elapsed time between events to a working time worked out from the events, changes no state, and is not emitted or recorded. Pre-flight stays outside the event stream as in S7. | Pass after amendment |
| III One owner of state | The Orchestrator is untouched apart from a read-only `now_ts()` on its clock. | Pass |
| IV One door | No change to how the human is asked. | Pass |
| V Roles are real | Model rows and tooltips name the real model and the seat on it. | Pass |
| VI Design for the failure | The family row enforces the Reviewer rule in the dot (amber). Each probe keeps its timeout and one-line failure. | Pass |
| VIII Reliability | The pre-flight now checks every model, the Introduction recording, and the replays, which are the demo-day fallback. | Pass |
| IX Writing rules | New copy lint-checked for em dashes. | Pass |
| X, XI Controlled sources | The constitution, `CLAUDE.md` rule 3, `docs/spec-input.md` 2.2 and 2.4 (to 0.8), and `docs/design-deviations.md` change first (task phase 1). | Pass |
| XII Vertical slices | Each story is demonstrable from the Demo, Settings, or Pre-flight page on its own. Schema unchanged. | Pass |
| XIII Acceptance recorded | Browser tests with clock control, route tests, and the visual comparison with masks recorded per added region. | Pass |
| XIV Projector | The clock is the design's own figure. Added pre-flight rows use the existing row component. | Pass |
| XV Dependencies | None added. Playwright's clock control is part of the installed package. | Pass |
| XVI Quality gates | `scripts/check.py` and `pytest -m visual` gate completion. | Pass |
| XVII Credentials | The env row stores key names and presence only. The marker test covers the new route, payload, and tooltips. | Pass |
| XVIII Design wired | No restyle. Added rows reuse `check-row`, masked with reasons. The termination eyebrow keeps its form. | Pass |
| XIX Approval | The constitution change, the eleven owner decisions, and the superseded S7 decisions are recorded in the spec. | Pass |
| Non-goals | Multi-user viewing: the dot updates in place on Settings only, other pages on load. Model leaderboard: no, rows report reachability only. | Pass |

Re-check after Phase 1 design: no new violation. The only timer is the Elapsed tick, which is bounded to a running, anchored run and writes one text node.

## Project Structure

### Documentation (this feature)

```text
specs/012-clock-seat-preflight/
  spec.md
  plan.md
  research.md
  data-model.md
  quickstart.md
  contracts/http-api.md
  contracts/ui.md
  checklists/requirements.md
  tasks.md                     (next: /speckit-tasks)
```

### Source Code (repository root)

```text
.specify/memory/constitution.md   1.3.0: principle II sentence, Sync Impact Report
CLAUDE.md                         rule 3 exception
docs/spec-input.md                0.8: 2.2 elapsed, 2.4 seat-aware dot, changelog with superseded S7 decisions
docs/design-deviations.md         elapsed entry replaced; pre-flight added rows
app/
  orchestrator/clock.py           Clock.now_ts()
  preflight/result.py             schema 2 rows with checked_at and subject; merge; no overall status
  preflight/checks.py             model rows (cloud probe, local pulled), shared Ollama tags, env facts, intro-recording and replays rows
  preflight/header.py             new: derived family row, env row on read, header policy and titles
  preflight/runner.py             concurrent full run, recheck(model_key), payloads with header and seats
  preflight/__init__.py           exports
  main.py                         header helper over current seats on every page and /api/meta; live_run_clock; clock on POST /api/runs; POST /api/preflight/recheck; full-run flag and shared lock
  web/pages/demo.html             script tag for clock.js
  web/static/js/clock.js          new: S1Clock.valueAt
  web/static/js/reducer.js        holds and working time into view.clock
  web/static/js/render.js         #elapsed from the clock value; termination eyebrow from working time
  web/static/js/demo.js           anchors (live from the run clock, replay per event), the 250 ms tick, reset
  web/static/js/settings.js       recheck after a swap; status line; header dot from the reply
  web/static/js/preflight.js      rows and dot from the payload's header
tests/
  unit/s12/                       header policy table, env on read, schema 2 load and merge, model rows, marker
  integration/s12/                preflight API payload and dot on every page, recheck route, run clock fields, stub live run with a recheck adds no event
  visual/test_e2e_clock.py        new: working time over every golden log, tick and hold at 1x and 4x, final value, reload mid-run, fixed views still
  visual/test_e2e_ui.py           Settings recheck updates the dot in place
  fixtures/preflight-all-pass.json, preflight-one-fail.json   rewritten at schema 2
  visual/masks.py                 added pre-flight rows; demo elapsed and eyebrow regions if they differ
  unit/s7/, integration/s7/       updated where they assert schema 1 or per-provider rows
```

**Structure Decision**: The single web application as before. The pre-flight policy moves into one new module so every caller shares it. The clock's arithmetic lives in one new pure module so the browser tests can call it directly. Everything else is an edit in place.

## Delivery order

1. Controlled documents: constitution 1.3.0, `CLAUDE.md` rule 3, `docs/spec-input.md` 0.8, design deviations.
2. User Story 1: reducer holds and working time, `clock.js`, the run clock on the two responses, the tick in `demo.js`, `#elapsed` and the termination eyebrow, browser tests.
3. User Story 2: schema 2 result, model rows and the new rows, concurrent run, header policy, every caller moved to it, Pre-flight page from the payload, fixtures and masks, tests.
4. User Story 3: recheck route and lock, Settings flow, tests including the stub live run with a recheck.
5. Gates, visual suite, one live pre-flight on the laptop and one live run watched on the projector, `docs/model-performance.md` untouched (no live run is measured by this change).

## Complexity Tracking

| Item | Why needed | Simpler alternative rejected because |
|---|---|---|
| Principle II amendment (a timer in the UI) | Owner decision 1: the clock must tick between events | No compliant alternative: a server tick on the stream would not reach the Introduction's public replay, and the owner chose the browser clock. |
