# Missing sheet

Scenario: the panel schedule for a panel shown on the single-line is absent from the drawing set.
Planted defect: remove the schedule sheet for panel [TBD].
Expected behaviour: Intake marks a blocking checklist item missing only if the checklist rule fires; otherwise Intake passes with a concern and the Estimator raises a blocker in Work. Both are acceptable; document which one the golden log shows.
Expected exit: blocker_escalated (or not_ready if Intake catches it first).
Presenter note: the 'what happens when it goes wrong' answer. Stopping with a clear reason is the feature.
