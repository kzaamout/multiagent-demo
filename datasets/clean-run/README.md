# Clean run

Scenario: complete request, complete drawing set, every BOM item priced.
Planted defects: none.
Expected sequence: Intake (Ready with assumptions, one non-blocking default) > Plan > Work (Estimator, then Pricing) > Assemble > Review pass > Handoff.
Expected exit: reviewer_pass, retry count 0.
Presenter note: use this for the second run at the end of the arc, to show the clarification not repeating. Also the source of the public Replay on the Introduction tab.
