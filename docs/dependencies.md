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
| Strands Agents (`strands-agents[litellm,ollama]`) | 1.55.1 (2026-09-14) | Model calls for every seat across Bedrock, Ollama, and LiteLLM providers, with tool calling, per-call usage, and hooks for tool calls; named in the stack (CLAUDE.md). Orchestration stays hand-written: Strands runs one seat's call, never the loop | A provider client per vendor plus hand-written tool-calling loops and usage accounting for each | S2 |
| LiteLLM (via the Strands extra) | 1.96.0 (2026-09-14; latest is 1.101.0, but Strands 1.55.1 caps it at 1.96.0) | Gemini for the Reviewer and Grok, per the stack | A separate Google client and a second provider code path | S2 |
| Ollama Python client (via the Strands extra) | 0.6.2 (2026-09-14) | The local model for Pricing | Hand-written HTTP calls to the Ollama API | S2 |
| boto3 (via Strands) | 1.43.94 (2026-09-14) | Bedrock credentials and calls | None practical; it is Bedrock's official SDK | S2 |
| Typst (authoring only) | 0.15.1 (2026-09-15) | Compiles the Clean run request and drawing PDFs from sources kept in `datasets/clean-run/source/`; not needed to run the demo until S4 | Hand-drawn PDFs with no reproducible source | S2 |
| Ollama (setup) | 0.34.0 (2026-09-15), winget package `Ollama.Ollama` on Windows, the official install script on Linux, the download page on macOS | Runs the local Pricing model; `scripts/setup.py` installs it with consent and pulls the seat models over the Ollama API | Manual install steps per presenter | S2 |
| uv standalone installer (setup) | current from astral.sh (2026-09-15) | `scripts/setup.ps1` and `scripts/setup.sh` install uv when it is missing, and uv installs Python 3.13 and the locked dependencies | Manual Python and dependency setup per presenter | S2 |
| pypdfium2 | 5.13.0 (2026-09-14) | Text per page and page rendering to PNG for the Intake parsing tool and the Estimator's drawing reading; BSD-3-Clause and Apache-2.0, Windows wheels | PyMuPDF does both but is AGPL; pypdf extracts text but cannot render pages | S2 |

Not adopted, with reason:

| Considered | Reason not used |
|---|---|
| sse-starlette 3.4.11 | The stream is sixty lines on a streaming response and resume needs the run's own event list anyway |
| Any orchestration framework | Forbidden by constitution XV; the Orchestrator is the thing being demonstrated |
| Strands multi-agent graphs and swarms | Orchestration framework features; the hand-written Orchestrator owns the loop (constitution XV) |
| PyMuPDF 1.28.2 | AGPL licence; pypdfium2 covers the same need under permissive licences |
| Strands native Gemini provider (`google-genai`) | The stack names LiteLLM for Gemini; one provider path for Gemini and Grok |
| Frontend framework or bundler | Spec 2.10: static HTML, one stylesheet, vanilla scripts; the export runtime and React are not shipped |

Later slices append here: Typst 0.15.1 and the career-hub compile script (S4), Cloudflare Tunnel (S7).
