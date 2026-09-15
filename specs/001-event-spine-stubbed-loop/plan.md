# Implementation Plan: Event spine and stubbed loop (S1)

**Branch**: `001-event-spine-stubbed-loop` | **Date**: 2026-09-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-event-spine-stubbed-loop/spec.md`

## Summary

Freeze the event schema as version 1.0.0 (prose document plus Pydantic models with a generated JSON Schema), build the hand-written Orchestrator state machine with all six stages and eight exits, drive it with stubbed agents that emit canned sequences for the six scenario datasets, record every run and replay it verbatim over a hand-rolled server-sent event stream, and flatten the Claude Design export into static HTML, one stylesheet, and vanilla render functions that build the Demo page from events alone. Login, Settings, and Pre-flight ship as static pages. Six golden logs, the replay-and-compare suite, the screenshot comparison, and the quality gates (ruff, mypy, pytest, em-dash lint, `.env` leak test) are the completion evidence. No model is called.

Versions and service names were verified on 2026-09-14 and are recorded in [research.md](research.md); nothing is pinned from memory.

### Verified on 2026-09-14 (sources and the full table in research.md)

| Item | Verified | Source |
|---|---|---|
| Strands Agents (Python SDK, package `strands-agents`) | 1.55.1, released 2026-09-09; extras `anthropic`, `ollama`, `litellm`, `gemini` | PyPI, github.com/strands-agents/sdk-python |
| Strands Agents tools (`strands-agents-tools`) | 0.8.8, released 2026-09-04 | PyPI |
| Amazon Bedrock AgentCore Python SDK (`bedrock-agentcore`) | 1.23.0, released 2026-09-11 | PyPI |
| Amazon Bedrock AgentCore service names | Harness, Runtime, Memory, Gateway, Identity, Code Interpreter, Browser, Observability, Payments, Evaluations, Optimization, Policy, Registry | AWS developer guide overview page |
| Typst | 0.15.1, released 2026-07-17; 0.15.1 installed locally | github.com/typst/typst releases, `typst --version` |

None of these is installed in S1. Strands arrives in S2, Typst in S4, and AgentCore stays a phase 2 production story per the non-goals. The AgentCore list is longer than the one most copy assumes (Harness, Payments, Optimization, Policy, and Registry are recent), so the Introduction copy check in S6 should use this list.

## Technical Context

**Language/Version**: Python 3.13 (3.13.14 on the reference machine; owner decision 2026-09-14)

**Primary Dependencies**: FastAPI 0.141.1, Uvicorn 0.53.0, Pydantic 2.13.5, PyYAML 6.0.3, python-dotenv 1.2.3. Dev: pytest 9.1.1, pytest-asyncio 1.4.0, httpx 0.28.1, mypy 2.3.1, ruff 0.16.7, Playwright 1.62.0, Pillow 12.3.0. Managed with uv 0.9.21 and a lock file. Rationale in `docs/dependencies.md`.

**Storage**: files only. Recordings under `runs/<run_id>/` (git-ignored), golden logs under `datasets/<id>/golden-events.jsonl`, prompt bundles as JSON, knowledge file as markdown.

**Testing**: pytest with asyncio; API tests through httpx against the FastAPI app; visual tests through Playwright and Pillow; lint scripts as tests.

**Target Platform**: Windows 11 presenter laptop (primary), any Linux host for cloud mode later. Chromium at 1920 by 1080.

**Project Type**: web application with a static frontend served by the same process.

**Performance Goals**: a stubbed run of any dataset finishes in under three minutes at pace 4 (scenario 2 in about 63 seconds); events reach the page within 100 ms of emission; replay timing error under one second per gap at 1x.

**Constraints**: UI renders only from events (no timers, no inferred state); the Orchestrator is the single owner of stage, human contact, knowledge writes, and termination; no em dashes anywhere; no credentials outside `.env`; design export untouched; no orchestration framework; fixed 1920 by 1080 frame per the export.

**Scale/Scope**: one presenter, one live run at a time, six datasets, four pages, roughly 25 event types, about seventy styled elements in the Demo page.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How S1 complies | Status |
|---|---|---|
| I Demo, not product | One live run at a time, no run browser, no accounts. Replay plays one recording per dataset. | Pass |
| II Schema first, events only | Schema frozen as the first task; every state change is an event; the page reduces events into the view; chat is not in S1. | Pass |
| III One owner of state | Only `Orchestrator` emits stage changes, dispatches, human questions, knowledge appends, retry counts, pause, resume, termination. Stubs cannot; tests assert that stub modules emit only agent event types. | Pass |
| IV One door to the human | Banner, blocker card, and Approve post to the Orchestrator's run endpoints; nothing is sent externally. | Pass |
| V Roles are real | Seat identity fixed; names random per run from two options; model label on every card comes from the actor object. | Pass |
| VI Design for the failure | All eight exits in the state machine; five exercised by stubs, three by unit tests; `run.terminated` always last. | Pass |
| VII Provenance | `task.completed` carries provenance; `draft.committed` carries tags; hover arrives in S4. | Pass (deferred hover is in the roadmap) |
| VIII Reliability on demo day | Every run recorded; Replay at 1x and 4x; cost ceiling in the state machine. Pre-flight live in S7. | Pass |
| IX Writing rules | Em-dash lint is a gate; fixture copy reviewed. | Pass |
| X Controlled sources of truth | Spec 0.5 and the export govern; schema additions (`title`, `text`, nullable `pdf_path`) are recorded in the contract. | Pass |
| XI Reconcile before building | Pre-build deviations are in `design/README.md`; deviations found while building are in `docs/design-deviations.md`, since `design/` is never edited. | Pass |
| XII Vertical slices on one foundation | S1 is the foundation plus a demonstrable slice; nothing built ahead of need except the eight exits, which the schema freeze requires. | Pass |
| XIII Acceptance testable and recorded | Golden logs, replay-compare suite, screenshot comparison, gates. | Pass |
| XIV Built for a projector | Export sizes copied verbatim; one-click controls. | Pass |
| XV Dependencies earn their place | `docs/dependencies.md` opened with every S1 dependency. | Pass |
| XVI Automated quality gates | `scripts/check.py` runs ruff, mypy, pytest, em-dash lint, `.env` leak test. | Pass |
| XVII Credentials in .env only | No credentials needed in S1; the leak test guards recordings and bundles. | Pass |
| XVIII Export wired, never redesigned | Hand-flattened with values copied verbatim; additions (blocker card, Dry intake toggle, Edit and Reject, build stamp on every header) in the export's families. | Pass |
| XIX Human approval for consequential change | The five pre-S1 decisions are approved; schema additions are additive and recorded; no non-goal touched. | Pass |
| Non-goals | None approached. Pause and Stop endpoints exist for the state machine but the UI controls stay disabled. | Pass |

Post-design re-check (after Phase 1): no new violations. The only judgement calls are recorded in research.md D4 (fixture timestamps for stubs), D5 (human actions live against stubs), and D9 (deferred comparison regions).

## Project Structure

### Documentation (this feature)

```text
specs/001-event-spine-stubbed-loop/
  plan.md
  research.md
  data-model.md
  quickstart.md
  contracts/
    events-v1.0.0.md
    http-api.md
  checklists/requirements.md
  tasks.md              (from /speckit-tasks)
```

### Source code (repository root)

```text
pyproject.toml            uv project, exact pins, ruff and mypy config
uv.lock
scripts/
  check.py                quality gate runner
  lint_em_dash.py         em-dash lint (repo tracked files and runs/)
  extract_design_assets.py  fonts and SVG from design/*.html manifests into app/web/static
  capture_export.py       renders export bundles per state to tests/visual/reference/
  regen_golden.py         runs each stub scenario with its human script, writes golden logs
docs/
  schema/events-v1.0.0.md     frozen schema (copy of the contract)
  schema/events-v1.0.0.json   generated from the models
  dependencies.md
app/
  __init__.py
  main.py                 FastAPI app, page routes with build-stamp substitution, API routes
  config.py               settings: paths, retry budget, cost ceiling, stub pace, .env
  buildinfo.py            git hash and date
  schema/
    __init__.py
    events.py             envelope, payload models, discriminated union, enums
    bundles.py            PromptBundle
    export.py             JSON Schema generation
  orchestrator/
    __init__.py
    roster.py             seats, names, colours, default models, random pairing
    state.py              RunState and transition rules
    orchestrator.py       run loop, dispatch, human gate, pause, cost ceiling, termination
    knowledge.py          per-run knowledge file copy and append
  agents/
    __init__.py
    base.py               StubAgent protocol and script step types
    stubs/
      __init__.py         registry by dataset id, prompt bundle registry
      clean_run.py
      planted_inconsistency.py
      missing_sheet.py
      missing_price.py
      not_ready.py
      prospect_own.py
  runs/
    __init__.py
    bus.py                per-stream subscriber queues
    recorder.py           runs/<id>/ writer
    replay.py             replay session
    registry.py           live run registry, dataset discovery, replay source resolution
  web/
    pages/
      demo.html
      login.html
      settings.html
      preflight.html
    static/
      css/app.css
      js/
        events.js         SSE client with resume
        reducer.js        events to view model
        render.js         DOM builders per card kind and page part
        demo.js           page wiring, composer, banner, blocker, approve
        pages.js          shared header behaviour
      fonts/              extracted woff2
      img/person.svg      extracted icon
datasets/<id>/golden-events.jsonl   six files
tests/
  unit/
    test_schema.py
    test_schema_export.py
    test_state_machine.py
    test_roster.py
    test_stubs_emit_only_agent_events.py
  integration/
    test_orchestrator_scenarios.py
    test_golden_compare.py
    test_recording.py
    test_replay.py
    test_api.py
    test_stream.py
  visual/
    masks.py
    test_screenshots.py
    reference/            committed captures
  lint/
    test_em_dash.py
    test_env_leak.py
```

**Structure Decision**: one Python package `app` serving both the API and the static frontend, because the demo runs as one process on the presenter laptop and the spec fixes a static frontend with no build step. Tests split by kind so the visual suite can be skipped where Chromium is absent.

## Phase 0: Research

Done. See [research.md](research.md): verified versions table with date, and decisions D1 to D13.

## Phase 1: Design

Done.
- [data-model.md](data-model.md): entities, state machine transitions, view model derivation.
- [contracts/events-v1.0.0.md](contracts/events-v1.0.0.md): the frozen schema.
- [contracts/http-api.md](contracts/http-api.md): pages, API, stream, recording layout.
- [quickstart.md](quickstart.md): setup, run, validate, gates.
- `docs/dependencies.md`: rationale record.

## Design notes for implementation

### Flattening the export
- Decode the page string from each bundle's `__bundler/template` script (already done once in research; the extraction script does it repeatably). Fonts: 20 woff2 assets across Inter 400 and 500, JetBrains Mono 400 and 500, Space Grotesk 400 and 500, keyed by unicode range; write them with readable names and one `@font-face` block per face in `app.css`.
- Class naming: `.hdr`, `.hdr-nav`, `.pf-dot[data-status]`, `.loop`, `.node[data-state]`, `.arrows path[data-arrow][data-fired]`, `.banner`, `.composer`, `.btn-run`, `.btn-ghost`, `.replay`, `.feed`, `.card[data-kind]`, `.card-hd`, `.agent`, `.avatar`, `.summary`, `.phase`, `.time`, `.event`, `.why`, `.prompt-btn`, `.prompt-panel`, `.replies`, `.finding`, `.sev[data-severity]`, `.term`, `.artifact`, `.compare`, `.meters`, `.meter[data-open]`, `.meter-detail`, `.raw`, `.chat`. Values copied verbatim; hover and active rules from `style-hover` and `style-active`.
- Bindings to port: node styles (idle, active, complete, paused), arrow fired, run and pause and stop opacities (0.45 when disabled), verdict pill, severity colours, plan glyphs, chevrons, elapsed and meter formatting (`fmtTok`, `fmtUsd`), raw lines.
- Additions in family: blocker card (`data-kind="blocker"`, white card with a 4px `#b30000` left border, Answer as the dark pill button, Escalate as the outlined pill); Dry intake toggle (a two-segment switch like the mode switch, `Dry intake · off`, disabled at 0.45 opacity); Edit and Reject as outlined pills next to Approve, disabled; build stamp span in every header nav in the Settings style; the pre-flight indicator in every header (Settings and Pre-flight exports lack it: added in the Demo style, pending state grey `#d9d9dd` with `○`).
- Removed: the state switcher, sample data, the `#artifact-v1` links, the design-time chat sample text (chat panel markup kept, hidden, disabled).

### Stub script format
Each stub module declares `STEPS: list[Step]` where a `Step` is one of `Emit(seat, type, offset_ms, payload, bundle=..., meter=...)` or `Wait(kind)` markers that let the Orchestrator act (for example `Wait.human_answers`, `Wait.dispatch("t1")`). The Orchestrator interprets the plan: it dispatches tasks, gathers independent ones, waits for dependents, and calls the stub for each task, which yields its emissions with offsets. Concurrency: independent sub-tasks run as asyncio tasks; Pricing awaits Estimator's completion event.

### Screenshot references
Capture script copies each export bundle into the scratch folder, rewrites the `data-props` default for the state (`idle`, `running`, `paused`, `terminated`, plus `chatOpen: true` for the chat capture and `preflight` variations), renders in Chromium at 1920 by 1080 with `file://`, waits for fonts and the bundle loader, and saves `tests/visual/reference/<page>-<state>.png`. The export's own `screenshots/` remain untouched and are cross-checked once against the recapture of the same states.

## Complexity Tracking

No constitution violations to justify.

## Risks

- The export bundle may render differently from `design/screenshots/` (font loading, animation frames). Mitigation: capture with animations disabled and fonts awaited; compare recaptures with the shipped screenshots once and record any drift in `design/README.md`.
- Pixel tolerance may hide small deviations. Mitigation: threshold 0.5 percent plus a manual side-by-side review at the end of the slice.
- The stub pacing default may feel slow or fast on the projector. Mitigation: `STUB_PACE` in config.
