# Feature Specification: Event spine and stubbed loop (slice S1)

**Feature Branch**: `001-event-spine-stubbed-loop`

**Created**: 2026-09-14

**Status**: Draft

**Input**: User description: "Slice S1, Event spine and stubbed loop, as written in docs/roadmap.md, with the referenced sections of docs/spec-input.md version 0.5 (2.2, 2.5, 2.10, 3, 4.1 to 4.3, 6, 7, 9 M1, 10 criteria 2, 3, 4, 11), design/README.md deviations and handling rules, and datasets/*/README.md expected sequences and exits."

**Governing documents**: `docs/spec-input.md` 0.5 for behaviour, `design/` for appearance, `.specify/memory/constitution.md` 1.1.1, `docs/roadmap.md` for the slice boundary and the five pre-S1 decisions. Where this specification restates those documents it does so for testability; where it is silent, they govern.

## Purpose of the slice

S1 lays the one frozen horizontal foundation, the typed event schema, and proves the whole demo surface on top of it without a single model call. The presenter can open the Demo page, pick any of the six scenario datasets, press Run, and watch a complete run play from stubbed agents: the loop strip lights stage by stage, the feed fills with message cards, the meters accumulate, the raw drawer shows the event stream, and the run ends on a termination card with the expected exit. Every recorded run replays at 1x or 4x and looks identical to the live stubbed run. The four Demo states in the design export (idle, running, paused, terminated) all appear on cue. Login, Settings, and Pre-flight exist as static pages that match the export. The quality gates that every later slice must pass are in place.

Nothing in this slice calls a model. Real agents arrive in S2.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run a stubbed scenario and watch the loop (Priority: P1)

The presenter opens the Demo page, selects a scenario dataset from the composer, and presses Run. Stubbed agents emit the scenario's canned event sequence through the Orchestrator. The presenter sees the loop strip light each stage as it is entered, the feed fill with cards for every event, the meters accumulate per agent and per run, the raw drawer list every event as JSON, and the run end on a termination card that states the exit and the Orchestrator's reason. For scenarios that pause for the human (a blocking clarification, a blocker), the presenter answers or escalates from the page and the run continues or ends accordingly. For scenarios that reach Handoff, the presenter presses Approve and the run terminates.

**Why this priority**: This is the slice outcome. Without it nothing is demonstrable and no later slice has a surface to land on.

**Independent Test**: Start the application with no model credentials configured. Run each of the six datasets to termination, acting at every human touchpoint. Each run ends on the termination exit its dataset README states, and every element on the page can be traced to a specific event in the raw drawer.

**Acceptance Scenarios**:

1. **Given** the Demo page in the idle state, **When** the presenter selects Clean run and presses Run, **Then** the loop strip lights Intake, Plan, Work, Assemble, Review, Handoff in that order, the feed shows one thread per sub-task with Pricing visibly waiting on Estimator, a plan card lists three sub-tasks with Assemble assigned to the Writer, the Reviewer's verdict card shows pass, and the termination card renders from `handoff.ready` with exit reviewer_pass and retry count 0.
2. **Given** a Clean run at Handoff, **When** the presenter presses Approve, **Then** a `human.approved` event with decision approve is recorded, `run.terminated` follows with exit reviewer_pass and human decision approve, the termination card closes with that decision, and no further event arrives.
3. **Given** Planted inconsistency selected, **When** the run reaches Intake and raises a blocking clarification, **Then** the run pauses, the Intake node shows the paused treatment from the export, the waiting-on-you banner shows the batched questions with editable pre-filled defaults, and no new dispatch occurs until the presenter submits.
4. **Given** the run paused on the banner, **When** the presenter submits answers, **Then** `clarification.answered` events with actor human are recorded, `knowledge.appended` follows for each Intake clarification, the run resumes, and the banner disappears.
5. **Given** Planted inconsistency running past Intake, **When** the Reviewer fails version 1 with a major finding routed to the Estimator, **Then** the Review to Work backward arrow animates once, the retry badge on Review reads 1 of 2, the Estimator receives a rework thread, version 2 is committed, the Reviewer passes, and the run reaches Handoff with retry count 1.
6. **Given** Missing sheet running in Work, **When** the Estimator raises a blocker that needs a human, **Then** the run pauses, a blocker card visually distinct from other cards offers Answer and Escalate, and the composer shows the paused state.
7. **Given** the blocker card on screen, **When** the presenter presses Escalate, **Then** a `clarification.answered` event with action escalate is recorded, `run.terminated` follows with exit blocker_escalated, and the termination card lists the missing sheet under what is missing.
8. **Given** Missing price selected, **When** the run completes, **Then** the Pricing thread shows an exception for the unpriced item, the Reviewer verdict passes with one minor finding, and the termination card carries that finding as a note.
9. **Given** Not ready selected, **When** the run starts, **Then** Intake reports verdict not ready with the checklist graded item by item, the run terminates before Plan with exit not_ready, and the termination card lists the deadline and the specification as missing.
10. **Given** Prospect own selected, **When** the run starts, **Then** the stub performs a dry intake: Intake produces a brief and readiness verdict, and the run terminates with exit dry_intake and the verdict on the termination card, without entering Plan.
11. **Given** any run, **When** it terminates, **Then** `run.terminated` is the last event in the feed, the raw drawer, and the recording.
12. **Given** any agent message in the feed, **When** the presenter clicks its prompt toggle, **Then** a read-only panel expands showing the stored prompt bundle for that call sectioned as system instructions, context slice, task, tools available, and model used.
13. **Given** any Orchestrator event in the feed, **When** the presenter clicks it, **Then** its one-sentence reason is shown.
14. **Given** a new run, **When** the roster is announced in `run.started`, **Then** each seat carries one of its two names chosen at random with the matching initials avatar, and the same name is used everywhere for that run.

---

### User Story 2 - Replay a recorded run at 1x or 4x (Priority: P1)

Every run is recorded. The presenter selects a dataset, presses Replay, and chooses 1x or 4x. The page plays the most recent recording for that dataset (or the dataset's golden log if no recording exists) with the original event identities and the original relative timing scaled by speed. The display is indistinguishable from the live stubbed run.

**Why this priority**: Replay is the demo-day safety net and the proof that the UI renders only from events (constitution II and VIII, acceptance criterion 2).

**Independent Test**: Run Clean run live, then Replay it at 4x. Capture the final page state of both. They match element for element, and the two event lists are identical apart from timestamps.

**Acceptance Scenarios**:

1. **Given** a completed Clean run, **When** the presenter presses Replay at 1x, **Then** the same events arrive in the same order with the same `run_id` and `event_id` values and gaps between events matching the original within one second each.
2. **Given** the same recording, **When** replayed at 4x, **Then** every gap is one quarter of the original and the final page state is identical to the 1x replay.
3. **Given** a dataset that has never been run, **When** the presenter presses Replay, **Then** the dataset's golden log plays.
4. **Given** a replay in progress, **When** a human touchpoint is reached, **Then** the recorded human events play without waiting for input, and the banner and blocker card show what was answered.
5. **Given** any replay, **When** it finishes, **Then** no new recording is written and the recording folder count is unchanged.

---

### User Story 3 - Golden logs and the replay-and-compare suite (Priority: P1)

The owner needs proof, not a demo that happened to work once. Every dataset ships with a golden event log. An automated suite runs each scenario through the stubbed Orchestrator, records it, and compares the recorded stage sequence and termination exit against the golden log. The suite is the completion evidence for this slice and the harness every later slice reuses.

**Why this priority**: Constitution XIII makes the golden log the completion evidence; roadmap S1 lists six committed golden logs and a green suite as evidence.

**Independent Test**: Run the suite from a clean checkout. It passes for all six datasets. Change one stub so a run skips Plan; the suite fails for that dataset naming the divergence.

**Acceptance Scenarios**:

1. **Given** the six golden logs, **When** the suite runs, **Then** every scenario's live stubbed run matches its golden stage sequence (the ordered list of `stage.changed` transitions) and its termination exit.
2. **Given** a golden log, **When** validated against the schema, **Then** every event passes envelope and payload validation, `seq` is strictly increasing from 1, and the last event is `run.terminated`.
3. **Given** the golden log for Planted inconsistency, **When** inspected, **Then** it contains exactly one backward `stage.changed` from Review to Work and one `retry.incremented` with count 1.
4. **Given** the golden log for Missing sheet, **When** inspected, **Then** it records the Escalate path and ends with exit blocker_escalated.
5. **Given** a deliberately corrupted stub, **When** the suite runs, **Then** the failing dataset is named with the first point of divergence.

---

### User Story 4 - The Demo page matches the design export (Priority: P2)

The Demo page is the design export flattened to static markup, one stylesheet, and plain scripts, with the design-time state switcher and sample data removed. Side by side with the export at 1920 by 1080, each of the four states shows no visible difference.

**Why this priority**: Constitution XVIII and spec 2.10 make the export the appearance; acceptance criterion 3 requires the comparison. It is P2 only because a pixel-faithful page with no events behind it demonstrates nothing.

**Independent Test**: Capture the flattened Demo page in each of the four states driven by events, and the export in the same four states driven by its switcher. Compare each pair at 1920 by 1080.

**Acceptance Scenarios**:

1. **Given** the export's missing captures (Demo idle, running, paused, chat panel open), **When** S1 captures them from the export files, **Then** they are stored alongside the existing screenshots and named for their state.
2. **Given** the flattened Demo page in each state, **When** compared with the corresponding capture, **Then** no visible difference is found at 1920 by 1080.
3. **Given** the flattened page, **When** inspected, **Then** no state switcher, sample feed text, or inline demo data is present; the scenario 2 sample copy exists only as the scenario 2 stub fixture.
4. **Given** the composer, **When** the page loads, **Then** Run and Replay with speed are live; Pause, Stop, Dry intake, and the Single model switch are present and disabled, not hidden; Approve is live at Handoff; Edit and Reject are present and disabled.
5. **Given** the header, **When** any page loads, **Then** it shows the product name, page navigation, the pre-flight indicator in its pending state, and the build stamp with the git hash and date in the Settings style.
6. **Given** the loop strip, **When** a backward `stage.changed` fires for any of the three backward routes, **Then** that arrow receives the fired treatment the export gives the Review to Work arrow.
7. **Given** the artifact panel, **When** any run is in progress, **Then** it shows a placeholder stating that compiled output arrives in S4.

---

### User Story 5 - Login, Settings, and Pre-flight as static pages (Priority: P3)

Sales staff and the owner can open every page of the application. Login, Settings, and Pre-flight are flattened from the export and match their screenshots. They carry the shared header. Their controls do nothing yet beyond navigation: Login's Sign in leads to the Demo page, Settings shows the default roster with the model dropdown rendered but inert, Pre-flight shows the eight checks in the pending state.

**Why this priority**: Completes the page set so the four screens can be compared (criterion 3 except Introduction) and the nav works, but nothing behind them is live until S5 and S7.

**Independent Test**: Open each page, compare with its screenshot at 1920 by 1080, and follow every nav link.

**Acceptance Scenarios**:

1. **Given** Login, **When** compared with `Login.png`, **Then** no visible difference; pressing Sign in reaches the Demo page.
2. **Given** Settings, **When** compared with `Settings.png`, **Then** no visible difference apart from the dropdown being closed; each row shows the agent card with the default model label.
3. **Given** Pre-flight, **When** compared with `Preflight.png` and the pending state capture, **Then** no visible difference; the Run button is disabled.

---

### User Story 6 - Quality gates (Priority: P2)

Every change is checked automatically: tests, static type checking, linting, an em-dash lint over the repository and generated output, and a test that no event payload or prompt bundle contains a value from `.env`. A dependency rationale record opens with this slice.

**Why this priority**: Constitution XVI makes a slice incomplete while any gate is red, and XV requires the rationale record.

**Independent Test**: Run the gate command from a clean checkout; all pass. Insert an em dash into a content file and a run recording; the lint fails naming both.

**Acceptance Scenarios**:

1. **Given** the repository, **When** the em-dash lint runs, **Then** it scans every tracked text file and every file under the recordings folder and fails on the first em dash found, printing the path and line.
2. **Given** a run recording, **When** the leak test runs with a `.env` containing a known marker value, **Then** it fails if the marker appears in any event or prompt bundle.
3. **Given** the schema models and the Orchestrator, **When** the type checker runs, **Then** it reports no errors.
4. **Given** the dependency record, **When** read, **Then** it has an entry for each major dependency introduced in S1 stating the problem it solves and the cost of doing without it.

---

### Edge Cases

- Run pressed while a run is in progress: the composer refuses with Run disabled during a run; a second run never starts.
- Replay pressed during a live run: disabled until the run terminates.
- A dataset whose folder has no golden log and no recording: Replay is disabled for that dataset with a visible reason.
- The presenter reloads the page mid-run: the page reconnects to the stream and rebuilds from the run's events so far; nothing is inferred from timers.
- The stream disconnects and reconnects: events resume from the last `seq` received, no duplicate cards.
- A stub emits an event that fails schema validation: the run terminates with exit stopped and the reason names the validation failure; the invalid event is never recorded.
- The retry budget is exhausted in a stub sequence: the state machine exits retry_exhausted through Handoff (covered by a unit test, not a shipped scenario).
- Cost ceiling breached by stub meter deltas: the state machine terminates with cost_ceiling before any further dispatch (unit test).
- Stop and Pause: the state machine supports both and emits their events; the composer buttons stay disabled in S1.
- A second Work to Intake route in one run: becomes a blocker (unit test).
- Answer on a blocker card: resumes at Work with the answer in the specialist's context; the S1 stub for Missing sheet records only the Escalate path in its golden log, but Answer works against the stub and continues to a pass.
- Two runs of the same dataset: the second run's roster may carry different names, since names are chosen at random per run.

## Requirements *(mandatory)*

### Functional Requirements

Schema and models

- **FR-001**: The event schema in spec section 6 MUST be published as a versioned document (version 1.0.0) plus typed models with validators for the envelope and every payload, including the eight exit values, the structured termination summary with `readiness_verdict`, and the prompt bundle. It is frozen at this version; changes go through the constitution amendment procedure.
- **FR-002**: Every event MUST validate before it is emitted, recorded, or rendered. `seq` starts at 1 and increases by one per run. `stage` is null for `run.started`, `run.terminated`, and every event of a Single-model run.
- **FR-003**: Every Orchestrator event MUST carry a one-sentence reason. Every agent message MUST carry a `prompt_ref` that resolves to a stored prompt bundle.

Orchestrator

- **FR-004**: The Orchestrator MUST be the only component that changes stage, dispatches work, presents questions to the human, appends to the knowledge file, tracks the retry budget, pauses or resumes, and terminates a run.
- **FR-005**: The Orchestrator MUST implement the six stages, the three backward routes, the review retry budget (default two, configurable), the Work to Intake cap of one per run (a second attempt becomes a blocker), the Handoff sequence (`handoff.ready`, `human.approved`, `run.terminated` with the same exit), pause gating (no new dispatch, in-flight work completes), and the cost ceiling check after every `meter.update`.
- **FR-006**: The Orchestrator MUST support all eight exits: reviewer_pass, retry_exhausted, blocker_escalated, not_ready, cost_ceiling, stopped, single_complete, dry_intake. `run.terminated` MUST be the last event of every run and its summary MUST be structured per the schema.
- **FR-007**: Blocking clarifications MUST be batched into one `clarification.asked` and pause the run; non-blocking ones MUST proceed on the default with `assumption.accepted`. Intake clarification answers MUST be followed by `knowledge.appended`; blocker answers MUST NOT be.
- **FR-008**: A blocker with `needs_human` MUST pause the run with `clarification.asked` carrying the blocker; Answer resumes at Work with the answer in the specialist's context; Escalate terminates with blocker_escalated and a structured missing list.
- **FR-009**: The plan MUST list the specialist sub-tasks plus Assemble assigned to the Writer, each with agent, dependencies, and visibility scope. Independent sub-tasks run concurrently; dependent ones wait, and the wait is visible in the feed.

Stubbed agents and scenarios

- **FR-010**: Stubbed agents MUST emit canned event sequences for all six datasets with no model calls. Scenario 2 MUST use the sample transcript from the design export as its fixture; the other five MUST use minimal plausible text marked as fixture.
- **FR-011**: Each stubbed run MUST reach the exit its dataset README states: Clean run reviewer_pass with retry 0; Planted inconsistency reviewer_pass with retry 1 after one Review to Work rework; Missing sheet blocker_escalated via the Escalate action; Missing price reviewer_pass with one minor finding; Not ready not_ready with the deadline and specification listed as missing; Prospect own dry_intake with the readiness verdict.
- **FR-012**: Stubs MUST emit `task.progress`, `tool.called`, and per-call `meter.update` with fixture token counts and costs so threads, provenance inputs, and meters have data.
- **FR-013**: Every stub call MUST store a prompt bundle (system, context slice, task, tools, model) so the prompt toggle shows a real bundle.
- **FR-014**: Each run MUST choose one of the two names per seat at random and use the matching initials avatar consistently across every card for that run.

Stream, recording, replay

- **FR-015**: Events MUST reach the page over a live stream in order, with reconnection resuming from the last received `seq` without duplicates.
- **FR-016**: Every run MUST be recorded as an ordered event list plus prompt bundles under a per-run folder. Replay MUST NOT write a recording.
- **FR-017**: Replay MUST re-emit the recorded events verbatim over the same stream with the original `run_id` and `event_id` values, at the original relative timing scaled by 1x or 4x, playing the most recent recording for the selected dataset or, failing that, the dataset's golden log.
- **FR-018**: The page MUST render identically from a live stubbed run and from its replay.

Demo page

- **FR-019**: The Demo page MUST be flattened from the export per spec 2.10: static markup, one stylesheet with classes derived from the inline styles, plain render functions driven by events, no design runtime, no state switcher, no sample data.
- **FR-020**: The UI MUST render only from events. It MUST NOT infer state, run timers to guess progress, or hardcode stage transitions.
- **FR-021**: The loop strip MUST light from `stage.changed` only; each of the three backward arrows MUST animate once with the fired treatment when its backward transition fires; the Review node MUST show the retry badge from `retry.incremented`; the paused treatment MUST follow the export (coral with the exclamation glyph).
- **FR-022**: The feed MUST render every card kind: orchestrator note, agent message, assumption, question, human answer, specialist thread with progress and tool-call replies, plan card, draft committed, verdict with severity-coded findings, termination, and a new blocker card in the export's card family with a red left border and Answer and Escalate actions. Threads auto-expand while active and collapse to one line on completion. Clarification, assumption, and blocker cards are visually distinct.
- **FR-023**: Every agent message MUST show the agent card (avatar, name and role, model label in grey) and a prompt toggle. Orchestrator events MUST show their reason on click.
- **FR-024**: The composer MUST offer the dataset dropdown, workflow selector, run mode switch, Dry intake toggle, Run, Pause, Stop, Replay, and speed. In S1 Run, Replay, and speed are live; Pause, Stop, Dry intake, and Single model are disabled, not hidden.
- **FR-025**: The waiting-on-you banner MUST appear when the run is paused for human input, with the batched questions and an answer form whose proposed defaults are pre-filled and editable; submitting records one `clarification.answered` per question.
- **FR-026**: The termination card MUST render from `handoff.ready` with Approve live when Handoff is entered, and from `run.terminated` for every other exit, listing what is missing for not_ready and blocker_escalated and the readiness verdict for dry_intake. Edit, Reject, Download PDF, and Download run timeline are present and disabled in S1.
- **FR-027**: The meters strip MUST accumulate per-agent tokens and cost from `meter.update` deltas, show elapsed time from event timestamps, the run total, and a per-agent detail row (calls, tokens in and out, cost, wall time, last event) on click. The comparison line and ceiling indicator render their empty states.
- **FR-028**: The raw turns drawer MUST list every event of the run as JSON, collapsed by default.
- **FR-029**: The artifact panel MUST show a placeholder stating that compiled output arrives in S4. The Compare strip MUST show its empty state. The chat panel markup MUST be present and disabled.
- **FR-030**: Every page header MUST show the product name, navigation, the pre-flight indicator in its pending state, and the build stamp (git hash and date) in the Settings style. The Demo header adds the workflow selector.

Other pages

- **FR-031**: Login, Settings, and Pre-flight MUST be flattened from the export as static pages sharing the header. Login's Sign in navigates to Demo. Settings shows the default roster with inert dropdowns. Pre-flight shows eight checks pending with Run disabled.

Evidence and gates

- **FR-032**: Each dataset MUST ship a golden event log produced by the stub and validated against the schema.
- **FR-033**: A replay-and-compare suite MUST run every scenario through the stubbed Orchestrator and compare the stage sequence and termination exit against the golden log, naming the first divergence on failure.
- **FR-034**: The missing export captures (Demo idle, running, paused, chat panel) MUST be produced from the export files, and a screenshot comparison MUST pass for Demo in four states, Login, Settings, and Pre-flight at 1920 by 1080.
- **FR-035**: Quality gates MUST run on every change: tests, static type checking over at least the schema models and Orchestrator, linting, an em-dash lint over every tracked text file and every recording, and a test that no `.env` value appears in any event or prompt bundle.
- **FR-036**: A dependency rationale record MUST exist with an entry for each major dependency introduced in S1.
- **FR-037**: No file, comment, prompt, fixture, or rendered copy in this slice MAY contain an em dash.

### Key Entities

- **Event**: One typed, validated record in a run. Envelope: id, run id, sequence number, timestamp, type, stage or null, actor, reason (Orchestrator), prompt reference (agent messages), payload. The only thing the UI, recorder, replayer, meters, and tests consume.
- **Run**: An ordered list of events from `run.started` to `run.terminated`, identified by run id, with a workflow, dataset, mode, and roster. Recorded under its own folder with prompt bundles.
- **Stage**: One of intake, plan, work, assemble, review, handoff. Changed only by the Orchestrator through `stage.changed`.
- **Exit**: One of the eight termination values. Four narrative, four control.
- **Agent card**: Seat identity (avatar, name, role) plus the runtime model object (provider, model id, label). Name chosen per run from the seat's two options.
- **Prompt bundle**: Stored per call; system, context slice, task, tools, model. Referenced by `prompt_ref`.
- **Scenario dataset**: A folder with README, brand, and golden log; in S1 no inputs or fixtures beyond text.
- **Golden event log**: The expected recorded run for a dataset; compared on stage sequence and exit only.
- **Recording**: A run's persisted events and bundles; the source for Replay.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All six datasets run to their expected exit from the Demo page with no model credentials configured, in under three minutes each at 1x.
- **SC-002**: A live stubbed run and its 4x replay produce the same final page state and the same event list apart from timestamps, for all six datasets.
- **SC-003**: The replay-and-compare suite passes for six of six golden logs from a clean checkout, and fails naming the divergence when one stub is altered.
- **SC-004**: The screenshot comparison shows no visible difference at 1920 by 1080 for seven captures: Demo idle, running, paused, terminated, Login, Settings, Pre-flight.
- **SC-005**: The last event of every recording is `run.terminated`, checked by the suite over every recording produced during the test run.
- **SC-006**: Every element that changes on the Demo page during a run can be attributed to a single event in the raw drawer; a reviewer sampling twenty elements finds zero exceptions.
- **SC-007**: The em-dash lint finds zero occurrences across the repository and all recordings, and every quality gate is green.
- **SC-008**: Every agent message in every scenario has a working prompt toggle showing a bundle with all five sections populated.
- **SC-009**: The presenter can reach any control needed during a run in one click, with no dialog or nested menu.

## Assumptions

- The five pre-S1 decisions in `docs/roadmap.md` are in force: exit `dry_intake`, the composer Dry intake toggle, git initialised with the baseline committed, Replay source as the most recent recording falling back to the golden log, Python 3.13.
- Human actions needed to finish a stubbed run are live in S1 against the stubs: the banner answer form, Answer and Escalate on the blocker card, and Approve at Handoff. The roadmap's deferral of "blocker actions in live form" to S3 refers to their operation against real agents. Without these, the Paused state could not be resolved and the Missing sheet golden log could not record the Escalate path.
- The Prospect own dataset has no inputs, so its S1 stub performs a dry intake and exits `dry_intake`. This exercises the eighth exit and the dry-intake termination card without the composer toggle, which stays disabled until S3. The golden log is replaced in S9.
- The Missing sheet stub takes the Estimator blocker path, not the Intake not_ready path; the golden log records this per the dataset README's instruction to document which path was taken.
- Stub events carry fixture timestamps: each stub event has an offset from run start (the scenario 2 offsets match the design export's card times), the recorded timestamp is run start plus that offset, and the stub emits with a configurable pacing factor (default four times faster than the offsets) so a full run stays under three minutes. Replay honours the recorded gaps scaled by the chosen speed. With real agents from S2, timestamps are wall time.
- Stub meter values are plausible fixture numbers and are labelled as such in the stub fixtures; they exist so the meters have data, not to represent real cost.
- Screenshot comparison tolerates differences caused only by the random roster name and by timestamps; the comparison run pins both.
- The export captures for Demo idle, running, paused, and chat are taken by rendering the export bundles in a browser with their design-time switches, before the comparison.
- Settings dropdown lists and Pre-flight checks are rendered from the export's static content in S1; they become live in S5 and S7.
- The build stamp reads the git hash and commit date at startup; a checkout without git shows "no git" in the same style.
- The knowledge file for stub runs is a per-run copy of the dataset's `knowledge.seed.md` when present, otherwise an empty file, so `knowledge.appended` has somewhere to write without polluting datasets.
- Login is a static page in S1; nothing is protected until S7.

## Out of scope for this slice

Real agents and model calls, provider registry, Pause and Stop as live controls, Dry intake as a live control, compiled pages and provenance hover, Settings behaviour, Single-model mode, chat, the Introduction tab, login enforcement, live pre-flight, tunnel, leave-behind. See `docs/roadmap.md` S2 to S9.
