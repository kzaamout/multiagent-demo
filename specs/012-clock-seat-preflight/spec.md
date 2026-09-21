# Feature Specification: Presenter clock and seat-aware pre-flight

**Feature Branch**: `012-clock-seat-preflight`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "1. the time ELAPSED is updated by the code directly (it is not a client side timer). this result in staggard time updates where the ELAPSED time is not updated every second, instead it freezes for a while then update several minutes at a time. 2. preflight should not display red X icon in the menu above unless issues are identified with the models selected under settings's Agent Seats. the pre-flight check itself must continue to identify all issues with all connected models/apis and flag them in red x inside the page itself (example: gemini did not answer) but if a gemini is not selected in the Seat the red X must not be displayed in the top menu (e.g. Pre-flight (X)). every time a seat is changed, the pre-flight check must rerun the test relevant to the change." Owner answers of 2026-09-21 are listed under Owner decisions.

**Governing documents**: `.specify/memory/constitution.md` 1.2.0 (II, III, VIII, X, XVII, XVIII, XIX), `CLAUDE.md` working rule 3, `docs/spec-input.md` 0.7 sections 2.2 (meters strip) and 2.4 (Pre-flight), `specs/008-demo-day-readiness/spec.md` (User Story 1, FR-001, FR-005, FR-016, the seat swap edge case, the login pair assumption), `docs/design-deviations.md` (the elapsed meter entry), `design/README.md` (the pre-flight indicator's three states).

## Purpose

Two things on screen tell the presenter and the prospect something untrue.

The Elapsed figure in the meters strip only moves when an event arrives. While a model works on a long call it sits still for minutes, then jumps. On a projector that reads as a hung demo.

The pre-flight dot beside Pre-flight in every header goes red for failures that cannot touch the demo the presenter is about to give. Today it is red on the presenter laptop because the shared login pair is missing, which does not matter when the app runs on the laptop, and a Gemini model that no seat uses fails its probe and would push the dot to amber on its own. The dot is also frozen at the moment the pre-flight ran: moving a seat to another model in Settings changes nothing until the presenter reruns the whole pre-flight. The presenter needs the dot to answer one question, "will the demo I have set up work", and the Pre-flight page to go on answering the wider one, "what is broken anywhere".

## Owner decisions (2026-09-21)

1. The Elapsed figure becomes a display-only clock in the browser. It starts with the run, ticks while the run works, and stops when the run ends by any exit. Principle II of the constitution and `CLAUDE.md` working rule 3 are amended to allow it, taking the constitution from 1.2.0 to 1.3.0.
2. The clock freezes while the run waits on a human and continues once the human submits the response.
3. In replay the clock ticks at the chosen replay speed.
4. The header dot is red for a failed seat model and for the checks that stop any run (Typst, page PNG export, disk, a missing key for a seat's provider). The login pair counts only in Cloud mode, where the tunnel exposes the site. The dot is also red for anything else that could stop the demo or cause issues for it.
5. A failure on a model no seat uses leaves the header dot green; the row is red on the Pre-flight page.
6. The Pre-flight page probes every cloud model in the Settings menu with one short call each, run at the same time, and checks every local model is pulled.
7. A seat change reruns the checks for the chosen model and for its provider's key, updates the stored result, and the header is worked out again from the current seats.
8. When that recheck fails the seat change still applies; the Settings status line names the failure and the header dot turns red.
9. A seat change during a live run still runs the recheck. It is out of band: not an event, not recorded.
10. The termination card shows the same working time as the clock, so the two figures always match on screen.
11. Four conditions that could cause issues for the demo turn the dot amber, not red: the Reviewer and the Writer on the same model family; the Introduction's public replay recording missing on this machine; a scenario dataset with nothing to replay; the tunnel not answering while a hostname is set.
12. Feed card times show working time, like the clock (agreed after implementation, 2026-09-21).
13. The Compare strip and the comparison line show compute time, the working time without human waits, for both the Team and the Single-model run, not the overall execution time (2026-09-21).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Elapsed ticks like a clock (Priority: P1)

The presenter starts a run. The Elapsed figure counts up one second at a time while the agents work, including through a model call that takes several minutes. When the Orchestrator puts a batch of questions to the presenter, the figure stops and stays still until the presenter submits the answers, then carries on from where it stopped. When the run ends, by any exit, the figure stops for good. In a replay the figure counts at the replay's speed, four seconds per second at 4x.

**Why this priority**: The meters strip is on screen for the whole demo. A clock that freezes for minutes and jumps is the first thing a prospect reads as broken.

**Independent Test**: Replay a recorded run that contains a clarification batch at 1x and at 4x in the browser test harness, sample the Elapsed text every 250 ms, and assert that it advances once per second of run time while the run works (four per second at 4x), holds still between the question and the last answer, and holds its final value after the run ends.

**Acceptance Scenarios**:

1. **Given** no run has started, **When** the Demo page loads, **Then** Elapsed reads 00:00 and does not move.
2. **Given** a live run in Work with a model call in flight and no event for two minutes, **When** the presenter watches the meters strip, **Then** Elapsed advances by one every second throughout the two minutes.
3. **Given** a run whose Orchestrator has asked a clarification batch, **When** the presenter takes 90 seconds to answer, **Then** Elapsed holds the value it had when the questions appeared for the whole 90 seconds and resumes counting from that value once the answers are submitted.
4. **Given** a run paused by the presenter, **When** the presenter resumes it, **Then** Elapsed held still while paused and continues from the held value.
5. **Given** a run that reaches Handoff, **When** the Orchestrator asks the presenter to approve, **Then** Elapsed holds still until the presenter approves, edits, or rejects, then counts the Orchestrator's closing work until the run ends.
6. **Given** a run that ends by stop, cost ceiling, reviewer pass, or any other exit, **When** the final event arrives, **Then** Elapsed shows its final value and never changes after it, and the termination card shows the same figure.
7. **Given** a replay at 4x, **When** the recorded run is working, **Then** Elapsed advances four seconds for each second on the wall, and each event sets it to the working time that the recording gives for that event.
8. **Given** a live run in progress, **When** the presenter reloads the Demo page, **Then** Elapsed shows the run's current working time, not 00:00 and not the time of the last event, and carries on ticking.

---

### User Story 2 - The header dot reflects only what would hurt this demo (Priority: P1)

The presenter runs the pre-flight. The page shows one row for every model the Settings menu offers, so a Gemini model that no longer answers shows as a red row with its reason, even though no seat uses it. The dot beside Pre-flight in every header stays green, because every seat's model answered and every check the current setup depends on passed. Its tooltip says that the checks for the current seats pass and that one row for an unused model failed. Had a seat been on that Gemini model, the dot would be red and its tooltip would name that model.

**Why this priority**: This is the owner's request. The dot is the one signal the presenter glances at before a meeting; a red dot that does not mean "your demo will fail" teaches the presenter to ignore it.

**Independent Test**: With injected probes, make one unused cloud model fail and everything else pass, then assert that the page row is red, the header dot on Demo, Settings, Pre-flight, and Introduction is green, and the tooltip names the unused failure. Move a seat onto that model and assert the dot is red on the next page load without rerunning anything.

**Acceptance Scenarios**:

1. **Given** every check passes except a cloud model no seat uses, **When** any page loads, **Then** that model's row is red on the Pre-flight page with a one-line reason, and the header dot is green with a tooltip naming the unused failure.
2. **Given** a seat's model fails its probe, **When** any page loads, **Then** the header dot is red and its tooltip names that model and the seat that uses it.
3. **Given** Laptop mode and no login pair in `.env`, **When** the pre-flight runs and everything else passes, **Then** the `.env completeness` row reports the missing login pair and the header dot is not red for it.
4. **Given** Cloud mode and no login pair in `.env`, **When** the pre-flight runs, **Then** the header dot is red naming the missing login pair.
5. **Given** a seat's provider has no key in `.env`, **When** the pre-flight runs, **Then** the header dot is red naming the missing key by name only.
6. **Given** Typst, page PNG export, or disk space fails, **When** the pre-flight runs, **Then** the header dot is red, whatever the seats are.
7. **Given** a stored result and seats that have changed since it was taken (for example after a server restart returned every seat to its configured model), **When** a page loads, **Then** the dot is worked out from the stored rows against the seats in force now, not the seats at the time of the pre-flight.
8. **Given** a seat on a model that has no stored row (added to the registry after the last pre-flight), **When** a page loads, **Then** the dot is grey with a tooltip naming the unchecked seat model, unless a check that matters has failed, in which case it is red.
9. **Given** every red condition passes, **When** the presenter moves the Reviewer onto the Writer's model family, **Then** the family row on the Pre-flight page fails and the header dot is amber with a tooltip saying the Reviewer shares the Writer's family.
10. **Given** every red condition passes, **When** the Introduction's public recording is missing, a scenario dataset has nothing to replay, or the tunnel does not answer while a hostname is set, **Then** that row is red on the Pre-flight page and the header dot is amber naming it.

---

### User Story 3 - A seat change rechecks the chosen model (Priority: P2)

In Settings the presenter moves the Estimator seat to another model. The change applies at once. The status line says the chosen model is being checked and, a few seconds later, says whether it answered. If it did not, the line names the failure and the header dot on the Settings page turns red without a reload. Moving the seat back to a model that answers turns the dot green again. The same happens during a live run; the check costs one short model call and leaves no trace in the run.

**Why this priority**: It keeps the dot honest between full pre-flights, which the presenter runs once before a meeting, not after every seat change.

**Independent Test**: With injected probes, post a seat change to a failing model and assert that the seat moved, the stored result holds the model's new failed row with the recheck's time, the Settings status line and header dot show the failure, and no event was added to a live run. Post a change to a local model and assert that the Ollama reachability row and that model's pulled row were rechecked.

**Acceptance Scenarios**:

1. **Given** a seat on a passing model, **When** the presenter moves it to a cloud model that fails its probe, **Then** the seat moves, the status line reads that the model did not answer with its reason, and the Settings header dot turns red.
2. **Given** a seat on a failing model, **When** the presenter moves it to a model that answers, **Then** the status line reads that the model answered, and the dot returns to the state the other rows give.
3. **Given** a seat change to a local model, **When** the recheck runs, **Then** the Ollama reachability row and that model's pulled row are rechecked, not a model call.
4. **Given** a seat change, **When** the recheck runs, **Then** the `.env completeness` row is rechecked for the chosen model's provider key, and no other row changes.
5. **Given** a live run in progress, **When** the presenter changes a seat, **Then** the recheck runs, no event is added to the run, and the run's meters, cost, recording, and metrics do not include the probe.
6. **Given** a full pre-flight is running, **When** the presenter changes a seat, **Then** the recheck waits for the full pre-flight to finish and then runs.

---

### Edge Cases

- A run already ended when the page loads: Elapsed shows the final working time at once and never ticks.
- The browser tab is hidden and shown again during a run: Elapsed shows the right working time as soon as the tab is visible again.
- An event arrives with a time slightly earlier than the value already on screen: the figure never goes backwards; it holds until the run's working time passes it.
- The Introduction's public replay shortens long recorded gaps to a few seconds: the clock ticks at replay speed through the shortened gap and moves forward to the recorded working time when the next event arrives.
- A clarification batch with several questions: the clock stays frozen until the last question in the batch is answered.
- A blocker that the presenter escalates instead of answering: the run ends, and the clock stays at the value it had when the blocker was put to the presenter.
- A run stopped while Handoff waits for approval: the clock stays at the value it had when approval was asked for.
- The presenter pauses during a question batch: the clock is already frozen and stays frozen until both the answers and the resume have arrived.
- Two seat changes in quick succession: each recheck runs; the stored row for each model holds its latest result and the dot reflects the seats in force at the end.
- A recheck that times out: the row fails with "no answer within 30 s", the seat change stands.
- A stored pre-flight result written before this change: it is read as "not run yet", and the presenter runs the pre-flight once.
- Cloud mode with a seat on a local model: the dot is red naming the seat, as today.

## Requirements *(mandatory)*

### Functional Requirements

**Elapsed clock**

- **FR-001**: The Demo page's Elapsed figure MUST advance by one for every second of run time while the run is working, in live runs and in replays, with no stretch longer than one second of run time without a change outside a human wait.
- **FR-002**: The figure MUST read 00:00 before the run starts and MUST start counting from the run's start event.
- **FR-003**: The figure MUST freeze while the run waits on the human: from a clarification batch being put to the presenter until the last answer in the batch is submitted; from a blocker being put to the presenter until it is answered; from a presenter Pause until Resume; and from the Handoff approval request until the presenter's decision. It MUST resume from the frozen value when the answering event arrives.
- **FR-004**: The figure MUST stop at the run's final event, whatever the exit, and MUST NOT change afterwards.
- **FR-005**: In replay the figure MUST advance at the chosen speed, and each event MUST set it to the working time the recorded events give at that event.
- **FR-006**: The working time at an event MUST be the time from the run's start event to that event, less the time spent in the human waits of FR-003 before it, taken only from the run's events. Between events the figure MUST add the time since the latest event, scaled by replay speed, unless the run is in a human wait or has ended.
- **FR-007**: The figure MUST NOT decrease during a run.
- **FR-008**: The clock MUST be display only: it MUST NOT emit, record, or send anything, and no stage, card, status, control, or other figure may depend on it. Events stay the only source of run state.
- **FR-009**: Opening or reloading the Demo page during a run MUST show the run's current working time within one second and continue ticking.
- **FR-010**: The termination card's elapsed figure, both while Handoff waits for approval and after the run ends, MUST show the same working time as the clock, worked out from the events by FR-006. The recorded `run.terminated` summary is not changed. The time on each feed card MUST be the working time at its event, so no time on screen disagrees with the clock (owner decision 12).
- **FR-010a**: The Compare strip and the comparison line MUST show each recording's compute time, its working time worked out from its events by FR-006, for both the Team and the Single-model run (owner decision 13). The run timeline PDF MUST print each event's working time, as the feed cards do. The recorded `summary.elapsed_ms` is not changed.

**Pre-flight coverage**

- **FR-011**: The Pre-flight page MUST show one row for every model the Settings menu offers. A cloud model's row MUST make one minimal model call when its provider has a credential, and MUST be not applicable with a line saying the key is missing otherwise; all cloud model calls in a pre-flight MUST run at the same time. A local model's row MUST check that Ollama has the model pulled. The Ollama reachability, Typst, page PNG export, tunnel, disk, and `.env completeness` rows stay. Three rows are added: the Reviewer and the Writer on different model families, worked out from the seats in force when the page loads; the Introduction's public replay recording present on this machine; and every scenario dataset having a recording or golden log to replay, naming any that has neither.
- **FR-012**: A row MUST be red on the Pre-flight page whenever its check failed, whether or not any seat uses it, with one line of detail as today.
- **FR-013**: In Cloud mode every local model row MUST be not applicable, and the Ollama reachability row MUST fail naming any seat still on a local model, as today, else be not applicable.

**Header dot**

- **FR-014**: The header dot on every page MUST be worked out when the page loads from the stored rows and the seats and run mode in force at that moment, not from a status stored with the result.
- **FR-015**: The dot MUST be red when any of these failed: the row of a model a seat is on; Ollama reachability while a seat is on a local model in Laptop mode; a seat on a local model in Cloud mode; the key for a seat's provider; Typst; page PNG export; disk space; and the login pair in Cloud mode only.
- **FR-016**: The dot MUST be amber when nothing in FR-015 failed and any of these failed: the Reviewer and the Writer on the same model family; the Introduction's public replay recording missing; a scenario dataset with nothing to replay; the tunnel not answering while a hostname is set. The amber tooltip MUST name the first of them.
- **FR-017**: The dot MUST be green when nothing in FR-015 or FR-016 failed, even when rows for models no seat uses failed; its tooltip MUST then say how many such rows failed.
- **FR-018**: The dot MUST be grey when no pre-flight has run, and when a seat's model has no stored row and nothing in FR-015 failed; the tooltip names the unchecked seat model.
- **FR-019**: A red tooltip MUST name the first failure that makes it red and, for a model row, the seat that uses it.

**Recheck on a seat change**

- **FR-020**: Every seat change MUST recheck the chosen model's row (a model call for a cloud model; the Ollama reachability row and the pulled row for a local model) and the `.env completeness` row, and MUST store the new rows with the recheck's time. No other row changes.
- **FR-021**: The seat change MUST apply whatever the recheck finds.
- **FR-022**: The Settings status line MUST say that the chosen model is being checked, then give the result in one line. When the recheck finishes the Settings page's header dot MUST update without a reload. Other open pages show the new state on their next load.
- **FR-023**: A recheck MUST be out of band: it adds no event to any run, and it is not counted in any run's meters, cost, recording, metrics, or seat calls. This holds during a live run.
- **FR-024**: A recheck asked for while a full pre-flight is running MUST wait for it to finish and then run.
- **FR-025**: No page, status line, tooltip, stored result, or response MAY contain a credential value (constitution XVII).
- **FR-026**: Neither the Settings page nor the Pre-flight page MAY poll or run a timer to learn a result; each result arrives as the reply to the request that asked for it.

**Controlled documents**

- **FR-027**: Before code changes, the constitution MUST be amended to 1.3.0 with a Sync Impact Report, stating in principle II that the Demo page may show a display-only clock derived from the events; `CLAUDE.md` working rule 3 MUST say the same.
- **FR-028**: `docs/spec-input.md` MUST record the change in sections 2.2 and 2.4 with a version and changelog entry; `docs/design-deviations.md` MUST replace its elapsed meter entry; the S7 decisions superseded here (no recheck after a seat swap; a laptop cannot go green without a login pair) MUST be recorded as superseded.
- **FR-029**: The machine identifiers of the fixed rows (`ollama`, `typst`, `png`, `tunnel`, `disk`, `env`) MUST stay. The per-provider rows are replaced by per-model rows identified by the model's registry key; the stored result's format version changes.

### Key Entities

- **Check row**: one checked thing (a model, Ollama reachability, Typst, PNG export, tunnel, disk, `.env`, the Reviewer and Writer families, the Introduction recording, the replay recordings), its status (pass, fail, not applicable), one line of detail, whether it is a model row and which model, and when it was last checked.
- **Stored pre-flight result**: every check row, the run mode, and when the last full pre-flight ran. It holds no overall status; the header state is never stored.
- **Header state**: derived on every page load from the stored rows, the current seats, and the run mode: green, amber, red, or grey, with a one-line tooltip. Whether a failed row turns the dot red or amber, or not at all, is decided here, never stored with the row.
- **Human wait**: an interval of a run between an event that puts something to the presenter and the event that answers it, taken from events the schema already has.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a browser test over a recorded run at 1x and 4x, Elapsed changes at every one-second step of run time while the run works, and never stays the same for longer than one second of run time outside a human wait.
- **SC-002**: In the same test, Elapsed holds one value for the whole of each human wait and resumes from it within one second of the answering event.
- **SC-003**: At run end Elapsed equals the working time the events give, to the second, and is unchanged ten seconds later.
- **SC-004**: With one unused cloud model failing and every other check passing, the model's row is red on the Pre-flight page and the header dot is green on Demo, Settings, Pre-flight, and Introduction.
- **SC-005**: Moving a seat onto a failing model turns the Settings header dot red within one probe's time limit (35 seconds at most) without a full pre-flight, and moving it back returns the dot to green.
- **SC-006**: A full pre-flight on the presenter laptop with every model in the Settings menu still ends within 60 seconds.
- **SC-007**: The golden replay suite passes unchanged, and a live run with a seat change mid-run has the same event types and counts as without the recheck, apart from the `model.changed` event the swap already emits.
- **SC-008**: A planted marker in `.env` appears in no page, status line, tooltip, stored result, or response.
- **SC-009**: On the presenter laptop in Laptop mode, with a Gemini model failing that no seat uses and no login pair in `.env`, the header dot is green.
- **SC-010**: Each of the four amber conditions, tested on its own with every red condition passing, turns the header dot amber and never red.
- **SC-011**: For every recorded run with a human wait, the termination card's figure equals the final Elapsed value.
- **SC-012**: For every golden log, the server's working time equals the page's final Elapsed value, and a Team recording with a human wait shows a Compare strip time shorter than its total time by the length of the wait.

## Assumptions

- Seats live in memory and return to their configured models when the server restarts. Working the dot out on every page load keeps it right without a rerun.
- The probe is the existing minimal call that asks for one word; a full pre-flight makes six today (three Bedrock, two Gemini, one Grok), each costing a fraction of a cent.
- No event, event type, or payload field changes. The human waits are read from events schema 1.1.0 already has (`clarification.asked`, `clarification.answered`, `run.paused`, `run.resumed`, `handoff.ready`, `run.terminated`), so no golden log is re-recorded and the schema version stays.
- The clock keeps the export's MM:SS form; a run over an hour reads 60:00 and above.
- Only the Settings page updates its dot in place. Pushing pre-flight state to other open pages would need a timer or a new stream, and is not built.
- The Single-model choice in the composer is not a seat, so a failure on that model shows on the Pre-flight page only.
- The stored result's format changes, so a result written before this change reads as "not run yet".
- Why the Gemini 2.5 Pro entry fails its probe (`NotFoundError`) is a model registry question for a separate change; this feature only stops it from turning the dot for demos that do not use it.

## Out of scope

- A button to test one row, automatic retries of a failed probe, or scheduled pre-flights.
- Probing a local model with a model call; a local row checks that the model is pulled.
- Any change to the event schema, the recorded runs, or the golden logs.
- Pushing the header state to pages other than Settings without a reload.
