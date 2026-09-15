# Planted inconsistency

Scenario: same as Clean run, with one deliberate defect.
Planted defect: panel schedule for panel [SHEET TBD] states a 200A main breaker; the single-line on [SHEET TBD] shows 225A for the same panel. Fill in sheet numbers when curated.
Expected behaviour: either the Estimator raises a concern and the Reviewer catches the resulting inconsistency, or the Estimator raises a blocker directly. Target path is one Review fail routed to Estimator, one rework, then pass.
Expected exit: reviewer_pass, retry count 1.
Presenter note: this is the primary live demo dataset when the prospect's own file is unavailable or passes too cleanly. Say afterward that the defect was planted, and why.
