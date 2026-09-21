# Research: Lettered provenance markers

Phase 0 for `specs/013-lettered-markers/spec.md`. The owner's ten decisions left no open question in the spec; these notes record how each design choice was settled.

## R1. The label rule

**Decision**: bijective base 26 over lowercase a to z. Marker 1 is a, 26 is z, 27 is aa, 52 is az, 53 is ba, 702 is zz, 703 is aaa. Written as a loop of `divmod(n - 1, 26)`, collecting letters from the right.

**Rationale**: this is how spreadsheet columns count (owner decision 4a). Every label is unique, the labels sort by length and then alphabetically, and two letters cover 702 markers against the 45 on record.

**Alternatives considered**: doubled letters (aa, bb, cc), rejected by the owner (4b); skipping i, l and o, rejected by the owner (3b); Typst's own `numbering("a", n)`, rejected because it would compute the label a second time inside the template, while the table, `markers.json` and the overlay need it in Python (FR-002).

## R2. Where the label is computed and how it reaches each surface

**Decision**: one function, `marker_label(n)`, in `app/compile/markers.py`, the module that already numbers the markers. `prepare_markdown` stores the label on each `MarkerDraft` and writes it into the raw Typst call as a string argument: `#prov(n, "a", "pricing")`. The template prints the label it is given. `appendix` prints `m.label` in the Marker column. `pipeline._typst_markers` copies the label onto each `Marker`, so `markers.json` carries it. The overlay reads `m.label`.

**Rationale**: every surface takes the label from the one place that makes it (FR-002). The template, the table and the overlay only display a string. The integer `n` stays everywhere it is used as an identifier: the metadata Typst reports for `typst query`, the join between the query result and the drafts, `data-marker` in the DOM, and the `unresolved` list in the `artifact.compiled` payload (FR-009).

**Alternatives considered**: the overlay working out the letter from `n` in JavaScript, rejected because it is a second implementation of the rule and because it would put letters over the numbered pages of old recordings (decision 6a); passing only the label to Typst and dropping `n`, rejected because `n` joins the query result to the drafts and is an identifier.

## R3. How a superscript letter renders

**Decision**: keep the template's style exactly: `super(text(size: 6.5pt, fill: brand, weight: 600)[label])`.

**Rationale**: a test compile on this machine with Typst 0.15.1 printed $79,063.75 with a superscript a, 200A with a superscript d, and $13,284.80 with a superscript aa, all in the same size, colour and weight as today's numbers (FR-003). The brand colour and the smaller size set a letter marker apart from a unit letter such as the A in 200A (spec edge case).

**Alternatives considered**: a larger marker, or brackets on the displayed page; neither was asked for, and the printed size is recorded as small by design in the S4 status.

## R4. The Reviewer's page text

**Decision**: in the text compile (`--input markers=text`) the template writes ` [a]` where it wrote ` [1]`. Nothing else in the page text changes.

**Rationale**: the bracket keeps the marker apart from its figure, which is why roadmap decision 26 introduced it; the letter now also matches the page image the Reviewer sees beside it. `app/live/materials.py` hands `pages.json` to the Reviewer unchanged, and no other code reads `pages.json` or parses the bracketed marker (searched `app/` and `scripts/`).

**Alternatives considered**: none; decision 1a puts the same letter on all four surfaces.

## R5. Recordings made before the change

**Decision**: `label` is optional when `markers.json` is read. The overlay shows `m.label` when it is a non-empty string and `String(m.n)` otherwise. Nothing is recompiled.

**Rationale**: 216 compiled drafts under `runs/`, every dataset's `golden-artifacts/` and the Introduction's pinned run `f2dda488` have numbers printed on their page images. A label-less `markers.json` is exactly those recordings, so the fallback keeps the overlay in agreement with the page underneath it (decision 6a, FR-007). No Python code reads `markers.json` after writing it, so there is no second reader to update (searched `app/` and `scripts/`).

**Alternatives considered**: recompiling recordings in place, rejected because a recording is what the run produced (constitution VIII); always showing letters, rejected by the owner (6b).

## R6. The Reviewer's seat instruction

**Decision**: reword the first paragraph of `config/electrical-bid/seats/reviewer.md`: each figure carries a small superscript letter in the page image, and the same letter in square brackets in the page text, as in $79,063.75 [a]; the marker is never part of the figure, so $79,063.75 with marker a and $79,063.75 with marker b are the same price; cite the page number and, for a figure, its marker letter.

**Rationale**: FR-008. The sentence keeps its structure, so the only thing that changes for the seat is what a marker looks like. The project's rule is to name the shape of a fault and never a specific document, which this wording already does.

**Alternatives considered**: dropping the sentence now that a letter cannot read as a digit, rejected because the page text still sets a marker beside a figure and the rule that it is not part of the figure costs nothing to keep.

## R7. Checking the Reviewer before merging

**Decision**: a scratch script, not committed, replays 5 recorded Reviewer requests. For each: read the recorded bundle from `runs/<id>/prompts/`, recompile that run's committed draft with the new code into a scratch folder, replace the recorded page text in the context with the new page text, send the new page images, and use the new seat instruction and the model that answered the first time. Parse the reply with the seat's own parser and compare the verdict and the cited markers with the recorded `review.verdict`. The method and the results go in `evidence.md`.

**Selection**: first reviews from runs recorded on or after 2026-09-19, so the recorded page text already brackets its markers and the Reviewer's context already carries the verified note, on `gemma4 12b, local`, the Reviewer's model in 187 of 225 recorded Reviewer calls. The five cover at least one recorded pass and one recorded fail, at least two datasets, and at least one draft with more than 26 markers, so the two letter labels are exercised.

**Rationale**: this is the project's practice for a change to a seat's input: replay recorded prompts before spending live runs. Recompiling rather than editing strings in the recorded context means the page images and the page text the Reviewer sees are the ones this code produces. Ollama runs locally, so the check costs no money. No sweep was in flight when this was planned; the replay is run only when none is.

**Alternatives considered**: substituting the letters into the recorded page text with a regular expression and reusing the old page images, rejected because the images would still show numbers, so the Reviewer would see two different labels for one marker; a live sweep, rejected by the owner (8c).

## R8. What the Writer sees

**Decision**: no change for the Writer.

**Rationale**: the Writer writes tags and never sees markers. A finding routed back to it cited "marker 3" before and will cite "marker c" now; in neither case does the Writer get a table from marker to tag, and adding one is outside this change.
