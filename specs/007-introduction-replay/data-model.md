# Data model: Introduction tab and public replay (S6)

No event payload changes. Everything below is derived at request time or written under `runs/_intro/`.

## Section

| Field | Meaning |
|---|---|
| `id` | the export's section id: what-it-is, architecture, agentic-loop, the-team, how-agents-differ, aws, faq |
| `eyebrow` | the mono label above the heading, from the export |
| `title` | the file's first heading |
| `blocks` | the file's blocks in order: paragraph, list (ordered or not), table, each with inline bold and italic |
| `diagram` | the diagram slot the file's comment names: architecture, loop, demo-vs-production, or none |
| `text` | the file's plain text without markup or comments, for the content diff and the lint |

Files are read in the fixed order 01 to 07; a missing file is an error at startup, never a blank section.

## Diagram

| Field | Meaning |
|---|---|
| `name` | architecture, loop, demo-vs-production |
| `svg` | the drawing as a string, `viewBox` set, no external fonts required |
| `text` | every text node, for the lint |

The demo-vs-production drawing reuses the architecture description with two badge sets: laptop badges on the left copy, AgentCore service badges (Runtime, Gateway, Memory, Observability, Identity) on the right, on the boxes the content table maps.

## Team card

| Field | Source |
|---|---|
| `agent_id` | roster seat id, or `case_manager` / `market_analyst` for the appraisal cards |
| `names` | the name pair from the content file ("Oscar / Olivia") |
| `role` | roster role, or the content file's role for the appraisal cards |
| `model` | the seat's current model label from the registry, or "swaps in for the appraisal workflow" |
| `blurb` | the content file's sentence for the agent |
| `owns`, `sees`, `tools` | `SEAT_DEFINITIONS` visibility kinds and tool names in plain words; owns from the seat file's first paragraph; the appraisal cards carry the content file's parenthesised list |
| `colour`, `initials` | the seat colour and initials the feed uses |

## Pinned run

`Settings.public_run_id` (from `PUBLIC_RUN_ID`), the run folder under `runs_dir`, and its dataset id and exit read from the recording for the frame's caption. When the folder is missing the page renders with a one-sentence note in the frame.

## Introduction PDF

`runs/_intro/introduction.md`, the three `*.svg` files, `introduction.typ` and `introduction.pdf`, regenerated when any content file, the diagram module or the template is newer than the PDF.

## Public mode of the Demo page

A presentation flag (`?public=1&run=<id>&speed=1|4`) that changes what the page shows, never what it stores: no composer, no controls, no Handoff actions, no navigation; the events, files and prompt bundles come from the public routes. It is not an event and not state.
