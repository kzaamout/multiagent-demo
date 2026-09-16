<!--
Sync Impact Report
Version change: 1.1.1 -> 1.2.0 (MINOR, 2026-09-15): principle III applies a review limit instead of tracking a retry budget; principle VI replaces the fixed retry budget with a progress-based review limit under a hard ceiling and names the stop reason on the termination card; principle VIII requires a full recording that replays from its own folder. Per the owner's change request of 2026-09-15 recorded in docs/roadmap.md (slice S3b). Earlier: 1.1.0 -> 1.1.1 (PATCH, 2026-09-14): principle VI lists dry intake among the control exits, per the owner's pre-S1 decision recorded in docs/roadmap.md. Earlier: unversioned base (treated as 1.0.0, amended 2026-09-14 for II, VI, and one non-goal) -> 1.1.0
Modified principles: none renamed; I through IX carried over verbatim and moved from level-2 to level-3 headings under Core Principles
Added sections:
  - Engineering Principles (X through XIX)
  - Governance (amendment procedure, versioning policy, compliance review)
Removed sections: none. The Non-goals list is preserved verbatim under its own heading.
Templates: plan, spec, tasks, and checklist templates read the constitution at runtime; no template files changed.
Follow-up TODOs: none. Ratification date set to 2026-09-14, the day the constitution entered this repository.
-->

# Sterling AI Multi-Agent Demo Constitution

These principles do not change between features. Spec, plan, and tasks must comply.

## Core Principles

### I. Demo, not product
This system exists to be demonstrated live by its owner to a prospect and to be understood by sales staff. Any requirement that only matters when an unattended stranger uses it is out of scope. The test is applied to every feature proposal. Creep is flagged and parked, never quietly built.

### II. Schema first, events only
The typed event schema is frozen before any agent is written. Every state change, agent action, human interaction with the run, model change, and metering update is an event. The UI, the replay engine, the meters, the provenance links, and any future renderer (Slack) consume the same stream. Nothing renders that was not emitted. Chat with an agent does not touch the run and is out of band: not an event, not recorded, not replayed.

### III. One owner of state
The Orchestrator alone changes stage, dispatches work, batches and asks human questions, appends to the knowledge file, applies the review limit, and terminates a run. Every Orchestrator event carries a one-sentence reason. No other agent may do any of these things.

### IV. One door to the human
Agents raise clarifications and blockers as events. Only the Orchestrator presents them to the human, in one batch, with the run paused. Nothing is sent externally by the system; a human approves at Handoff.

### V. Roles are real
Agents differ on three axes and only these: instructions and success criteria, tool access, and visibility scope. Name and role are fixed identity. The underlying model is a runtime attribute, swappable per seat, and must be displayed truthfully wherever the agent appears.

### VI. Design for the failure
Termination is a first-class concern with exactly four narrative exits: reviewer pass, the progress-based review limit with a hard ceiling stopped the loop, blocker escalated, intake not ready. Rework continues only while a review cycle reduces the blocker and major findings and repeats none of them; a fixed maximum number of cycles and the cost ceiling bound it, and the termination card names which stop fired. Control exits (cost ceiling, stopped, single-model complete, dry intake) exist for safety and control and are not part of the demo narrative. `run.terminated` is always the last event of a run. Scenario datasets deliberately contain planted defects so failure paths run on cue. The Reviewer is on a different model family from the Writer and cannot see the team working.

### VII. Provenance
Every factual figure in a deliverable carries a tag linking it to the agent output that produced it. The Writer invents nothing.

### VIII. Reliability on demo day
Every run is recorded in full: its events, every prompt and response, every file it produced, and a manifest, so it replays from its own folder alone. Replay mode reproduces a recorded run faithfully at 1x or 4x. A pre-flight page verifies every dependency. A hard per-run cost ceiling halts runaway loops.

### IX. Writing rules
No em dashes anywhere: code, comments, prompts, UI copy, generated content, docs. Plain, direct English. Agents are referred to by name and role in user-facing copy.

## Engineering Principles

### X. Controlled sources of truth
Behaviour is defined by `docs/spec-input.md` and the specifications derived from it. Appearance is defined by the Claude Design export in `design/`. Both are controlled documents: a change is made in the document first, with a version or changelog entry, and only then in code. Conversation, memory, and inference never override them. Anything found in neither is not a requirement until it is written down.

### XI. Reconcile before building
When the spec, the design export, the design brief, and the content files disagree, the conflict MUST be resolved before implementation starts. Behaviour follows the spec and appearance follows the export. Every case that cannot satisfy both is recorded with its decision in `design/README.md` or the spec changelog. No implementer picks a side silently.

### XII. Vertical slices on one frozen foundation
The event schema is the single horizontal foundation. It is versioned and frozen before any agent exists, and it changes only through the amendment procedure below. Everything else is delivered as vertical slices. Each slice is independently demonstrable from the Demo page and ends in a state the presenter could show a prospect. No slice depends on an unbuilt layer, and no horizontal layer is built ahead of the slice that needs it.

### XIII. Acceptance is testable and recorded
Every slice states its acceptance criteria before work starts, and each criterion is checkable by a test, a comparison, or a recorded artifact. Wherever a slice exercises a scenario dataset, the completion evidence is a recorded golden event log that the replay-and-compare suite passes against. Wherever a slice wires a screen, the evidence includes the screenshot comparison against the design export. A slice without its evidence is not complete.

### XIV. Built for a projector
The primary audience reads the screen from three metres away. Legibility at distance governs typography, contrast, and density, and body text in the feed never falls below the size the design sets. Interaction depth is minimal: anything the presenter needs during a run is at most one click away, and nothing is hidden behind a dialog, a nested menu, or a keyboard shortcut.

### XV. Dependencies earn their place
No architectural framework or major dependency enters the codebase without a documented rationale in the plan stating the problem it solves and what it would cost to do without it. Orchestration is written by hand. No orchestration framework of any kind is used, per the spec, because the Orchestrator is the thing being demonstrated.

### XVI. Automated quality gates
Automated tests, static type checking, and linting run on every change and gate completion. The lint includes a check that fails on any em dash anywhere in the repository or in generated output, including prompts, rendered copy, and deliverables. Type checking covers the schema models and the Orchestrator at minimum. A slice is not complete while any gate is red.

### XVII. Credentials live in .env only
Provider keys, passwords, and tokens exist only in `.env`, which is never committed. They never appear in code, configuration files, fixtures, prompts, logs, event payloads, or the UI. The UI and pre-flight report at most whether a credential is present, never its value.

### XVIII. The design export is wired, never redesigned
The export in `design/` is the appearance. Implementation flattens it and wires it to the event stream. It does not restyle, rearrange, or add elements beyond what the spec requires, and any addition matches the export's own component family. Design-time controls such as the state switcher, the sample feed text, and inline demo data are fixtures: they may seed stubs and tests, and they never ship as application logic.

### XIX. Human approval for consequential change
Consequential architecture changes, any deviation from the non-goals, and any change to a frozen artifact (the event schema, an approved slice boundary, a controlled source of truth) require the owner's explicit approval before implementation. The proposal states what changes, why, and what it costs. Silence is not approval. A concern that was raised and then reaffirmed by the owner is a decision, and work proceeds on it.

## Non-goals (parked, do not build)
- Adding providers or credentials from the UI (secure storage, validation, test connection). Credentials live in .env.
- Agent memory beyond the per-client knowledge file: no vector store, embeddings, retrieval layer, or conflict resolution.
- Changing agent instructions or prompts mid-run from the UI.
- Per-user accounts, signup, password reset, roles, per-user run history. Ceiling is a shared login from .env.
- Live integrations with Building Connected, Construction Connect, supplier websites, or a real CRM. Fixtures only.
- Provenance beyond hover-to-highlight: no citation graph, search, or export.
- Automated email sending of the leave-behind. Generation is automated; sending is manual.
- Video generation, text-to-speech, animated talking avatars, a narrator agent.
- Multi-user simultaneous viewing, a dashboard of past runs, a model leaderboard.
- Deploying to AgentCore Runtime for the demo itself. AgentCore is the phase 2 production story only.
- Live editing of the prompt shown by the prompt toggle. The toggle is read-only.
- A Handoff reject that re-enters the loop. Reject is recorded and the run terminates.

## Governance

This constitution supersedes every other practice, template, and convention in the repository. Where a plan, task, or review conflicts with it, the constitution wins and the conflicting item is corrected.

Amendments: a proposed amendment states the change, the rationale, and the affected principles, and the owner approves it before it is written. Every amendment updates the version line below and carries a Sync Impact Report while under review. Principles are never removed or softened silently; removal or redefinition is a MAJOR change.

Versioning: MAJOR for a removal or redefinition of a principle or non-goal, MINOR for a new principle or section or materially expanded guidance, PATCH for clarifications and wording that do not change meaning.

Compliance review: every specification, plan, and task list includes a constitution check against the principles above and the non-goals. Reviews verify the check. Anything that sits close to a non-goal states how it stays on the right side. `CLAUDE.md` carries the runtime working rules and points here.

**Version**: 1.2.0 | **Ratified**: 2026-09-14 | **Last Amended**: 2026-09-15
