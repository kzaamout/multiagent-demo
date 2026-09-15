# Implementation roadmap

Version 1.0, approved by the owner on 2026-09-14. Nine vertical slices on one frozen foundation, per constitution XII. Each slice is independently demonstrable from the Demo page. Slice boundaries are frozen artifacts under constitution XIX: moving work between slices needs the owner's approval.

Compared with `docs/spec-input.md` section 9: the Reviewer joins in the first live slice rather than the second, Missing price moves from the artifact slice to the failure slice, the artifact slice can run in parallel with the failure slice, pre-flight, login, tunnel, and the leave-behind form one demo-day slice, the appraisal workflow gets its own slice since section 9 omits it, and the em-dash lint and screenshot capture start in slice 1.

## Decisions taken before S1 (owner approvals under constitution XIX, 2026-09-14)

1. **Dry intake exit.** An eighth control exit, `dry_intake`, is added to the schema. Dry intake mode terminates after Intake with this exit whatever the verdict, and the structured summary carries the readiness verdict.
2. **Dry intake control.** A Dry intake toggle sits in the composer beside the Team / Single switch, in the export's switch style. It exists disabled in S1 and goes live in S3. Recorded as a deviation in `docs/design-deviations.md`.
3. **Git.** The folder becomes a git repository at the start of S1, with `.env` and `runs/` ignored and the current documents committed as the baseline.
4. **Replay source.** Replay plays the most recent recording for the selected dataset, falling back to that dataset's golden log. There is no run browser.
5. **Python.** 3.13, the interpreter installed on the reference machine. `CLAUDE.md` and spec open item 11 updated.

## Decisions taken before S2 (owner approvals under constitution XIX, 2026-09-14)

1. **Rating disagreements are a concern, not a blocker.** `config/electrical-rfp/estimating-conventions.md` changed. Planted inconsistency shows the Review fail and rework.
2. **A missing panel schedule is a concern at Intake.** `config/electrical-rfp/readiness-checklist.md` changed. Missing sheet shows the Estimator's blocker, Answer, and Escalate.
3. **Orchestrator model scope.** The Orchestrator's model proposes the plan, reasons, question wording, routing within the Reviewer's recommendations, and the termination headline. The hand-written run engine keeps every rule and validates every proposal.
4. **Provenance tag syntax** is `{{value|src:<source_id>}}`, parsed by the S4 compile step.
5. **Long-lead threshold** is 28 days.
6. **The price lookup tool returns extended costs and totals**, so Pricing on the local model copies numbers rather than computing them.
7. **S2 starts before its owner inputs exist.** Specify, plan, and tasks run now, and everything that needs no credentials or curated dataset is built. Live runs wait for the Clean run dataset, Bedrock and Gemini credentials, and Ollama.

## Adjustments after constitution 1.1.0

- **S1 gains the quality gates.** Test runner, type checker, linter, and the em-dash lint over the repository and generated output are set up in S1 and gate every later slice (XVI). S1 also adds a schema-level test that no event payload or prompt bundle contains a value from `.env` (XVII).
- **Dependency rationale is a running record.** S1 opens it with FastAPI, the schema models, and the SSE approach; S2 adds Strands and its LiteLLM provider; S4 adds Typst and the career-hub script; S7 adds the Cloudflare Tunnel (XV).
- **Laptop versus Cloud mode greying moves from S5 to S7**, with the slice that introduces run modes (XII).
- **Every screen-wiring slice lists its screenshot comparison.** S5 adds the Settings comparison. S3 and S4 add a family-consistency review for the blocker card, the Pause control, the Dry intake toggle, and the Edit and Reject buttons, since no export screenshot shows them (XIII, XVIII).
- **S9 gains a projector pass.** A physical legibility check at three metres (XIV), which also closes the design README's open note on sub-16px meta text.
- **The pre-S1 decisions are formal approvals under XIX**, and the approved slice boundaries are frozen artifacts.

## Slices

### S1. Event spine and stubbed loop

- **Status.** Built 2026-09-14 on branch `001-event-spine-stubbed-loop`, awaiting the owner's review in the browser. Evidence: golden logs in `datasets/*/golden-events.jsonl`; suites under `tests/`; screenshot references in `tests/visual/reference/`; deviations in `docs/design-deviations.md`; quickstart in `specs/001-event-spine-stubbed-loop/quickstart.md`.

- **Outcome.** The presenter opens the Demo page, picks any of the six datasets, presses Run, and the loop strip, feed, meters, and raw drawer play a complete run from stubbed agents with no model calls. All four Demo states appear on cue, any recorded run replays at 1x or 4x, and the display is identical whether live-stubbed or replayed.
- **Scope.** Event schema frozen as a versioned document plus typed models with validators. Orchestrator state machine: six stages, all eight exits, review retry budget, Work to Intake cap, Handoff sequence ending in `run.terminated`, pause gating, cost ceiling check. Stubbed agents emitting canned sequences for all six scenarios, scenario 2 from the export's sample transcript, the rest minimal fixture text. Stub prompt bundles stored per call so the prompt toggle works. SSE stream. Run recording under `runs/<run_id>/` and verbatim Replay. The full Demo page flattened per spec 2.10 with the state switcher removed: header with nav and a pending-state pre-flight dot, loop strip with all three backward arrows given the fired treatment, composer with Run and Replay live and Pause, Stop, Dry intake, and Single model disabled, feed with every card kind including a new blocker card, prompt toggle, meters with the detail row, raw drawer, artifact panel placeholder, chat panel markup disabled. Login, Settings, and Pre-flight flattened as static pages. Random name and avatar pairing per run with initials placeholders. Golden event logs for all six scenarios and the replay-and-compare test suite. Quality gates: test runner, type checker, linter, em-dash lint, `.env` leak test. Dependency rationale record opened. Capture of the missing export screenshots, then the screenshot comparison.
- **Deferred.** Real agents to S2. Pause, Stop, Dry intake, blocker actions, and the remaining exits in live form to S3. Compiled pages to S4. Settings behaviour, Single model, and chat to S5. Introduction to S6. Login enforcement, live pre-flight, and tunnel to S7.
- **Dependencies.** None on other slices. The five decisions above.
- **Spec sources.** `docs/spec-input.md` 2.2, 2.5, 2.10, 3, 4.1 to 4.3, 6, 7, 9 M1, 10. `design/README.md` deviations. `datasets/*/README.md` for expected sequences.
- **Design.** `Demo.html` in all four states, `Login.html`, `Settings.html`, `Preflight.html`. Screenshots `Demo.png`, `Login.png`, `Settings.png`, `Preflight.png`, plus the idle, running, paused, and chat captures S1 produces from the export.
- **Datasets.** All six, README and brand.yaml only; stubs need no inputs.
- **Evidence.** Six golden logs committed. Test suite green on replay compare. Screenshot comparison passes for Demo in four states, Login, Settings, and Pre-flight. Acceptance criteria 2, 3 except Introduction, 4 for the last-event rule, and 11. Quality gates green.
- **Constitution risks.** Principle II: stubs must emit every state change and the UI must never infer or time anything. Principle III: only the state machine changes stage even when agents are canned. Non-goal "dashboard of past runs": Replay plays one recording for the selected dataset with no run browser.

### S2. Live team on the clean run

- **Outcome.** The presenter runs Clean run live. Anna produces a real brief and one clarification, the presenter answers in the banner, Elena, Pavel, Willa, and Rafael work on real inputs on their default models including the local one, the proposal draft passes review, and every prompt toggle shows the real bundle. A second run does not ask the question again.
- **Scope.** Strands integration and a provider registry built from `.env` with structured model objects and labels. The six RFP seats with instructions from `config/electrical-rfp/`, visibility scopes enforced in the bundle, and tools: document parsing, vision on the drawing pages, quantity calculator, price list lookup on the fixture, template renderer, compile trigger stubbed. `task.progress` and `tool.called` emitted from real calls. Per-call `meter.update` from real token counts. Knowledge file read at Intake and append at answer time. Clarification pause and resume through the Orchestrator. Concurrent gather over independent tasks. Reviewer on Gemini judging the markdown text as an interim input until S4. Interim draft text view in the artifact panel, replaced in S4. Dependency record: Strands and its LiteLLM provider.
- **Deferred.** Review fail routing, blockers, Stop, Pause, cost ceiling to S3. Page images and provenance hover to S4. Model swap to S5.
- **Dependencies.** S1. Curated Clean run dataset with inputs, fixtures, and knowledge seed, an owner task. Credentials in `.env`, Bedrock and Gemini access, Ollama with the local model pulled.
- **Spec sources.** 2.2 banner, 2.5, 3 stages 1 to 6 forward path, 4, 6, 7 scenario 1, 8 markdown only. `config/electrical-rfp/*`. `datasets/README.md`.
- **Design.** `Demo.html` running and paused states. `Demo.png`.
- **Datasets.** clean-run.
- **Evidence.** A live Clean run replays against its golden stage sequence and exit. The second run shows no repeated clarification and a `knowledge.appended` event in the first. Criteria 5 for clarifications and 7.
- **Constitution risks.** Non-goal "memory beyond the knowledge file": one file, appended by the Orchestrator only. Principle IV: the banner is the only door. Principle V: the Reviewer bundle provably excludes specialist reasoning and sources.

### S3. Failure paths and presenter controls

- **Outcome.** The presenter runs Planted inconsistency and the prospect watches the Reviewer fail v1, the arrow fire back to Elena, the retry badge tick to 1 of 2, and v2 pass. Missing sheet pauses on a blocker with Answer and Escalate, and Escalate ends with a card listing exactly what is missing. Not ready stops in seconds with the missing items. Missing price surfaces as a minor note at Handoff. Pause and Stop work mid-run and a low ceiling halts a run on cost.
- **Scope.** Review fail routing to Work with a named specialist or to Assemble, rework dispatch with findings in context, retry counter and `retry_exhausted`. Blocker handling: `clarification.asked` carrying the blocker, Answer resuming at Work, Escalate terminating with the structured missing list. Work to Intake route with its cap. `not_ready` with the structured list. Dry intake mode with exit `dry_intake` and the composer toggle live. Cost ceiling after every meter event. Stop with exit `stopped`. Pause and Resume with their events, in-flight calls completing. Termination cards for every exit. Scenarios 2 to 5 live. Family-consistency review for the blocker card, the Pause control, and the Dry intake toggle.
- **Deferred.** Reviewer on page images and Edit and Reject to S4.
- **Dependencies.** S2. Datasets 2 to 5 curated with planted defects documented in their READMEs.
- **Spec sources.** 2.2 composer, blocker card, termination card. 3 global rules, stages 3, 5, 6, Exits, cost ceiling. 6. 7 scenarios 2 to 5. 9 M3. `config/electrical-rfp/reviewer-criteria.md`, `estimating-conventions.md` blocker rules, `readiness-checklist.md`.
- **Design.** `Demo.html` terminated state: fail verdict, routing note, rework thread, v2 pass, termination card. `Demo.png`. The blocker card, Pause control, and Dry intake toggle are built in the card and composer families per the README deviations.
- **Datasets.** planted-inconsistency, missing-sheet, missing-price, not-ready.
- **Evidence.** Live runs of scenarios 2 to 5 match their golden sequences and exits. Criteria 1 for five of six scenarios, 4 for Stop, 5 for blockers.
- **Constitution risks.** Principle VI: four narrative exits plus control exits, nothing else. Non-goal "reject re-enters the loop": rework only happens from Review. Pause must stay a freeze, not a step debugger that lets anyone edit prompts mid-run.

### S4. Compiled deliverable and provenance

- **Outcome.** The proposal appears as real pages that refresh in place as Willa writes, with the prospect's brand on the cover. The presenter hovers a provenance tag and the feed jumps to and highlights the specialist message behind that number. Rafael judges the pages. At Handoff the presenter approves, edits, or rejects, and downloads the PDF and the run timeline.
- **Scope.** Markdown to Typst to PDF and page PNGs on every `draft.committed`, reusing the career-hub compile script, emitting `artifact.compiled`. Artifact panel live with in-place refresh, preserved scroll, and version label. Provenance tag overlay and hover highlight. Reviewer input switched to page images. Brand variables from `brand.yaml` into the response template. Handoff actions: Approve, Edit with one in-place recompile, Reject with notes, Download PDF, Download run timeline rendered from the event log. `handoff.ready` package populated. Dependency record: Typst and the career-hub script. Family-consistency review for Edit and Reject.
- **Deferred.** Leave-behind bundling to S7. Introduction PDF to S6.
- **Dependencies.** S2. Runs in parallel with S3. Typst installed, the career-hub script located, and the `templates/rfp-response.typ` template, which does not exist yet.
- **Spec sources.** 2.2 artifact panel, 2.6, 3 stages 4 and 6, 3 stage 5 page images, 6 `draft.committed`, `artifact.compiled`, `handoff.ready`, `human.approved`, 8, 9 M4. `config/electrical-rfp/knowledge-file.seed.md` template reference. `datasets/*/brand.yaml`.
- **Design.** `Demo.html` terminated state artifact panel with pages, tags, and handoff actions. `Demo.png`. Edit and Reject added in the export's button style per the README.
- **Datasets.** clean-run, planted-inconsistency for v1 and v2, missing-price.
- **Evidence.** Golden logs regain `artifact.compiled` events. Criterion 8. A visual check that a new version swaps without flicker and keeps scroll. The interim markdown review path from S2 is removed.
- **Constitution risks.** Principle VII: a figure without a tag is a major finding, so the Writer prompt and the Reviewer criteria enforce it. Non-goal "provenance beyond hover": no graph, search, or export. Non-goal "automated sending": downloads only.

### S5. Seats, single model, and chat

- **Outcome.** The presenter opens Settings mid-run, moves the Estimator to another model, and the grey text changes on every card within a second while the next dispatch uses it. A Single-model run on the same dataset fills the Compare strip: cheaper, faster, no review, no sources. After the run the presenter clicks Elena's card and asks why she chose 225 A.
- **Scope.** Settings live: per-seat dropdown from the registry, greyed providers with the "no credentials" note, dependency notes, `model.changed` applied at the next dispatch and propagated to every card. Single-model mode as its own run with `single_complete` and the Compare strip. Meters completed: comparison line, ceiling indicator, per-agent detail row. Chat panel backed by an out-of-band endpoint using the agent's system prompt and run context, read-only, cleared on close. Settings screenshot comparison.
- **Deferred.** Provider health checks and Laptop versus Cloud greying to S7.
- **Dependencies.** S2. S3 for a completed team run to compare against.
- **Spec sources.** 2.2 composer switch, Compare strip, meters. 2.3, 2.7, 4.1, 5, 6 `model.changed`, `meter.update`, `single_complete`, 9 M5.
- **Design.** `Settings.html` and `Settings.png` with the dropdown open. `Demo.html` Single model toggle, Compare strip, meter detail row, chat panel via the `chatOpen` switch. `Demo.png`.
- **Datasets.** Any; clean-run for the comparison.
- **Evidence.** Criterion 6. A Single-model run recorded with exit `single_complete` and replayable. A test proving the run log is byte-identical before and after a chat.
- **Constitution risks.** Non-goal "providers or credentials from the UI": Settings lists only what `.env` holds. Non-goal "changing instructions mid-run": Settings changes the model only, chat cannot touch the run. Non-goal "model leaderboard": one comparison line, no history. Principle V: the label is always the live model.

### S6. Introduction tab and public replay

- **Outcome.** A prospect or sales staff opens the public Introduction page and reads the seven sections with the architecture, loop, and demo-versus-production diagrams, expands the team cards, reads the FAQ, and watches a read-only replay of a recorded clean run at the bottom. The page exports to PDF.
- **Scope.** Render `content/intro/*.md` in order without new copy. Architecture and demo-versus-production diagrams as exported. Loop diagram by reusing the Demo loop strip in a static fully-lit state with labelled backward arrows. Team grid with expand and the appraisal swap-in cards. FAQ. Embedded replay frame fed by the unauthenticated endpoint pinned to one run id. Introduction to PDF through Typst.
- **Deferred.** Leave-behind bundling to S7.
- **Dependencies.** S1 for replay, loop strip, and feed rendering. S4 for the Typst pipeline. A recorded clean run from S2 to pin; the S1 stub recording serves until then.
- **Spec sources.** 2.1, 6 recording and public Replay, 8 Introduction PDF, 9 M6, 11 AgentCore name check. `content/intro/*.md`. `docs/design-brief.md` 11.
- **Design.** `Introduction.html`. `Introduction - partial.png`, with the rest of the page captured in S1. README deviations on the loop diagram and the static replay mock.
- **Datasets.** clean-run, the pinned recording.
- **Evidence.** Screenshot comparison for Introduction, completing criterion 3. A test that the public endpoint serves only the pinned run. PDF produced. Content diff against the markdown files is empty apart from markup. No em dashes.
- **Constitution risks.** Non-goals "multi-user viewing" and "dashboard of past runs": one pinned run, read-only. The public page must not link into Demo, Settings, or Pre-flight without login.

### S7. Demo-day readiness

- **Outcome.** On the presenter laptop, pre-flight goes green and the dot in every header turns green. The app answers at the Sterling AI subdomain through the tunnel behind the shared login while the Introduction stays public. One command produces the three leave-behind PDFs.
- **Scope.** Live pre-flight checks: each configured provider responds, Ollama and models, Typst test compile, PNG export, tunnel reachability, disk space, `.env` completeness, each classed essential or non-essential, result stored and driving the three-state header indicator. Shared login from `.env` guarding Demo, Settings, and Pre-flight. Laptop and Cloud mode configuration, including greying of local models in Cloud mode. Cloudflare Tunnel configuration. Build stamp from git in every header. Leave-behind command producing the run PDF, the run timeline, and the Introduction PDF. Illustrated avatars swapped in if delivered. Dependency record: Cloudflare Tunnel.
- **Deferred.** Nothing within scope.
- **Dependencies.** S4 and S6 for the PDFs, S2 for providers, a git repository, and the subdomain and tunnel target from open items.
- **Spec sources.** 2.2 header, 2.4, 2.8, 2.9, 8 leave-behind, 9 M6, 10 criteria 9 and 10, 11 subdomain and avatars.
- **Design.** `Preflight.html` with `Preflight.png` and the pending and one-fail states from the switcher. `Login.html` with `Login.png`. The header indicator via the `preflight` switch in `Demo.html`.
- **Datasets.** None; the test compile uses a fixture.
- **Evidence.** Criteria 9 and 10. Screenshot comparison for Pre-flight states and Login. A test that unauthenticated requests reach Introduction and are refused on the other three pages.
- **Constitution risks.** Non-goal "per-user accounts": one shared login, no reset or lockout screens. Non-goal "credentials from the UI": pre-flight only reports a missing key. Non-goal "AgentCore for the demo": tunnel and laptop only.

### S8. Appraisal workflow

- **Outcome.** The presenter switches the workflow selector to Appraisal and runs an intake-to-report with Clara and Marcus in the specialist seats, on the same loop, the same page, and the same cards.
- **Scope.** Appraisal workflow configuration: seat instructions, readiness checklist, reviewer criteria, report template, CRM and comparables fixtures with their lookup tools and the adjustment calculator. Roster swap. Workflow selector live. One appraisal clean dataset with README, fixtures, and golden log.
- **Deferred.** Appraisal failure scenarios, which no document specifies; parked until asked.
- **Dependencies.** S3 and S4. Owner curation of appraisal fixtures, template, and a request; none exist today and section 9 does not schedule them.
- **Spec sources.** 1, 2.2 workflow selector, 4.3 appraisal seats, 4.4, 7 dataset structure, 8 template.
- **Design.** `Demo.html` workflow selector. Settings rows for Case Manager and Market Analyst in `Settings.png`. Introduction swap-in cards.
- **Datasets.** New appraisal dataset to be curated.
- **Evidence.** An appraisal clean run live, matching its golden sequence and exit, extending criterion 1.
- **Constitution risks.** Non-goal "live CRM integrations": fixtures only. Principle I: one configuration, no appraisal-specific UI.

### S9. Rehearsal and golden re-record

- **Outcome.** The full demo arc runs three times on the presenter laptop without intervention. Every scenario's golden log is a verified live recording. The prospect-own procedure has been executed once with a stand-in file.
- **Scope.** Re-record all golden logs from verified live runs, replacing the S1 stubs, and pass the suite against them on stage sequence and exit only. Three rehearsal runs recorded. Prospect-own dry run per `datasets/README.md`: populate, Dry intake, resolve, two full runs, record a clean run. Pin the public replay to a verified run. Final lint across generated content. Screenshot re-check after any avatar swap. Projector pass: a physical legibility check at three metres.
- **Deferred.** Nothing.
- **Dependencies.** Everything above, all datasets, the tunnel.
- **Spec sources.** 7 scenario 6, 9 M7, 10 criterion 1. `datasets/README.md` and `datasets/prospect-own/README.md`. The sales playbook stays unread by tooling.
- **Design.** None new.
- **Datasets.** All six plus the prospect-own procedure.
- **Evidence.** Criterion 1 in full. Three rehearsal recordings under `runs/`. Golden logs replaced and the suite green.
- **Constitution risks.** Principle I: rehearsal findings will tempt product features such as browsing past runs; they get parked in the non-goals, not built.

## Interims

S2 and S3 let the Reviewer judge markdown text and show the draft as text in the artifact panel until S4 delivers page images. Both are small and are removed in S4.
