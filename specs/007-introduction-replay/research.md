# Research: Introduction tab and public replay (S6)

## R1. Service and SDK names (spec 11 open item, decision 6a)

- **Checked 2026-09-17**: Amazon Bedrock AgentCore Runtime, Gateway, Memory, Identity and Observability are current component names in the AWS AgentCore developer guide (overview and observability pages) and the general availability announcement of October 2025. AgentCore Observability reports through Amazon CloudWatch, which matches the copy's "AgentCore Observability plus CloudWatch". Strands Agents is AWS's open-source agent SDK in Python and TypeScript and is built to deploy on AgentCore Runtime, which matches the copy's sentence that the orchestrator and agents are built on the SDK AgentCore is designed around.
- **Decision**: no change to the content files. The maintainer note in `06-real-in-your-aws-account.md` stays as a comment and is not rendered.
- **Not in the copy and not added**: AgentCore Policy, Evaluations, Browser and Code Interpreter; the copy names only what the demo's table maps to.

## R2. Rendering the content files

- **Decision**: a small in-house converter for the markdown subset the seven files use: `#` and `##` headings, paragraphs, `**bold**` and `_italic_`, numbered and bulleted lists, one pipe table, and HTML comments dropped. It also yields plain text per section for the content diff test and the em-dash lint.
- **Rationale**: the subset is fixed by seven files under the project's control; a markdown library would be a dependency for a page that never sees user input. The S2 interim renderer handled the same subset in JavaScript; this one lives in Python so the page and the PDF share it.
- **Alternatives considered**: pandoc to HTML at request time (a subprocess per page view); a Python markdown package (a dependency the constitution asks to justify, for no gain).

## R3. Diagrams as SVG (decision 2a)

- **Decision**: `app/intro/diagrams.py` describes the architecture as bands (renderers, event stream, orchestrator, agents, tools, model providers, the human figure with the "one door" arrow) and emits SVG. The demo-versus-production figure emits the same bands twice with badge sets; the loop figure emits the Demo strip's six nodes, forward arrows, three labelled backward arrows, the human icons, the retry badge and the exits card. The page inlines the SVG; the PDF embeds the same strings as files.
- **Rationale**: the export draws the architecture as HTML bands with one inline SVG for the provider lines; a raster or HTML figure cannot go into the Typst PDF, and drawing it twice would drift. One SVG source keeps the page and the leave-behind identical. The bands, colours, radii and type sizes are copied from the export's inline styles so the SVG reads as the export does.
- **Alternatives considered**: screenshots of the page for the PDF (decision 2b, declined); keeping the export's HTML on the page and a separate SVG for the PDF (two truths).

## R4. The loop diagram (decision 3a)

- **Decision**: the loop SVG uses the same labels, glyphs, colours and arrow geometry as the Demo strip in `demo.html` and `app.css` (node pill 48 px, ink border for lit nodes, the red backward arrow colour, the retry badge), drawn static and fully lit, with the three backward arrows labelled as the strip labels them and a terminal card off Handoff listing the four exits, Not ready branching off Intake.
- **Rationale**: spec 2.1; the export's section is text only (design/README.md records the brief's undercount). Reusing the strip's markup directly would drag the Demo's live wiring into a static page; reproducing its geometry in SVG keeps the look and lets the PDF carry it.

## R5. Team cards (decision 5a)

- **Decision**: `app/intro/team.py` builds eight cards: the six seats from `build_roster` (both name variants from the content file's "Oscar / Olivia" pairs, the role from the roster, the model label from `config/models.yaml` at request time) with owns, sees and tools from `SEAT_DEFINITIONS` and the seat file's first paragraph; the two appraisal cards from the content file's names and descriptions with "swaps in for the appraisal workflow" where the model would be. The card markup is the export's team card (96 px avatar, name, model in grey, blurb, expandable detail grid).
- **Rationale**: principle V; the roster and seat definitions are the truth for the six seats, and S8 will supply the appraisal seats later.

## R6. The public replay frame (decision 4a)

- **Decision**: `GET /public/run/{run_id}/events`, `/files/{path}` and `/prompts/{ref}` serve exactly `Settings.public_run_id` (from `PUBLIC_RUN_ID`) and answer 404 for any other id, reading the run folder like the private routes. The Demo page gains `?public=1`: it loads the pinned run through the public routes, hides the composer, run controls, Handoff actions and the navigation links, keeps the loop strip, the feed, the prompt toggles, the pages and markers, and offers replay speed only. The Introduction embeds it in an iframe inside the export's frame shell, with the export's header strip (Replay, 1x, 4x) driving the frame's speed through the iframe's URL.
- **Rationale**: one renderer, one reducer; the frame cannot drift from the Demo. Serving one id keeps every other recording private before the S7 login exists.
- **Alternatives considered**: a second lightweight renderer (decision 4b, declined); reusing `/api/runs/{id}` unauthenticated (would expose every recording).

## R7. The pinned run (decision 1a)

- **Decision**: `PUBLIC_RUN_ID` in `.env`, with the default in `app/config.py` set to the fresh Planted inconsistency recording made under the concern check on 2026-09-17, or to `f2dda488-0a2f-457a-9ef1-33fcac05fa70` when that run does not rework. The frame shows the S4 message when a pinned recording has no compiled pages.
- **Rationale**: the owner's choice; the run is recorded once and stays.

## R8. The PDF (decision 7a)

- **Decision**: `app/intro/pdf.py` writes one markdown file with the seven sections (comments dropped, the table kept) and the three SVG diagrams as images, then `app.compile.render_markdown` with `templates/introduction.typ` (Letter, single column, ink headings, Inter). `scripts/intro_pdf.py` calls it and prints the path; `GET /introduction.pdf` serves it, regenerating when a content file, the diagram module or the template is newer than the PDF; 503 names a missing tool.
- **Rationale**: the S7 leave-behind command and a presenter's browser both reach it.

## R9. Flattening the export

- **Decision**: the page template decoded from `design/Introduction.html` gives the section order, ids, max widths, paddings, borders, the eyebrow labels in JetBrains Mono, the 48 px Space Grotesk headings, the 18 px body, the FAQ item rule, the team card and the replay frame shell. These become `.intro-*` rules in `app.css` and the markup in `introduction.html`, with the design-time `sc-for` and `sc-if` bindings replaced by server-rendered sections. The export's replay mock and its text-only loop section are recorded deviations; the design-time replay caption "dataset 01 Clean run" is replaced by the pinned run's dataset and exit.

## R10. What S7 needs from this slice

- The list of routes that must stay public after the login lands: `/introduction`, `/introduction.pdf`, `/public/run/{id}/...`, `/static/...`, and `/demo?public=1` for the pinned run only. Recorded in the contract for the S7 session.
