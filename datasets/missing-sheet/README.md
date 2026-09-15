# Missing sheet

Scenario: the panel schedule for a panel shown on the single-line is absent from the drawing set.
Planted defect: remove the schedule sheet for panel [TBD].
Expected behaviour: Intake grades the missing schedule as a concern for the Estimator (readiness checklist, decision 2026-09-14). The Estimator raises a blocker in Work; the run pauses; the presenter chooses Escalate.
Expected exit: blocker_escalated.
Presenter note: the 'what happens when it goes wrong' answer. Stopping with a clear reason is the feature.
