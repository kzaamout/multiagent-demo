# Event schema, version 1.0.0

Status: frozen on 2026-09-14 under constitution II and XII. Source: `docs/spec-input.md` 0.5 section 6, with the pre-S1 decisions applied. Changes require an amendment under constitution XIX and a new version. The JSON Schema export `events-v1.0.0.json` is generated from the typed models and must match this document.

## Envelope

| Field | Type | Rule |
|---|---|---|
| `event_id` | uuid string | unique per event |
| `run_id` | uuid string | the run the event belongs to; replays keep the original |
| `seq` | integer | starts at 1, increases by exactly 1 per run |
| `ts` | ISO 8601 string with timezone | for stubbed runs, run start plus a fixture offset; for live agents, wall time |
| `type` | string | one of the types below |
| `stage` | `intake`, `plan`, `work`, `assemble`, `review`, `handoff`, or null | null for `run.started`, `run.terminated`, and every event of a Single-model run |
| `actor` | Agent object, `"human"`, or `"system"` | Agent is `{ agent_id, name, role, model }`; `model` is `{ provider, model_id, label }` |
| `reason` | string | required on every Orchestrator event, one sentence; absent otherwise |
| `prompt_ref` | string | required on agent messages: `intake.brief`, `intake.readiness`, `clarification.needed`, `task.progress`, `tool.called`, `task.completed`, `blocker.raised`, `draft.committed`, `review.verdict`; absent otherwise |
| `payload` | object | type-specific, below |

Orchestrator events (actor is the Orchestrator seat, `reason` required): `run.started`, `stage.changed`, `clarification.asked`, `assumption.accepted`, `plan.created`, `task.dispatched`, `retry.incremented`, `handoff.ready`, `knowledge.appended`, `run.paused`, `run.resumed`, `run.terminated`.

Human events (actor `"human"`): `clarification.answered`, `human.approved`, and `draft.committed` plus `artifact.compiled` for a Handoff edit.

System events (actor `"system"`): `model.changed` (from Settings), `artifact.compiled` when the compiler runs outside an agent, `meter.update`.

## Event types and payloads

- `run.started` `{ workflow, dataset_id, mode: team | single, roster: [Agent] }` (Orchestrator, stage null)
- `stage.changed` `{ from: Stage | null, to: Stage, direction: forward | backward, target_reason: string }`
- `intake.brief` `{ brief: object }`
- `intake.readiness` `{ verdict: ready | ready_with_assumptions | not_ready, checklist: [{ item, status: pass | fail | assumed, note }], legibility: [{ page, confidence }] }`
- `clarification.needed` `{ question_id, question, why_it_matters, proposed_default, blocking: bool }`
- `clarification.asked` `{ question_ids: [string], blocker: { blocker_id, task_id, agent_id, description } | null }` (Orchestrator; the run pauses)
- `clarification.answered` `{ question_id, answer, action: answer | escalate }` (human; `escalate` only for a blocker)
- `assumption.accepted` `{ question_id, default_used }` (Orchestrator)
- `plan.created` `{ subtasks: [{ task_id, title, agent_id, depends_on: [task_id], scope: [string] }] }` (Orchestrator; includes Assemble for the Writer)
- `task.dispatched` `{ task_id, agent_id, inputs_summary }` (Orchestrator)
- `task.progress` `{ task_id, agent_id, message, headline: string (optional, default empty) }`
- `tool.called` `{ task_id, agent_id, tool, args_summary, result_summary, duration_ms }`
- `task.completed` `{ task_id, agent_id, result: object, provenance: [{ tool, source, confidence }] }`
- `blocker.raised` `{ blocker_id, task_id, agent_id, description, needs_human: bool, route_back_to: intake | null }`
- `draft.committed` `{ version, markdown_path, provenance_tags: [{ tag_id, source_event_id }], note: string (optional, default empty) }` (Writer, or human at Handoff)
- `artifact.compiled` `{ version, pdf_path: string | null, page_images: [string] }` (empty in S1; populated from S4)
- `review.verdict` `{ verdict: pass | fail, findings: [{ id, severity: blocker | major | minor, text, evidence, route_to: work | assemble | null, agent_id: string | null }], summary: string (optional, default empty) }`
- `retry.incremented` `{ count, budget }` (Orchestrator)
- `handoff.ready` `{ exit_determination: reviewer_pass | retry_exhausted, package: { pdf_path: string | null, page_images: [string], verdict_event_id, unresolved_findings: [finding id], assumptions: [question_id], clarifications: [{ question_id, answer }], event_log_path } }` (Orchestrator)
- `human.approved` `{ decision: approve | edit | reject, notes }` (human)
- `knowledge.appended` `{ client_id, entries: [{ question_id, answer, source_event_id }] }` (Orchestrator; Intake clarifications only)
- `run.paused` `{ by: human }` (Orchestrator)
- `run.resumed` `{ by: human }` (Orchestrator)
- `model.changed` `{ agent_id, from_model: Model, to_model: Model }` (system)
- `meter.update` `{ agent_id, call_id, tokens_in, tokens_out, wall_ms, est_cost }` (system; per-call delta)
- `run.terminated` `{ exit: Exit, summary: Summary }` (Orchestrator, stage null; always the last event)

Where

- `Stage` is `intake | plan | work | assemble | review | handoff`
- `Exit` is `reviewer_pass | retry_exhausted | blocker_escalated | not_ready | cost_ceiling | stopped | single_complete | dry_intake`
- `Summary` is `{ headline: string, missing: [{ item, note, source_event_id }], unresolved_findings: [finding id], retries: { count, budget }, readiness_verdict: ready | ready_with_assumptions | not_ready | null, event_count, elapsed_ms, est_cost, human_decision: approve | edit | reject | null }`. `missing` is filled for `not_ready` and `blocker_escalated`; `unresolved_findings` for `retry_exhausted`; `readiness_verdict` for `not_ready` and `dry_intake`. `event_count` counts every event of the run including `run.terminated`.

Additions relative to spec section 6, all recorded as decisions: `title` on plan sub-tasks (the export's plan card shows one), `text` on findings (the export shows finding text and evidence separately), `headline` on `task.progress` (the one-line thread summary while a sub-task is active), `note` on `draft.committed` and `summary` on `review.verdict` (the export's cards carry a one-line commit note and a verdict sentence), `status` values on checklist items, `pdf_path` nullable and `page_images` possibly empty on `artifact.compiled` while the compiler is stubbed, `readiness_verdict` on the summary (pre-S1 decision 1).

## Prompt bundle

`{ prompt_ref, system, context_slice, task, tools: [string], model: Model }`. Stored per call. Referenced by `prompt_ref` on agent messages.

## Run-level rules

1. The first event of a run is `run.started`; the last is `run.terminated`; nothing follows it.
2. `seq` is 1, 2, 3, ... with no gaps.
3. Every event validates against its payload model before it is emitted, recorded, or rendered.
4. Recording: `runs/<run_id>/events.jsonl` holds the events in order, one JSON object per line. Replay re-emits them verbatim.
5. Golden logs use the same line format and are compared on the ordered `stage.changed` transitions and the terminal `exit`.

## Line format

One event per line, JSON, UTF-8, no em dashes, keys in the envelope order above.
