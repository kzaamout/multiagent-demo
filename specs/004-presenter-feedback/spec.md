# Feature Specification: Presenter feedback after the S3 review (slice S3b)

**Feature Branch**: `004-presenter-feedback`

**Created**: 2026-09-16

**Status**: Draft

**Input**: User description: "Slice S3b, presenter feedback after the S3 review, exactly as written in docs/spec-input.md 0.7 (change list in the header) and docs/design-deviations.md S3b decisions 1 to 9, on the frozen event schema docs/schema/events-v1.1.0.md. Ten items: nav order, collapsed threads, loop strip stage label and bypassed nodes, arrow pulse, progress-based review limit with review_max_cycles and a recorded stop reason, deterministic prepare_documents in Intake, full run recording with run.json and performance in metrics.json, meter latency, three prospect dataset scaffolds (prospect-a, prospect-b, prospect-c, never naming the prospect), and the bid response vocabulary with config/electrical-rfp renamed config/electrical-bid while machine identifiers stay stable. Branch 004-presenter-feedback already exists and is checked out; reuse it."

**Governing documents**: `docs/spec-input.md` 0.7 (header change list, sections 2.2, 3 stage 1 and stage 5, 6, 7 scenarios 7 to 9), `.specify/memory/constitution.md` 1.2.0, `docs/roadmap.md` (S3 entry and the S3b change request of 2026-09-15), `docs/schema/events-v1.1.0.md` (frozen amendment), `docs/design-deviations.md` (S3b decisions 1 to 9), `CLAUDE.md` working rules 11, 13, 14, 15.

## Purpose of the slice

The owner watched the S3 demo and asked for ten changes. Four are about what the presenter sees on the projector (navigation order, collapsed agent threads, a loop strip that tracks every stage change, an arrow pulse). Three are about how a run behaves and is kept (a review limit that stops when review stops making progress instead of after a fixed two cycles, an Intake tool that prepares the documents deterministically before any model reads them, a recording that holds everything a run produced). Two prepare for real prospect files (three scaffolded prospect datasets, and a document tool that copes with a multi-sheet binder). One is vocabulary: the workflow is a bid response and the incoming documents are a bid request and a tender package.

Items 1 to 4 and 7 to 8 are in the tree at the start of this spec (branch `004-presenter-feedback`, commit `03bed7a`). This specification covers the whole slice so the record is complete; the work still open is items 5, 6, 9 and 10.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Review stops when it stops making progress (Priority: P1)

The presenter runs a scenario whose Reviewer fails the draft more than once. Rework continues while each review cycle reduces the serious findings and repeats none of them, up to a hard ceiling of `review_max_cycles` cycles (default 4). When a cycle makes no progress, repeats a finding, or reaches the ceiling, the run goes to Handoff with the findings unresolved and the termination card names which stop fired.

**Why this priority**: The two-cycle budget was the weakest answer in the S3 review ("why two?"). A progress rule with a named stop reason is the answer the prospect wants to hear.

**Independent Test**: Scripted Reviewer verdicts drive each stop reason on the run engine; the recorded `run.terminated` carries the reason and the card shows it.

**Acceptance Scenarios**:

1. **Given** a failing verdict at cycle 1, **When** the ceiling is not reached, **Then** rework is dispatched whatever the findings, and the retry badge reads 1 of `review_max_cycles` minus one.
2. **Given** a failing verdict at cycle 2 with as many or more blocker and major findings than cycle 1, **When** the Orchestrator applies the rule, **Then** the run goes to Handoff with exit retry_exhausted and stop reason no_progress.
3. **Given** a failing verdict at cycle 2 with fewer serious findings, **When** one finding matches a finding from cycle 1 on normalized evidence text and route target, **Then** the run goes to Handoff with stop reason repeated_finding.
4. **Given** every cycle makes progress with new findings, **When** cycle `review_max_cycles` fails, **Then** the run goes to Handoff with stop reason max_cycles.
5. **Given** any retry_exhausted exit, **When** the termination card renders, **Then** it names the stop reason in plain words and the summary carries `stop_reason`.
6. **Given** a pass at any cycle, **Then** the exit is reviewer_pass and `stop_reason` is null.

---

### User Story 2 - Intake prepares the documents before reading them (Priority: P1)

Before the Intake Analyst reads anything, a deterministic tool splits every PDF in the dataset into single-sheet files, page images, and one text file per sheet, and writes a manifest listing every sheet with its sheet number, title, discipline, "Issued for" stamp, revision date, page count, and legibility confidence. The Analyst reads the manifest and the sheet text; specialists receive sheets by reference. The feed shows one tool call per source file and one for the manifest.

**Why this priority**: The real prospect packages are multi-sheet binders. Without preparation the Analyst cannot read them, and the current tools assume one file per sheet.

**Independent Test**: Run the tool on the synthetic Clean run set and on a multi-page test binder; check the prepared folder, the manifest fields, and that unreadable fields are recorded as unknown.

**Acceptance Scenarios**:

1. **Given** a dataset with one PDF per sheet, **When** Intake starts, **Then** `prepared/` under the run folder holds one PDF, one PNG, and one text file per sheet and a manifest that lists them all.
2. **Given** a multi-page binder, **When** the tool runs, **Then** each page becomes its own sheet entry and the manifest names the source file and page for each.
3. **Given** a sheet whose title block cannot be read for a field (discipline, stamp, revision date), **When** the manifest is written, **Then** that field reads unknown and the Analyst grades the related checklist item as an assumption rather than guessing.
4. **Given** a set whose stamp is not Issued for Tender or Issued for Construction, **When** the Analyst grades readiness, **Then** the issue stamp surfaces as an assumption.
5. **Given** the tool ran, **When** the presenter reads the feed, **Then** one tool call appears per source file and one for the manifest, under the Intake thread, before the Analyst's first progress line.

---

### User Story 3 - Three prospect datasets are ready to receive real inputs (Priority: P2)

The composer offers Prospect A, Prospect B, and Prospect C beside the stock scenarios. Each is a scaffold: a README with the expected behaviour, a brand template, empty input and fixture folders, and a golden log recorded from a stub so Replay and the tests work before the owner drops in redacted inputs. Nothing tracked names the prospect, the project, or the site.

**Why this priority**: The meeting is won on the prospect's own file. The scaffolds let the owner populate and dry-run each one without touching code.

**Independent Test**: The dataset listing shows nine entries in spec order; a stub run of each prospect scaffold reaches its expected exit; a search of tracked files finds no prospect name.

**Acceptance Scenarios**:

1. **Given** the three scaffold folders exist locally, **When** the Demo page loads, **Then** the dataset dropdown lists them as 07, 08 and 09 with neutral labels.
2. **Given** no inputs yet, **When** a prospect scaffold is run, **Then** it runs on the stub with its README's expected exit (Prospect A reviewer_pass after one rework, Prospect B reviewer_pass, Prospect C not_ready).
3. **Given** the owner drops redacted inputs into a scaffold, **When** the run starts, **Then** it runs live with the prepared documents and no code change.
4. **Given** the repository is public, **When** tracked files are searched, **Then** no prospect, project, site, or defect from a shared set is named; the mapping lives only in the ignored datasets folder.

---

### User Story 4 - The demo speaks of bid responses, not RFPs (Priority: P3)

Every piece of display copy says "bid response" for the workflow and "bid request" or "tender package" for the incoming documents. The seat instructions, the checklist, the knowledge seed, the workflow selector, the Settings seat notes, and the Introduction copy follow. The configuration folder is `config/electrical-bid`. Event types, the workflow id, agent ids, dataset ids and question ids do not change, so every recorded run still replays.

**Why this priority**: Vocabulary is what the prospect hears; it costs nothing to get right and it is wrong today.

**Independent Test**: A search of display copy finds no "RFP" outside the design export, the spec history and the playbook; the recorded runs and golden logs replay unchanged.

**Acceptance Scenarios**:

1. **Given** the Demo page, **When** it loads, **Then** the workflow selector reads "Electrical bid response".
2. **Given** a recorded run from S3, **When** it is replayed, **Then** it plays unchanged, because its identifiers are the same.
3. **Given** the seat files moved to `config/electrical-bid`, **When** a live run starts, **Then** every seat loads its instructions from the new folder and the prompt toggle shows the new wording.

---

### User Story 5 - The presenter's view follows the run (Priority: P1, in the tree)

Navigation reads Pre-flight, Introduction, Demo, Settings. Agent threads start collapsed with an activity indicator and an unread count. The loop strip follows every stage change in both run modes, with a stage label, bypassed nodes, filled connectors, and a one-shot pulse on every arrow. Every run keeps every prompt and model reply, a run manifest, and per-seat performance in one metrics file; meter updates carry the provider's latency.

**Why this priority**: These were the first things the owner asked for and they are already built (design-deviations S3b decisions 1 to 5 and 7 to 9, commit `c10fe92`). Listed so the slice record is whole.

**Independent Test**: The screenshot comparison and the recording tests already in the suite.

**Acceptance Scenarios**:

1. **Given** a completed run, **When** its folder is opened, **Then** it holds the events, every prompt, every reply, the manifest, the metrics, and the files the run produced, and Replay needs nothing else.

---

### Edge Cases

- A Reviewer that fails cycle 1 with zero blocker or major findings (only minors) is a contradiction: minors never fail a draft, so the verdict is rejected as malformed before it reaches the loop, as today.
- Two findings in one cycle with the same evidence are counted once for the repeat check; a finding repeated in the same cycle is not a repeat across cycles.
- A cost ceiling trip during rework ends the run with exit cost_ceiling, never retry_exhausted.
- `review_max_cycles` of 1 means the first fail goes to Handoff with stop reason max_cycles.
- A PDF that cannot be opened is listed in the manifest as unreadable with every field unknown, and the Analyst grades the drawing set from what it can read.
- A binder page with no text layer gets an empty text file, legibility 0.3, and unknown for every title block field.
- A prospect scaffold with a request file but no drawings is not curated and runs on the stub; the README says so.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The run engine MUST replace the fixed retry budget with the progress rule in spec-input 0.7 stage 5: after a failing verdict at cycle c, rework continues only if c is 1 or the blocker plus major count is strictly lower than the previous cycle; no finding matches a previous-cycle finding on normalized evidence text plus route target; c is below `review_max_cycles`; and the cost ceiling has not tripped.
- **FR-002**: `review_max_cycles` MUST be configurable with default 4, recorded in the run manifest's config snapshot, and reported by the API so the retry badge shows the maximum number of reworks (`review_max_cycles` minus one).
- **FR-003**: On retry_exhausted the engine MUST record `summary.stop_reason` as one of no_progress, repeated_finding, max_cycles, evaluated in that order when more than one condition holds, and the termination card MUST name it in plain words.
- **FR-004**: The typed event models MUST move to schema 1.1.0 with the additive fields the frozen amendment lists (`stop_reason`, `latency_ms`, `stage.changed` permitted in a Single-model run, `budget` defined as the maximum reworks) and the JSON export MUST match the document.
- **FR-005**: Golden logs MUST be re-recorded from the stubs so `retry.incremented` and `summary.retries` carry the new budget; stage sequences and exits do not change.
- **FR-006**: Intake MUST run a deterministic `prepare_documents` tool (no model call) before its first model call, producing per-sheet PDF, PNG and text files and a manifest under `runs/<run_id>/prepared/`, and emitting one `tool.called` per source file plus one for the manifest.
- **FR-007**: The manifest MUST record `unknown` for any field the tool cannot read (discipline, "Issued for" stamp, revision date, sheet number, title) and never a guessed value; the readiness checklist MUST grade an unknown or non-tender stamp as an assumption.
- **FR-008**: Specialists MUST receive prepared sheets by reference; the Estimator's drawing tool MUST resolve a sheet name against the prepared folder first and the dataset's drawings folder second.
- **FR-009**: The three prospect datasets MUST be registered as `prospect-a`, `prospect-b`, `prospect-c` (labels Prospect A, B, C, numbers 07 to 09) with stub scenarios matching spec section 7 scenarios 7 to 9 and golden logs recorded from them.
- **FR-010**: No tracked file MAY name a prospect, their project, their site, or a defect in a set they shared; scaffold READMEs describe the expected behaviour in neutral terms and the mapping stays in the ignored datasets folder.
- **FR-011**: Display copy MUST say "bid response", "bid request" and "tender package"; the seat configuration folder MUST be `config/electrical-bid`; machine identifiers (workflow id, event types, agent ids, dataset ids, question ids) MUST NOT change.
- **FR-012**: The `RETRY_BUDGET` setting and `{retry_budget}` placeholder MUST be replaced by `REVIEW_MAX_CYCLES` and `{review_max_cycles}`; the seats README table follows.
- **FR-013**: The existing tests for a two-fail budget MUST be replaced by tests for each stop reason, and the visual and API tests updated for the new badge arithmetic.

### Key Entities

- **Review cycle**: one Reviewer verdict on one draft version; carries the blocker plus major count and the normalized findings used by the next cycle's progress check.
- **Stop reason**: why review stopped on a retry_exhausted exit: no_progress, repeated_finding, or max_cycles.
- **Prepared sheet**: one page of one source PDF, with its own PDF, PNG and text file and a manifest row (source file, page, sheet number, title, discipline, stamp, revision date, page count, legibility confidence), any field of which may be unknown.
- **Prospect scaffold**: a dataset folder with README, brand template, empty inputs and fixtures, and a stub golden log, waiting for redacted inputs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Each of the three stop reasons is produced by a scripted run and named on the termination card; the quality gates pass.
- **SC-002**: A run on the synthetic Clean run set shows six preparation tool calls under Intake before the Analyst's first progress line, and the prepared folder holds five sheets with every manifest field filled or unknown.
- **SC-003**: The tool run locally on the owner's three real binders (never committed) produces a manifest for every page, with no exception and no guessed field.
- **SC-004**: The dataset dropdown lists nine entries; each prospect scaffold's stub run matches its golden log on stage sequence and exit.
- **SC-005**: A search of tracked display copy for "RFP" returns nothing outside `design/`, `docs/spec-input.md`, `docs/roadmap.md`, `docs/sales-playbook.md`, `docs/design-brief.md`, and history; every S3 recording under `runs/` still replays.

## Assumptions

- The workflow id stays `electrical_rfp`; only the configuration folder and display copy are renamed (owner decision pending on the alternative; see the session's decision list).
- With the default of 4 cycles the retry badge reads "of 3"; the screenshot comparison masks that digit and the deviation is recorded.
- Stop reasons are evaluated in the order no_progress, repeated_finding, max_cycles.
- Page images from preparation are rendered at a resolution capped near 4000 pixels on the long side so a large binder stays within tens of megabytes.
- The raw prospect binders stay where the owner put them until redacted; the scaffolds ship with empty inputs.
- `CLAUDE.md` is not edited by this slice.
