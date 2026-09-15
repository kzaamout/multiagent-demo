# Feature Specification: Failure paths and presenter controls (slice S3)

**Feature Branch**: `003-failure-paths-controls`

**Created**: 2026-09-15

**Status**: Draft

**Input**: User description: "Slice S3, Failure paths and presenter controls, exactly as written in docs/roadmap.md, plus the roadmap decisions 1 to 15 that bear on it, with docs/spec-input.md 0.6 sections 2.2 (composer controls, blocker card, termination card), 3 (global rules, stages 3, 5, 6, exits, cost ceiling), 6, 7 scenarios 2 to 5, 9 M3, and config/electrical-rfp/reviewer-criteria.md, estimating-conventions.md blocker rules, readiness-checklist.md. The four failure datasets are derived by the implementer from the synthetic Clean run dataset (owner instruction 2026-09-15), each with its planted defect documented in its README."

**Governing documents**: `docs/spec-input.md` 0.6, `.specify/memory/constitution.md` 1.1.1, `docs/roadmap.md` (S3 entry and decisions 1 to 15), `docs/schema/events-v1.0.0.md` (frozen), `config/electrical-rfp/`, `docs/design-deviations.md`.

## Purpose of the slice

S2 proved the team on a request that goes right. S3 proves the loop when things go wrong, which is the part a prospect remembers: a Reviewer that sends work back and a retry badge that ticks, a blocker that pauses and asks, a request that is stopped in seconds because it is not ready, a missing price that is disclosed rather than invented. It also gives the presenter control of a live run: Pause, Stop, Dry intake, and a cost ceiling that ends a run before it overspends.

The run engine from S1 already implements these paths on stubbed agents. S3 makes them work with live agents on real inputs, turns on the controls that are disabled today, and derives the four failure datasets from the Clean run set.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The Reviewer sends work back and the second draft passes (Priority: P1)

The presenter runs Planted inconsistency. The panel schedule states a 200 A main breaker where the single-line shows 225 A. The Estimator proceeds on the single-line value and flags the disagreement. The Reviewer fails draft v1 on the contradiction and routes it to the Estimator, the Review to Work arrow fires, the retry badge reads 1 of 2, the Estimator reworks with the finding in its context and confirms the value, the Writer assembles v2, and v2 passes.

**Why this priority**: It is the primary live demo dataset and the clearest proof that review is real.

**Independent Test**: Run Planted inconsistency live, approve at Handoff, and compare the recording with the dataset's golden log on stage transitions and exit.

**Acceptance Scenarios**:

1. **Given** the Planted inconsistency dataset, **When** the Reviewer returns a fail with a major finding routed to the Estimator, **Then** the run records one backward change from Review to Work with a reason, the retry counter becomes 1, and only the Estimator is dispatched for rework with the finding in its context.
2. **Given** the rework output, **When** the Writer assembles and the Reviewer judges v2, **Then** a pass takes the run to Handoff and the exit is reviewer_pass with retry count 1.
3. **Given** a fail routed to Assemble instead, **When** the budget allows, **Then** only the Writer reworks, with the findings in its context.
4. **Given** a third failed review, **When** the budget of two is spent, **Then** the run goes to Handoff with exit retry_exhausted and the unresolved findings listed.

---

### User Story 2 - A blocker pauses the run and asks (Priority: P1)

The presenter runs Missing sheet. The single-line shows a panel whose schedule is not in the drawing set. Intake records it as a concern for the Estimator and proceeds. The Estimator raises a blocker. The run pauses and the blocker card offers Answer and Escalate. Escalate ends the run with a card that lists exactly what is missing. Answer resumes Work with the answer in the Estimator's context.

**Why this priority**: It is the "what happens when it goes wrong" answer and an acceptance criterion.

**Independent Test**: Run Missing sheet live and press Escalate; the run ends with exit blocker_escalated and the card names the missing schedule and its panel. Run it again and answer instead; the Estimator continues with the answer and the run proceeds.

**Acceptance Scenarios**:

1. **Given** a blocker that needs a human, **When** it is raised, **Then** the Orchestrator asks with the blocker attached, the run pauses, and the blocker card shows the description, the reason, an answer field, Answer, and Escalate.
2. **Given** the blocker card, **When** the presenter chooses Escalate, **Then** the run ends with exit blocker_escalated and the termination card lists the missing items from the structured summary.
3. **Given** the blocker card, **When** the presenter answers, **Then** the run resumes at Work with the answer in the blocked specialist's task, the answer stays in this run's brief for the seats that see the brief, and it is not written to the client knowledge file.
4. **Given** a specialist that finds the brief incomplete, **When** it routes back to Intake for the first time in the run, **Then** Intake runs again once; a second route back becomes a blocker.

---

### User Story 3 - A request that is not ready stops in seconds (Priority: P1)

The presenter runs Not ready. The request has no submission deadline and no Division 26 specification although the scope refers to specifications. Intake returns Not ready and the run ends before Plan with both items listed.

**Why this priority**: It is the "what if our RFP is a mess" answer, and the cheapest failure to show.

**Independent Test**: Run Not ready live; the run ends with exit not_ready, no specialist is dispatched, and the card lists the deadline and the specification.

**Acceptance Scenarios**:

1. **Given** the Not ready dataset, **When** Intake grades it, **Then** the verdict is not_ready with a note for each failing blocking item.
2. **Given** a not_ready verdict, **When** the Orchestrator reads it, **Then** the run terminates with exit not_ready before Plan and the card lists each missing item.

---

### User Story 4 - A missing price is disclosed, not invented (Priority: P2)

The presenter runs Missing price. One material the drawings require is absent from the supplier price list. Pricing lists it as an unpriced exception, the Writer states it as an exclusion with its reason, the Reviewer records at most a minor finding, and the run passes with the note carried to Handoff.

**Why this priority**: It shows honesty under a gap, but the loop shape is the same as Clean run.

**Independent Test**: Run Missing price live; the exit is reviewer_pass with retry count 0, the priced bill of materials shows the item as unpriced, and the draft names it as an exclusion.

**Acceptance Scenarios**:

1. **Given** the Missing price dataset, **When** Pricing looks up the bill of materials, **Then** the missing material is an unpriced exception and no substitute price appears.
2. **Given** the exception, **When** the Writer assembles, **Then** the draft lists it under exclusions and the total excludes it.
3. **Given** minor findings on a passing draft, **When** the run reaches Handoff, **Then** the notes are listed on the termination card.

---

### User Story 5 - Pause and Stop a live run (Priority: P1)

During any run the presenter can pause dispatch, resume, or stop.

**Why this priority**: Presenter safety on a live stage, and an acceptance criterion for Stop.

**Independent Test**: Start a live run, press Pause during Work, confirm no new sub-task starts while paused, press Resume, then press Stop; the run ends with exit stopped and its last event is the termination.

**Acceptance Scenarios**:

1. **Given** a run in progress, **When** the presenter presses Pause, **Then** the Orchestrator records the pause with a reason, calls already in flight complete, and nothing new is dispatched until Resume.
2. **Given** a paused run, **When** the presenter presses Resume, **Then** the Orchestrator records the resume with a reason and dispatch continues.
3. **Given** a run in progress or paused, including one waiting on a question or a blocker, **When** the presenter presses Stop, **Then** the run ends with exit stopped and the termination card says the presenter stopped it.
4. **Given** no run in progress, **When** the page is idle or a run has ended, **Then** Pause and Stop are disabled.

---

### User Story 6 - Dry intake before a meeting (Priority: P2)

The presenter switches Dry intake on and runs a dataset. The run stops after Intake whatever the verdict, and the card shows the readiness verdict.

**Why this priority**: It is how the Prospect own slot is prepared, and it costs nothing but the Intake call.

**Independent Test**: Turn Dry intake on, run Clean run; the run ends after Intake with exit dry_intake and the card shows the readiness verdict.

**Acceptance Scenarios**:

1. **Given** Dry intake on, **When** Intake finishes with any verdict, **Then** the run ends with exit dry_intake and the summary carries the verdict.
2. **Given** Dry intake off, **When** a run starts, **Then** the run proceeds normally.

---

### User Story 7 - A cost ceiling stops a run before it overspends (Priority: P2)

The per-run cost ceiling is checked after every usage record. On breach the run ends with exit cost_ceiling before anything further is dispatched.

**Why this priority**: The owner's assurance against a large bill, and a roadmap evidence item.

**Independent Test**: Start a run with a ceiling below the Estimator's first call; the run ends with exit cost_ceiling, no sub-task is dispatched after the breach, and the card states the ceiling and the spend.

**Acceptance Scenarios**:

1. **Given** a ceiling, **When** a usage record takes the estimated spend past it, **Then** the run ends with exit cost_ceiling and no further dispatch or model call starts.
2. **Given** the meters strip, **When** a run is live, **Then** the ceiling indicator shows spend against the ceiling.

---

### User Story 8 - Four failure datasets derived from Clean run (Priority: P1)

Each failure dataset starts from the Clean run inputs and changes only what its scenario needs, and its README says exactly what was planted and where.

**Why this priority**: Without them no failure path can be shown live.

**Independent Test**: For each dataset, integrity tests confirm the planted defect is present, everything else matches Clean run, and every page is legible.

**Acceptance Scenarios**:

1. **Given** Planted inconsistency, **Then** exactly one rating disagrees between the single-line and the panel schedule, and the README names both sheets and both values.
2. **Given** Missing sheet, **Then** a panel on the single-line has no schedule in the set, and the README names the panel and the absent sheet.
3. **Given** Missing price, **Then** exactly one scheduled material is absent from the price list, and the README names it.
4. **Given** Not ready, **Then** the request has no submission deadline and no specification document while its scope refers to specifications, and the README says so.

---

### Edge Cases

- Stop arrives while a model call is in flight: the run ends with exit stopped; the call's late result is discarded and never reaches the event stream.
- Stop arrives while the run waits on a clarification, a blocker, or Handoff: the run ends with exit stopped and no answer or decision is recorded.
- Pause arrives while the run waits on a human: the run is already paused for input; Pause has no further effect and Resume does not answer the question.
- The Reviewer routes a finding to a specialist who cannot fix it, for example Pricing when a description is wrong: the rework runs, the retry counts, and the run may end retry_exhausted. The engine does not second-guess the route.
- A blocker that does not need a human: the specialist proceeds on its stated rule and the blocker becomes a concern; no pause.
- The cost ceiling is breached during a call in flight: the call completes, its usage is recorded, and the run ends before the next dispatch.
- Dry intake on a request that is not ready: the exit is dry_intake, not not_ready, and the card shows the not_ready verdict.
- Datasets share one prospect and so one knowledge file: an Intake answer stored by Clean run is used by later scenarios and not asked again. Blocker answers are never stored.
- A live model does not reproduce the planted story, for example the Reviewer passes v1: the recording does not match the golden log, the mismatch is reported, and the golden log is not changed to fit.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A failed review within budget MUST route to Work with the named specialist or to Assemble, as the Reviewer's findings recommend, with a reason on the backward stage change, and MUST increment the retry counter.
- **FR-002**: Rework MUST dispatch only the routed seat, with the routed findings in its context, and the Writer MUST reassemble after specialist rework.
- **FR-003**: A failed review with the budget spent MUST go to Handoff with exit retry_exhausted and the unresolved findings listed.
- **FR-004**: A blocker that needs a human MUST pause the run through the Orchestrator's question with the blocker attached, and the blocker card MUST offer Answer and Escalate.
- **FR-005**: Answer MUST resume Work with the answer in the blocked specialist's task; the answer is run-local (spec input section 3): it stays in this run's brief and MUST NOT be written to the client knowledge file.
- **FR-006**: Escalate MUST end the run with exit blocker_escalated and a structured list of what is missing, shown on the termination card.
- **FR-007**: A route from Work back to Intake MUST be allowed once per run and a second attempt MUST become a blocker.
- **FR-008**: A not_ready verdict MUST end the run before Plan with exit not_ready and the failing items listed on the card.
- **FR-009**: Dry intake MUST be selectable in the composer before a run starts and MUST end the run after Intake with exit dry_intake and the readiness verdict on the summary.
- **FR-010**: The cost ceiling MUST be checked after every usage record and a breach MUST end the run with exit cost_ceiling before any further dispatch or model call.
- **FR-011**: Pause MUST record a pause with a reason, let calls in flight complete, and dispatch nothing new until Resume, which MUST record a resume with a reason.
- **FR-012**: Stop MUST end the run with exit stopped from any state before termination, including while waiting on a human, and results that arrive afterwards MUST be discarded.
- **FR-013**: Pause, Resume, and Stop MUST be enabled only while a live run is in progress, and every control whose behaviour is not built MUST stay disabled, not hidden.
- **FR-014**: Every exit MUST produce a termination card: from Handoff for reviewer_pass and retry_exhausted, and from the run's end for the others, with the missing list for not_ready and blocker_escalated, the verdict for dry_intake, and the spend for cost_ceiling.
- **FR-015**: Planted inconsistency, Missing sheet, Missing price, and Not ready MUST each run live on their derived inputs, and each MUST have a recorded live run that matches its golden log on stage transitions and exit.
- **FR-016**: Each derived dataset MUST change only what its scenario needs relative to Clean run, and its README MUST name the planted defect, the sheet or file it is in, the expected stage sequence, the expected exit, and the presenter note.
- **FR-017**: Integrity tests MUST check each derived dataset's planted defect and legibility.
- **FR-018**: The blocker card, the Pause control, and the Dry intake toggle MUST be reviewed for consistency with the card and composer families, and the review MUST be recorded in the design deviations.
- **FR-019**: The screenshot comparison and all S1 and S2 gates MUST stay green, and no em dash may appear in any file, prompt, recording, or rendered copy.
- **FR-020**: Nothing in S3 may let a presenter edit prompts or instructions mid-run; Pause freezes dispatch and nothing else.

### Key Entities

- **Review finding**: severity, text, evidence, recommended route (Work with a named specialist, or Assemble). Routed findings become rework context.
- **Retry counter**: count and budget per run; incremented by each failed review that dispatches rework.
- **Blocker**: description, whether a human is needed, optional route back to Intake; carried on the Orchestrator's question; resolved by Answer or Escalate.
- **Structured termination summary**: headline, missing items with notes, unresolved findings, retries, readiness verdict, event count, elapsed time, estimated cost, human decision.
- **Derived dataset**: Clean run inputs with one planted change, its Typst sources, price list, README, and golden log.
- **Presenter control state**: running, paused by the presenter, paused for input, ended.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Each of the four failure scenarios has at least one live run, started from the Demo page, whose stage transitions and exit match its golden log.
- **SC-002**: Planted inconsistency shows exactly one backward change from Review to Work and a retry count of 1 in its matching run; repeated runs are reported with how many matched.
- **SC-003**: Not ready ends within two minutes of pressing Run, with both missing items on the card and no specialist dispatched.
- **SC-004**: Escalate on the Missing sheet blocker ends the run within five seconds, and the card names the missing schedule and its panel.
- **SC-005**: Stop ends a live run within five seconds of being pressed in every state tested: during a model call, while paused, and while waiting on a human.
- **SC-006**: Between a pause and its resume, no sub-task is dispatched in any recorded run.
- **SC-007**: A run started with a ceiling below one Estimator call ends with exit cost_ceiling, and no dispatch follows the breach.
- **SC-008**: Every live verification run stays under the configured per-run ceiling, and the total estimated spend for S3 verification is reported.
- **SC-009**: All tests, the screenshot comparison, the em-dash lint, and the credential leak test pass.

## Assumptions

- Seat models are those of roadmap decisions 13 to 15: five local seats on Ollama and the Estimator on Claude Sonnet 5 through Bedrock with thinking off. The Reviewer is Gemma 4 12B, a different family from the Writer.
- Live verification runs use a per-run cost ceiling of 1.00 USD. Not ready and Dry intake runs make no Estimator call and cost nothing.
- The golden logs committed in S1 for scenarios 2 to 5 define the expected stage transitions and exits. They are not changed to fit a live run; if a live model cannot reproduce a story, the dataset or seat instructions are adjusted within the documented rules, and a persistent mismatch is reported to the owner.
- The derived datasets reuse Clean run's fictional project, prospect, and knowledge file. Planted inconsistency and Missing sheet may add a second sheet or panel where the scenario needs one.
- Missing sheet needs a second panel so that removing its schedule leaves a coherent set; the panel is added to the single-line and the plans with its own circuits.
- The Reviewer still judges the markdown draft; page images arrive in S4. Edit and Reject stay disabled until S4.
- Single-model mode, Settings model swap, and chat stay out of scope until S5.
- Stop discards late results rather than cancelling provider calls mid-stream; a call in flight may still be billed.
