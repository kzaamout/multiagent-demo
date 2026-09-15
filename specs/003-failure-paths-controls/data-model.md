# Data model: Failure paths and presenter controls (S3)

The event schema v1.0.0 is frozen and unchanged. S3 adds one field to the run request and uses events and summary fields that already exist.

## Run request (API)

| Field | Type | Rule |
|---|---|---|
| dataset_id | string | a discovered dataset |
| workflow | string | `electrical_rfp` |
| mode | `team` | Single model arrives in S5 |
| names | map or null | display names per seat |
| dry_intake | boolean, default false | new in S3; ends the run after Intake with exit `dry_intake` |

## Presenter control state (page)

| State | Entered by | Pause | Stop | Dry intake toggle |
|---|---|---|---|---|
| idle | page load, run ended | disabled | disabled | enabled |
| running | `run.started`, `run.resumed` | enabled, reads Pause | enabled | disabled |
| paused by presenter | `run.paused` | enabled, reads Resume | enabled | disabled |
| waiting on a human | `clarification.asked`, `handoff.ready` | disabled | enabled | disabled |
| ended | `run.terminated` | disabled | disabled | enabled |
| replay or fixed state | replay start, `?run=`, `?golden=` | disabled | disabled | disabled |

## Events used

| Event | Emitted by | When | Payload |
|---|---|---|---|
| `run.paused` | Orchestrator | presenter pauses a running run | `{"by": "human"}`, reason |
| `run.resumed` | Orchestrator | presenter resumes | `{"by": "human"}`, reason |
| `stage.changed` backward | Orchestrator | failed review routed to Work or Assemble; Work routed to Intake | direction `backward`, target reason |
| `retry.incremented` | Orchestrator | failed review within budget | count, budget |
| `blocker.raised` | specialist | a blocker in its reply | blocker id, description, needs human, route back |
| `clarification.asked` | Orchestrator | blocker needing a human | question ids, blocker |
| `clarification.answered` | human | Answer or Escalate | question id, answer, action |
| `run.terminated` | Orchestrator | every end | exit, structured summary |

## Structured summary on `run.terminated` (existing)

headline, missing (item, note, source event), unresolved findings, retries (count, budget), readiness verdict, event count, elapsed ms, estimated cost, human decision.

Card rules by exit:

| Exit | Card source | Extra lines |
|---|---|---|
| reviewer_pass, retry_exhausted | `handoff.ready`, closed by `run.terminated` | notes carried to Handoff, decision |
| not_ready | `run.terminated` | missing items |
| blocker_escalated | `run.terminated` | missing items |
| dry_intake | `run.terminated` | readiness verdict |
| cost_ceiling | `run.terminated` | estimated spend against the ceiling |
| stopped | `run.terminated` | the presenter stopped the run |

## Derived dataset (files)

| Path | Content |
|---|---|
| `README.md` | scenario, planted defect with sheet or file, expected sequence, expected exit, presenter note, build commands |
| `source/*.typ` | copy of Clean run sources with the scenario's edits |
| `inputs/*.pdf`, `inputs/drawings/*.pdf` | compiled request documents and sheets |
| `fixtures/supplier-prices.csv` | Clean run price list, less the missing item for Missing price |
| `brand.yaml` | Fictional Prospect Ltd., shared with Clean run |
| `golden-events.jsonl` | S1 golden log, unchanged |
