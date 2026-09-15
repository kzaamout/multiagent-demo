# Design brief: Sterling AI multi-agent demo UI

For Claude Design (produce the UI) and for Claude Code (implement it). Describes what the screens are, what each element means, and what must not be designed. No implementation detail.

## 1. What this is
A live sales demo. A presenter runs it on a projector for one prospect. Several AI agents, each with a name, role, and avatar, work under an Orchestrator to turn a business request (an electrical RFP) into a reviewed proposal that the prospect approves on screen. The UI's only job is to make the agents, their communication, and the orchestration visible and legible from three metres away.

Design language: a team chat you can watch, not a dashboard. Borrow the idiom of Slack (named participants with avatars, threads, reaction-like status marks) without copying its chrome. Calm, high contrast, generous type, few colours. Motion only where it carries meaning (a stage lighting up, an arrow firing backward, a page image swapping).

## 2. Screens
1. Introduction (public): long-form marketing and explainer page.
2. Demo (login): the working screen. Design this first and best.
3. Settings (login): one row per agent seat.
4. Pre-flight (login): a checklist that goes green.
5. Login: one username field, one password field, one button. Nothing else.

## 3. Demo screen layout
Desktop 1920 x 1080 primary (projector). Reasonable at 1440 wide. No mobile layout required.

Top to bottom:
- Header: product name, workflow selector, build stamp far right (small, muted).
- Loop strip: full width. Six nodes in a row: Intake, Plan, Work, Assemble, Review, Handoff. Forward arrows between them. Three curved backward arrows drawn beneath the row: Review to Work, Review to Assemble, Work to Intake, each labelled. Review node carries a retry counter badge (0 of 2). Intake, Work, and Handoff carry a small human icon meaning "a person may be needed here." States per node: idle, active (lit, subtle pulse), complete, paused-for-human (amber), failed-routing-back (arrow animates once).
- Composer bar: dataset dropdown, run mode switch (Team / Single model), model dropdown that appears only in Single mode, Run, Pause, Stop, Replay toggle with 1x / 4x speed. Keep it one line.
- Main area, two columns. Left two-thirds: event feed. Right third: artifact panel.
- Meters strip beneath the main area: elapsed time, per-agent tokens and cost as small cards using the agent card, run total, a one-line Team vs Single comparison, cost ceiling indicator (a thin bar).
- Raw turns drawer at the very bottom, collapsed by default, expands to show JSON lines.

## 4. The agent card (used everywhere)
Avatar left (circle, 40px in feed, 56px in Settings, 96px on the Introduction page). Line 1: name and role in normal weight, for example "Anna, Intake Analyst". Line 2: model identifier in small grey text, for example "claude-sonnet via Bedrock" or "llama3.1 8b, local". The grey line is truth, not decoration; it changes when the model changes. Until illustrations arrive, avatar placeholder is initials in a coloured circle, one colour per seat, consistent across the whole app.

Colour per seat (suggested, adjust to palette): Orchestrator slate; Intake Analyst teal; Estimator amber; Pricing green; Writer indigo; Reviewer red-brown; Case Manager teal-dark; Market Analyst green-dark. The human is a plain neutral.

## 5. Feed message anatomy
Each message: agent card header; timestamp muted; body; a small "prompt" toggle at the bottom left that expands a sectioned, pretty-printed panel: System instructions, Context provided, Task, Tools available, Model. Read-only, monospace for the content, section labels in the UI font. Always present on every agent message.

Message kinds, each visually distinct but from one family:
- Orchestrator note: plan, dispatch, decision. Clicking it reveals a one-sentence "Why" (the reason field) beneath.
- Plan card: checklist of sub-tasks with assignee avatars and dependency arrows.
- Specialist thread: a parent message per sub-task; replies indented; thread auto-expands while active, collapses to a one-line summary with a status mark on completion.
- Assumption card: muted amber left border. "Proceeding on default: X. Flagged for Handoff."
- Question card: strong amber. Appears inside the Waiting-on-you banner as well.
- Blocker card: red left border, states what is missing and why work cannot continue.
- Draft committed: compact, links to the artifact version.
- Verdict card: pass in green, fail in red; findings listed with a severity chip (blocker, major, minor), evidence line, and a routing chip ("back to Estimator", "back to Writer").
- Termination card: full-width, states the exit in plain words and the Orchestrator reason. Four narrative exits: reviewer passed; retry budget spent; blocker escalated; intake not ready.

## 6. Artifact panel
Shows the compiled deliverable as page images stacked vertically, with a version label and page count. On a new version, pages swap in place without flicker and scroll position is preserved. Provenance tags appear as small superscript markers inside the page image area (implementation will overlay them); on hover, the feed scrolls to and highlights the source message. A collapsible Compare strip sits above the panel and holds the most recent Single-model output as plain text with its own cost and time. At Handoff the panel gains three actions: Approve, Download PDF, Download run timeline.

## 7. Waiting-on-you banner
When the run pauses for a human, a banner slides in beneath the loop strip: "Waiting on you" with the batched questions, each with the proposed default pre-filled and a why-it-matters line, and one Resume button. The paused node in the loop strip turns amber. Designed so the prospect can be handed the keyboard.

## 8. Chat with an agent
Clicking an agent card while the run is paused or finished opens a side panel conversation with that agent. Same card as header. Input at the bottom. No history across runs. Closes without trace.

## 9. Settings screen
One row per seat: agent card, model dropdown, and a note of dependencies ("runs after Estimator"). Providers without credentials appear greyed with "no credentials in .env". A small status line: "Changes apply at the next stage." Nothing else on this page.

## 10. Pre-flight screen
A vertical checklist. Each row: item name, status dot (grey pending, green pass, red fail), one line of detail. A single "Run pre-flight" button. When all green, a large confirmation. Designed to be glanced at, not read.

## 11. Introduction page
Long scroll, seven sections in this order: What it is; Architecture; The agentic loop; The team; How agents differ; How this becomes real inside your AWS account; FAQ. Then an embedded Replay of a recorded run (the Demo screen loop strip and feed in a read-only frame). Two diagrams:
- Architecture: three horizontal bands. Renderers (Web UI, Slack greyed with a "future" tag). Event stream as a bus. Orchestrator as one box containing the six-stage strip and a retry counter. Agents as a row of six agent cards. Tools as small boxes only beneath specialists and Writer. Model providers along the bottom (Bedrock, Anthropic, Gemini, Grok, Local) with dotted lines to agent cards. A human figure to the right of the Orchestrator with a single arrow labelled "one door".
- Demo vs Production: the architecture diagram drawn twice side by side, identical shapes; left labelled Demo with laptop badges, right labelled Your AWS account with AgentCore service badges on the same boxes.
The team section shows eight agent cards in a grid, two specialists marked "swaps in for the appraisal workflow". Each card can flip or expand to show role, what it owns, what it sees, tools.

## 12. Tone and typography
Serious, warm, unhurried. One sans for UI, a readable monospace for prompts and JSON. Large type in the feed (16px minimum body) because it will be read on a projector. Avoid dense tables in the Demo screen. Avoid gradients and glassmorphism. Dark and light themes both acceptable; if only one, choose light for projector legibility.

## 13. Do not design
- A sidebar navigation, a dashboard of past runs, charts of anything.
- A signup, password reset, profile, or team management screen.
- Credential or API key entry fields anywhere.
- An editor for agent prompts. The prompt toggle is read-only.
- A mobile layout.
- Talking or animated avatars, sound, confetti.
- Marketing hero imagery on the Demo screen. The agents are the imagery.

## 14. Deliverables from Claude Design
Static HTML and CSS (or a single-page prototype) for all five screens, with the Demo screen shown in four states: idle, running with a specialist thread open, paused with the Waiting-on-you banner, and terminated after a Review fail and rework. Component styles isolated so Claude Code can wire them to the event stream without redesign.
