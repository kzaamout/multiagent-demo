# CLAUDE.md

Sterling AI multi-agent orchestration demo. Read this first, then the pointers below.

## What this is
A sales demo that shows several AI agents, under an orchestrator, taking a business request from intake to a reviewed, human-approved deliverable. Two workflows on one engine: electrical RFP response (build first) and appraisal intake-to-report (second). It is a demo, not a product.

## Working rules
1. Ask up to 10 clarifying questions before any plan or implementation. Do not proceed from a vague ask.
2. Schema first. `docs/spec-input.md` section 6 defines the event schema. Freeze it before writing any agent. Everything (UI, replay, meters, provenance, future Slack renderer) hangs off it.
3. The UI renders events. It never infers state, never runs timers to guess progress, never hardcodes stage transitions.
4. The Orchestrator is the only component that changes stage, talks to the human, writes the knowledge file, or ends a run.
5. The demo-not-product test: if a requirement only matters when a stranger uses this unattended, it is product. Check `.specify/memory/constitution.md` non-goals before building anything not in the spec. Flag creep, do not build it.
6. Never use em dashes in any file, comment, UI copy, prompt, or generated content. Use commas, colons, or a full stop.
7. Build in the milestone order in `docs/spec-input.md` section 9. Do not start with the UI.
8. Every scenario dataset ships with a golden event log. Tests replay a live run and compare stage sequence and termination exit.
9. Deliver as text or diffs in the session unless asked to produce a file or artifact.

## Pointers
- Principles and non-goals: `.specify/memory/constitution.md`
- Requirements, loop, agents, event schema, milestones: `docs/spec-input.md` (input to `/speckit.specify`)
- UI design brief (also given to Claude Design): `docs/design-brief.md`
- Claude Design export: what the files are, known deviations, handling rules: `design/README.md`
- Runtime content served by the Introduction tab: `content/intro/*.md`
- Agent runtime config for the electrical RFP workflow: `config/electrical-rfp/`
- Scenario datasets and curation checklist: `datasets/`
- Sales playbook (humans only, do not load unless asked): `docs/sales-playbook.md`
- Approved slice roadmap and pre-S1 decisions: `docs/roadmap.md`
- Frozen event schema: `docs/schema/events-v1.0.0.md` (typed models in `app/schema/`)
- Dependency rationale record: `docs/dependencies.md`
- Deviations found while building (design/ is never edited): `docs/design-deviations.md`
- Quality gates: `uv run python scripts/check.py`; screenshots and browser tests: `uv run pytest -m visual`

## Stack (verify current versions before pinning)
Python 3.13, FastAPI, server-sent events, static HTML with one CSS file and vanilla JS flattened from the Claude Design export in `design/` (the export's runtime and React are not shipped; see `docs/spec-input.md` section 2.10), Strands Agents SDK for model calls (Bedrock, Anthropic, Ollama native; Gemini and Grok via its LiteLLM provider), custom orchestrator (no CrewAI, no LangGraph for orchestration), Typst for PDF and page PNG compile, Ollama for local models, Cloudflare Tunnel for demo-day hosting. Credentials in `.env` only.
