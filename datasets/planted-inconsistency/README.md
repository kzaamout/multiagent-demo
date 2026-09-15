# Planted inconsistency

Scenario: same as Clean run, with one deliberate defect.
Planted defect: panel schedule for panel [SHEET TBD] states a 200A main breaker; the single-line on [SHEET TBD] shows 225A for the same panel. Fill in sheet numbers when curated.
Expected behaviour: the Estimator proceeds on the single-line value and raises a concern (estimating conventions, decision 2026-09-14); the Reviewer catches the resulting inconsistency. One Review fail routed to the Estimator, one rework, then pass.
Expected exit: reviewer_pass, retry count 1.
Presenter note: this is the primary live demo dataset when the prospect's own file is unavailable or passes too cleanly. Say afterward that the defect was planted, and why.
