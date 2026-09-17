# Contract: Introduction page, public replay, and the Introduction PDF (S6)

Responses are HTML, JSON or a file. Errors on JSON routes use HTTP status and `{"error": "<one sentence>"}`.

## GET /introduction

- 200 HTML: the flattened page with the seven sections rendered from `content/intro/*.md`, the three inline SVG diagrams, eight team cards, and the replay frame shell whose iframe points at `/demo?public=1&run=<pinned>&speed=1`.
- Needs no login now or after S7.

## GET /introduction.pdf

- 200 `application/pdf`, regenerated when a source is newer, cached under `runs/_intro/introduction.pdf`.
- 503 `compiler missing (<tool>)`.
- Needs no login now or after S7.

## Public run routes (needs no login now or after S7)

- `GET /public/run/{run_id}/events`: 200 the recording's events for the pinned id; 404 for any other id, including ids that exist under `runs/`.
- `GET /public/run/{run_id}/files/{path}`: 200 a file inside the pinned run's folder, same suffix rules as the private files route; 404 otherwise.
- `GET /public/run/{run_id}/prompts/{prompt_ref}`: 200 the bundle sections for a prompt of the pinned run; 404 otherwise.
- `GET /public/run/{run_id}/meta`: 200 `{"run_id", "dataset_id", "exit", "has_pages"}` for the caption; 404 otherwise.

## GET /demo?public=1&run={run_id}&speed={1|4}

- Renders the Demo page in public mode: it loads the run through the public routes and hides the composer, Pause, Stop, Dry intake, dataset choice, Approve, Edit, Reject, downloads and the header navigation; it keeps the loop strip, the feed, prompt toggles, pages and markers, meters and the raw turns drawer. The page does not open a stream and never posts.
- With a run id other than the pinned one, the public routes refuse and the page shows the S4 empty message with the frame's one-sentence note.

## Script: `uv run python scripts/intro_pdf.py [--out PATH]`

- Writes the PDF and prints its path; exit 2 with the tool's name when the compiler is missing.

## Module: `app.intro`

- `sections() -> list[Section]`, `render_page(settings) -> str`, `diagrams() -> dict[str, Diagram]`, `team_cards(registry) -> list[TeamCard]`, `render_pdf(settings) -> Path`.

## What S7 must keep public

`/introduction`, `/introduction.pdf`, `/public/run/{id}/...`, `/static/...`, and `/demo` only when `public=1` and the run id is the pinned one. Everything else goes behind the login.
