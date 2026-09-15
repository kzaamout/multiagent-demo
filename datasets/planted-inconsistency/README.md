# Planted inconsistency

**Status.** Derived on 2026-09-15 from the synthetic Clean run set (`../clean-run/README.md`): same fictional project, prospect, request, specification, and price list, with one planted change.

Scenario: same as Clean run, with one deliberate defect.
Planted defect: panel schedule **E-002** states a **200 A main breaker** for panel LP-1; the single-line **E-001** shows **225 A** for the same panel, and specification section 26 24 16 also says 225 A. The notes on E-001 and E-002 that said the ratings agree are removed. Nothing else differs from Clean run.
Expected behaviour: the Estimator proceeds on the single-line value and raises a concern naming both sheets (estimating conventions, decision 2026-09-14). The draft carries the disagreement; the Reviewer fails v1 on the inconsistency and routes it to the Estimator. The Estimator reworks with the finding in its context and confirms 225 A under the single-line rule; the Writer assembles v2 with one rating; v2 passes.
Expected sequence: Intake > Plan > Work > Assemble > Review > Work (back) > Assemble > Review > Handoff.
Expected exit: reviewer_pass, retry count 1.
Presenter note: this is the primary live demo dataset when the prospect's own file is unavailable or passes too cleanly. Say afterward that the defect was planted, on E-002, and why. Run Clean run first so the bid security answer is already in the knowledge file and this run does not pause on it.

## Build

Typst 0.15.1 with Arial. From `datasets/planted-inconsistency`:

```
typst compile source/invitation-to-tender.typ inputs/invitation-to-tender.pdf
typst compile source/division-26-specification.typ inputs/division-26-specification.pdf
typst compile source/E-000.typ inputs/drawings/E-000.pdf
```

and the same for E-001, E-002, E-101, and E-102. `tests/integration/s3/test_failure_datasets.py` checks the planted change.
