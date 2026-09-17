# Contract: compiled deliverable, provenance and Handoff (S4)

Responses are JSON unless a file is served. Errors use HTTP status and `{"error": "<one sentence>"}`. Existing routes keep their shape; additions are marked.

## Events (frozen 1.1.0, now populated)

- `artifact.compiled` `{ version, pdf_path: "artifacts/v1/draft-v1.pdf", page_images: ["artifacts/v1/page-01.png", ...] }`, emitted by the Orchestrator after every `draft.committed`, before any Reviewer dispatch. `pdf_path` is never null from this slice on.
- `handoff.ready.package` carries `pdf_path` and `page_images` of the final version, `verdict_event_id`, `unresolved_findings`, `assumptions`, `clarifications`, `event_log_path`.
- `draft.committed` with `actor.agent_id: "human"` for a Handoff edit, `provenance_tags` recomputed from the edited markdown.

## Files in the run folder

Served by the existing `GET /api/runs/{run_id}/files/{path}` (suffixes `.md`, `.png`, `.pdf`, `.json`; `.typ` is not served). Layout per version under `artifacts/v<N>/` as in [data-model.md](../data-model.md). `markers.json` and `pages.json` are fetched by the panel with the images.

## POST /api/runs/{run_id}/decision (extended)

Body: `{"decision": "approve" | "edit" | "reject", "notes": "", "markdown": ""}`.

- 202 for approve and reject as today.
- 202 for edit when `markdown` compiles: the Orchestrator commits it as the next version with the human as actor, emits `artifact.compiled`, records the decision and terminates.
- 400 for edit when `markdown` is empty or does not compile; the body's `error` carries the compiler's first line and the run stays at Handoff.
- 409 when the run is not waiting at Handoff.

## GET /api/runs/{run_id}/timeline.pdf (new)

- 200 `application/pdf`, rendered on demand from the recorded events and cached under `artifacts/timeline.pdf`; for a live run only after termination.
- 404 unknown run. 409 when the run has not terminated. 503 when the compiler is missing, naming the tool.

## POST /api/runs (unchanged shape, new refusal)

- 409 `Live run unavailable: compiler missing (typst)` or `(pandoc)` when a run that compiles cannot, in stub or live mode.

## Module: `app.compile`

- `compile_draft(run_folder, version, markdown, brand, sources) -> Compiled`: writes `artifacts/v<N>/`, returns the record; raises `CompileError(message)` with the tool's first error line.
- `compile_timeline(run_folder, events) -> Path`.
- `tools_available() -> dict[str, str | None]`: tool name to version or None.
- `read_brand(dataset_folder) -> Brand` with the fallbacks in the data model.

## Page (artifact panel)

- Renders the pages of the latest `artifact.compiled`, version label `v<N>`, lazy loading below the fold, replaced in place with scroll preserved.
- Marker hotspots from `markers.json`; hover adds `is-source` to the feed message whose event id matches and scrolls it into view; leaving removes it.
- At Handoff for exits `reviewer_pass` and `retry_exhausted` in live mode: Approve, Edit, Reject, Download PDF, Download run timeline. Edit shows the text area with the latest `drafts/draft-v<N>.md`; Save posts the decision with `markdown`; Cancel restores the pages. Reject prompts for notes in the same area and posts `decision: reject`.
- Downloads link to the files route for the PDF and to the timeline route.
