# Design deviations recorded during implementation

Constitution XI requires every case where the export and the spec cannot both be satisfied to be recorded with its decision. `design/README.md` holds the deviations found before implementation. The folder `design/` is not edited by implementation work, so deviations found while building a slice are recorded here instead. Behaviour follows the spec; appearance follows the export.

## Slice S1 (2026-09-14)

### Owner decisions (2026-09-15)

1. **Termination card eyebrow at Handoff.** Spec 2.2 renders the termination card from `handoff.ready`, with Approve available, before the run ends. The export's card at that moment reads "Run ended · 04:12". The owner chose behaviour over the export's copy: the eyebrow reads "Ready for approval · 04:12" until `run.terminated` arrives, then "Run ended". The terminated screenshot comparison masks that one line, listed in `tests/visual/masks.py`.
2. **Em-dash lint scope.** Constitution XVI says the lint fails on any em dash anywhere in the repository. Two sets of tracked files contain em dashes the project must not edit. Spec Kit's installed tooling (`.claude/skills/`, `.specify/` except `memory/`) is vendor code. The Claude Design bundle loader script inside `design/*.html` is also vendor code. The owner accepted the scope: the lint excludes the Spec Kit tooling and lints the decoded page template of each design bundle instead of its loader. Every exclusion is listed in `scripts/lint_em_dash.py`. Project content, prompts, recordings, and generated output are all covered.

### Decided in S1 (appearance kept, behaviour per spec)

- **Dry intake toggle** (pre-S1 decision 2). A two-segment switch labelled Dry intake sits beside the Team / Single model switch, in the export's switch style, disabled until S3. It is masked in the screenshot comparison.
- **Pre-flight indicator pending state.** The export has pass, warn, and fail. Before S7 there is no pre-flight result, so the dot shows a grey pending state with an open circle. The indicator also appears in the Settings and Pre-flight headers (decision in spec 2.2).
- **Disabled controls.** Controls whose behaviour arrives later use the export's own disabled treatment, opacity 0.45: workflow selector (S8), Single model (S5), Pause and Stop (S3), Edit, Reject, Download PDF, and Download run timeline (S4), Run pre-flight (S7). The Run button is also disabled while the run waits at Handoff, because a new run cannot start while one is live. The export shows it enabled in its terminated state, which is not a live run.
- **Settings model selects** stay at full appearance and do nothing until S5. The page is a static preview of the seats in S1.
- **Introduction link** in every header is inert until S6.
- **Blocker card.** Built in the card family: white card, 4px red left border, Orchestrator agent card, description, reason, answer field, Answer as the dark pill, and Escalate as the outlined pill. No export screenshot shows it; reviewed for family consistency.
- **Tool-call replies** in a specialist thread use a monospace chip for the tool name, followed by arguments, result, and duration.
- **Question card after answering.** As in the export, the question card gives way to the human answer card once every question is answered. The `clarification.asked` event stays in the raw drawer and the recording.
- **Orchestrator notes** carry the export's prompt button. In S1 the Orchestrator is the state machine and makes no model call, so the button is inert with a title saying so. The prompt toggle on every agent message is live.
- **Active threads auto-expand** (spec 2.2). The running-state reference capture opens the Estimator thread by clicking it in the export, which is how the export shows the expanded state described in `design/README.md`.
- **Artifact panel placeholder** reads "Deliverable appears here after the first draft. Compiled pages arrive in slice S4." It is masked in the comparison until S4.
- **Event counts and elapsed time.** The stub emits every event the schema requires, including meter deltas. The termination card and raw drawer therefore count 62 or 65 events where the export's sample says 41. The elapsed meter shows the last event's time (01:35 in the running state) because the UI never runs timers; the export shows 01:37.

### Screenshot references

`design/screenshots/` holds only five captures, at a smaller scale than 1920 by 1080. The comparison uses references recaptured from the export bundles at 1920 by 1080 by `scripts/capture_export.py`, stored in `tests/visual/reference/`. The recaptured Demo terminated, Login, Settings with the Estimator dropdown open, and Pre-flight all-pass states were checked by eye against `design/screenshots/` and match. Masks for deferred regions are listed with reasons in `tests/visual/masks.py`.

## Slice S2 (2026-09-15)

### Owner decisions

1. **Settings page model labels are stale until S5.** Every seat now runs on a local Ollama model (roadmap decision 13), but the Settings page is still the static S1 preview and shows the export's cloud labels, such as "claude-sonnet via Bedrock". This conflicts with constitution V, which requires a seat's model to be displayed truthfully wherever the agent appears. The owner chose to leave the page unchanged until S5 wires it to the running configuration, rather than make the labels read-only truthful now. The Demo page is not affected: its agent cards take model labels from the run's events. Presenters should not show the Settings page before S5.

## Slice S3 (2026-09-15)

### Family-consistency review

Three states the export does not show were captured at 1920 by 1080 (`tests/visual/output/s3/`) and reviewed against the export's card, button, and switch families.

- **Blocker card** (Missing sheet golden log). Matches the export's clarification card: Orchestrator agent card, 4px red left rule, `clarification.asked` eyebrow with the run clock, the description as body text, a Why line, the answer field, Answer as the dark pill and Escalate as the outlined pill. The pair reads as one choice, as the export's Approve and Edit pair does. No change needed.
- **Paused composer.** Pause takes the export's outlined button treatment and reads Resume while paused; Run is disabled at opacity 0.45 because a paused run is still live; Stop stays a ghost button. The export has no paused state, so the treatment is new: the outlined pill marks the one control that moves the run on, and the ghost keeps Stop quieter than Resume. The thread carries an Orchestrator card reading "Run paused by the presenter", which is how every other control event appears.
- **Dry intake toggle switched on.** The same two-segment switch as Team and Single model, dark active segment, same height and radius, sitting to their right. While a run is live or in replay the label and both segments take the export's disabled treatment, as the Single model segment does.

### Notes

- The Dry intake masks in `tests/visual/masks.py` now say the toggle is wired in S3 and is a permanent addition to the export, rather than a deferred region. The region stays masked because the export has no such control.

## Slice S3b (2026-09-15)

### Owner decisions, from the change request after the S3 review

1. **Navigation order.** The export orders the header nav Demo, Introduction, Pre-flight, Settings on every page. The owner's order is Pre-flight, Introduction, Demo, Settings, because Pre-flight is what the presenter opens before a meeting. Behaviour over the export's order; the same links, styles, indicator, and build stamp.
2. **Threads start collapsed.** The export's running state shows the Estimator thread expanded and spec 0.6 said active threads auto-expand. Spec 0.7 collapses every thread until clicked, with a live indicator on the avatar and header border (the loop strip's active pulse, invisible when animations are frozen) and an unread count chip in the retry badge style. The running-state reference capture opens the thread by clicking it, as it always did, so the comparison is unchanged.
3. **Stage label under the loop strip.** Spec 0.7 adds a one-line label under the strip with the `target_reason` of the latest `stage.changed`. The export has no such line; it is added in the export's meta text style and masked in the comparison.
4. **Bypassed nodes and filled connectors.** New node state `bypassed` (dimmed, dashed border) and a filled forward connector between completed nodes. Both are extensions of the export's node states; no export screenshot shows them, so they are reviewed for family consistency like the S3 controls.
5. **Forward arrow pulse.** The export animates only the Review to Work arrow. Spec 0.7 pulses every arrow once on every `stage.changed`, forward and backward, about 600 ms, in the same red as the export's fired arrow for backward and the ink colour for forward.
6. **Vocabulary.** The export's copy says "Electrical RFP" (workflow selector, Settings seat notes, sample feed text). The application says "Electrical bid response" and "bid request" or "tender package". The export is not edited; the 43 occurrences in `design/` stay as reference text.
7. **Intake's activity indicator.** Neither the stubs nor the live engine emit `task.dispatched` or `task.completed` for Intake (the Analyst's messages are `intake.brief`, `intake.readiness`, and its tool calls). The Intake card's indicator therefore turns on when `stage.changed` enters Intake and off at `intake.readiness`, the Intake equivalents of dispatch and completion, still events only.
8. **Unread chip while live.** The count of replies since the last collapse shows while the task is live (dispatched and not yet completed or blocked). Once the task completes, the header summary carries the outcome and the chip is dropped, so a finished run's feed matches the export's terminated state; the presenter reads the count while it matters.
9. **Performance toggle on the termination card.** A "performance" toggle in the prompt-toggle style opens the per-agent, per-stage, and per-run tables from `performance.json`; a Download performance button joins the Handoff actions in the outlined button style. Not in the export; added in its component family.
10. **Retry badge arithmetic** (2026-09-16). The export's badge reads "retry 1 of 2" because the S1 budget was two reworks. With the review limit the badge reads "retry N of M" where M is `review_max_cycles` minus one, 3 by default (spec 0.7 section 2.2, schema 1.1.0). The digit therefore differs from the export in the idle, running, and terminated captures, and the termination card side reads "retries 1 of 3". One glyph is within the comparison's tolerance (0.5 percent of unmasked pixels), so no mask is added and the comparison still passes; setting `REVIEW_MAX_CYCLES=3` reproduces the export's digit exactly.
11. **Stop reason line on the termination card** (2026-09-16). For exit retry_exhausted the card carries one more "Review stopped:" line in the Orchestrator-reason style, naming no progress, a repeated finding, or the maximum number of cycles from `summary.stop_reason`. The export has no such exit on screen.
12. **Preparation tool calls in the Intake thread** (2026-09-16). On a live run the Intake thread opens with one `tool.called` reply per input file and one for the manifest from `prepare_documents`, before the Analyst's first progress line. The S1 stub scenarios, which the screenshot captures replay, are fixture copy and do not emit them, so the captures are unchanged.

## S4, compiled deliverable and provenance (2026-09-17)

Reviewed against the export's artifact panel, its outlined and pill button families, and its input style. Nothing in `design/` is edited.

1. **Pages in the artifact panel.** The export's terminated state shows a static mock of two pages with hand-drawn tags. The application renders the run's own compiled pages (one PNG per page at 150 ppi) stacked in the panel with a page number caption in the meta text style, replaced in place on every new version so the swap keeps the scroll and never shows an empty frame. The panel's region stays masked in the screenshot comparison because the page content differs by construction; the frame, header, version label, and action row are compared.
2. **Provenance markers.** On the printed page every tagged figure carries a small superscript number in the brand colour (decision 2a). In the panel the same number sits in a 22 px ink circle with a white ring at the marker's position, sized to be read at three metres (constitution XIV). Hovering it highlights the source message with the export's active border colour and a soft halo, and scrolls the feed to it; nothing on click. The export's mock shows tags as underlined figures, which cannot be positioned on a raster page.
3. **Edit and Reject.** Both use the export's outlined button family beside Approve, as `design/README.md` allows. Edit replaces the pages with a text area in the export's input style (mono, 13 px) and a Save and Cancel pair in the pill and outline styles; Reject reuses the same area for notes with the Save button relabelled. The area is in the panel, not a dialog (constitution XIV).
4. **Downloads.** Download PDF and Download run timeline are outlined links rather than buttons, so the browser saves the file; a disabled link is dimmed and inert. The timeline is available only after the run ends, since it renders from the complete event log.
5. **Reviewer scope.** The Reviewer now receives the page images and the text of each page; the seat file and the seats README say so. The prompt toggle gains a sixth "Pages" section listing the images sent. The export's prompt panel shows five sections; the sixth follows the same label and text style.
6. **Cover wordmark.** No dataset ships a logo file, so every cover carries a wordmark: the prospect name set large in the brand colour (decision 7a). The response template and the run timeline template are new files under `templates/`; the export has no PDF design, so the cover, headings, and table rules follow the export's colour and weight conventions rather than a drawing.
