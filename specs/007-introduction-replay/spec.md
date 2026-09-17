# Feature Specification: Introduction tab and public replay (slice S6)

**Feature Branch**: `007-introduction-replay`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Slice S6, Introduction tab and public replay, as written in docs/roadmap.md "S6. Introduction tab and public replay" and docs/spec-input.md 0.7 sections 2.1, 2.8, 6 (recording and public Replay), 8 (Introduction PDF), 9 M6, 11 (AgentCore name check), with the content in content/intro/*.md, docs/design-brief.md section 11, and design/README.md Introduction notes. Owner decisions 2026-09-17: 1a record a fresh Planted inconsistency run under the concern check and pin it, falling back to run f2dda488; 2a the two diagrams are inline SVG on the page and the same SVG files go into the Typst PDF; 3a the loop diagram reuses the Demo loop strip markup in a static fully-lit state with the backward arrows labelled; 4a the replay frame is an iframe of a read-only Demo variant served by a public endpoint that only serves the pinned run id; 5a eight team cards, the six seats plus the two appraisal swap-ins, expanding on click; 6a verify the Strands Agents and Bedrock AgentCore names against current documentation and change the copy only where a name is wrong; 7a the Introduction PDF has both a script and a route."

**Governing documents**: `docs/spec-input.md` 0.7 (2.1, 2.8, 6 public Replay, 8, 9 M6, 10 criterion 3, 11), `.specify/memory/constitution.md` 1.2.0, `docs/roadmap.md` S6 entry, `docs/design-brief.md` 11 and 12, `design/README.md` (Introduction notes and the loop diagram decision), `content/intro/*.md` (the copy, never rewritten here), `CLAUDE.md` rules 3, 6, 11, 13.

## Purpose of the slice

A prospect or a salesperson opens the public Introduction page and reads what the system is, how it is built, how the loop runs, who the team is, how the agents differ, how it becomes real in their AWS account, and the FAQ, with the three diagrams, expandable team cards, and, at the bottom, a read-only replay of one recorded run playing in the real Demo renderer. The page exports to a PDF through the S4 pipeline for the leave-behind. Nothing on the page links a stranger into the Demo, Settings or Pre-flight pages.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The seven sections read in order with the copy as written (Priority: P1)

A visitor opens the Introduction page without logging in and reads the seven sections in the order the spec fixes, rendered from the content files with their headings, paragraphs, bold runs, lists and the one table, in the export's typography. The header is the shared header without the workflow selector.

**Why this priority**: The page is the leave-behind and the first thing a prospect sees; the copy is a controlled source and must reach the page whole.

**Independent Test**: A content diff between each rendered section's text and its markdown file is empty apart from markup; the screenshot comparison against the export's partial capture passes; no em dash appears.

**Acceptance Scenarios**:

1. **Given** the content folder, **When** the page renders, **Then** the sections appear in the order what it is, architecture, the agentic loop, the team, how agents differ, how this becomes real, FAQ, each with its heading and every paragraph, list item and table row of its file.
2. **Given** the header, **When** the page loads, **Then** it carries the product name, the navigation in the order Pre-flight, Introduction, Demo, Settings with Introduction marked current, the pre-flight indicator and the build stamp, and no workflow selector.
3. **Given** the page is opened with no session, **Then** it renders in full; the other three pages are not reachable from it without the login the S7 slice adds (until then their links behave as today).

---

### User Story 2 - The three diagrams show the real shapes (Priority: P1)

The architecture diagram shows the three bands the content file describes; the loop diagram is the Demo loop strip, fully lit, with the three backward arrows labelled and the terminal card listing the four exits; the demo-versus-production diagram is the architecture drawn twice with laptop badges on the left and AgentCore badges on the right.

**Why this priority**: The diagrams are what a salesperson points at. Reusing the loop strip keeps the Introduction and the Demo consistent by construction.

**Independent Test**: Each diagram is an inline SVG element with the named parts present; the loop diagram's six nodes carry the same labels as the Demo strip; the PDF contains the same three drawings.

**Acceptance Scenarios**:

1. **Given** the architecture section, **Then** its SVG shows Renderers (Web UI, Slack greyed with a "future" tag), the event stream bus, the Orchestrator box with the six-stage strip and a retry counter, six agent cards, tool boxes only under the specialists and the Writer, the five provider labels along the bottom with dotted lines to the cards, and the human figure with the single "one door" arrow.
2. **Given** the loop section, **Then** the strip shows Intake, Plan, Work, Assemble, Review and Handoff all lit, forward arrows, the three backward arrows labelled Review to Work, Review to Assemble and Work to Intake, the human icon on Intake, Work and Handoff, the retry badge on Review, and a terminal card off Handoff listing the four exits with Not ready branching off Intake.
3. **Given** the demo-versus-production section, **Then** two copies of the architecture sit side by side, the left titled Demo with laptop badges, the right titled Your AWS account with AgentCore badges on the corresponding boxes.

---

### User Story 3 - The team grid and the expandable cards (Priority: P2)

The team section shows eight agent cards in a two-column grid: the six seats, then the two appraisal specialists in a second row marked as swapping in for the appraisal workflow. Each card shows the avatar, the name pair and role, and the model in grey; clicking expands it to what the agent owns, what it sees, and its tools. Nothing flips.

**Why this priority**: The cards are the same component the feed uses (spec 4.2), so the team is recognisable on the Demo page a minute later.

**Independent Test**: Eight cards render; clicking each toggles its detail; the six seat cards' names, roles and models come from the roster and the seat definitions, not from copy.

**Acceptance Scenarios**:

1. **Given** the page, **Then** the grid holds Orchestrator, Intake Analyst, Estimator, Pricing, Writer, Reviewer, then Case Manager and Market Analyst with the swap-in note.
2. **Given** a card, **When** it is clicked, **Then** it expands to show role, owns, sees and tools, and clicking again collapses it.
3. **Given** the six seats, **Then** their tools and visibility scopes are the seat definitions' lists, so the card cannot disagree with the engine.

---

### User Story 4 - The public replay plays one pinned run (Priority: P1)

At the bottom of the page a frame plays a read-only replay of the pinned run: the loop strip, the feed with its cards, threads and prompt toggles, the compiled pages and their markers, at 1x or 4x. The frame has no composer, no controls beyond replay speed, no Handoff actions, and no link into the Demo. The endpoint that feeds it serves only the run id in configuration and refuses every other id.

**Why this priority**: Spec 2.1 and 6; the replay is the proof behind the copy.

**Independent Test**: A test asks the public endpoint for the pinned run and gets it, asks for another recorded run and gets a refusal, and the frame shows the pinned run's cards.

**Acceptance Scenarios**:

1. **Given** the pinned run id in configuration, **When** the page loads, **Then** the frame plays that run from its recording with the same reducer and renderer as the Demo, at the chosen speed, and its pages appear when the compiled events fire.
2. **Given** any other run id, **When** the public endpoint is asked, **Then** it refuses, and no other route serves recordings without the login S7 adds.
3. **Given** the frame, **Then** it offers replay and speed only; Run, Pause, Stop, Dry intake, dataset choice, Approve, Edit, Reject and downloads are absent, and clicking a card opens it without leaving the frame.
4. **Given** no recording exists for the pinned id, **Then** the frame says so in one sentence and the page still renders.

---

### User Story 5 - The Introduction as a PDF (Priority: P2)

A script and a route produce the Introduction as a PDF through the S4 pipeline: the seven sections' copy, the three diagrams as the same SVG drawings, and the team as a list, on Letter pages in the same template family as the bid response.

**Why this priority**: The leave-behind (S7) bundles it; the roadmap puts the pipeline here.

**Independent Test**: The PDF's page text contains every heading and every paragraph of the seven files; the three drawings are embedded; no em dash.

**Acceptance Scenarios**:

1. **Given** the content files and the diagram SVGs, **When** the script runs, **Then** it writes one PDF whose text carries every heading and paragraph and whose pages show the three diagrams.
2. **Given** the route, **When** it is requested, **Then** it returns the same PDF, regenerated when a content file or a diagram is newer than the file.
3. **Given** the compiler is missing, **Then** the route says so with the tool's name and the script exits with a message.

---

### User Story 6 - The copy is checked before it ships (Priority: P3)

The names of the AWS services and the SDK in the copy are checked against current documentation; a name that is wrong is corrected in the content file with the change listed, and nothing else in the copy changes.

**Why this priority**: Spec section 11 open item; a wrong service name in front of an AWS-literate prospect costs credibility.

**Independent Test**: The record of the check lists each name, the source consulted and whether it changed.

**Acceptance Scenarios**:

1. **Given** the names Bedrock AgentCore Runtime, Gateway, Memory, Observability, Identity, and Strands Agents, **When** checked, **Then** each is confirmed or corrected, and the record is in the slice's research file and the roadmap status.

---

### Edge Cases

- A content file with an HTML comment (the diagram and layout notes) renders without the comment.
- A content file with a table renders it as a table on the page and in the PDF.
- The pinned run id points at a recording that has a compiled version: the frame shows pages; one that predates compiled pages shows the S4 message and no pages.
- The public endpoint is asked for a path outside the pinned run's folder: refused.
- The page is opened at phone width: sections stack, diagrams scale to the width, the frame keeps its aspect.
- A diagram label longer than its box wraps inside the box rather than overflowing.
- The screenshot comparison's reference is the export's partial capture (top of the page only); the rest of the page is reviewed for family consistency.
- Replay speed in the frame is a presenter convenience remembered per browser, never state.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Introduction page MUST render the seven content files in the fixed order as sections, with headings, paragraphs, bold and italic runs, lists and tables, without HTML comments, and MUST NOT rewrite the copy.
- **FR-002**: The page MUST carry the shared header without the workflow selector, with Introduction marked current, and MUST be served without a login.
- **FR-003**: The architecture, loop and demo-versus-production diagrams MUST be inline SVG on the page, drawn from the content files' diagram notes and the design brief, with the parts the acceptance scenarios list.
- **FR-004**: The loop diagram MUST reuse the Demo loop strip's node labels, arrow set and badge, rendered static and fully lit, with the backward arrows labelled and the exits card, and this reuse MUST be recorded as the deviation the export's text-only section requires.
- **FR-005**: The team section MUST render eight agent cards from the roster and seat definitions (six seats) plus the two appraisal seats named in the content file, in the agent card component, expanding on click to role, owns, sees and tools.
- **FR-006**: A public endpoint MUST serve the events, files and prompt bundles of exactly one run id from configuration (`PUBLIC_RUN_ID` in `.env`, defaulting to the run the roadmap names) and MUST refuse any other id; it MUST need no login.
- **FR-007**: The page MUST embed a read-only replay frame fed by that endpoint, using the Demo reducer and renderer, with replay and speed controls only, no composer, no run controls, no Handoff actions and no navigation into the Demo.
- **FR-008**: The frame MUST show the pinned run's compiled pages and markers when the recording has them, and the S4 message when it does not.
- **FR-009**: A script (`scripts/intro_pdf.py`) and a route (`GET /introduction.pdf`) MUST produce the Introduction as a PDF through the S4 pipeline with a Typst template in the response template's family, embedding the three SVG diagrams, regenerated when a source is newer, and MUST name a missing tool.
- **FR-010**: The AWS service and SDK names in the copy MUST be checked against current documentation; corrections are made in the content files only where a name is wrong and each change is listed.
- **FR-011**: Event types, agent ids, dataset ids and the workflow id MUST NOT change (rule 13); the page renders only from events and the files they name (rule 3).
- **FR-012**: The em-dash lint MUST cover the rendered page text, the SVG text and the PDF's text.

### Key Entities

- **Section**: one content file rendered in order: heading, blocks, an optional diagram slot named by the file's comment.
- **Diagram**: an inline SVG for the page and a file for the PDF, one of architecture, loop, demo-versus-production.
- **Team card**: an agent card with the roster's name pair, role and model, plus owns, sees and tools from the seat definition; two appraisal cards from the content file with a swap-in note.
- **Pinned run**: the one run id the public endpoint serves, from configuration, with its recording folder.
- **Introduction PDF**: the compiled leave-behind, regenerated when its sources change.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every one of the seven files, the rendered section's text equals the file's text apart from markup and comments (criterion 3 content diff), and the page has no em dash.
- **SC-002**: The screenshot comparison for the Introduction passes against the export's partial capture, and the below-the-fold sections pass the family-consistency review recorded in the deviations.
- **SC-003**: The public endpoint serves the pinned run and refuses every other run id, proven by a test; no unauthenticated route serves any other recording.
- **SC-004**: The frame plays the pinned run to termination at 4x in the browser test, with its pages and markers on screen.
- **SC-005**: The PDF is produced by both the script and the route; its text carries every heading and paragraph of the seven files and its pages show the three diagrams.
- **SC-006**: The service name check is recorded with a source per name and each change listed.

## Assumptions

- Owner decisions of 2026-09-17: 1a the pinned run is a fresh Planted inconsistency recording under the concern check, falling back to f2dda488; 2a inline SVG diagrams shared with the PDF; 3a the loop strip reused statically; 4a an iframe of a read-only Demo variant on a public endpoint that serves one run id; 5a eight team cards; 6a service names verified and corrected only where wrong; 7a a script and a route for the PDF.
- The export's Introduction bundle is flattened the way the Demo page was (spec 2.10, design/README.md): its markup and styles are taken as the appearance; the export's replay mock and its text-only loop section are recorded deviations.
- The appraisal seats (Case Manager, Market Analyst) do not exist in the roster until S8; their two cards take name pair, role and one-line description from the content file and show "swaps in for the appraisal workflow" in place of a model.
- The read-only Demo variant is the existing Demo page with a public flag that hides the composer, run controls and Handoff actions and loads the pinned run; it lives in the same files as the Demo page and reuses its scripts unchanged.
- The Introduction PDF template is a second Typst template beside the response template, Letter, single column, the brand colour replaced by the product's ink colour since the page is not a prospect deliverable.
- `PUBLIC_RUN_ID` is read from `.env` like the other settings; the default is written into `app/config.py` when the pinned recording exists.
- The login that hides Demo, Settings and Pre-flight is S7's; this slice makes sure nothing it adds needs one and that the Introduction and its endpoint stay outside it.

## Constitution check

- I Demo, not product: one public page, one pinned run, no run browser, no analytics.
- II Events only: the frame renders the recording's events through the Demo reducer; the page is static content.
- III, IV: no run is started or touched; the endpoint is read-only.
- V Roles are real: the six seat cards read the roster and seat definitions.
- VIII Reliability: the frame plays from the recording folder alone.
- IX Writing rules: content files are the copy; lint covers page, SVG and PDF text.
- X, XI Controlled sources: copy from `content/intro/`, appearance from `design/Introduction.html`; the loop diagram and the replay frame are recorded deviations.
- XIII Acceptance recorded: content diff, screenshot comparison, endpoint test, browser replay test, PDF test.
- XIV Projector: the page is read on a laptop or phone rather than a projector, but body text keeps the export's sizes.
- XV Dependencies: none added; Typst and pandoc are already recorded.
- Non-goals: no multi-user viewing, no dashboard of past runs; one pinned run, read-only.
