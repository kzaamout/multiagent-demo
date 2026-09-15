# Implementation Plan: Live team on the clean run (S2)

**Branch**: `002-live-team-clean-run` | **Date**: 2026-09-14 | **Spec**: [spec.md](spec.md)

## Summary

Replace canned agents with real ones on Clean run while keeping S1's engine, schema, page, recording, and replay unchanged. Each seat call is one Strands Agents invocation built from the seat's instruction file, its scoped context slice, its tools, and its configured model. Replies are validated and converted into schema v1.0.0 events; progress lines, tool calls, and per-call usage become `task.progress`, `tool.called`, and `meter.update`. Part A (now) proves the whole path with a scripted model and synthetic inputs. Part B (after the owner's inputs) runs it on real models and records the evidence.

## Verified versions and names (2026-09-14)

| Item | Verified | Source |
|---|---|---|
| Strands Agents | 1.55.1, with `litellm` and `ollama` extras | PyPI; wheel source, tag `python/v1.55.1` in `strands-agents/harness-sdk` |
| LiteLLM | 1.96.0 (Strands caps it; latest is 1.101.0) | PyPI, Strands METADATA |
| boto3 | 1.43.94 | PyPI |
| pypdfium2 | 5.13.0 | PyPI |
| Amazon Bedrock AgentCore services | Harness, Runtime, Memory, Gateway, Identity, Code Interpreter, Browser, Observability, Payments, Evaluations, Optimization, Policy, Registry (unchanged since S1's check; not used in S2) | AWS developer guide |
| Typst | 0.15.1 (unchanged; used from S4) | GitHub releases |
| Claude Sonnet 5 on Bedrock | `us.anthropic.claude-sonnet-5`; rejects non-default temperature | AWS model card, Anthropic docs |
| Gemini for the Reviewer | `gemini-2.5-pro` stable; `gemini-3.8-flash` stable; `gemini-3.1-pro-preview` | ai.google.dev |
| Local model | `llama3.1:8b` still published; Ollama v0.34.0 | ollama.com, GitHub releases |

Full table with prices: [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: S1 stack plus Strands Agents 1.55.1 (Bedrock, LiteLLM, Ollama providers), pypdfium2 5.13.0. Rationale in `docs/dependencies.md`.

**Storage**: files. Recordings under `runs/`; client knowledge files under `knowledge/` (git-ignored); drafts under `runs/<run_id>/drafts/`.

**Testing**: pytest; the live path is exercised end to end with a scripted Strands model; the S1 suites stay as regression.

**Constraints**: constitution II to V and XVII. The Reviewer's bundle excludes the team's working. Credentials never leave `.env` and the boto3 chain.

## Constitution Check

| Principle | S2 compliance | Status |
|---|---|---|
| I Demo, not product | One scenario live; no provider management UI; scripted model is test-only | Pass |
| II Events only | Agent work reaches the page only as validated events | Pass |
| III One owner of state | Agents return replies; the Orchestrator emits every event and owns stages, questions, knowledge writes | Pass |
| IV One door | Agents never address the human; clarifications go through the Orchestrator's banner | Pass |
| V Roles are real | Instructions per seat file, tools per roster, context per scope with tests; truthful model labels | Pass |
| VI Failure | Invalid replies and provider errors terminate as stopped with a named reason; review routing is S3 | Pass |
| VII Provenance | Writer sources labelled with event ids; tags parsed into `draft.committed` | Pass |
| XV Dependencies | Strands, LiteLLM, Ollama client, boto3, pypdfium2 recorded with rationale | Pass |
| XVII Credentials | Registry reports presence only; leak test extended to live-mode artefacts | Pass |
| XIX Approval | Model defaults below need the owner's confirmation before Part B | Open |
| Non-goals | Memory beyond one knowledge file: not built. Providers from the UI: not built. | Pass |

## Owner decisions on the model questions (2026-09-15)

1. **Claude seats.** Sonnet 5 at its default temperature for every Claude seat, the Orchestrator included. Spec input 4.3 no longer asks for a low temperature. The Orchestrator's proposals stay bounded by the run engine's validation.
2. **Reviewer.** `gemini-2.5-pro`, the export's label.
3. **Local Pricing model.** `llama3.1:8b`, the export's label, at temperature 0.1.
4. **Bedrock routing.** The `us.` geo profile from ca-central-1, so data stays in US and Canada regions.

`config/models.yaml` already held these defaults and now records them as confirmed.

## Project Structure

```text
config/models.yaml                 providers, models, prices, seat defaults
app/live/
  providers.py                     registry: availability and reasons, Strands model factory
  documents.py                     pypdfium2 text, legibility, page images
  strands_tools.py                 per-run @tool closures over app/tools/*
  seat_call.py                     one seat invocation: agent build, hooks, progress, usage, retry
  source.py                        LiveAgentSource: context assembly, replies to Emits
  materials.py                     run materials from dataset and run events
app/agents/source.py               AgentSource protocol; StubAgentSource wraps S1 scenarios
app/orchestrator/orchestrator.py   consumes AgentSource; live clock behaviour
app/main.py                        live mode per dataset, provider refusal, registry endpoint
tests/support/scripted_model.py    scripted Strands Model for tests
tests/fixtures/s2/                 synthetic request, drawing page, price fixture
tests/integration/s2/              live path end to end, ask once, scoping in real bundles
```

## Complexity Tracking

None.
