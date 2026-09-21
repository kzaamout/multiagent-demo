# Feature Specification: Lettered provenance markers

**Feature Branch**: `013-lettered-markers`

**Created**: 2026-09-21

**Status**: Implemented

**Input**: User description: "Model responses include markers for prices and such. These markers are numbers displayed as superscripts at the end of amounts. Change from numbers to letters to avoid possible confusion where the superscript is thought to be part of the amount."

**Owner decisions (2026-09-21)**: 1a all four surfaces carry the same letter; 2a lowercase; 3b all 26 letters, none skipped; 4a after z the sequence continues aa, ab, ac, as spreadsheet columns do; 5a identifiers the system stores stay as they are, and the letter is a display label worked out in one place and stored beside each marker's position; 6a a recorded run with no stored label keeps showing its number, so it matches its own pages; 7a the Introduction keeps its pinned recording until the owner pins one recorded after this change; 8a the Reviewer is checked by replaying 5 recorded Reviewer requests with the letters in place before any live run; 9a the work happens in its own worktree; 10b the work runs straight through to implementation, then is committed and merged to main.

## Why

Every tagged figure in the compiled bid response carries a provenance marker, printed as a small superscript just after the figure. Today the marker is a number, so a price of $79,063.75 with marker 1 reads on the page as $79,063.75¹, and a reader, whether the prospect on the projector, the presenter at Handoff, or a model reading the page, can take the superscript for another digit of the amount. The engine already works around this for the Reviewer's text copy of the pages (roadmap decision 26: 113 of 125 Reviewer blocker findings said figures disagreed, most because a marker read as extra digits). The page people see still invites the misreading. A letter cannot be mistaken for a digit of an amount.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A figure on the page reads as the figure (Priority: P1)

The presenter shows the compiled bid response in the Deliverable panel, or hands over the PDF. Every tagged amount is followed by a small superscript letter, not a number, so nobody reads the marker as part of the price.

**Why this priority**: This is the whole request. The markers are there to prove where a number came from; if they change what the number appears to be, they undermine the claim they exist to support.

**Independent Test**: Compile a draft with tagged figures and look at the PDF and the page images: each marker is a lowercase letter, in document order a, b, c.

**Acceptance Scenarios**:

1. **Given** a draft with three tagged figures, **When** it is compiled, **Then** the page shows the markers a, b and c in document order, each as a small superscript after its figure, and no marker is a digit.
2. **Given** a draft with 30 tagged figures, **When** it is compiled, **Then** markers 1 to 26 read a to z and markers 27 to 30 read aa, ab, ac and ad.
3. **Given** a draft with no tagged figures, **When** it is compiled, **Then** no marker is printed and the Provenance section says no figures carry a marker, as today.

---

### User Story 2 - Every surface names the marker the same way (Priority: P1)

A marker appears in four places: on the printed page, as the hover button the Deliverable panel lays over it, in the Marker column of the printed Provenance table, and in the Reviewer's text copy of the page. The same marker carries the same letter in all four, so the presenter can point from a Reviewer finding to the figure on the page and to its line in the table without translating.

**Why this priority**: If the page says "c" while the Reviewer's finding says "marker 3", the change creates a new confusion at Handoff. Consistency is part of the fix, not an extra.

**Independent Test**: Compile a draft and compare, for every marker, the letter on the page, the letter on the overlay button, the letter in the Provenance table, and the bracketed letter in the Reviewer's page text.

**Acceptance Scenarios**:

1. **Given** a compiled draft, **When** the presenter hovers the button over the third marker, **Then** the button shows "c" and the feed highlights the source message, as it does today.
2. **Given** the same draft, **When** the Provenance table is read, **Then** its Marker column lists a, b, c in the same order as the page.
3. **Given** the same draft, **When** the Reviewer is sent the page text, **Then** each tagged figure reads with its letter in brackets after it, as in "$79,063.75 [c]", and the Reviewer's instruction describes the markers as letters and asks it to cite a figure by its marker letter.

---

### User Story 3 - Recordings made before the change still replay correctly (Priority: P2)

Runs recorded before this change, including the dataset golden runs and the Introduction's pinned recording, have numbered superscripts baked into their page images. When one of them is replayed, the overlay buttons show the number their pages show, not a letter that disagrees with the page underneath.

**Why this priority**: The demo leans on replay (the Introduction frame, Replay mode, golden replays). A replay whose overlay contradicts its own pages would look broken on the projector. It ranks below the change itself because it only preserves what works today.

**Independent Test**: Replay a recorded run from before the change and check that each overlay button shows the number printed on its page.

**Acceptance Scenarios**:

1. **Given** a run recorded before this change, **When** it is replayed on the Demo page or in the Introduction frame, **Then** each overlay button shows the marker's number, matching its page, and hover still highlights the source message.
2. **Given** a run recorded after this change, **When** it is replayed, **Then** each overlay button shows the marker's letter, matching its page.
3. **Given** any recorded run or golden log, **When** the replay-and-compare suite runs, **Then** it passes without any golden being re-recorded.

---

### User Story 4 - The Reviewer is not thrown by the letters (Priority: P2)

The Reviewer reads the page images and the page text. Before any live run is spent, 5 recorded Reviewer requests are sent again on their drafts compiled with letters, and their answers are compared with what the Reviewer said the first time.

**Why this priority**: The Reviewer's input changes. The project's practice is to test a change to a seat's input by replaying recorded prompts before spending live runs.

**Independent Test**: Replay 5 recorded Reviewer requests with the markers relabelled, and compare verdicts and citations with the recorded replies.

**Acceptance Scenarios**:

1. **Given** 5 recorded Reviewer requests from runs that reached Review, with the recorded draft compiled again so that the page images and the page text both carry the letters, **When** they are sent again to the model that answered them, **Then** no finding reads a marker letter as part of a figure, and every finding that cites a marker cites a letter that exists on the page it names.
2. **Given** the same replays, **When** each verdict is compared with the recorded verdict, **Then** every difference is recorded with the reason found by reading the reply.

### Edge Cases

- **More than 26 markers.** Recorded drafts carry up to 45 markers, and 14 of 216 go past 26. After z the sequence continues aa, ab and so on, and after zz it continues aaa. The label never runs out and never repeats within a draft.
- **A figure that ends in a letter.** A tagged value can end in a unit letter, such as an ampere rating. The marker still follows it as a smaller superscript in the brand colour, which sets it apart. In the Reviewer's text the bracket separates them, as in "200A [d]".
- **A marker whose source is unknown.** It keeps its letter and is shown as unresolved, as numbered markers are today.
- **A human Edit at Handoff.** The recompiled version gets letters from a in document order, like any new version.
- **A recording with a stored label that is empty or missing.** The overlay shows the number.
- **Past Reviewer findings.** Findings recorded before the change say "marker 3". They are history and are not rewritten.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each provenance marker MUST be labelled with lowercase letters in document order: markers 1 to 26 are a to z, and after z the sequence continues aa, ab through az, then ba, and so on, as spreadsheet columns are labelled. All 26 letters are used.
- **FR-002**: The label MUST be worked out in exactly one place, and every surface MUST take it from there: the printed page, the overlay button, the Provenance table, and the Reviewer's page text.
- **FR-003**: The compiled PDF and page images MUST print each marker as its letter, in the same small superscript style, colour and weight as today's number.
- **FR-004**: The Reviewer's text copy of each page MUST write each marker as its letter in square brackets after the figure, as in "$79,063.75 [a]", in place of today's bracketed number.
- **FR-005**: The Marker column of the printed Provenance table MUST list each marker's letter.
- **FR-006**: The record of marker positions kept beside each compiled version MUST store each marker's letter alongside the fields it already has, and the overlay MUST show that stored letter.
- **FR-007**: When the stored letter is missing or empty, as it is in every recording made before this change, the overlay MUST show the marker's number, so it matches the page it sits on.
- **FR-008**: The Reviewer's seat instruction MUST describe the markers as small superscript letters in the page image and the same letter in square brackets in the page text, and MUST ask it to cite a figure by its marker letter. Its rule that a marker is never part of the figure stays.
- **FR-009**: The identifiers the system stores and replays MUST NOT change: the marker's integer number, the tag ids, the source ids, the event types and every event payload. The event schema version stays as it is and no golden log is re-recorded.
- **FR-010**: Hover behaviour MUST NOT change: hovering a marker highlights its source message and scrolls the feed to it, and nothing happens on click.
- **FR-011**: The project records that describe the markers MUST say letters instead of numbers: the design deviation that describes the printed markers, the seat flow and deep dive notes on the Reviewer's page text, and code comments that describe the marker as a number. A decision entry in the roadmap records this change and the owner decisions above.
- **FR-012**: The Introduction's pinned recording MUST NOT change in this work. Pinning a recording made after the change is an owner step, listed in the quickstart.

### Key Entities

- **Provenance marker**: one tagged figure's mark on the compiled pages. It has an integer number in document order (unchanged), a letter label derived from that number (new), the tag id and source id it resolves through (unchanged), and its page and position (unchanged).
- **Marker label**: the letter or letters shown for a marker on every surface, derived from its number by the rule in FR-001.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a draft compiled after the change, 100% of the markers on the pages are letters and none is a digit.
- **SC-002**: For every marker in a compiled draft, the page, the overlay button, the Provenance table and the Reviewer's page text show the same label: 100% agreement across the four surfaces.
- **SC-003**: Every recorded run and golden replay made before the change shows, on each overlay button, the number printed on its page, and the replay-and-compare suite passes with no golden re-recorded.
- **SC-004**: In the 5 replayed Reviewer requests, zero findings read a marker letter as part of a figure, zero findings cite a marker by number, and every cited marker letter exists on the page it names.
- **SC-005**: The event schema version, the event types and every golden log are unchanged, and every quality gate passes.

## Assumptions

- "Model responses" means the compiled bid response, the only place markers are printed. The Writer never writes marker labels itself: it writes provenance tags, and the compile turns them into markers.
- Lowercase superscript letters in the brand colour are distinct enough from uppercase unit letters (such as A for amperes) at the size already used, so no letter is skipped, per decision 3b.
- The overlay button stays its current size. A label of two letters fits it at the current font size; three letters would only appear past 702 markers, far beyond any recorded draft.
- The appraisal workflow is not built yet. It will use the same compile step and inherits the letters with no further work.
- Recorded runs and dataset golden runs are not recompiled. Their pages keep their numbers, and FR-007 keeps their overlays consistent with them.
- The Reviewer replays in User Story 4 cost a few model calls on the models that answered them. They are chosen from runs recorded on or after 2026-09-19, so their page text already carries bracketed markers (roadmap decision 26) and their context already carries the note of what the engine verified.
