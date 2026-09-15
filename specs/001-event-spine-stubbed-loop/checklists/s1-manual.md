# S1 manual and browser checks

**Date**: 2026-09-14
**Build**: branch `001-event-spine-stubbed-loop`
**Browser**: Chromium (Playwright 1.62.0) at 1920 by 1080; the presenter's Chrome for the owner review

The checks below were run through the Demo page by clicking, not by calling the API. The automated form of each is in `tests/visual/test_e2e_ui.py`, so they repeat on every visual run.

## Quickstart steps (T042)

- [x] 01 Clean run: Run, loop strip lights Intake to Handoff in order, Pricing shows "Waiting for the Estimator" until the takeoff completes, verdict pass, termination card from `handoff.ready` with Approve live, Approve closes the card with the decision. Covered by the Orchestrator scenario suite and the page flow for scenario 2.
- [x] 02 Planted inconsistency: banner with two questions and editable defaults, Intake node paused (coral, "!"), Resume records both answers and closes the banner, Review to Work arrow fires, retry badge reads "retry 1 of 2", Approve ends the run with 65 events in the raw drawer, all six nodes complete, recording written under `runs/`.
- [x] 03 Missing sheet: blocker card with Answer and Escalate, Work node paused, Escalate ends the run with exit `blocker_escalated` and "What is missing" naming LP-2.
- [x] 05 Not ready: run stops after Intake listing the submission deadline and the Division 26 specification.
- [x] 06 Prospect own: dry intake ends with exit `dry_intake` and the readiness verdict on the card.
- [x] Prompt toggle on an agent message shows System instructions, Context provided, Task, Tools available, and Model. An Orchestrator note shows its reason on click.
- [x] No page errors in the browser console across the flows.

## Replay (T047)

- [x] Replay at 4x of Not ready plays the golden log in about six seconds (24 seconds of recorded time divided by four) with the six original event ids.
- [x] Replay at 4x of the recorded Planted inconsistency run renders the same cards, card times, loop strip states, meters, and elapsed time as a static render of the recording.

## Family consistency review (T057)

- [x] Blocker card: white card, hairline border, 4px red left border, Orchestrator agent card at 40px, event label, body text at 16px, "Why" block, dark pill and outlined pill from the Handoff action family.
- [x] Dry intake toggle: segmented switch in the mode switch style with a 13px muted label, disabled at the export's 0.45 opacity.
- [x] Edit and Reject: outlined pills matching Download PDF, disabled at 0.45 opacity.
- [x] Build stamp and pre-flight dot in every header: build stamp in the Settings style, dot in the Demo header style with a grey pending state.

## Screenshot comparison

| Capture | Unmasked pixels differing | Result |
|---|---|---|
| Demo idle | 0.050% | pass |
| Demo paused | 0.075% | pass |
| Demo running | 0.107% | pass |
| Demo terminated | 0.275% | pass |
| Login | 0.000% | pass |
| Settings | 0.040% | pass |
| Pre-flight pending | 0.308% | pass |

Threshold 0.5% of unmasked pixels, channel tolerance 24. Masks and reasons: `tests/visual/masks.py`.
