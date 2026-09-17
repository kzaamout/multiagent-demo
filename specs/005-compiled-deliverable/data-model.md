# Data model: compiled deliverable and provenance (S4)

No event payload changes. The frozen 1.1.0 payloads for `draft.committed`, `artifact.compiled`, `handoff.ready` and `human.approved` are used as written. Everything below is a file in the run folder or an in-memory record.

## Compiled version (file record)

Written by `app/compile/pipeline.compile_draft` to `runs/<run_id>/artifacts/v<N>/`:

| File | Content |
|---|---|
| `draft-v<N>.typ` | the intermediate Typst source from pandoc, retained |
| `draft-v<N>.pdf` | the compiled proposal |
| `page-01.png` ... `page-NN.png` | one image per page at 150 ppi, two-digit page numbers |
| `markers.json` | list of Marker records (below) |
| `pages.json` | list of strings, the extracted text of each page in order |
| `compiled.json` | the record the Orchestrator reads: `version`, `pdf_path`, `page_images`, `marker_count`, `unresolved`, `page_count`, `elapsed_ms`, `tool_versions` |

All paths in `compiled.json` are relative to the run folder, so they can go straight into the `artifact.compiled` payload and be served by the existing files route.

Validation: `page_images` has `page_count` entries; every marker's page is within `page_count`; `unresolved` lists marker numbers whose source id was not a source in the run.

## Marker

One numbered provenance mark on a page.

| Field | Type | Meaning |
|---|---|---|
| `n` | int, from 1 | marker number, in document order; printed beside the figure |
| `source_id` | str | the short source id from the tag (`src:`), resolved to a message by the run's source map |
| `source_event_id` | str or null | the event id of the specialist message, null when unresolved |
| `page` | int, from 1 | page the marker sits on |
| `x`, `y` | float | position on the page image in pixels at 150 ppi (points times 150 divided by 72) |

The panel draws a hotspot at (`x`, `y`) on `page-<page>.png`, scaled by the displayed image width over its natural width. The provenance appendix in the PDF lists `n`, the source id and the message headline.

## Brand

Read from `datasets/<id>/brand.yaml`.

| Field | Type | Rule |
|---|---|---|
| `prospect_name` | str, required | cover title and wordmark text |
| `logo_path` | str | relative to the dataset folder; empty when the file is missing, which selects the wordmark |
| `primary_colour` | str | six-digit hex with `#`; otherwise the template default and an assumption recorded on the run naming the field |

## Prompt bundle (recorded file, extended)

`PromptBundle.images: list[str]`, default empty, run-relative paths of the page images sent with the call. Shown in the prompt toggle under a "Pages" label. Only the Reviewer's call carries images in this slice.

## Decision request (API body, extended)

`{"decision": "approve" | "edit" | "reject", "notes": "", "markdown": ""}`. `markdown` is required for `edit` and ignored otherwise.

## Run timeline (file, on demand)

`runs/<run_id>/artifacts/timeline.pdf`, rendered from `events.jsonl`: one row per event with time from run start (mm:ss), stage, actor name and role, event type, and a one-line summary. Regenerated when the event log is newer than the file.

## State transitions touched

- Assemble: draft written, compile run, `draft.committed` relayed, `artifact.compiled` emitted (real paths), then Review as today.
- Handoff, edit: human markdown written as version N+1, compile run, `draft.committed` (actor human), `artifact.compiled`, `human.approved` decision edit, `run.terminated` with the Handoff exit. A compile failure leaves the run at Handoff and returns the message.
- Handoff, reject: `human.approved` decision reject with notes, `run.terminated` with the Handoff exit. Unchanged path, now offered on the page.
