# Dependency rationale record

Required by constitution XV. One entry per major dependency, stating the problem it solves and what it would cost to do without it. Versions verified on the date shown; pins live in `pyproject.toml`.

| Dependency | Version (verified) | Problem it solves | Cost of doing without | Slice |
|---|---|---|---|---|
| FastAPI | 0.141.1 (2026-09-14) | HTTP routing, request validation, static files, streaming responses for the event stream | Hand-written ASGI routing and validation, roughly a week of work and a bug surface the demo does not need | S1 |
| Uvicorn | 0.53.0 (2026-09-14) | ASGI server for FastAPI | No other supported way to serve the app | S1 |
| Pydantic | 2.13.5 (2026-09-14) | Typed event models with validation and JSON Schema export; the frozen schema document is generated from them | Two hand-kept sources of truth (prose and validator) that drift | S1 |
| PyYAML | 6.0.3 (2026-09-14) | Reads `brand.yaml` per dataset | A hand parser for a three-key file, tolerable but pointless | S1 |
| python-dotenv | 1.2.3 (2026-09-14) | Loads `.env` for configuration without credentials in code | Manual parsing of `.env` | S1 |
| pytest, pytest-asyncio | 9.1.1, 1.4.0 (2026-09-14) | Test runner for the replay-and-compare suite and async Orchestrator tests | unittest with hand-rolled async support | S1 |
| httpx | 0.28.1 (2026-09-14) | Test client transport for FastAPI and streaming tests | Cannot exercise the API in tests | S1 |
| mypy | 2.3.1 (2026-09-14) | Static type checking over the schema and Orchestrator, required by constitution XVI | No type gate | S1 |
| ruff | 0.16.7 (2026-09-14) | Lint and format gate | No lint gate | S1 |
| Playwright | 1.62.0 (2026-09-14) | Renders the export bundles for reference captures and the flattened pages for comparison at 1920 by 1080 | No screenshot acceptance, which constitution XIII requires | S1 |
| Pillow | 12.3.0 (2026-09-14) | Pixel comparison of captures with masks | Hand-written PNG decoding | S1 |

Not adopted, with reason:

| Considered | Reason not used |
|---|---|
| sse-starlette 3.4.11 | The stream is sixty lines on a streaming response and resume needs the run's own event list anyway |
| Any orchestration framework | Forbidden by constitution XV; the Orchestrator is the thing being demonstrated |
| Frontend framework or bundler | Spec 2.10: static HTML, one stylesheet, vanilla scripts; the export runtime and React are not shipped |

Later slices append here: Strands Agents 1.55.1 and its LiteLLM provider (S2), Typst 0.15.1 and the career-hub compile script (S4), Cloudflare Tunnel (S7).
