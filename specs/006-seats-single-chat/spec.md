# Feature Specification: Seats, single model, and chat (slice S5)

**Feature Branch**: `006-seats-single-chat`

**Created**: 2026-09-16

**Status**: Draft

**Input**: User description: "Slice S5, Seats, single model, and chat, exactly as written in docs/roadmap.md "S5. Seats, single model, and chat", with docs/spec-input.md 0.7 sections 2.2 (composer switch, Compare strip, meters), 2.3 Settings, 2.7 chat, 4.1 identity, 5 Single-model mode, 6 (model.changed, meter.update, single_complete), 9 M5, 10 criterion 6, and design brief sections 8 and 9. Owner decisions 2026-09-16 (ten, listed under Assumptions). Work happens in the worktree on the existing branch 006-seats-single-chat."

**Governing documents**: `docs/spec-input.md` 0.7 (2.2, 2.3, 2.7, 4.1, 4.2, 5, 6, 9 M5, 10), `.specify/memory/constitution.md` 1.2.0 (V, X, and the non-goals on credentials from the UI, changing instructions mid-run, and a model leaderboard), `docs/roadmap.md` S5 entry, `docs/schema/events-v1.1.0.md` (frozen; `model.changed`, `meter.update`, `single_complete`, `stage.changed` in a Single-model run), `docs/design-brief.md` 8 and 9, `design/README.md` (Settings dropdown, Compare strip, meter detail row, `chatOpen` switch), `config/models.yaml`.

## Purpose of the slice

Three things a prospect asks in every meeting: "can I swap the model?", "why not just one model?", and "can I ask the agent why?". S5 answers all three on screen. Settings goes live so a seat moves to another model mid-run and every card follows within a second. Single-model mode runs the same request through one model and fills the Compare strip, so the contrast with the team (cheaper, faster, no review, no sources) is visible rather than argued. Chat lets the presenter click an agent after the run and ask it a question, without touching the run.

The peer slice S4 (compiled deliverable and provenance) is built in parallel on `005-compiled-deliverable`; the artifact panel, compile pipeline, and provenance code are out of scope here. Ownership of shared files is recorded under Assumptions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Swap a seat's model and see it everywhere (Priority: P1)

The presenter opens Settings during a live run and moves the Estimator to another model from the dropdown. Within a second the grey model text on the Estimator's card changes on the Settings row, in every feed card, in the meters, and in the roster shown by the API. The next dispatch to that seat uses the new model; the call already in flight finishes on the old one. Providers whose credentials are not in `.env` are greyed with "no credentials in .env" and cannot be chosen. A status line says "Changes apply at the next stage."

**Why this priority**: Acceptance criterion 6 in spec section 10 and the roadmap outcome. It is the proof that the model is a runtime attribute, not the agent (constitution V).

**Independent Test**: With scripted seat models, swap a seat between two events and check that the `model.changed` event carries from and to, that later events from that seat carry the new model on their actor, and that the next prompt bundle names the new model. The Settings screenshot comparison passes with the dropdown closed and open.

**Acceptance Scenarios**:

1. **Given** the Settings page, **When** it loads, **Then** every seat row shows the seat's live model, and the dropdown lists every model in the registry with the providers lacking credentials greyed and unselectable.
2. **Given** a live run in Work, **When** the presenter chooses another model for the Estimator, **Then** a `model.changed` event is emitted within a second with the old and new model objects, every card for that seat shows the new label, and the Estimator's next dispatch uses the new model.
3. **Given** a swap that puts the Reviewer on the same model family as the Writer, **When** it is chosen, **Then** the swap is applied and a warning line on the row says the Reviewer now shares the Writer's family.
4. **Given** the application restarts, **When** Settings loads, **Then** every seat shows the default from the models configuration file again.
5. **Given** no run is live, **When** a seat is swapped, **Then** the next run starts with the new model in its roster and no event is emitted until a run starts.

---

### User Story 2 - Single-model run fills the Compare strip (Priority: P1)

The presenter switches the composer to Single model, picks a model (defaulting to the Orchestrator's), and runs the same dataset. One actor, "Single model", does the whole job with the same deterministic tools, in one task. The loop strip tracks Intake, Work, Assemble, and Handoff with Plan and Review bypassed. The run ends with exit `single_complete` and its own run id. The Compare strip above the artifact panel shows the Single-model output with its cost and elapsed time, and the meters' comparison line reads the most recent Team and Single runs of that dataset side by side.

**Why this priority**: The contrast is the sales argument for a team. Without it the demo asserts the value of review and provenance instead of showing it.

**Independent Test**: A Single-model run on scripted models records `run.started` with mode single, four `stage.changed` events, one `task.dispatched`, one `task.completed`, meter updates, and `run.terminated` with `single_complete`, and replays from its folder. The Compare strip and comparison line populate from the recordings after a reload.

**Acceptance Scenarios**:

1. **Given** Single model is selected, **When** the presenter runs, **Then** a new run starts with mode single, actor "Single model" on the chosen model, and the stage sequence Intake, Work, Assemble, Handoff, with Plan and Review rendered bypassed.
2. **Given** the run completes, **When** `run.terminated` arrives, **Then** the exit is `single_complete`, the termination card renders from it, and the recording replays.
3. **Given** a Team run and a Single-model run exist for the selected dataset, **When** the Demo page loads, **Then** the Compare strip shows the latest Single-model output with its cost and time and the comparison line shows both runs' cost and time.
4. **Given** the Single-model output, **When** it is read, **Then** figures came from the tools and no provenance tags or review verdict exist; the strip states "no review, no sources".
5. **Given** a Single-model run is live, **When** the presenter clicks Pause or Stop, **Then** they behave as in a Team run.

---

### User Story 3 - Meters complete (Priority: P2)

The meters strip shows the Team versus Single comparison line, a thin cost ceiling bar that fills as estimated spend approaches the ceiling, and a per-agent detail row opened by clicking an agent meter: calls, tokens in and out, cost, wall time, provider latency, last event.

**Why this priority**: Already drawn in the export; the numbers exist in events. Small work that makes cost visible on the projector.

**Independent Test**: Reduce a recorded run and compare the detail row values with sums over its `meter.update` events.

**Acceptance Scenarios**:

1. **Given** a run with meter updates, **When** the presenter clicks an agent meter, **Then** a detail row opens with the six figures computed from that agent's events only.
2. **Given** a cost ceiling, **When** spend grows, **Then** the ceiling bar fills proportionally and turns to the warning colour past 80 percent.

---

### User Story 4 - Ask an agent why (Priority: P2)

After the run ends (or while it is paused, or during a replay), the presenter clicks an agent card. A side panel opens with the same card as its header and an input at the bottom. The agent answers from its own instructions and the context of its last call in this run. The conversation is out of band: no event, nothing recorded, nothing replayed. Closing the panel clears it. The panel footer shows the chat's own token count and estimated cost; the meters do not move.

**Why this priority**: The roadmap outcome ends with it. It shows the agent is a role with a prompt, not a chat window.

**Independent Test**: Record a run, chat with a seat, and compare the run folder byte for byte before and after; the API refuses chat on a running, unpaused run.

**Acceptance Scenarios**:

1. **Given** a terminated run, **When** the presenter clicks the Estimator's card and asks a question, **Then** the reply comes from the Estimator's model with its instructions and last context, and the run's event log and folder are unchanged.
2. **Given** a running, unpaused run, **When** a card is clicked, **Then** no chat opens and the card explains chat is available when the run is paused or finished.
3. **Given** a replayed run, **When** a card is clicked, **Then** chat opens using the recorded prompt bundle for that seat.
4. **Given** the panel is closed, **When** it is reopened, **Then** the conversation is empty.
5. **Given** a chat exchange, **When** the meters and `metrics.json` are read, **Then** they are unchanged; the panel footer alone shows the chat's tokens and cost.

---

### Edge Cases

- A swap while the seat's call is in flight: the in-flight call completes on the old model; the seat's next call uses the new one; `model.changed` is emitted at once, not at the dispatch.
- A swap to a model whose provider is greyed is refused by the page and by the API.
- Ollama is not running at startup: its models are absent from the dropdown until restart; no live check on page load.
- A Single-model run on a dataset that is not curated runs on a stub Single-model scenario with the same event shape.
- A Single-model run that hits the cost ceiling ends with `cost_ceiling`, not `single_complete`.
- Chat while a Team run is live and paused for a blocker: allowed; the chat never answers the blocker.
- A chat model call fails: the panel shows one line saying the model could not be reached; nothing else changes.
- A model swap during a Single-model run does not change the Single-model actor's model; the single actor's model is chosen in the composer.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Settings MUST list, per seat, every model in the registry; providers whose credentials are absent from `.env` MUST be greyed with "no credentials in .env" and unselectable; Ollama models MUST be listed only when detected once at startup; no health checks run on page load.
- **FR-002**: Choosing a model MUST take effect at that seat's next dispatch, emit `model.changed` with the previous and new model objects while a run is live, and update the seat's label on every card within one second; while no run is live it MUST change the roster of the next run without emitting an event.
- **FR-003**: A swap MUST live in memory until restart; the models configuration file remains the default and is never written by the application.
- **FR-004**: A swap that puts the Reviewer on the Writer's model family MUST be allowed and MUST show a warning line on the Settings row.
- **FR-005**: The Single-model switch in the composer MUST be live, with a model dropdown visible only in Single mode, defaulting to the Orchestrator's current seat model.
- **FR-006**: A Single-model run MUST be its own run id with mode single, one actor with agent id `single`, role "Single model", two names and its own colour, a dedicated instructions file, and the same deterministic tools as the team; it MUST emit `run.started`, `stage.changed` into Intake, Work, Assemble, and Handoff, one `task.dispatched`, one `task.completed` carrying the output, `meter.update`, and `run.terminated` with exit `single_complete`, and it MUST record and replay like any run.
- **FR-007**: The Compare strip MUST show the most recent terminated Single-model run for the selected dataset from the recordings, with its output, model, cost, elapsed time, and the words "no review, no sources"; the comparison line MUST show the most recent Team and Single-model runs' cost and time for that dataset.
- **FR-008**: The meters MUST show a cost ceiling bar and, on click, a per-agent detail row with calls, tokens in and out, cost, wall time, provider latency, and last event, all computed from that agent's events.
- **FR-009**: Chat MUST be available on paused, terminated, and replayed runs only, MUST use the seat's current model with the seat's instructions and the prompt bundle of its last call in the run, MUST be read-only with respect to the run, and MUST leave the run folder byte-identical.
- **FR-010**: Chat MUST NOT emit events, MUST NOT be recorded or replayed, MUST NOT count in the meters, the ceiling, or `metrics.json`, and MUST clear when the panel closes; the panel footer alone shows the chat's tokens and estimated cost.
- **FR-011**: The Settings screenshot comparison MUST pass with the dropdown closed and with it open, against the export references.
- **FR-012**: No machine identifier changes except the added agent id `single`; the schema stays at 1.1.0.

### Key Entities

- **Registry**: the models and providers from configuration, each provider's credential presence, the Ollama models detected at startup, and the per-seat override in memory.
- **Single-model run**: a run with mode single, one actor, the four-stage sequence, and exit `single_complete`.
- **Comparison**: the latest terminated Team and Single-model recordings for a dataset with their cost and elapsed time.
- **Chat session**: a seat, a run, the seat's last prompt bundle, and an in-memory message list that lives while the panel is open.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Swapping any seat in Settings changes the grey model text everywhere within one second and the next dispatch uses the new model (spec criterion 6), shown by a scripted test and a live run.
- **SC-002**: A Single-model run is recorded with exit `single_complete`, replays from its folder, and fills the Compare strip and comparison line after a page reload.
- **SC-003**: A test proves the run log and the whole run folder are byte-identical before and after a chat exchange.
- **SC-004**: The Settings comparison passes in both dropdown states; the Demo comparisons are unchanged.
- **SC-005**: All quality gates pass and the roadmap S5 evidence lists the run ids and spend.

## Assumptions

Owner decisions of 2026-09-16, answered as a lettered list:

1. The Single-model prompt is a dedicated seat file, `single.md`, beside the six seat files.
2. The Single-model run uses the same deterministic tools as the team.
3. A dedicated actor, agent id `single`, role "Single model", two names and its own colour.
4. The Compare strip and comparison line read the most recent terminated run of each mode for the selected dataset from the recordings.
5. A Settings swap lives in memory until restart; `models.yaml` stays the default.
6. A swap that puts the Reviewer on the Writer's family is allowed, with a warning line.
7. A provider is greyed when `.env` lacks its key; Ollama models are listed when detected once at startup; no health checks (S7).
8. Chat is available on paused, terminated, and replayed runs.
9. Chat cost shows in the chat panel footer only, never in the meters or `metrics.json`.
10. The default model in Single mode is the Orchestrator's current seat model.

Further assumptions:

- The spec directory is numbered 006 to match the branch; 005 is the peer's S4 spec on its own branch, so the two never collide on merge.
- Shared files (`app/main.py`, the reducer and renderer scripts, the stylesheet, the event models) are touched only by adding functions and routes; the S4 branch owns the artifact panel, compile pipeline, templates, and tools folder; S5 owns the provider registry, Settings, the composer, meters, and chat.
- The Single-model actor uses the Orchestrator's prompt bundle recording and metrics like any seat; its performance rows appear in `metrics.json` under agent id `single`.
- Provider health checks and Laptop versus Cloud greying are deferred to S7 per the roadmap.
