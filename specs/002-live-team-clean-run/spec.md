# Feature Specification: Live team on the clean run (slice S2)

**Feature Branch**: `002-live-team-clean-run`

**Created**: 2026-09-14

**Status**: Draft

**Input**: User description: "Slice S2, Live team on the clean run, as written in docs/roadmap.md, with the pre-S2 decisions recorded there, the seat instructions in config/electrical-rfp/seats/, and the referenced sections of docs/spec-input.md 0.5 (2.2 banner, 2.5, 3 stages 1 to 6 forward path, 4, 6, 7 scenario 1, 8 markdown only). Build now everything that needs no credentials or curated dataset; stop before any live run."

**Governing documents**: `docs/spec-input.md` 0.5, `.specify/memory/constitution.md` 1.1.1, `docs/roadmap.md` (S2 entry and the decisions taken before S2), `docs/schema/events-v1.0.0.md` (frozen), `config/electrical-rfp/`.

## Purpose of the slice

S1 proved the event spine with canned agents. S2 replaces the canned agents with real ones on one scenario. The presenter runs Clean run and six agents do the work on their default models: the Intake Analyst reads the real request and raises one clarification, the presenter answers it in the banner, the Estimator reads real drawings, Pricing costs the bill of materials from the supplier fixture on a local model, the Writer assembles a proposal draft, and the Reviewer on a different model family passes it. Every prompt toggle shows the bundle that was actually sent. A second run on the same client does not ask the answered question again.

The page, the event schema, recording, and replay do not change. Only the source of agent emissions changes.

## Delivery in two parts

The owner decided on 2026-09-14 that S2 starts before its owner inputs exist.

- **Part A, buildable now:** everything that needs neither provider credentials nor the curated Clean run dataset. It is proven with a scripted model that follows the real call path and with small synthetic inputs made for tests.
- **Part B, waits for owner inputs:** live runs on real models, the recorded live Clean run, and the evidence that depends on them. Its inputs are the curated Clean run dataset, Bedrock and Gemini credentials in `.env`, and Ollama with the local model pulled.

The slice is complete only when Part B's evidence exists.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The team works the Clean run live (Priority: P1, Part B)

The presenter selects Clean run, presses Run, and watches real agents work. The Intake Analyst grades the request and raises one non-blocking or blocking clarification with a proposed default. If it blocks, the banner appears and the presenter answers. The Estimator and Pricing work in sequence, their threads filling with real progress lines and tool calls. The Writer commits a draft, the draft text appears in the artifact panel, the Reviewer passes it, and the run reaches Handoff for approval.

**Why this priority**: It is the slice outcome and the first time the demo shows real work.

**Independent Test**: With credentials and the curated dataset in place, run Clean run from the Demo page, answer the banner, approve, and replay the recording against the Clean run golden stage sequence and exit.

**Acceptance Scenarios**:

1. **Given** the curated Clean run dataset and working providers, **When** the presenter runs Clean run, **Then** the stage sequence is Intake, Plan, Work, Assemble, Review, Handoff and the run ends with exit reviewer_pass after Approve.
2. **Given** a live run, **When** any agent message appears, **Then** its prompt toggle shows the system instructions from that seat's file, the context slice that seat was given, the task, its tools, and the model actually used.
3. **Given** a live run, **When** a specialist calls a tool, **Then** a tool call reply appears in its thread with the tool name, a short argument summary, a short result summary, and the duration.
4. **Given** a live run, **When** any model call returns, **Then** a meter update with that call's real token counts and estimated cost follows, and the meters strip accumulates it.
5. **Given** Pricing's seat on the local model, **When** Pricing runs, **Then** its agent card shows the local model label and its cost is zero.

---

### User Story 2 - Ask once (Priority: P1, Part A proves the mechanism, Part B the live beat)

When the presenter answers an Intake clarification, the answer is appended to the client knowledge file. On the next run for the same client, the Intake Analyst reads the file, uses the answer, and does not raise that question again.

**Why this priority**: "Ask once" is a promised beat in the Introduction copy and a roadmap evidence item.

**Independent Test**: Run a scenario whose Intake raises a clarification, answer it, then run again for the same client; the second run's events contain no clarification with that question id, and the second run's Intake context slice contains the answer.

**Acceptance Scenarios**:

1. **Given** a clarification answered in run one, **When** run one continues, **Then** `knowledge.appended` follows `clarification.answered` for that question.
2. **Given** run one's answer in the knowledge file, **When** run two's Intake is dispatched, **Then** the knowledge file content in its context slice includes that answer under "Answers from previous runs".
3. **Given** run two, **When** Intake completes, **Then** no `clarification.needed` event repeats the answered question id.
4. **Given** knowledge files, **When** runs are made on different datasets, **Then** each dataset's client has its own file and runs do not pollute each other's datasets.

---

### User Story 3 - Roles are real: scoped context and tools (Priority: P1, Part A)

Each seat receives only the instructions, context, and tools its role allows (spec 4.3 and 4.4). The Reviewer's bundle provably contains no specialist reasoning, no tool output, and no Writer sources.

**Why this priority**: Constitution V and the roadmap's named risk for S2. It is also what the presenter tells the prospect to check with the prompt toggle.

**Independent Test**: Build the bundle for every seat from a run state that contains every kind of output, and assert the presence and absence of each item against the roster table.

**Acceptance Scenarios**:

1. **Given** a run state with a brief, specialist outputs with tool results, and a draft, **When** the Reviewer's bundle is built, **Then** it contains the brief, the draft, and the reviewer criteria, and none of the specialist outputs, tool results, prompts, or the knowledge file.
2. **Given** the same state, **When** Pricing's bundle is built, **Then** it contains the Estimator's bill of materials and labour hours and the knowledge file, and no drawing pages or request documents.
3. **Given** the same state, **When** the Estimator's bundle is built, **Then** it contains the brief, the drawing pages, and the estimating conventions, and no prices, supplier fixture, or knowledge file.
4. **Given** the same state, **When** the Writer's bundle is built, **Then** it contains the brief, every specialist output labelled with its source event id, the template, and the knowledge file, and no drawings or price fixture.
5. **Given** the Intake Analyst's bundle, **Then** it contains the request documents, the knowledge file, and the readiness checklist, and no other agent's output.
6. **Given** any seat, **When** its agent is built, **Then** it is given exactly the tools listed for it in the roster, and the Orchestrator and Reviewer are given none.

---

### User Story 4 - Providers from `.env` with truthful labels (Priority: P2, Part A)

The application builds a registry of providers and models from `.env` and from Ollama detection at startup. Each seat's model is a structured object with provider, model id, and label, and the label is what every agent card shows. A seat whose default provider has no credentials is reported, never silently swapped.

**Why this priority**: Constitution V (the grey model text is truth) and XVII (credentials only in `.env`). Model swapping itself is S5.

**Independent Test**: Start the registry with a test `.env` holding only an Anthropic key and no Ollama; the registry marks Anthropic available, Bedrock and Gemini unavailable, and Ollama not detected; a run cannot start in live mode with a seat on an unavailable provider and says which seat and why.

**Acceptance Scenarios**:

1. **Given** credentials for a provider in `.env`, **When** the registry loads, **Then** that provider is available and its models are listed with labels.
2. **Given** no credentials for a provider, **When** the registry loads, **Then** that provider is listed as unavailable with the reason "no credentials in .env", and no credential value appears in any response, event, bundle, or log.
3. **Given** Ollama reachable with the configured local model pulled, **When** the registry loads, **Then** the local model is available; otherwise it is unavailable with the reason.
4. **Given** live mode and a seat on an unavailable provider, **When** Run is pressed, **Then** the run does not start and the page shows which seat and provider are unavailable.

---

### User Story 5 - Live agents on the unchanged event spine (Priority: P1, Part A)

The Orchestrator drives live agents through the same stages, gates, recording, and replay as S1 stubs. Agent outputs are validated and converted to schema v1.0.0 events. Progress lines become `task.progress`, tool invocations become `tool.called`, and each model call's usage becomes `meter.update`. The stub mode stays available for S1 scenarios and tests.

**Why this priority**: It is the core of the slice and is fully provable without credentials using a scripted model.

**Independent Test**: Run the Clean run flow in live mode with a scripted model that returns the shapes the seat files require, using small synthetic inputs; the run passes schema validation, reaches reviewer_pass, and matches the Clean run golden stage sequence and exit.

**Acceptance Scenarios**:

1. **Given** live mode with a scripted model, **When** a run executes, **Then** every event validates against schema v1.0.0 and `run.terminated` is last.
2. **Given** an agent reply that does not match its seat's output shape, **When** the Orchestrator receives it, **Then** the agent is asked once more with the validation error, and if the second reply is also invalid the run terminates with exit stopped and a reason naming the seat.
3. **Given** the Estimator and Pricing sub-tasks, **When** Work runs, **Then** Pricing's call starts only after the Estimator's task completes, and independent sub-tasks start together.
4. **Given** the Orchestrator's model, **When** it proposes a plan, routing, or wording, **Then** the run engine validates the proposal against the stage rules and seat scopes and rejects anything outside them, falling back to the rule-based plan with a reason saying so.
5. **Given** a recorded live run, **When** it is replayed, **Then** the display is identical, and the prompt toggle works from the recording without calling any model.

---

### User Story 6 - Draft text in the artifact panel (Priority: P3, Part A)

Until compiled pages arrive in S4, the artifact panel shows the latest committed draft as readable text, refreshed in place when a new version is committed.

**Why this priority**: The roadmap's interim; without it the Writer's work is invisible in S2.

**Independent Test**: Commit two draft versions in a run; the panel shows version 2's text and the version label reads v2, with the scroll position kept.

**Acceptance Scenarios**:

1. **Given** a `draft.committed` event, **When** the page renders, **Then** the artifact panel shows that version's markdown as formatted text and the version label.
2. **Given** a later version, **When** it is committed, **Then** the text is replaced in place without clearing the panel, and the scroll position is preserved.
3. **Given** a replay, **When** the draft event is replayed, **Then** the same text shows, read from the recording.

### Edge Cases

- A provider call fails or times out: the call is retried once; a second failure terminates the run with exit stopped and a reason naming the seat and provider. Error text never includes credential values.
- An agent returns prose around its JSON: the JSON object is extracted; if none is found, it counts as an invalid reply.
- The Writer returns a figure without a tag: accepted in S2 and left for the Reviewer to find, as the criteria make it a major finding. Failure routing is S3.
- The Reviewer fails the draft in S2: the run proceeds to Handoff with exit retry_exhausted when rework routing is not yet built. Clean run is expected to pass.
- The knowledge file grows across runs: only the answers section is appended; the standing facts are never rewritten by the application.
- A dataset input page cannot be parsed: the parsing tool returns a confidence of zero for that page and the Intake Analyst lists it as unreliable.
- Ollama is slow to load the model on the first call: the first call has a longer timeout than later calls.

## Requirements *(mandatory)*

### Functional Requirements

Provider registry and models

- **FR-001**: The system MUST build a provider registry at startup from `.env` presence checks and Ollama detection, listing each provider and model as available or unavailable with a reason, and MUST never expose a credential value.
- **FR-002**: Each seat's model MUST be a model object with provider, model id, and label, taken from configuration, and the label MUST be what the agent card shows.
- **FR-003**: A live run MUST NOT start while any seat's provider is unavailable; the refusal MUST name the seat and the reason.
- **FR-004**: Stub mode MUST remain available and MUST be the mode for datasets without curated inputs.

Seats

- **FR-005**: Each seat's system instructions MUST be loaded from `config/electrical-rfp/seats/<seat>.md` with placeholders filled per run, and MUST appear verbatim in the prompt bundle.
- **FR-006**: Each seat's context slice MUST be built by the Orchestrator from the run state according to the roster's sees and does-not-see columns, and MUST be stored in the prompt bundle exactly as sent.
- **FR-007**: Each seat MUST receive exactly its roster tools: Intake document parsing and attachment extraction; Estimator drawing reading and quantity calculation; Pricing price lookup; Writer template rendering and compile trigger; Orchestrator and Reviewer none.
- **FR-008**: The Writer's sources in its context MUST be labelled with the source event id of each specialist output so it can tag figures as `{{value|src:<source_id>}}`.

Tools

- **FR-009**: Document parsing MUST return text per page and a legibility confidence per page between 0 and 1.
- **FR-010**: Drawing reading MUST provide a drawing page as an image to the seat's vision model and return what the model reports with a confidence.
- **FR-011**: Quantity calculation MUST total counts and lengths and apply the waste factors from the estimating conventions deterministically.
- **FR-012**: Price lookup MUST read the dataset's supplier price fixture and return per line unit price, unit, supplier, lead time, extended cost, a long-lead flag against the 28-day threshold, or no match; and totals for material, markup, labour, and grand total when given the markup rate, labour hours, and labour rate.
- **FR-013**: Template rendering MUST fill a markdown response template with the sections named in the knowledge file seed; compile trigger MUST record the draft version and emit `artifact.compiled` with no pages in S2.

Orchestration

- **FR-014**: The Orchestrator MUST run live agents through the S1 stage machine unchanged: stages, human gate, knowledge append at answer time, Handoff, and `run.terminated` last.
- **FR-015**: The Orchestrator's model MUST only propose the plan, reasons, question wording, routing, and the headline; the run engine MUST validate every proposal and MUST fall back to the rule-based choice with a stated reason when a proposal is invalid.
- **FR-016**: Every agent reply MUST be validated against its seat's output shape; one retry with the validation error is allowed; a second invalid reply MUST terminate the run with exit stopped.
- **FR-017**: Agent progress lines MUST become `task.progress` events, each tool invocation MUST become one `tool.called` event, and each model call's usage MUST become one `meter.update` event with real token counts and an estimated cost from a configured price table.
- **FR-018**: Independent sub-tasks MUST start concurrently; dependent sub-tasks MUST start only after their dependencies complete.
- **FR-019**: In S2 the Reviewer MUST receive the draft as markdown text, with its seat file's interim instruction.

Knowledge

- **FR-020**: At Intake the knowledge file for the dataset's client MUST be read into the Intake Analyst's context; answers to Intake clarifications MUST be appended when answered; blocker answers MUST NOT be appended.
- **FR-021**: The knowledge file MUST persist across runs for the same client in a location outside the dataset folder, seeded from the dataset's `knowledge.seed.md` on first use.

Page

- **FR-022**: The artifact panel MUST show the latest committed draft's markdown as formatted text with its version label, updated in place, from events and the recording only.

Evidence (Part B)

- **FR-023**: A live Clean run MUST be recorded and MUST match the Clean run golden stage sequence and exit in the replay-and-compare suite.
- **FR-024**: A second live run for the same client MUST show no repeated clarification.

### Key Entities

- **Provider**: a model source (Bedrock, Anthropic, Google, xAI, Ollama) with availability and a reason.
- **Model object**: provider, model id, label; the seat's runtime model.
- **Seat definition**: role, instructions file, tools, sees, does not see, default model.
- **Context slice**: the exact material a seat was given for one call, stored in the prompt bundle.
- **Tool call**: name, argument summary, result summary, duration; becomes `tool.called`.
- **Agent reply**: the JSON a seat returns, validated against its output shape.
- **Client knowledge file**: per client, seeded once, answers appended by the Orchestrator.
- **Price table**: estimated cost per thousand input and output tokens per model, for meters.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** (Part B): A live Clean run completes from Run to Approve with exit reviewer_pass and matches its golden stage sequence and exit.
- **SC-002** (Part B): The second live run for the same client raises zero clarifications already answered in the knowledge file.
- **SC-003** (Part A): In the scripted-model run, every event validates and the stage sequence and exit match the Clean run golden log.
- **SC-004** (Part A): For all six seats, the bundle scoping test passes on every sees and does-not-see item in the roster.
- **SC-005** (Part A): No credential value from a test `.env` appears in any event, bundle, recording, API response, or log line.
- **SC-006**: Every agent message in a live or scripted run has a prompt toggle whose five sections are populated with what was actually sent.
- **SC-007**: All S1 tests, golden comparisons, screenshot comparisons, and quality gates stay green.

## Assumptions

- Owner decisions of 2026-09-14 in `docs/roadmap.md` are in force, including the rating concern, the missing-schedule concern at Intake, the Orchestrator model scope, the tag syntax, the 28-day long-lead threshold, and lookup totals.
- Default models per seat follow spec 4.3; exact model ids are verified in the plan on the day they are pinned.
- The response template for S2 is a markdown template with the sections the knowledge file seed names; the Typst template arrives in S4.
- Estimated cost uses a configured price table per model; exact provider billing is not reproduced.
- The scripted model used in Part A is a test double of the model interface, not a product feature, and never ships as a selectable model.
- Synthetic test inputs (a small request PDF, one drawing page, a short price fixture) are made for tests and are not the curated dataset.
- Clean run is expected to pass review; if a live Reviewer fails it in S2, the run goes to Handoff as retry_exhausted until S3 builds rework routing.
- Knowledge files for live runs live under a git-ignored `knowledge/` folder, one per client id.

## Out of scope for this slice

Review fail routing, blockers in live form, Stop, Pause, and the cost ceiling in live form (S3). Compiled pages, page images for the Reviewer, provenance hover, Edit and Reject (S4). Model swap in Settings, Single-model mode, chat (S5). Other datasets live. The appraisal workflow.
