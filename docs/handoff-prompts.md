# Handoff prompts

## To Claude Design
Attach: `docs/design-brief.md`, `docs/spec-input.md` (sections 2, 3, 4 only if it accepts a second file), `content/intro/*.md`.

Prompt:

You are designing the UI for a live sales demo of a multi-agent AI system. Read the attached design brief in full before drawing anything; it defines every screen, every element, the agent card that appears everywhere, the message kinds in the feed, and an explicit list of things not to design. Treat that list as hard constraints. Produce the five screens in section 2, with the Demo screen in the four states listed in section 14. Use placeholder avatars (initials in coloured circles, one colour per seat as suggested) because illustrated avatars arrive later; keep avatar slots at the sizes given. Primary viewport is 1920 by 1080 for a projector; body text in the feed 16px minimum. The Introduction page content is attached as seven markdown files; lay it out in that order and render the two diagrams described in the HTML comments inside 02 and 06. Do not write new marketing copy; use the files as given and do not introduce em dashes anywhere. Deliver static HTML and CSS with component styles isolated so an engineer can wire them to a live event stream without redesigning. When something in the brief is ambiguous, ask before choosing; do not fill gaps with a dashboard, sidebar, or login extras.

## To Claude Code
Before starting: install Spec Kit in the repo, place `CLAUDE.md` at the root and `.specify/memory/constitution.md` where Spec Kit expects the constitution. Put the Claude Design export under `design/` unmodified.

Prompt:

Read CLAUDE.md, then .specify/memory/constitution.md, then docs/spec-input.md in full. Do not read docs/sales-playbook.md. Before any plan or code, ask me up to ten clarifying questions about anything in the spec that would change the architecture or the first milestone; do not proceed from assumptions. Then run /speckit.specify using docs/spec-input.md as the feature description, and /speckit.plan and /speckit.tasks, keeping the milestone order in section 9 as the build sequence. The event schema in section 6 must be finalised and committed as a versioned document plus typed models before any agent code exists, and the UI must render only from events. A Claude Design export is in design/; use its markup and styles as the frontend, wiring elements to the event stream, and do not redesign it. Credentials live only in .env. Do not build anything in the constitution non-goals; if a task seems to require one, stop and flag it. No em dashes anywhere, including generated copy and prompts; add a lint step that fails on them. Verify current versions of Strands Agents, the Bedrock AgentCore service names, and Typst before pinning or writing the Introduction copy. Finish M1 with a demonstrable loop strip and feed driven by stubbed agents and a working Replay before touching real models.
