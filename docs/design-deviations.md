# Design deviations recorded during implementation

Constitution XI requires every case where the export and the spec cannot both be satisfied to be recorded with its decision. `design/README.md` holds the deviations found before implementation. The folder `design/` is not edited by implementation work, so deviations found while building a slice are recorded here instead. Behaviour follows the spec; appearance follows the export.

## Slice S1 (2026-09-14)

### Needs an owner decision

1. **Termination card eyebrow at Handoff.** Spec 2.2 renders the termination card from `handoff.ready`, with Approve available, before the run ends. The export's card at that moment reads "Run ended · 04:12". S1 keeps the export's copy for fidelity. The run has not ended until `run.terminated` follows the human decision. Options: keep the copy, or read "Ready for approval · 04:12" until `run.terminated` arrives. The second option adds a text difference to the terminated screenshot comparison.
2. **Em-dash lint scope.** Constitution XVI says the lint fails on any em dash anywhere in the repository. Two sets of tracked files contain em dashes the project must not edit. Spec Kit's installed tooling (`.claude/skills/`, `.specify/` except `memory/`) is vendor code. The Claude Design bundle loader script inside `design/*.html` is also vendor code. The lint excludes the Spec Kit tooling and lints the decoded page template of each design bundle instead of its loader. Every exclusion is listed in `scripts/lint_em_dash.py`. Project content, prompts, recordings, and generated output are all covered.

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
