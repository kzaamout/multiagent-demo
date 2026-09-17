# Research: compiled deliverable and provenance (S4)

Every unknown in the Technical Context is resolved here. Probes were run on 2026-09-17 on the reference machine.

## R1. Pipeline shape

- **Decision**: reuse the career-hub two-step pipeline as a Python module: pandoc `-f markdown -t typst --template=<template>` to an intermediate `.typ`, then `typst compile` to PDF and `typst compile --format png --ppi 150` to one PNG per page, with the `.typ` retained beside the outputs. Subprocess calls with explicit timeouts; no shell.
- **Rationale**: the owner chose it (decision 1b); pandoc handles the Writer's tables and lists reliably; keeping the `.typ` is what makes the page-image export and the marker query possible, exactly the reason the career-hub script keeps it.
- **Alternatives considered**: `pandoc --pdf-engine=typst` in one step (loses the intermediate); a hand-written markdown to Typst converter (more code, worse table handling); an HTML renderer with a headless browser for page images (a second heavy dependency and no PDF fidelity).

## R2. Marker positions on page images

- **Decision**: the preprocessor replaces each `{{value|src:id}}` tag with the value followed by a raw Typst inline `#prov(n, "id")` (pandoc raw attribute `{=typst}`), where the template defines `prov` as a small superscript number plus `#metadata((n, src, page, x, y))<prov>` evaluated in a `context` block with `here().position()`. After the PDF compile, `typst query <typ> "<prov>" --field value` returns page and position in points for every marker. Positions are converted to pixel coordinates on the 150 ppi image (pixels = points times 150 divided by 72) and written to `markers.json` beside the images.
- **Rationale**: the probe returned `{"n":1,"src":"e1","page":1,"x":192.1,"y":98.3}` and `{"n":2,...,"page":2,...}` for a two-page file, which is exactly the hotspot data the panel needs; no second layout pass and no OCR.
- **Alternatives considered**: `typst eval 'query(<prov>)'` (the successor the CLI hints at; adopted as the fallback if `query` disappears in a later Typst); invisible markers (decision 2a chose visible numbers so the presenter can name them on stage); rendering the draft as HTML for hover and pages for looks (two truths on screen, rejected by the spec).

## R3. Page text for the Reviewer

- **Decision**: extract each page's text from the compiled PDF with pypdfium2, the reader `app/tools/prepare.py` already uses, and write `pages.json` (list of page texts) beside the images. The Reviewer bundle carries the page images as image content and the page text as a material labelled by page number.
- **Rationale**: decision 3b; what the Reviewer reads is what is on the page, including the marker numbers, so a finding can cite a page and a marker.
- **Alternatives considered**: sending the markdown alongside (the spec forbids the Reviewer seeing the Writer's sources or the markdown); text from the `.typ` source (not paginated).

## R4. Images in a seat call

- **Decision**: `PromptBundle` gains `images: list[str]` of run-relative paths (default empty). `SeatCall` turns them into image content blocks on the user message for a model whose registry entry has `image_input: true`, the same mechanism the Estimator's vision tool uses to send a drawing page. A seat with images on a model without `image_input` makes `LiveUnavailable` name the seat at run start.
- **Rationale**: bundles are recorded files, not events, so the frozen schema is untouched; the prompt toggle lists the image paths under a new section label.
- **Alternatives considered**: a Reviewer tool that reads pages on demand (the Reviewer has no tools by design); embedding base64 in the bundle (bloats the recording; paths are enough since the run folder holds the files).

## R5. Where the compile runs and who emits

- **Decision**: whoever commits a draft compiles it before the commit event is emitted: the live source after `commit_draft`, the stub after writing its fixture markdown, the Orchestrator for a human edit. The compile writes `artifacts/v<N>/compiled.json`. The Orchestrator, on relaying `draft.committed`, reads that record and emits `artifact.compiled` with the PDF path and the page image paths. A compile failure in the live source is a rejected reply with the compiler's message (second attempt, then the twice-invalid path).
- **Rationale**: principle III keeps the Orchestrator the only emitter; compiling before the commit means a draft that cannot compile never becomes a version; the existing rejected-reply machinery already records the attempt under `rejected/` and `responses/`.
- **Alternatives considered**: the Orchestrator compiling after the commit (a failed compile would leave a committed version with no pages); a compile tool call visible in the feed (the spec models compile as a system step, and a `tool.called` under the Writer would misattribute it).

## R6. Handoff edit and reject

- **Decision**: `DecisionRequest` gains an optional `markdown` field used with `decision: edit`. The Orchestrator writes `drafts/draft-v<N+1>.md`, compiles it, emits `draft.committed` with the human actor (the schema already allows it) and `artifact.compiled`, then `human.approved` with `decision: edit`, then terminates with the Handoff exit. A compile failure on the edit returns 400 with the compiler's message and leaves the run waiting at Handoff. Reject sends `decision: reject` with notes; the existing path records and terminates.
- **Rationale**: one route, one door (principle IV); the edit is one recompile, never a re-run (non-goal).
- **Alternatives considered**: a separate edit route (two doors); editing in the compiled pages (an editor, product).

## R7. Run timeline PDF

- **Decision**: `GET /api/runs/{run_id}/timeline.pdf` renders on demand from the recorded events: one markdown table (time from run start, stage, actor, type, one-line summary from the existing card summaries) through the pipeline with `templates/run-timeline.typ`, cached under `artifacts/timeline.pdf`. Works for live runs after termination and for recordings.
- **Rationale**: decision 5a; the same pipeline, one more template; the leave-behind command in S7 calls the same function.
- **Alternatives considered**: a markdown download (decision 5b, declined); rendering from the page (the page renders events, it does not produce files).

## R8. Brand on the cover

- **Decision**: `brand.yaml` values become pandoc template variables (`prospect-name`, `logo-path`, `primary-colour`). A missing logo file sets `logo-path` empty and the template draws a wordmark from the prospect name in the primary colour. A colour that is not a six-digit hex sets the template default and records an assumption on the run. The logo path is resolved inside the dataset folder only.
- **Rationale**: decisions 7a and 8a; the datasets ship without logo files today.
- **Alternatives considered**: failing the compile on a missing logo (would break every dataset).

## R9. Stubs compile for real

- **Decision**: the stub draft step writes a fixture markdown for the dataset (from `datasets/<id>/fixtures/` where present, else the shared S2 fixture draft) into `drafts/draft-v<N>.md` and compiles it, so stub runs and goldens carry real paths. Golden logs are re-recorded once with the tools present; the golden comparison stays on stage sequence and exit, so a later template change does not invalidate them.
- **Rationale**: decision 6a; Replay and the screenshot captures show real pages.
- **Alternatives considered**: shipping pre-rendered PNGs in the repository (binary churn and a second truth); mocking the compiler in stubs (goldens would name files that do not exist).

## R10. Missing tools

- **Decision**: `tools_available()` reports which of pandoc and Typst are on the path. `Registry.start_run` refuses a run that needs a compile with a message naming the tool, the same 409 path as a missing credential. Tests that need the tools carry `pytest.mark.compiler` and a conftest hook skips them with the tool's name, mirroring the dataset marker. Pre-flight (S7) will show the same check.
- **Rationale**: spec FR-016; a machine without Typst still runs the non-compile suite.

## R11. Em dashes in the compiled output

- **Decision**: the lint step extracts the text of every page of a compiled fixture draft and fails on an em dash, so a template or a converter cannot introduce one. Pandoc's smart punctuation is disabled (`-f markdown-smart`) so it does not turn `--` into a dash.
- **Rationale**: principle IX covers generated content and deliverables.

## R12. Reviewer seat wording

- **Decision**: `config/electrical-bid/seats/reviewer.md` and the seats README say the Reviewer sees the brief, the compiled page images with their page text, and the criteria. The criteria file already says page images (line 3) and asks for page numbers in evidence.
- **Rationale**: principle V requires the recorded scope to be true.
