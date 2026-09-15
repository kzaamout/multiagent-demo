# Research: Failure paths and presenter controls (S3)

Date: 2026-09-15. Sources: the S1 and S2 code on branch `002-live-team-clean-run` at `2af91c7`, the golden logs of scenarios 2 to 5, the recorded S2 live runs, and the package indexes named below.

## Verified versions (2026-09-15)

| Item | Verified | Source | S3 use |
|---|---|---|---|
| strands-agents | 1.55.1 pinned and installed; PyPI lists 1.56.0 as the latest release | PyPI JSON, `uv pip` metadata | Unchanged pin; S3 adds no dependency and the S2 live runs were verified on 1.55.1. An upgrade is considered with the next dependency change. |
| Ollama | 0.34.1 running (updated itself from 0.34.0) | `GET /api/version` | Local seats |
| Typst | 0.15.1 | `typst --version` | Authoring the derived dataset PDFs only |
| FastAPI, Pydantic, Uvicorn, pypdfium2, boto3, LiteLLM, Ollama client | 0.141.1, 2.13.5, 0.53.0, 5.13.0, 1.43.94, 1.96.0, 0.6.2 | installed metadata | Unchanged |

## What S1 and S2 already provide

- The run engine implements review routing to Work or Assemble, rework dispatch with findings, the retry counter and `retry_exhausted`, blockers with Answer and Escalate, the single Work to Intake route, `not_ready` with the missing list, `dry_intake`, the cost ceiling after every meter delta, and Stop. All are covered by stub scenario tests.
- The live agent source supports rework (`rework`), blocker continuation (`blocker_continuation`), and Estimator blockers in its reply shape.
- The API has pause, resume, and stop routes. The page has a blocker card, termination cards, and reducer cases for `run.paused` and `run.resumed`.
- The golden logs define the expected transitions: Planted inconsistency `intake, plan, work, assemble, review, work (backward), assemble, review, handoff` with `reviewer_pass`; Missing sheet `intake, plan, work` with `blocker_escalated`; Missing price `intake, plan, work, assemble, review, handoff` with `reviewer_pass`; Not ready `intake` with `not_ready`.

## Gaps found

1. `Orchestrator.pause()` and `resume()` change flags but never emit `run.paused` or `run.resumed`, which the spec requires as Orchestrator events with a reason.
2. Stop is observed only at gates and relays. A live call that yields nothing for minutes, such as the Writer composing a draft, delays Stop past the spec's five seconds.
3. The composer's Pause, Stop, and Dry intake controls are disabled, and the run request has no Dry intake field.
4. The cost ceiling termination card does not show the spend against the ceiling.
5. No dataset other than Clean run has inputs, so scenarios 2 to 5 run on stubs.

## Decisions

### D1. Stop cancels the run task

- Decision: `stop()` sets the stop flags and cancels the run task the registry started, and the work stage's child tasks. `Orchestrator.run` treats a cancellation that follows a stop request as a stop: it terminates with `stopped`, shielded from the cancellation, and emits nothing for results that arrive later. Seat calls already cancel their Strands task when their iterator is closed.
- Rationale: meets the five second target in every state without polling inside provider calls.
- Alternatives: a timeout inside every seat call (does not help a legitimately long call); leaving Stop at the next gate (misses the target by minutes).
- Cost note: a provider call cancelled on the client may still be billed for tokens already generated.

### D2. Pause and resume are Orchestrator events

- Decision: `pause()` and `resume()` schedule `run.paused` and `run.resumed` through the Orchestrator's serialised emitter with payload `{"by": "human"}` and a reason. Dispatch already waits on the pause gate; calls in flight keep relaying their progress and results. Pause is ignored while the run waits on a human, at Handoff, or after termination.
- Rationale: the schema and the page already expect these events; one owner of state (constitution III).

### D3. Dry intake on the run request

- Decision: the run request gains `dry_intake: bool = false`. The registry sets the agent source's Dry intake flag for live and stub runs alike. The composer toggle is enabled while no run is live and sends the flag.

### D4. Controls enabled only for a live run on this page

- Decision: Pause, Resume (the Pause button relabelled), and Stop are enabled only while this page follows a live run that has not terminated. Replays, golden fixed states, and ended runs keep them disabled, so the screenshot references stay valid.

### D5. Termination card detail

- Decision: the card for `cost_ceiling` adds "Estimated spend" against the ceiling from run metadata; `stopped` states that the presenter stopped the run; `dry_intake` shows the readiness verdict (already rendered); `not_ready` and `blocker_escalated` list the missing items (already rendered).

### D6. Derived datasets are self-contained copies of the Clean run sources

- Decision: each failure dataset gets a copy of `datasets/clean-run/source/` with only its scenario's edits, compiled into its own `inputs/`, plus its own price list. A build note in each README gives the compile commands.
- Rationale: a presenter or owner can read and edit one folder without following links into another dataset.
- Alternatives: one build script that patches Clean run at build time (hides the planted change in code).

Scenario designs:

- **Planted inconsistency.** E-002 states a 200 A main breaker for LP-1; E-001 and the specification keep 225 A. The two "ratings agree" notes on E-001 and E-002 are removed. Nothing else changes. Expected: the Estimator proceeds on 225 A with a concern naming both sheets; the draft carries the disagreement; the Reviewer fails it as an internal inconsistency routed to the Estimator; the rework confirms 225 A under the single-line rule; v2 states one rating and passes.
- **Missing sheet.** A second panel, LP-2, is added: a 100 A, 30-circuit panelboard in the staff workroom fed from LP-1 by a 100 A three-pole breaker and feeder. The program room receptacles move to LP-2 circuits on the power plan. The single-line and the drawing index refer to schedule E-003, which is not in the set. Expected: Intake grades the absent schedule as the Estimator's concern; the Estimator raises a blocker that needs a human; Escalate ends the run with `blocker_escalated` and the missing schedule listed.
- **Missing price.** The price list drops `Exit sign, LED`. Expected: Pricing lists it unpriced; the Writer excludes it with its reason; the Reviewer passes with at most a minor finding.
- **Not ready.** The invitation has no closing date or time and no questions deadline date, and `division-26-specification.pdf` is absent although section 2 lists it as a tender document. Expected: Intake returns `not_ready` listing the deadline and the specification.

### D7. Live seats on the failure paths

- Decision: no seat instruction changes are planned in advance. The Reviewer criteria already route data problems to Work and name the Estimator for drawings and ratings. The estimating conventions already require a concern for a rating disagreement and a blocker for a panel without a schedule. Live verification runs decide whether instructions need tuning; any change is recorded with the run that motivated it.
- Rationale: S2 showed that tuning without a failing run adds rules the models ignore.

### D8. Evidence comparison

- Decision: a small command, `scripts/compare_run.py`, prints a recorded run's transitions, exit, retries, clarifications, blockers, and estimated cost next to the dataset's golden log and exits non-zero on a mismatch. Integration tests keep using `app.runs.golden.compare`.

### D9. Family-consistency review

- Decision: capture the blocker card from the Missing sheet golden log, the paused composer from a paused live or stub run, and the Dry intake toggle switched on, at 1920 by 1080, and review them against the card and composer families of the export. Record the findings and any corrections in `docs/design-deviations.md`.

### D10. Verification budget

- Decision: live verification runs use `COST_CEILING=1.00`. Expected estimated spend: Planted inconsistency about 0.50 USD per run (takeoff and rework on Claude), Missing sheet about 0.30, Missing price about 0.31, Not ready and Dry intake nothing, Stop and Pause checks on Clean run a few cents, the cost ceiling check below 0.10. Repeats for Planted inconsistency are reported with how many matched.
