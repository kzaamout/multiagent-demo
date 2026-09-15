# Claude Design export

Exported from Claude Design on 2026-09-14. Source of truth for appearance. `docs/design-brief.md` and `docs/spec-input.md` are the source of truth for behaviour. When they disagree, behaviour follows the spec, appearance follows this export, and any case that cannot satisfy both is listed under Known deviations below.

Share link (humans only; not fetchable by tools): https://claude.ai/design/p/edfd8269-3fe8-4fb9-a40b-56a077e341af?via=share

Delivery shape chosen in Claude Design: one file per screen; the four Demo states live in a single file behind a state switcher; component styles isolated per element; mixed-set agent names (Oscar, Anna, Elena, Pavel, Willa, Rafael, Clara, Marcus); feed populated with realistic sample messages from scenario 2 (200A vs 225A inconsistency, one rework, pass). That sample text is demo fixture data. It must not appear on the Introduction page and it is not marketing copy.

## What the files actually are

Each `.html` file is a Claude Design bundle, not static HTML. It is a small loader page whose script tags carry two JSON payloads: a manifest of gzip-compressed, base64-encoded assets (the Claude Design runtime, React 18, React DOM, woff2 fonts, and one SVG icon on Demo and Introduction), and the page itself as a JSON string. The page is a `.dc.html` template: an `<x-dc>` root, a `<helmet>` with the font faces and a few global rules, elements styled inline and identified by `data-part` and `data-kind` attributes, `sc-if` and `sc-for` template tags with mustache bindings, `style-hover`, `style-focus`, and `style-active` pseudo-state attributes, and a `<script type="text/x-dc">` component class whose render method holds all sample data and the design-time state switcher. To read the markup, decode the page string from the bundle; the raw file is not readable as HTML.

## Files

| File | Screen | Brief section | Notes |
|---|---|---|---|
| `Introduction.html` | Introduction tab (public) | Design brief 11; content in `content/intro/*.md` | Seven sections in order, two diagrams, embedded Replay frame at the bottom |
| `Login.html` | Login | Design brief 2 | Product name plus username, password, one button. Nothing else |
| `Demo.html` | Demo tab, all four states | Design brief 3 through 8 | See state switcher below |
| `Settings.html` | Settings | Design brief 9 | One row per seat with model dropdown; providers without credentials greyed |
| `Preflight.html` | Pre-flight | Design brief 10 | Checklist with status dots and one Run button |
| `screenshots/` | Rendered captures of each screen and each Demo state | | Ground truth for visual intent when markup is ambiguous |

## Demo states (in `Demo.html`)

The state switcher is a design-time control and must not ship in the wired application; Claude Code replaces it with event-driven state.

| State | What is shown | Spec scenario |
|---|---|---|
| Idle | No run; composer ready; loop strip all idle | n/a |
| Running | Work stage active; Estimator thread expanded; Pricing waiting on Estimator | Scenario 2, mid-run |
| Paused | Waiting-on-you banner with batched questions; Intake node amber | Scenario 2, blocking clarification |
| Terminated | Review fail routed to Estimator, rework, pass; termination card reads reviewer passed, retry count 1; Handoff actions visible | Scenario 2, end |

## Screenshots

Present in `screenshots/`, named as exported (not renamed; this folder is reference):
- `Login.png`: Login.
- `Introduction - partial.png`: Introduction, top of the page only (What it is, start of Architecture).
- `Preflight.png`: Pre-flight in the all-pass state.
- `Settings.png`: Settings with the Estimator model dropdown open.
- `Demo.png`: Demo in the terminated state (scenario 2 end).

Missing: Demo idle, running, and paused; the chat panel; Introduction below the fold. Capture them from the export files before the screenshot comparison in M1 acceptance. The design-time switches are `state`, `mode`, `chatOpen`, and `preflight` in the Demo script's `data-props`.

## Known deviations from the brief and spec

Format and delivery
- The export is a runtime bundle, not static HTML and CSS (see above). Resolved by spec 2.10: flatten to static HTML, one CSS file, and vanilla JS; the runtime and React are not shipped.
- All styling is inline per element; there is no stylesheet. The flattening step derives classes from the inline styles, keyed by `data-part` and `data-kind`.
- Fonts (Inter 400 and 500, Space Grotesk 400 and 500, JetBrains Mono 400 and 500) and the human-figure SVG icon are embedded in the bundle manifests. Extract them into the application's static assets at flattening time.
- Visual direction: Sterling AI brand direction chosen at the questions step, not a client design system. Confirmed: no client-specific tokens. Palette in use: ink #17171c, text #212121, muted #75758a, muted-light #93939f, hairline #d9d9dd, hairline-light #e5e7eb, sand #eeece7, green #003c33, red #b30000, blue #1863dc, amber #B45309 and #e0730a, coral #ff7759 with #fff4f0 and #ffad9b.
- Seat colours as exported: Orchestrator #17171c, Intake #003c33, Estimator #b45309, Pricing #1863dc, Writer #071829, Reviewer #b30000, Case Manager #2f6b5e, Market Analyst #4a4a8a, human #75758a. These replace the hues suggested in the brief.
- No em dashes in any page.

Demo screen
- Fixed 1920 by 1080 frame with overflow hidden. The brief's "reasonable at 1440" is not covered; a 1440 layout is out of scope unless asked.
- Handoff actions are Approve, Download PDF, Download run timeline. Edit and Reject (spec stage 6) are absent; add them in the same button style.
- No blocker card exists (`data-kind` values present: orchestrator-note, agent-message, assumption, question, human-answer, specialist-thread, plan-card, draft-committed, verdict, termination). Add one in the card family with the brief's red left border and the Answer and Escalate actions from spec stage 3. No Work to Intake routing example either.
- The plan card lists Assemble as sub-task 3 assigned to the Writer. Adopted in spec 0.4.
- Thread replies are timestamped progress lines. Spec 0.4 adds `task.progress` and `tool.called`; tool calls need a reply variant in the same style.
- The meters strip has a per-agent detail row (calls, tokens in and out, cost, wall time, last event) beyond the brief. Supported by per-call `meter.update` in spec 0.4. Keep.
- A pre-flight status indicator sits in the header nav with pass, warn, and fail states. Not in the brief; spec 2.4 has only green or red. Decision: keep. Three states: green, warn, red; warn means a non-essential check failed, such as the tunnel unreachable in cloud mode. Added to spec 2.2 and 2.4.
- The build stamp appears only in the Settings header. The brief puts it on the Demo header and the spec in a Demo footer; no page has a footer element. Decision: the stamp goes in every page header in the Settings style (spec 2.2).
- The loop strip paused state is coral #ff7759 with a "!" glyph, not amber. Appearance follows the export.
- Only the Review to Work arrow has a fired style (red, animated once); Review to Assemble and Work to Intake are static grey. Wiring gives all three the fired treatment.
- Waiting-on-you banner inputs are read-only in the export; the wired banner makes them editable.
- Compare strip content exists only in the terminated state; the empty-state text is present.
- Raw turns sample lines omit `event_id`, `run_id`, and `role`, and give `run.started` the actor "system". Fixture only; the schema governs.
- Feed text below 16px: card meta and event labels 12 to 13px, prompt panel monospace 13px, finding evidence 14px, checklist grid 15px, raw drawer 12.5px. Body text and replies are 16px as required. Acceptable as meta; revisit if the projector test disagrees.

Introduction
- The replay frame is a static mock (six nodes and four cards). Wiring embeds the real read-only feed served from the pinned public run.
- Section 3, the agentic loop, has text only. The content file `03-agentic-loop.md` describes a loop diagram in its HTML comment, but the brief asks for two diagrams (architecture, demo vs production) and the export follows the brief. This is a defect in the brief, not a Design error: brief section 11 undercounted, the content file is right. Decision: add the loop diagram by reusing the Demo loop strip component in a static, fully-lit state with the backward arrows labelled, which keeps the two consistent (spec 2.1).
- The architecture diagram is rendered three times: once plain, then twice scaled to 49 percent side by side with Demo and AWS badges. The team cards expand on click to show role, owns, sees, tools; no flip.

Other screens
- Login: the Sign in control is a link to the Demo page, not a form submit. Wiring makes it a POST.
- Settings: the model dropdown is a custom list, not a native select; greyed providers carry "no credentials in .env". Matches the brief.
- Pre-flight: eight checks matching spec 2.4, with pending, one-fail, and all-pass states; the confirmation banner reads "Laptop mode" with a timestamp.

## Handling rules for Claude Code

- Do not modify files in this folder apart from this README. The export and screenshots are the reference.
- "Unmodified" means appearance. The application does not ship the Claude Design runtime or React. Flatten the export into static HTML, one CSS file with classes derived from the inline styles, and vanilla JS render functions driven by the event stream (spec 2.10).
- Acceptance: side-by-side screenshot comparison against `screenshots/` for each screen and each Demo state, no visible difference at 1920 by 1080.
- The state switcher, sample feed text, and any inline demo data are fixtures, not application logic. The scenario 2 sample copy becomes the scenario 2 stub fixture in M1.
- Placeholder avatars (initials in coloured circles) stay until the sixteen illustrated avatars are supplied; keep the slot sizes from the brief: 40px in the feed, 56px in Settings, 96px on the Introduction page.
