# Not ready

**Status.** Derived on 2026-09-15 from the synthetic Clean run set (`../clean-run/README.md`).

Scenario: request is missing blocking items.
Planted defect: section 3 of **invitation-to-tender.pdf** says the closing date and time will be issued by addendum, and section 6 has no questions deadline date, so there is **no submission deadline**. **division-26-specification.pdf is absent** from `inputs/` although section 1 of the invitation refers to Division 26 and section 2 lists the specification as a tender document. The drawings are the Clean run drawings.
Expected behaviour: Intake returns Not ready with both items listed; the run terminates before Plan and no specialist is dispatched.
Expected sequence: Intake.
Expected exit: not_ready.
Presenter note: the "what if our RFP is a mess" answer. Seconds to a clear list beats a beautiful answer to the wrong question.

## Build

As for Planted inconsistency, from `datasets/not-ready`, without compiling `division-26-specification.typ`, which stays in `source/` only for reference.
