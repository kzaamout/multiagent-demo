# Feature Specification: Compiled deliverable and provenance (slice S4)

**Feature Branch**: `005-compiled-deliverable`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Slice S4, compiled deliverable and provenance, exactly as written in docs/roadmap.md "S4. Compiled deliverable and provenance" and docs/spec-input.md 0.7 sections 2.2 (artifact panel, termination card), 2.6, 3 stages 4 to 6, 6 (draft.committed, artifact.compiled, handoff.ready, human.approved), 8. Owner decisions on 2026-09-17: reuse the career-hub compile pipeline (pandoc markdown to Typst with a template, typst compile to PDF, typst compile --format png --ppi 150 for page images) as a Python module with templates/rfp-response.typ; provenance tags render as small numbered markers on the page and typst query returns their positions for hover hotspots on the PNG; the Reviewer receives the page PNGs plus the extracted page text; Edit at Handoff is a text area replacing the pages with the draft markdown, Save recompiles once with actor human then the run terminates; the run timeline download is a PDF rendered from the event log through the same pipeline; stub runs compile a fixture draft for real so goldens regain artifact.compiled events; the cover renders a wordmark from prospect_name and primary_colour when brand.yaml's logo file is missing; Letter, single column, brand colour on cover and headings. The S2 and S3 interims (Reviewer judges markdown text, draft shown as text in the panel) are removed. Work happens in the git worktree C:\Users\Khobaib\OneDrive\Desktop\code\multiagent-demo-s4 on the existing branch 005-compiled-deliverable; the feature directory is specs/005-compiled-deliverable."

**Governing documents**: `docs/spec-input.md` 0.7 (sections 2.2 artifact panel and termination card, 2.6, 3 stages 4 to 6 and exits, 6 events `draft.committed`, `artifact.compiled`, `handoff.ready`, `human.approved`, 8), `.specify/memory/constitution.md` 1.2.0, `docs/roadmap.md` (S4 entry and its interims note), `docs/schema/events-v1.1.0.md` (frozen), `design/README.md` and `docs/design-deviations.md` (Edit and Reject added in the export's button style), `CLAUDE.md` working rules 3, 4, 6, 8, 13. The owner's eight decisions of 2026-09-17 are recorded in the Assumptions section.

## Purpose of the slice

Until now the artifact panel has shown the Writer's draft as text and the Reviewer has judged markdown. This slice makes the deliverable real: on every draft commit the proposal is compiled to a PDF and page images, the panel shows the pages and refreshes them in place, the Reviewer judges the pages, every figure on a page is a hover target that jumps the feed to the specialist message it came from, and at Handoff the presenter approves, edits once, or rejects, and downloads the PDF and a run timeline. The cover carries the prospect's brand. The S2 and S3 interims are removed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The proposal appears as pages and refreshes in place (Priority: P1)

The presenter watches the Writer commit a draft. Within seconds the artifact panel shows the compiled pages with a version label. When the Writer commits a second version after a rework, the pages swap in place without a flicker and the panel keeps its scroll position. A stub run and a Replay show pages the same way, from files in the run folder.

**Why this priority**: The compiled document is what the prospect takes away. Everything else in the slice hangs off the pages existing.

**Independent Test**: Run the Clean run dataset on the stubs, watch the panel, then replay the recording with the datasets folder removed.

**Acceptance Scenarios**:

1. **Given** a run in Assemble, **When** the Writer commits draft version 1, **Then** a compiled event follows with the PDF and one image per page, and the panel shows those pages with the label "v1" within ten seconds of the commit.
2. **Given** the panel is scrolled to page 2 of version 1, **When** version 2 is compiled, **Then** the page images are replaced in place, the scroll position is unchanged, and no empty frame is shown in between.
3. **Given** a recorded run, **When** it is replayed, **Then** the pages come from the run folder and appear at the same moments the compiled events fire; the dataset and the compiler are not needed.
4. **Given** a stub run of any of the nine scenario datasets, **When** it commits its fixture draft, **Then** a real compile produces the pages and the golden log carries the compiled event after every commit.

---

### User Story 2 - Every figure has a paper trail on the page (Priority: P1)

The presenter hovers a small numbered marker beside a figure on a page. The feed scrolls to the specialist message that produced that figure and highlights it. Moving off the marker removes the highlight. Nothing beyond hover.

**Why this priority**: Provenance is principle VII and the demo's answer to "how do I know it did not make that up".

**Independent Test**: Replay the Planted inconsistency recording, hover every marker on every page, and confirm the highlighted message is the source named in the draft's tag.

**Acceptance Scenarios**:

1. **Given** a compiled page with markers, **When** the presenter hovers marker 7, **Then** the feed scrolls to the message whose source id the Writer tagged for that figure and highlights it, and the marker itself is highlighted.
2. **Given** the presenter moves off the marker, **Then** the highlight on the message and the marker clears.
3. **Given** a figure whose tag names a source that is not in the run, **When** the draft is compiled, **Then** the marker is rendered with no target, the provenance appendix lists it as unresolved, and the Reviewer sees the same page (the Writer's reply validation already rejects unknown source ids before the commit, so this case only arises on a human edit).
4. **Given** a page image at any zoom the panel offers, **When** the presenter hovers where a marker is drawn, **Then** the hotspot matches the marker position on that image.

---

### User Story 3 - The Reviewer judges the pages (Priority: P1)

The Reviewer receives the compiled page images and the text extracted from each page, together with the brief and the criteria, and never the markdown. Presentation findings (legibility, cover, placeholder text) become possible. The interim markdown path is gone.

**Why this priority**: Spec stage 5 says the Reviewer sees page images. Judging text was an interim the roadmap commits S4 to remove.

**Independent Test**: A scripted Reviewer records what it was given; the test asserts pages and page text, not markdown. A live run on the Clean run dataset ends with a verdict that cites page numbers.

**Acceptance Scenarios**:

1. **Given** a compiled version, **When** the Reviewer is dispatched, **Then** its prompt bundle carries every page image of that version and the text of each page, and the recorded bundle shows the same.
2. **Given** the Reviewer's model cannot take images, **When** the run starts, **Then** the run refuses to start with a message naming the seat, as it does today for a missing credential.
3. **Given** a verdict finding, **When** it is rendered, **Then** its evidence names a page number.

---

### User Story 4 - Handoff: approve, edit once, reject, download (Priority: P2)

At Handoff the presenter sees Approve, Edit, Reject, Download PDF and Download run timeline. Approve ends the run. Edit replaces the pages with the draft text in a text area; Save recompiles once as the human's own commit, the pages refresh, and the run ends. Reject records notes and ends the run with the same exit. The downloads give the final PDF and a timeline PDF rendered from the event log.

**Why this priority**: The human gate is the demo's closing beat. Approve and downloads exist in part today; Edit and Reject are new controls added in the export's button style.

**Independent Test**: Drive a stub run to Handoff in the browser and exercise each control; check the recorded events and the downloaded files.

**Acceptance Scenarios**:

1. **Given** Handoff is entered, **When** the package event is emitted, **Then** it names the PDF, the page images, the verdict, the unresolved findings, the assumptions accepted, the clarifications asked and answered, and the event log path.
2. **Given** the presenter clicks Edit, changes one figure's text and clicks Save, **Then** exactly one more draft commit and one more compiled event follow with the human as actor, the pages refresh, and the run terminates with the same exit as the package event.
3. **Given** the presenter clicks Reject and enters notes, **Then** the decision is recorded with the notes and the run terminates with the same exit; nothing re-enters the loop.
4. **Given** the run has terminated after Handoff, **When** the presenter clicks Download PDF, **Then** the final version's PDF is delivered; **When** they click Download run timeline, **Then** a PDF listing every event of the run in order with time, stage, actor and summary is delivered.
5. **Given** a Single-model run or an exit that does not pass through Handoff, **Then** Edit and Reject are not offered.

---

### User Story 5 - The cover carries the prospect's brand (Priority: P2)

The proposal cover shows the prospect's name and logo in the dataset's brand colour, on Letter pages in a single column, with the brand colour on headings. When the dataset has no logo file, a wordmark drawn from the prospect name in the brand colour stands in.

**Why this priority**: The playbook has the presenter set the brand so the deliverable cover carries the prospect's name and logo; the demo is personal or it is generic.

**Independent Test**: Compile the fixture draft against each dataset's brand file and inspect page 1.

**Acceptance Scenarios**:

1. **Given** a dataset with a logo file, **Then** page 1 shows the logo, the prospect name, and the brand colour.
2. **Given** a dataset whose brand file points at a missing logo, **Then** page 1 shows the wordmark instead and the compile does not fail.
3. **Given** a brand file with a malformed colour, **Then** the compile uses the template's default colour and the run records an assumption naming the field.

---

### User Story 6 - The interims are gone and the record is whole (Priority: P3)

The text view of the draft in the panel and the markdown path to the Reviewer are removed. Every golden log carries the compiled event after every commit. The dependency record explains the compiler and the pipeline it reuses.

**Why this priority**: Roadmap S4 evidence. Leaving two paths alive would let the demo drift back to text.

**Independent Test**: The suite, the golden comparison, and a search of the front end for the text renderer.

**Acceptance Scenarios**:

1. **Given** the slice is complete, **Then** no code path renders the draft as text in the panel and no code path sends markdown to the Reviewer.
2. **Given** the nine goldens are re-recorded, **Then** each carries a compiled event after every commit and the replay-and-compare suite passes on stage sequence and exit.

---

### Edge Cases

- A draft the compiler rejects (malformed table, unbalanced markup) is treated like a malformed reply: the Writer is asked again once with the compiler's message, and a second failure ends the run the way a twice-invalid reply does today. A human edit that fails to compile is reported in the text area and the previous pages stay on screen; the run does not terminate until a version compiles.
- The compiler or the converter is missing from the machine: a live or stub run that needs a compile refuses to start with a message naming the missing tool, and tests that need the compiler are skipped with that reason, the way dataset tests are skipped without datasets.
- A figure tag inside a table cell or a heading still yields one marker and one hotspot.
- Two tags for the same figure on one line yield two markers.
- A page with no markers has no hotspots and the hover layer is empty.
- A ten-page draft compiles within the same limit as a two-page one; the artifact panel lists pages in order and lazy loads images below the fold.
- Replay of an S3 recording that has no compiled events shows the panel empty with the message that the recording predates compiled pages; it does not attempt to compile.
- The run folder keeps every version's PDF and pages; nothing is overwritten by a later version.
- A wordmark for a very long prospect name wraps to two lines and stays inside the cover margins.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: On every draft commit the system MUST compile the draft to a PDF and one image per page, write them under the run folder in a per-version location, and emit the compiled event naming the PDF and the page images, in that order, before any Reviewer dispatch.
- **FR-002**: The compile MUST reuse the two-step pipeline of the career-hub script (markdown to a typesetting source with a template, then the source to PDF and to page images at 150 pixels per inch), kept as a module the run engine calls, with the intermediate source retained beside the outputs.
- **FR-003**: A response template MUST exist for the proposal (`templates/rfp-response.typ`) matching the sections of the markdown template, Letter page size, single column, brand colour on the cover and headings, and a timeline template MUST exist for the run timeline.
- **FR-004**: Every provenance tag in the draft MUST render as a small numbered marker beside its figure, the provenance appendix MUST list marker number, source id and the specialist message it points to, and the marker positions for every page MUST be written beside the page images in a form the panel can read without a schema change.
- **FR-005**: The artifact panel MUST render the pages of the latest compiled version from the run folder, replace them in place on each new compiled event without flicker, preserve scroll, show the version label, and lazy load pages below the fold.
- **FR-006**: Hovering a marker MUST scroll the feed to the source message and highlight both; leaving the marker MUST clear both. Nothing beyond hover.
- **FR-007**: The Reviewer's prompt bundle MUST carry the page images and the extracted text of each page of the version under review and MUST NOT carry the markdown; the interim text path is removed from the engine, the stubs, and the panel.
- **FR-008**: A seat model that cannot accept images MUST make a live run refuse to start with a message naming the seat.
- **FR-009**: On entering Handoff the package event MUST be populated with the final PDF, the page images, the verdict event id, unresolved findings, assumptions accepted, clarifications asked and answered, and the event log path.
- **FR-010**: Approve, Edit, Reject, Download PDF and Download run timeline MUST be offered at Handoff for the two exits that pass through it and nowhere else; Edit and Reject use the export's button family and are recorded as design deviations.
- **FR-011**: Edit MUST show the current draft markdown in a text area in place of the pages; Save MUST commit exactly one new version with the human as actor, compile it, and terminate the run with the Handoff exit; Cancel restores the pages. Reject MUST record the notes and terminate with the same exit. Neither re-enters the loop.
- **FR-012**: The run timeline download MUST be a PDF rendered from the event log through the same pipeline, one row per event with time from run start, stage, actor, type and a one-line summary.
- **FR-013**: The cover MUST draw the prospect name, logo and colour from the dataset's brand file; a missing logo file MUST fall back to a wordmark from the prospect name; a malformed colour MUST fall back to the template default and record an assumption.
- **FR-014**: Stub runs MUST compile a fixture draft for real so every scenario's golden log carries a compiled event after every commit; goldens are re-recorded once with the compiler present and the schema version is unchanged.
- **FR-015**: A compile failure on a Writer draft MUST be fed back to the Writer as a rejected reply with the compiler's message; a second failure MUST end the run as a twice-invalid reply does today. A compile failure on a human edit MUST be shown in the text area with the previous pages retained.
- **FR-016**: When the compiler or converter is absent, runs that need them MUST refuse to start naming the tool, and tests that need them MUST skip naming the tool.
- **FR-017**: `docs/dependencies.md` MUST record the typesetting compiler, the converter, and the reused pipeline with the rationale the constitution requires.
- **FR-018**: Event types, agent ids, dataset ids and the workflow id MUST NOT change (rule 13); the frozen 1.1.0 event payloads for the four events MUST be used as written.

### Key Entities

- **Compiled version**: one draft version's PDF, page images, retained typesetting source, marker positions and extracted page text, all under the run folder.
- **Provenance marker**: a numbered mark on a page tied to one tag in the draft, one source id, and one specialist message; carries a page number and a position on that page's image.
- **Handoff package**: the final compiled version plus the verdict, unresolved findings, assumptions, clarifications and event log path, as the frozen schema lists.
- **Brand**: prospect name, logo path and primary colour from the dataset's brand file, with the wordmark and default colour fallbacks.
- **Run timeline**: a PDF rendering of the event log for a run, produced on demand.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a live run, pages appear in the panel within ten seconds of every draft commit, measured from the commit event to the compiled event.
- **SC-002**: On the Planted inconsistency recording, hovering every marker on every page highlights the message whose source id the draft tagged, with zero misses, checked by a test over all markers.
- **SC-003**: All nine golden logs carry a compiled event after every commit and the replay-and-compare suite passes on stage sequence and exit for each.
- **SC-004**: The terminated-state screenshot comparison passes with pages, markers and Handoff actions on screen, and a browser test shows a version swap keeping scroll with no empty frame.
- **SC-005**: A Handoff edit produces exactly one further commit and one further compiled event with the human as actor, followed by termination with the Handoff exit.
- **SC-006**: Page 1 for every scenario dataset shows the prospect name and brand colour; datasets without a logo file show the wordmark.
- **SC-007**: A search of the engine and the front end finds no path that sends markdown to the Reviewer or renders the draft as text.
- **SC-008**: A recorded run replays with the datasets folder removed and no compiler installed, showing its pages from the run folder.

## Assumptions

- Owner decisions of 2026-09-17: 1b the career-hub compile pipeline is reused (pandoc to a typesetting source with a template, then the compiler to PDF and to page images at 150 pixels per inch); 2a markers are visible numbered marks with positions from a compiler query; 3b the Reviewer gets page images plus extracted page text; 4a Edit is a text area with one recompile as the human; 5a the timeline download is a PDF through the same pipeline; 6a stubs compile for real; 7a wordmark fallback for a missing logo; 8a Letter, single column, brand colour on cover and headings.
- The career-hub script at the owner's path is the reference for the pipeline shape and its page-image export; its resume-specific contract and signal vocabulary are not adopted. The module is written for this engine.
- Marker positions are written as a file beside the page images, so the frozen schema needs no field for them; the panel fetches it with the images.
- Page text for the Reviewer is extracted from the compiled PDF with the same reader the preparation tool uses, so what the Reviewer reads is what is on the page.
- The Reviewer stays on a model that reads images; on this machine that is Gemma 4 12B, which the model registry marks as taking image input.
- A Typst compile of a ten-page proposal takes about one second on the presenter laptop; the ten-second limit in SC-001 leaves room for pandoc and the image export.
- The Compare strip above the panel belongs to slice S5 and is untouched here.
- The Performance toggle and download on the termination card exist from S3b and are untouched here.
- `CLAUDE.md` is not edited by this slice beyond the dependency pointer if one is needed.

## Constitution check

- I Demo, not product: the compile serves the presenter's screen and the leave-behind; no batch export, no document management.
- II Schema first, events only: the four events are used as frozen in 1.1.0; marker positions and page text live in the run folder, not in new fields.
- III One owner of state: the Orchestrator emits the compiled and package events and terminates after Edit or Reject; the compile module returns files and never emits.
- VI Design for the failure: a compile failure follows the existing twice-invalid path; no new exit.
- VII Provenance: every figure's marker resolves to a message or is listed as unresolved; the Writer's reply validation stays in front of the commit.
- VIII Reliability: every version's files are kept in the run folder and Replay needs nothing else.
- XV Dependencies: the compiler, the converter and the reused pipeline are recorded with rationale.
- XVIII Design export wired, not redesigned: Edit and Reject are added in the export's button family and recorded as deviations; the panel keeps the export's layout.
- Non-goals: provenance stays hover only; Reject terminates and never re-enters the loop; nothing is sent externally.
