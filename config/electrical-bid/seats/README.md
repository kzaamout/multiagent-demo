# Seat instructions: electrical bid response workflow

One file per seat. The whole file is the `system` section of the prompt bundle for that seat, so it appears verbatim in the prompt toggle. The context slice and the task are supplied per call by the Orchestrator; they are not part of these files. Loaded from slice S2.

Drafted 2026-09-14 and accepted by the owner the same day, together with the decisions below.

## Files

| File | Seat | Default model (spec 4.3) |
|---|---|---|
| `orchestrator.md` | Orchestrator | Claude via Bedrock, default temperature |
| `intake.md` | Intake Analyst | Claude via Bedrock |
| `estimator.md` | Estimator | Claude via Bedrock, vision |
| `pricing.md` | Pricing | local model via Ollama |
| `writer.md` | Writer | Claude via Bedrock |
| `reviewer.md` | Reviewer | Gemini, vision, a different model family from the Writer |

## Placeholders filled per run

| Placeholder | Source |
|---|---|
| `{name}` | the seat's name for this run, chosen at random from its two names |
| `{review_max_cycles}` | `REVIEW_MAX_CYCLES` in configuration, default 4: the hard ceiling on review cycles per run |
| `{long_lead_days}` | `LONG_LEAD_DAYS` in configuration, default 28 |

Output shapes in each file map onto event payloads in `docs/schema/events-v1.1.0.md`. Each seat reads its own config file named in the text: the Intake Analyst reads `readiness-checklist.md` and the knowledge file, the Estimator reads `estimating-conventions.md`, Pricing and the Writer read the knowledge file, and the Reviewer reads `reviewer-criteria.md`.

## Decisions (owner, 2026-09-14)

1. **Rating disagreements are a concern.** `estimating-conventions.md` now tells the Estimator to proceed on the single-line value and flag both values, so the Reviewer catches the inconsistency in Planted inconsistency.
2. **A missing panel schedule is a concern at Intake.** `readiness-checklist.md` now leaves it to the Estimator, who raises the blocker in Work, so Missing sheet shows Answer and Escalate.
3. **Orchestrator model scope.** The model proposes the plan, reasons, question wording, routing within the Reviewer's recommendations, and the termination headline. The run engine keeps every rule and validates every proposal.
4. **Provenance tag syntax** is `{{value|src:<source_id>}}`. The S4 compile step parses it.
5. **Long-lead threshold** is 28 days.
6. **The price lookup tool returns extended costs and totals**, so Pricing copies numbers rather than computing them.
