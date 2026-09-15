# Quickstart: verify S3

Prerequisites: S2 setup done (`scripts/setup.ps1`), Ollama running with the seat models, AWS keys in `.env`, and `COST_CEILING=1.00` in `.env`.

## Gates

```
uv run python scripts/check.py
uv run pytest -m visual
```

## Start the demo

```
$env:PYTHONUTF8 = "1"
uv run uvicorn app.main:app --port 8000
```

Open http://localhost:8000/demo.

## Scenarios from the Demo page

Run Clean run once first if the knowledge file has no bid security answer, so the failure scenarios do not pause on that question.

1. **Not ready.** Choose 05 Not ready, press Run. Expected within two minutes: exit not_ready, card lists the submission deadline and the Division 26 specification, no specialist thread.
2. **Missing price.** Choose 04 Missing price. Expected: Pricing thread shows one unpriced exception for Exit sign, LED; draft lists it under exclusions; Review passes; card shows notes carried to Handoff if the Reviewer made a minor finding. Approve.
3. **Missing sheet, Escalate.** Choose 03 Missing sheet. Expected: the Estimator raises a blocker; the blocker card offers Answer and Escalate. Press Escalate. Expected: exit blocker_escalated, card lists the missing LP-2 schedule.
4. **Missing sheet, Answer.** Run again and answer the blocker. Expected: the run resumes at Work and continues.
5. **Planted inconsistency.** Choose 02 Planted inconsistency. Expected: Review fails v1 with a finding routed to the Estimator, the Review to Work arrow fires, the retry badge reads 1 of 2, the Estimator reworks, v2 passes. Approve.
6. **Pause and Stop.** Run Clean run, press Pause during Work, watch that no new thread starts, press Resume, then Stop. Expected: exit stopped within 5 s.
7. **Dry intake.** Switch Dry intake on, run Clean run. Expected: exit dry_intake after Intake with the readiness verdict on the card.
8. **Cost ceiling.** Restart the server with `COST_CEILING=0.02`, run Clean run. Expected: exit cost_ceiling after the Estimator's first call, card shows the spend against the ceiling. Restore the ceiling afterwards.

## Evidence

```
uv run python scripts/compare_run.py <run_id>
```

Prints the run's transitions, exit, retries, questions, blockers, and estimated cost beside its dataset's golden log, and exits non-zero on a mismatch.
