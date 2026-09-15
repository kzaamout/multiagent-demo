# Seat instructions: electrical RFP workflow

One file per seat. The whole file is the `system` section of the prompt bundle for that seat, so it appears verbatim in the prompt toggle. The context slice and the task are supplied per call by the Orchestrator; they are not part of these files. Loaded from slice S2.

Drafted 2026-09-14 and accepted by the owner for commit the same day. The open decisions below were raised with the drafts and are not settled by that acceptance.

## Files

| File | Seat | Default model (spec 4.3) |
|---|---|---|
| `orchestrator.md` | Orchestrator | Claude via Bedrock, low temperature |
| `intake.md` | Intake Analyst | Claude via Bedrock |
| `estimator.md` | Estimator | Claude via Bedrock, vision |
| `pricing.md` | Pricing | local model via Ollama |
| `writer.md` | Writer | Claude via Bedrock |
| `reviewer.md` | Reviewer | Gemini, vision, a different model family from the Writer |

## Placeholders filled per run

| Placeholder | Source |
|---|---|
| `{name}` | the seat's name for this run, chosen at random from its two names |
| `{retry_budget}` | `RETRY_BUDGET` in configuration, default 2 |
| `{long_lead_days}` | long-lead threshold in configuration; value pending decision 5 |

Output shapes in each file map onto event payloads in `docs/schema/events-v1.0.0.md`. Each seat reads its own config file named in the text: the Intake Analyst reads `readiness-checklist.md` and the knowledge file, the Estimator reads `estimating-conventions.md`, Pricing and the Writer read the knowledge file, and the Reviewer reads `reviewer-criteria.md`.

## Open decisions

1. **Rating disagreements.** `estimating-conventions.md` makes a single-line versus schedule rating disagreement a blocker. The Planted inconsistency target path needs it to be a concern so the Reviewer catches it.
2. **Missing panel schedule at Intake.** `readiness-checklist.md` makes it blocking, so a live Missing sheet run ends `not_ready` at Intake rather than `blocker_escalated` in Work.
3. **Orchestrator model scope.** `orchestrator.md` gives the model the plan, reasons, question wording, routing within the Reviewer's recommendations, and the termination headline. The run engine keeps every rule.
4. **Provenance tag syntax.** `writer.md` uses `{{value|src:<source_id>}}`, which the S4 compile step must parse.
5. **Long-lead threshold.** No document defines it; 28 days is proposed.
6. **Arithmetic on the local model.** It is proposed that the price lookup tool return extended costs and totals so Pricing copies numbers rather than computing them.
