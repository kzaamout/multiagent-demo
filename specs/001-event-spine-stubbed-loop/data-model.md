# Data model: Event spine and stubbed loop (S1)

The event schema is the frozen foundation. Its normative text is `contracts/events-v1.0.0.md`, committed to `docs/schema/` when the slice lands. This file describes the runtime entities around it.

## Entities

### Event (frozen, version 1.0.0)
See `contracts/events-v1.0.0.md`. Envelope: `event_id`, `run_id`, `seq`, `ts`, `type`, `stage`, `actor`, `reason`, `prompt_ref`, `payload`. Validation: envelope and payload models, `reason` required when the actor is the Orchestrator seat, `prompt_ref` required on agent messages (types listed in the contract), `stage` null on `run.started`, `run.terminated`, and Single-model runs.

### Run
- `run_id` (uuid), `workflow` (`electrical_rfp`), `dataset_id`, `mode` (`team` | `single`), `started_at`, `roster` (list of AgentCard), `retry_budget` (int, default 2), `cost_ceiling` (float, from config), `status` (`running` | `paused` | `terminated`), `exit` (nullable).
- Relationships: owns an ordered list of Events; owns PromptBundles by `prompt_ref`; owns one knowledge file copy.
- Invariants: `seq` strictly increasing from 1 with no gaps; first event `run.started`; last event `run.terminated`; no event after termination; at most one `run.paused` outstanding.

### RunState (Orchestrator state machine)
- `stage` (nullable Stage), `retries` (count), `work_to_intake_used` (bool), `paused` (bool), `pending_human` (nullable: `clarifications` with question ids, `blocker` with blocker id, or `handoff`), `draft_version` (int), `est_cost` (accumulated), `tokens` per agent, `unresolved_findings` (ids), `assumptions` (question ids), `clarifications` (question ids with answers), `missing` (list for not_ready and blocker_escalated).
- Transitions (all emit `stage.changed` with direction):
  - null to intake (forward, on run start)
  - intake to plan (forward, verdict ready or ready_with_assumptions, all blocking clarifications answered)
  - intake to terminated (`not_ready`, or `dry_intake` when dry mode)
  - plan to work (forward)
  - work to assemble (forward, all sub-tasks except Assemble complete)
  - work to intake (backward, `route_back_to: intake`, once; second attempt becomes a blocker)
  - work to paused (blocker with `needs_human`; Answer resumes work; Escalate terminates `blocker_escalated`)
  - assemble to review (forward, after `draft.committed` and `artifact.compiled`)
  - review to handoff (forward, verdict pass, or fail with retries exhausted: `retry_exhausted`)
  - review to work (backward, fail routed to work, retries within budget, `retry.incremented`)
  - review to assemble (backward, fail routed to assemble, retries within budget, `retry.incremented`)
  - handoff to terminated (after `human.approved`, same exit as `handoff.ready`)
  - any to terminated (`stopped` on Stop; `cost_ceiling` after a `meter.update` breaches the ceiling, before any further dispatch)
- Pause gating: `run.paused` sets `paused`; dispatch waits while paused; in-flight stub tasks complete; `run.resumed` clears it.

### Stage
`intake | plan | work | assemble | review | handoff`. Ordered for the loop strip. Only the Orchestrator changes it.

### Exit
`reviewer_pass | retry_exhausted | blocker_escalated | not_ready | cost_ceiling | stopped | single_complete | dry_intake`. Only `reviewer_pass` and `retry_exhausted` pass through Handoff.

### AgentCard (actor)
- `agent_id` (seat key: `orchestrator | intake | estimator | pricing | writer | reviewer | case | market`), `name` (one of the seat's two names), `role` (fixed label), `model` (Model object).
- Seat definitions (fixed): names, role, colour (from the export), default model label. Two names per seat per spec 4.3.

### Model
`provider` (`bedrock | anthropic | google | ollama | xai`), `model_id`, `label` (grey text). S1 uses the default roster labels from the export as fixture values; the registry arrives in S2.

### PromptBundle
`prompt_ref`, `system`, `context_slice`, `task`, `tools` (list of strings), `model` (Model). Stored as JSON under `runs/<run_id>/prompts/<prompt_ref>.json` and registered by the stub fixtures.

### Scenario stub
- Module per dataset under `app/agents/stubs/`. Exposes `SCRIPT`: an ordered list of steps, each either an agent emission (seat, event type, payload, fixture offset ms, prompt bundle, meter delta) or an Orchestrator expectation marker (where the state machine acts). Exposes `HUMAN_SCRIPT`: the answers, the blocker action, and the handoff decision the presenter is expected to give, used by tests and by the golden regenerator.
- The Orchestrator, not the script, emits `run.started`, `stage.changed`, `assumption.accepted`, `clarification.asked`, `plan.created`, `task.dispatched`, `retry.incremented`, `handoff.ready`, `knowledge.appended`, `run.paused`, `run.resumed`, `run.terminated`. Stubs emit only agent events: `intake.brief`, `intake.readiness`, `clarification.needed`, `task.progress`, `tool.called`, `task.completed`, `blocker.raised`, `draft.committed`, `artifact.compiled` (stubbed compile, empty page list in S1), `review.verdict`, `meter.update`.

### Dataset
- `id` (folder name), `label` (from README title, numbered in the composer as `01 · Clean run` etc. in folder order given by a `datasets/index.yaml`? No: order is fixed in code by the spec's numbering 1 to 6), `readme`, `brand` (from `brand.yaml`), `knowledge_seed` (optional), `golden_path`.
- Numbering follows spec section 7: 01 clean-run, 02 planted-inconsistency, 03 missing-sheet, 04 missing-price, 05 not-ready, 06 prospect-own.

### Recording
- Folder `runs/<run_id>/` with `events.jsonl` (one event per line, in `seq` order), `prompts/*.json`, `meta.json` (`run_id`, `dataset_id`, `workflow`, `mode`, `started_at`, `ended_at`, `exit`), `knowledge.md`.
- Written incrementally as events are emitted (append), so a crash leaves a partial but valid prefix.

### Golden event log
- `datasets/<id>/golden-events.jsonl`, same line format as a recording. Compared on the ordered `stage.changed` transitions and the `run.terminated.exit`. Also schema-validated in full.

### Replay session
- `session_id`, `source` (`recording` | `golden`), `run_id` (original), `speed` (1 | 4), `dataset_id`. Serves events on the stream endpoint; writes nothing.

### Build stamp
- `hash` (short git hash or `no-git`), `date` (commit date or today), rendered in every header.

## UI view model (derived from events only)

The page keeps an in-memory list of events and reduces them into the view. Nothing else is state.

| View element | Events consumed |
|---|---|
| Loop strip node states | `stage.changed`, `run.paused`, `run.resumed`, `run.terminated` |
| Backward arrow fired | `stage.changed` with direction backward (arrow chosen by from and to) |
| Retry badge | `retry.incremented`; initial text uses the run's `retry_budget` from run metadata |
| Feed cards | every event except `meter.update` (which updates meters) |
| Thread expansion | thread active from `task.dispatched` until `task.completed` or `blocker.raised` |
| Waiting-on-you banner | `clarification.asked` with null blocker opens it; `clarification.answered` for all question ids closes it |
| Blocker card actions | `clarification.asked` with a blocker; closed by `clarification.answered` |
| Termination card | `handoff.ready` (with Approve live) then `run.terminated`; or `run.terminated` alone |
| Meters | `meter.update` deltas summed per agent; elapsed from last event `ts` minus `run.started.ts` |
| Raw drawer | every event |
| Agent card text | actor object on each event; `model.changed` (S5) |
