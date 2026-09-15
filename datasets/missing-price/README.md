# Missing price

**Status.** Derived on 2026-09-15 from the synthetic Clean run set (`../clean-run/README.md`). The request, specification, and drawings are identical to Clean run.

Scenario: one item required by the drawings is absent from supplier-prices.csv.
Planted defect: the row for **`Exit sign, LED`** (item code `EM-EXIT-LED` in Clean run) is removed from `fixtures/supplier-prices.csv`. The drawings still call for four exit signs (E-101, E-002 circuit 9, materials schedule M2). `Exit sign, LED, with battery backup` stays in the list as a near miss that must not be substituted.
Expected behaviour: Pricing lists the item as an unpriced exception; the Writer states it as an exclusion with its reason and the total excludes it; the Reviewer records at most a minor finding; the run passes.
Expected sequence: Intake > Plan > Work > Assemble > Review > Handoff.
Expected exit: reviewer_pass, retry count 0, a minor finding at Handoff if the Reviewer makes one.
Presenter note: shows that gaps surface honestly rather than being invented.

## Build

`inputs/` holds the Clean run PDFs, compiled from `source/`, which is an unchanged copy.
