# Missing sheet

**Status.** Derived on 2026-09-15 from the synthetic Clean run set (`../clean-run/README.md`), with a second panel added so that its missing schedule leaves an otherwise coherent set.

Scenario: the panel schedule for a panel shown on the single-line is absent from the drawing set.
Planted defect: panel **LP-2** (30-circuit, 100 A, staff workroom, fed from LP-1 by feeder F2 on a 100 A three-pole breaker) appears on single-line **E-001**, in the drawing index on **E-000**, on power plan **E-102** (the program room receptacles are tagged LP-2-1), on panel schedule E-002 (circuits 14, 16, 18), and in the invitation's drawing list. Its schedule, **E-003 Panel Schedule LP-2**, is not in the set.
Expected behaviour: Intake grades the absent schedule as a concern for the Estimator and the index mismatch as a default, not a question (readiness checklist, decision 2026-09-14). The Estimator raises a blocker that needs a human; the run pauses on the blocker card. The presenter chooses Escalate.
Expected sequence: Intake > Plan > Work, then the blocker.
Expected exit: blocker_escalated, with the missing LP-2 schedule on the termination card.
Presenter note: the "what happens when it goes wrong" answer. Stopping with a clear reason is the feature. Answer instead of Escalate to show the run resuming, for example with "Treat LP-2 as a 30-circuit 100 A panelboard with one 20 A circuit for the four program room receptacles"; a blocker answer is never written to the client knowledge file.

## Build

As for Planted inconsistency, from `datasets/missing-sheet`. There is no `E-003.typ`.
