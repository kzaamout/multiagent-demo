# Feature Specification: Seat model guide on Settings

**Feature Branch**: `014-seat-model-guide`

**Created**: 2026-09-21

**Status**: Implemented

**Input**: User description: "I want add to the settings page information that helps people pick the right models for each seat. I want to display next to each seat the Top Open Model & its Accuracy AND the Top Propriatory Model & its Accuracy. Accuracy here should be measured as the model's ability to follow the provided instructions correctly."

**Owner decisions (2026-09-21)**: 1a the guide stays on the right side of the "model leaderboard" non-goal: two names per seat on the existing Settings page, with no list, no history and no sorting, and the spec's constitution check records it; 2b instruction accuracy is the share of a seat's first attempts at a reply that the Orchestrator accepted; 3a every recorded run counts, whatever version of the seat's instructions it ran on; 4a a model needs at least 5 runs on a seat to be named for it, the threshold the performance report already uses; 5c the top model is the one with the highest share after allowing for how many replies back it, taken as the low end of a 95% confidence range, while the page shows the plain share and its counts; 6a each model in the model registry states whether its weights are open or proprietary, set by hand from its licence; 7a a slot with no qualifying model says so, and this work starts no model call and no run; 8a the server works the figures out from the metrics every run already writes, and keeps them until the recorded runs change; 9a the figure is labelled "Instruction accuracy", a line under the page title defines it, and every figure shows the counts behind it; 10a the performance report carries the same figure and the same two picks per seat, from the same calculation as the page. The work happens in its own worktree on branch `014-seat-model-guide`.

## Why

The Settings page lets the presenter move any seat to any model in the registry, and the menu says only whether each model can be reached. Nothing on the page says which model has done the job well. The answer exists: every run records, for every seat, how often the model's reply was accepted the first time the Orchestrator checked it against the seat's instructions (a well-formed reply in the right shape, tools called rather than figures typed, figures matching what the tool returned, concerns carried forward). The owner's rule is that model choices come from that data, not from impressions, but today the data lives in a report the presenter does not have open. Showing, beside each seat, the best open model and the best proprietary model with their figures puts the evidence where the choice is made, and lets the presenter answer a prospect's "why that model?" from the page.

## Clarifications

### Session 2026-09-21

- Q: The report already shows this figure as "First time", beside an "Accuracy" column that measures behaviour checks. How should the report name them? → A: B, rename "First time" to "Instruction accuracy" and "Accuracy" to "Behaviour accuracy" in the report's display labels, correct both definitions, and leave the raw file's column names unchanged. Also, the Settings page carries a note at its foot saying what each of the two measures covers (answer A to the follow-up: the Settings page, not the report).
- Q: When a seat's current model is not one of the two picks, should its own instruction accuracy be shown too? → A: C, the seat's model button shows the current model's instruction accuracy and counts after its name, for every seat, whether or not the model is a pick.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the best open and proprietary model beside each seat (Priority: P1)

The presenter opens Settings. Under each seat's model menu are two short lines: the top open model with its instruction accuracy and the counts behind it, and the top proprietary model with the same. The seat's model button shows the current model's own figure after its name. A line under the page title says what instruction accuracy is and how many recorded runs the figures come from, and a note at the foot of the page says what instruction accuracy and behaviour accuracy each measure. The presenter compares a seat's current model with the two picks and changes the seat if the evidence says so.

**Why this priority**: This is the whole request. Without it the rest has nothing to show.

**Independent Test**: With a folder of recorded runs whose figures are known, load Settings and read, for every seat, the two named models, their percentages and their counts, and compare them with the expected picks.

**Acceptance Scenarios**:

1. **Given** recorded runs in which the Pricing seat's open models are qwen3.5 9b (212 of 226 first attempts accepted, 196 runs) and gemma4 12b (5 of 5, 5 runs), **When** Settings loads, **Then** the Pricing seat's open line names qwen3.5 9b, local, with instruction accuracy 94% (212 of 226 replies).
2. **Given** recorded runs in which the Estimator seat ran Claude Sonnet 5 on Bedrock in 26 runs with 29 of 31 first attempts accepted, **When** Settings loads, **Then** the Estimator seat's proprietary line names that model with 94% (29 of 31 replies).
3. **Given** any seat, **When** Settings loads, **Then** the two lines sit with that seat's row and are visibly distinct from the seat's own model, which the seat's card and menu go on showing as today.
4. **Given** Settings is loaded, **When** the presenter reads under the page title, **Then** one line defines instruction accuracy in plain words and states how many recorded runs the figures come from.
5. **Given** the Writer seat is on gemma4 12b, which has 0 of 12 first attempts accepted at the Writer, **When** Settings loads, **Then** the Writer's model button reads the model's name followed by its figure, 0% (0 of 12), while the open line names the top open model with its own figure.
6. **Given** the presenter moves a seat to another model, **When** the swap is applied, **Then** the seat's model button shows the new model's name and that model's figure for the seat.
7. **Given** Settings is loaded, **When** the presenter reads the foot of the page, **Then** a short note says what instruction accuracy measures and what behaviour accuracy measures, where behaviour accuracy is reported, and that neither measure looks at whether the price is right.

---

### User Story 2 - The figures do not overstate thin evidence (Priority: P1)

A model tried a handful of times can post a perfect record that means little. The guide never names a model with fewer than 5 runs on the seat, never lets a short perfect record outrank a long near-perfect one, and says plainly when no model qualifies.

**Why this priority**: A pick that a prospect can knock down with "you tried it three times" costs more credibility than no pick. The guide is only worth showing if it is honest.

**Independent Test**: Build a folder of recorded runs with a seat on which one model has 13 of 13 first attempts accepted over 8 runs and another has 390 of 397 over 288 runs, a proprietary model with 4 runs, and no other proprietary model, and check the picks.

**Acceptance Scenarios**:

1. **Given** the Orchestrator seat has gemma4 12b at 13 of 13 over 8 runs and qwen3.5 9b at 390 of 397 over 288 runs, **When** Settings loads, **Then** the top open model is qwen3.5 9b at 98% (390 of 397 replies).
2. **Given** a seat on which the only proprietary model has 4 runs, **When** Settings loads, **Then** the proprietary line says no proprietary model has 5 runs on the seat yet, and names no model.
3. **Given** a seat no proprietary model has ever held, **When** Settings loads, **Then** the proprietary line says there are no runs yet.
4. **Given** a model that lacks something the seat needs, such as image input at the Reviewer, **When** Settings loads, **Then** that model is never named for that seat, whatever its figure.

---

### User Story 3 - The figures follow the runs without a restart (Priority: P2)

The presenter finishes a live run, or a sweep finishes runs in the background, and reloads Settings. The figures now include those runs. Nobody restarts the server and the page runs no timer.

**Why this priority**: A guide that silently goes stale contradicts the report and the rule that choices come from the data. It ranks below the display because the display is useful even when a restart is needed.

**Independent Test**: Load Settings, add one finished run folder that changes a seat's figure, reload, and check the new figure. Then reload again with nothing changed and check the figures are served without being worked out again.

**Acceptance Scenarios**:

1. **Given** Settings has loaded once, **When** a run finishes in the app and the page is reloaded, **Then** the figures include that run.
2. **Given** Settings has loaded once, **When** a run finished by another process appears in the runs folder and the page is reloaded, **Then** the figures include that run.
3. **Given** the app is running a run, **When** Settings loads, **Then** that run is not counted until it has ended, so the figures hold still while the presenter works.
4. **Given** nothing in the runs folder has changed, **When** Settings is reloaded, **Then** the figures are the same and are not worked out again from every run.

---

### User Story 4 - The report says the same thing (Priority: P2)

The owner refreshes the performance report after a batch of runs. It carries a section with the same two picks per seat and the same instruction accuracy figures the page shows, worked out by the same calculation, and names the figure the same way.

**Why this priority**: Two places that work out one number separately will drift, and the project's rule is one place per kind of number. The report is where the owner makes model decisions; the page is where the presenter acts on them.

**Independent Test**: With the same runs folder, generate the report and load Settings, and compare every seat's two picks, percentages and counts.

**Acceptance Scenarios**:

1. **Given** a runs folder, **When** the report is generated and Settings is loaded from the same folder, **Then** every seat's two picks, percentages and counts agree exactly.
2. **Given** the report, **When** its tables and column definitions are read, **Then** the column once called "First time" is labelled "Instruction accuracy" and defined in the same words the page uses, the column once called "Accuracy" is labelled "Behaviour accuracy" with its definition unchanged in meaning, no unqualified "Accuracy" label remains, and the per-run raw file's column names are unchanged.

### Edge Cases

- **No recorded runs on this machine.** A fresh checkout has no runs. Every slot says there are no runs yet, the defining line says the figures come from 0 recorded runs, and nothing fails.
- **A model that no longer appears in the registry.** Recorded runs may name a model since removed from the registry. It cannot be chosen from the menu, so it is never named as a pick; the report's other tables go on listing its runs.
- **A model in the registry that does not say whether it is open or proprietary.** It is never named as a pick, and the report lists it by name as not classified, so the gap is visible rather than guessed.
- **A tie on the ranking figure.** The model with more replies wins; if still tied, the model listed first in the registry wins, so the pick never changes between two loads of the same data.
- **A top pick that cannot be reached on this machine.** The pick is shown as the data says. The model menu goes on saying why that model cannot be chosen here, as today.
- **The pick is the seat's current model.** It is shown the same way as any other pick, and the model button shows the same figure.
- **The seat's current model has few or no runs on the seat.** The model button shows its figure with its counts even below 5 runs, since the counts say how thin it is; the 5-run threshold governs only who is named as a pick. With no replies on the seat at all, the button says there are no runs yet after the name.
- **A run folder that cannot be read.** It is left out, as the report already leaves it out, and the rest of the figures still show.
- **A run that never finished.** A run cut off by closing the app, or a sweep's run still going in another process, has no finished metrics. The report already counts such a run with the replies it made, worked out from its event log, and the page does the same, so the two agree. Only the run this app is running now waits until it ends.
- **Runs recorded before the seat's instructions were last changed.** They count (decision 3a). A model tried only on older wording is compared with one tried on today's.
- **Stub runs, replays and pre-flight probes.** They make no model reply the Orchestrator checks, so they add nothing to any figure.
- **The Single-model seat.** It has no row on Settings and gets no picks on the page or in the report's new section.
- **The appraisal seats.** Settings already shows rows for the Case Manager and the Market Analyst, whose workflow is not built. They have no guide lines and no figure in their model button until that workflow records runs and the guide is extended to them.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: For each seat on the Settings page (Orchestrator, Intake, Estimator, Pricing, Writer, Reviewer), the page MUST show the top open model and the top proprietary model for that seat, each with its instruction accuracy as a whole-number percentage and the counts behind it, as in "94% (212 of 226 replies)".
- **FR-002**: Instruction accuracy for a seat and a model MUST be the replies the seat produced on that model that the Orchestrator accepted on the first attempt, divided by all the replies the seat produced on that model. A reply on which the run stopped counts as not accepted first time. It MUST be worked out across every recorded run, whatever version of the seat's instructions and whatever settings the run used.
- **FR-003**: A model MUST have at least 5 runs on a seat to be named as a pick for that seat.
- **FR-004**: Among the qualifying models of each kind, the pick MUST be the model with the highest low end of the 95% confidence range around its instruction accuracy (the Wilson score interval), so that the number of replies behind a share counts. Ties MUST go to the model with more replies, then to the model listed first in the registry. The page MUST show the plain share, not the low end.
- **FR-005**: Every model in the registry MUST state whether its weights are open (published for anyone to download and run) or proprietary (served only by its vendor), set by hand from its licence. The kind of a pick MUST come from that statement, never from the provider it is served through.
- **FR-006**: A model MUST NOT be named as a pick for a seat when it is missing from the registry, when the registry does not say whether it is open or proprietary, or when the registry says it lacks image input and the seat needs it (the Estimator reads drawing pages as images, the Reviewer reads compiled pages). Tool calling is not checked: the registry records no model without it, and every model the report probes takes tool calls.
- **FR-007**: When no model of a kind qualifies for a seat, its line MUST say so without naming a model, and MUST distinguish "no runs yet" (no model of that kind has held the seat) from "fewer than 5 runs" (at least one has, but none has 5).
- **FR-008**: A line under the Settings page title MUST define instruction accuracy in plain words (the share of a seat's replies the Orchestrator accepted the first time it checked them against the seat's instructions) and state how many recorded runs the figures come from.
- **FR-009**: The picks MUST be visibly separate from the seat's own model: the seat's card and model menu go on showing the model the seat is on, and the picks never replace or restyle that label.
- **FR-010**: Each seat's model button MUST show, after the current model's name, that model's instruction accuracy at that seat with its counts, as in "40% (100 of 248)", whatever its number of runs. When the model has no replies on the seat, the button MUST say there are no runs yet. The model's name itself MUST stay exactly as today, and the figure MUST be visually secondary to it. The options in the open model menu carry no figures.
- **FR-011**: The figures MUST come from the metrics each run already writes when it ends, or, for a run without them, from its event log, as the report already does. This work MUST NOT add a stored file of per-run or per-model figures.
- **FR-012**: The figures MUST count the same recorded runs the performance report counts, as they stand when the page loads, including runs finished by another process and runs left unfinished (a sweep's run in progress, a run cut off by closing the app), each with the replies it made. The one exception is the run this app is running now, which MUST NOT be counted until it has ended. When the recorded runs have not changed since the last load, the figures MUST be served without being worked out again from every run. The page MUST NOT poll or run a timer to learn of new runs.
- **FR-013**: The performance report MUST include a section giving, for the same six seats, the same two picks with the same percentages and counts, worked out by the same calculation the page uses, and MUST define instruction accuracy in the same words the page uses. It MUST name the registry models not classified as open or proprietary, if any.
- **FR-014**: The report's existing figure that is the same calculation as instruction accuracy (today's "First time" column, accepted first time over replies) MUST NOT be worked out a second way. In the report's tables, text and column definitions it MUST be labelled "Instruction accuracy", and its definition MUST say that a reply the run stopped on counts as not accepted first time. The per-run raw file's column names MUST NOT change.
- **FR-015**: The report's "Accuracy" column (checks met over checks defined, from the dataset's expectations of each seat) MUST be labelled "Behaviour accuracy" in the report's tables, text and column definitions, with its meaning and calculation unchanged. No unqualified "Accuracy" label may remain in the report.
- **FR-016**: The foot of the Settings page MUST carry a short note saying what instruction accuracy measures (replies accepted the first time the Orchestrator checked them against the seat's instructions) and what behaviour accuracy measures (whether the seat did what its scenario expects, such as raising the planted blocker or passing a clean draft), that behaviour accuracy is in the performance report rather than on the page, and that neither measure looks at whether the price is right.
- **FR-017**: This work MUST NOT start a model call, a run or a sweep, and MUST NOT change any event type, event payload, the event schema version, or any golden log.
- **FR-018**: The Settings page's existing behaviour MUST NOT change: choosing a model for a seat, the family warning, the dependency notes and the status line work as today.
- **FR-019**: The layout deviation from the design export MUST be recorded with the other design deviations, and the page's copy MUST contain no em dash.

### Key Entities

- **Seat model record**: one seat on one model across every recorded run: the runs it appears in, the replies it produced, and the replies accepted on the first attempt. Instruction accuracy and its ranking bound derive from it.
- **Model kind**: open or proprietary, stated per model in the registry from its licence.
- **Seat pick**: for one seat and one kind, either the chosen model with its record, or the reason no model qualifies (no runs yet, or fewer than 5 runs).
- **Seat guide**: for every seat on Settings, the two picks and the current model's record at that seat, with the number of recorded runs they come from.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On Settings, all six seats show both lines, and each line either names a model with a percentage and its counts or states why no model is named; every seat's model button shows its current model's figure or says there are no runs yet.
- **SC-002**: For the same runs folder, the page and the performance report agree on 100% of picks, percentages and counts.
- **SC-003**: No model with fewer than 5 runs on a seat is ever named for it, and in the fixture of User Story 2 the pick with 390 of 397 replies outranks the one with 13 of 13.
- **SC-004**: With about 400 recorded runs, Settings shows its figures within 1 second of opening on the presenter laptop, and a reload with no new runs does not work the figures out again.
- **SC-005**: After a run finishes, the next load of Settings includes it, with no restart.
- **SC-006**: The work adds zero model calls and zero runs; the event schema version, the event types and every golden log are unchanged; every quality gate passes.

## Constitution check

- **Non-goal "a model leaderboard"** (decision 1a): the guide names two models per seat on the existing Settings page and shows the figure of the model the seat is on. It has no page of its own, no ranked list, no history over time, no sorting, and no figures in the model menu's options. The full tables stay in the report, which is a document, not a screen.
- **Principle II, nothing renders that was not emitted**: the picks are not run state. Like the model menu and its availability, they come from what the Settings page already requests, and nothing on the Demo page or in a run depends on them.
- **Principle V, the model is displayed truthfully**: the seat's card and menu go on showing the model the seat is on, and the figure added to the model button follows the model's name without changing it. The picks are labelled as the top open and top proprietary models and never stand in for the seat's model (FR-009, FR-010).
- **Non-goal "providers or credentials from the UI"**: nothing is added to what the page can change. The open or proprietary statement lives in the registry file, edited by hand.
- **Working rules 10 and 15**: the figures come from each run's metrics, and one calculation serves both the page and the report.

## Assumptions

- "Open" means open weights: the weights are published and can be run locally, whatever the licence's other terms. Every Ollama model in the registry today is open (qwen3.5 9b and 4b, gemma4 12b, llama3.1 8b, granite4.1 8b, deepseek-r1 14b) and every Bedrock, Google and xAI model is proprietary, but the statement is made per model so an open model served from a cloud provider would stay open.
- "Accepted by the Orchestrator" means the reply passed every check the engine makes of it against the seat's instructions: a well-formed reply in the right shape, tools called rather than figures typed, figures matching what the tool returned or what the Estimator gave, amounts present in the sources, concerns carried forward. These are the refusal reasons the engine already records.
- The report's "First time" column is already this calculation: accepted first time over replies, where a reply the run stopped on is a reply not accepted first time. Its written definition ("share of accepted replies that needed no correction") understates that and is corrected as it is relabelled (FR-014). The owner's ranking for the best local model keeps its substance; its wording follows the new labels.
- The two picks are information only: they are not buttons, and the seat changes only through its model menu, as today.
- With the 385 runs recorded on 2026-09-21, the expected picks are: Orchestrator, qwen3.5 9b at 98% (390 of 397); Intake, qwen3.5 9b at 57% (216 of 381); Estimator, qwen3.5 9b at 44% (155 of 349) and Claude Sonnet 5 on Bedrock at 94% (29 of 31); Pricing, qwen3.5 9b at 94% (212 of 226); Writer, qwen3.5 9b at 40% (100 of 248); Reviewer, gemma4 12b at 98% (195 of 198). Every seat but the Estimator has no proprietary runs yet. These figures illustrate the rule and change as runs are added.
- The runs folder is the one the app is configured with, so a worktree pointed at another checkout's runs shows that checkout's figures.
