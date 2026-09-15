# Research: Event spine and stubbed loop (S1)

Date of verification: 2026-09-14. Every version below was read from the package index or the project's official release page on that date. Nothing is pinned from memory.

## Verified versions and names (2026-09-14)

| Item | Verified value | Source | Used in S1 |
|---|---|---|---|
| Python | 3.13.14 installed on the reference machine | `python --version` | Yes, target 3.13 |
| Strands Agents (product name as written on the project README) | `strands-agents` 1.55.1, released 2026-09-09, requires Python >= 3.10, extras include `anthropic`, `ollama`, `litellm`, `gemini` | pypi.org JSON, github.com/strands-agents/sdk-python | Recorded only; installed in S2 |
| Strands Agents tools | `strands-agents-tools` 0.8.8, released 2026-09-04 | pypi.org JSON | Recorded only |
| Amazon Bedrock AgentCore Python SDK | `bedrock-agentcore` 1.23.0, released 2026-09-11 | pypi.org JSON | Recorded only; AgentCore is phase 2 per the non-goals |
| Amazon Bedrock AgentCore services (exact names on the AWS developer guide overview) | Harness, Runtime, Memory, Gateway, Identity, Code Interpreter, Browser, Observability, Payments, Evaluations, Optimization, Policy, Registry | docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html | Recorded for the Introduction copy in S6 |
| Typst | 0.15.1, released 2026-07-17, installed locally (`typst 0.15.1`) | github.com/typst/typst releases, `typst --version` | Recorded; used from S4. Note: the Pre-flight export shows "typst 0.13" in sample text; that is fixture text and the live check reports the real version |
| FastAPI | 0.141.1, released 2026-07-29, requires Python >= 3.10 | pypi.org JSON | Yes |
| Uvicorn | 0.53.0, released 2026-09-14 | pypi.org JSON | Yes |
| Pydantic | 2.13.5, released 2026-08-28 | pypi.org JSON | Yes |
| sse-starlette | 3.4.11, released 2026-09-05 | pypi.org JSON | No, see decision below |
| pytest | 9.1.1, released 2026-06-19 | pypi.org JSON | Yes |
| pytest-asyncio | 1.4.0, released 2026-05-26 | pypi.org JSON | Yes |
| httpx | 0.28.1, released 2024-12-06 | pypi.org JSON | Yes, test client transport |
| mypy | 2.3.1, released 2026-08-15 | pypi.org JSON | Yes |
| ruff | 0.16.7, released 2026-09-10 | pypi.org JSON | Yes |
| Playwright for Python | 1.62.0, released 2026-07-31 | pypi.org JSON | Yes, screenshot capture and comparison |
| Pillow | 12.3.0, released 2026-07-01 | pypi.org JSON | Yes, pixel diff |
| PyYAML | 6.0.3, released 2025-09-25 | pypi.org JSON | Yes, `brand.yaml` |
| python-dotenv | 1.2.3, released 2026-08-16 | pypi.org JSON | Yes, `.env` loading |
| uv | 0.9.21 installed | `uv --version` | Yes, environment and lock file |
| git | 2.52.0 installed | `git --version` | Yes, build stamp |

Pins are exact (`==`) in `pyproject.toml` with a `uv.lock`. Upgrades are deliberate and recorded in the dependency record.

## Decisions

### D1. Server-sent events are hand-rolled on a Starlette streaming response
- Decision: implement the event stream with `StreamingResponse`, an asyncio queue per subscriber, a 15 second keepalive comment, `id:` set to `seq`, and `Last-Event-ID` (or `?since=`) resume from the run's event list.
- Rationale: the whole feature is under sixty lines, the resume rule needs the run's own event list anyway, and constitution XV says a dependency must earn its place. `sse-starlette` would add a package for behaviour that is trivial here.
- Alternatives: `sse-starlette` 3.4.11 (rejected for the reason above); WebSockets (rejected: the stream is one-way and the spec names SSE).

### D2. Typed models are Pydantic v2 with a discriminated union on `type`
- Decision: one `Event` envelope model with `payload` validated by a per-type payload model chosen from `type`; the exit, stage, direction, verdict, severity, and decision values are `Literal` unions; `seq` and ordering rules are validated at the run level, not per event.
- Rationale: Pydantic gives JSON schema export for the versioned document, strict validation before emit, and mypy-checkable types. The discriminated union keeps the schema document and the code in one place.
- Alternatives: dataclasses plus jsonschema (two sources of truth); attrs (no JSON schema).

### D3. The schema document is generated from the models and committed
- Decision: `docs/schema/events-v1.0.0.md` (prose, frozen) and `docs/schema/events-v1.0.0.json` (JSON Schema exported from the models) are both committed. A test regenerates the JSON and fails if it differs from the committed file.
- Rationale: the prose document is the controlled source people read; the JSON export proves the code matches it.

### D4. Stub timing uses fixture offsets with a pacing factor
- Decision: each stub event carries a fixture offset in milliseconds from run start. The event `ts` is run start plus the offset. The stub emits the event after `offset / STUB_PACE` of wall time (default `STUB_PACE=4`). Replay uses the `ts` gaps scaled by the presenter's speed (1x or 4x).
- Rationale: the design export's scenario 2 timestamps (00:41, 01:06, 04:12) appear on cards and in the elapsed meter. Carrying them in `ts` makes the screenshot comparison exact and makes Replay of a stub run look like the run the export depicts. A pacing factor keeps a live stub run under the three-minute budget (scenario 2 plays in about 63 seconds at pace 4). With real agents from S2, `ts` is wall time and no pacing applies.
- Consequence: the spec assumption on stub timing is updated to say this. The golden logs carry the fixture offsets.
- Alternatives: wall-clock `ts` with masked timestamp regions in the comparison (rejected: masks hide the very thing the export shows, and the elapsed meter would never match); wall-clock `ts` with 1x stubs taking 4:12 (rejected: too slow for a live demo).

### D5. Human touchpoints in stubbed runs are real requests
- Decision: the banner answer form, the blocker card's Answer and Escalate, and Approve at Handoff post to the run's API. The Orchestrator waits on an asyncio event for the human. The test suite and the golden log regenerator drive the same Orchestrator in-process with a scripted human per scenario (`human_script` in each stub module).
- Rationale: constitution III and IV. The stub is the agent; the human is still the human. Replay re-emits the recorded `clarification.answered` and `human.approved` events without waiting.

### D6. Replay is a stream session that re-emits a recording verbatim
- Decision: `POST /api/replays` opens a session for a dataset at a speed. The session resolves its source (latest recording under `runs/` for that dataset, else the dataset's golden log), and serves the events on the same stream endpoint shape as a live run, with original `run_id`, `event_id`, `seq`, and `ts`, sleeping `gap / speed` between events. A replay writes nothing under `runs/`.
- Rationale: spec section 6 recording paragraph and pre-S1 decision 4.

### D7. Prompt bundles for stubs are deterministic and resolvable without a recording
- Decision: stub `prompt_ref` values are deterministic per scenario and call (`pb-<dataset>-<nn>`). Bundles are stored under `runs/<run_id>/prompts/` for a live run and also resolvable from the stub fixture registry, so the prompt toggle works when a golden log is replayed with no recording present.
- Rationale: spec 2.5 says the toggle is always available.

### D8. The Demo page is hand-flattened with named classes copied verbatim from the export
- Decision: a one-time extraction script pulls the fonts and the human-figure SVG out of the bundle manifests into `app/web/static/`. The page markup and one stylesheet are written by hand from the decoded `.dc.html` template, one class per `data-part` or `data-kind` element with the export's inline style values copied verbatim, plus state modifiers for the values the template binds (`node-idle`, `node-active`, `node-complete`, `node-paused`, arrow fired, severity). Render functions in vanilla JS build the same DOM from events.
- Rationale: the template has about seventy distinct styled elements, the bindings are simple, and a hand-written stylesheet is readable and reviewable. A generic inline-to-class converter would produce opaque names and still leave the template logic to hand-port.
- Alternatives: automatic conversion (rejected as above); shipping the export runtime (forbidden by spec 2.10).

### D9. Screenshot comparison with Playwright and Pillow, with declared deferred regions
- Decision: Playwright drives Chromium at 1920 by 1080, device scale 1, fonts loaded, animations disabled. Reference captures come from copies of the export bundles in a scratch folder with the `data-props` defaults edited to each state (the copies never touch `design/`). Pillow computes the fraction of pixels whose channel difference exceeds 24 out of 255; a state passes below 0.5 percent after masking declared regions. Deferred regions in S1: the artifact panel body (placeholder until S4), the Compare strip body and comparison line (S5), the meter detail row (opened by click, compared separately). Each mask is listed in `tests/visual/masks.py` with the slice that removes it.
- Rationale: acceptance criterion 3 and roadmap S1 evidence, while the artifact panel is a placeholder by roadmap decision.

### D10. Loop node states derive from `stage.changed` and the pause events only
- Decision: current stage node is active; any stage entered earlier in the run and not current is complete; while the run is paused the current stage node takes the paused treatment; after `run.terminated` every entered stage is complete. Retry badge text comes from `retry.incremented` (initial `retry 0 of 2` from `run.started` budget in the roster payload is not available, so the initial badge reads from a `retries` field the Orchestrator adds to `run.started.payload`).
- Correction to the last point: spec section 6 fixes `run.started` payload fields. The initial badge reads `retry 0 of N` where N comes from `GET /api/runs/{id}` metadata, fetched once on connect, not from an event. This is configuration, not state. Documented in the data model.

### D11. Roster names are chosen server-side per run, pinnable for tests
- Decision: the Orchestrator picks one of the two names per seat with `random.Random(seed)`; `POST /api/runs` accepts an optional `names` map for tests and screenshot pinning. The chosen roster appears in `run.started.payload.roster` and every actor object.

### D12. Quality gate command
- Decision: `uv run poe check` is not used (no task runner dependency). A `Makefile`-free approach: `scripts/check.py` runs ruff, mypy, pytest, the em-dash lint, and the `.env` leak test in order and exits non-zero on the first failure. Documented in quickstart.

### D13. Console encoding on Windows
- Decision: the app and scripts set `PYTHONUTF8=1` via `pyproject.toml` `[tool.uv]` env is not possible; instead every script that prints non-ASCII reconfigures `sys.stdout` to UTF-8, and the quickstart tells the presenter to run with `PYTHONUTF8=1`.
- Rationale: the reference machine's console defaults to cp1252 and the export text uses arrows and check marks.

## Open questions resolved

- Dry intake exit, control, git, replay source, Python: settled by the owner on 2026-09-14 (`docs/roadmap.md`).
- Build stamp without git: shows `build no-git` in the same style.
- Knowledge file for stubs: per-run copy of `datasets/<id>/knowledge.seed.md` when present, else empty, written under `runs/<run_id>/knowledge.md`.
