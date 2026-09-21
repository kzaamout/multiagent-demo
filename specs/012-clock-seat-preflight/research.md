# Research: Presenter clock and seat-aware pre-flight

All decisions below were taken against the code on `main` at 7a75a68 (2026-09-21). No new dependency is added.

## D1. Where the working time comes from

**Decision**: The reducer (`app/web/static/js/reducer.js`) works out the run's working time from the events alone, as it works out everything else: the time from `run.started` to the latest event, less the time covered by human waits (D2). It exposes `view.clock = { workMs, lastTsMs, running, ended, workAtHandoffMs }`. The reducer stays pure and runs no timer.

**Rationale**: Principle II keeps events the only source of run state. The working time at every event is a fact the events already carry; only the stretch since the latest event needs the passage of time, and that is the one thing the display-only clock adds (D3).

**Alternatives considered**: a server-side tick pushed on the stream every second (rejected by the owner, decision 1, and it would not cover the Introduction's public replay, which plays in the browser); a new event carrying elapsed time (a schema change, and it would bloat every recording and golden log).

## D2. Human waits, read from existing events

**Decision**: A hold is open over these intervals, all from events schema 1.1.0 already has:

| Hold | Opens at | Closes at |
|---|---|---|
| Clarification batch | `clarification.asked` without `blocker` | the `clarification.answered` that answers the last of its `question_ids` |
| Blocker | `clarification.asked` with `blocker` | `clarification.answered` whose `question_id` is the blocker's id |
| Pause | `run.paused` | `run.resumed` |
| Handoff | `handoff.ready` | `human.approved` (any decision) |

`run.terminated` closes every open hold and ends the clock. The held time is the union of the hold intervals, so a Pause during a question batch is not counted twice. The working time at an event is `(ts(event) - ts(run.started)) - held time before it`.

The Handoff hold closes at the human's decision, not at the run's end. Owner decision 2 is that the clock "continues after the human submits the response"; after an Edit decision the Orchestrator commits and compiles the human's draft before `run.terminated`, and that is work. Spec FR-003 and User Story 1 scenario 5 are corrected to say so.

**Rationale**: Every wait the owner named is bracketed by an Orchestrator or human event, so the working time needs no new event and no golden log is re-recorded. Recordings made before this change get the same working time when replayed.

**Alternatives considered**: counting from `blocker.raised` (the specialist raises it before the Orchestrator puts it to the human, and the run keeps working in between); counting a hold from `clarification.needed` (Intake raises questions before the Orchestrator batches them, the same objection).

## D3. How the clock advances between events

**Decision**: A small pure module `app/web/static/js/clock.js` (`S1Clock`) gives the value to show at a moment, from `view.clock`, an anchor, and a rate:

- **Live run** (the page follows a run through the stream): the anchor is the run's own clock read from the server, `{ now, pace }`, taken with the client time at which the response arrived. The run's clock at client time `t` is `now + (t - receivedAt) * pace`. The value is `workMs + max(0, runNow - lastTsMs)` while running, else `workMs`.
- **Replay** (the server replay stream, or the Introduction's public replay in the browser): the anchor is the client time the latest event arrived, the rate is the chosen speed. The value is `workMs + (t - arrivedAt) * speed` while running.
- **Fixed views** (`?golden=`, `?run=`, a finished run): no anchor, so the value is `workMs` and nothing ticks. The screenshot states stay still.

The Demo page runs one `setInterval` of 250 ms divided by the replay speed (250 ms for a live run), only while a run is running and anchored. On each tick it writes the `#elapsed` text if the shown second changed. It re-renders nothing else. The shown value never decreases during a run: the page keeps the highest value shown since the run began and resets it with the view.

**Rationale**: Live runs use the server's run clock, not the browser's wall clock. A viewer reaching the laptop through the tunnel may have a clock minutes off. Stubbed runs stamp events at `STUB_PACE` (4 by default) times wall time, so the browser cannot know the rate without being told. Reading the run clock once when the page attaches also answers FR-009: a reload mid-run shows the right working time at once. A 250 ms tick keeps the shown second within a quarter second of the true one, and the hidden-tab case needs nothing extra, because the value is computed from the time, not counted up.

**Alternatives considered**: the browser's wall clock against event timestamps (clock skew over the tunnel, and wrong for stubbed runs); counting seconds up with `setInterval` (drifts, and a throttled background tab stops counting).

## D4. The run clock on the wire

**Decision**: The Orchestrator's `Clock` gains `now_ts()`, the timestamp of the current offset on the run's own clock. Two existing responses carry `{ "now": <ts>, "pace": <float> }`: the `POST /api/runs` reply as `clock`, and `/api/meta` as `live_run_clock` when a live run exists (null otherwise). No new route. No polling: the page reads it once when it attaches to a run.

**Rationale**: These are the two moments the page attaches to a live run: when it starts one, and when it loads while one is running. Both responses already exist, and an added field does not break their S1 and S5 contracts.

## D5. The termination card uses the same figure

**Decision**: The termination card's eyebrow shows `view.clock.workMs` once the run has ended, and `view.clock.workAtHandoffMs` while Handoff waits for approval. The recorded `run.terminated.summary.elapsed_ms` is not changed. It stays the run's total time for the performance record and the comparison route.

**Rationale**: Owner decision 10. After the run ends the clock and the card read the same value from the same reducer.

**Follow-up, owner decision 13**: The Compare strip's line ("Team $x in m:ss · Single model $y in m:ss") read `summary.elapsed_ms`, so a Team run with a human wait showed its total time there. It now shows compute time, the working time, worked out on the server by D15.

## D15. Working time on the server

**Decision**: `app/runs/working_time.py` holds the hold table of D2 in Python, once: `working_times(events)` gives the working time at every event and `working_ms(events)` the final value. The comparison route adds `working_ms` to each recording's figures; `elapsed_ms` stays for the S5 contract. The Compare strip and the comparison line read `working_ms`. The run timeline PDF prints each event's working time. The browser suite checks that the Python function and the page's reducer agree at every event of every golden log, so the two copies of the rule cannot drift apart unseen.

**Rationale**: Owner decisions 12 and 13. The comparison is read from recordings on the server and the timeline is compiled there, so neither can use the reducer. Nothing is stored: rule 15 keeps one place per kind of number, and the working time is always derived from the events.

**Alternatives considered**: storing the working time in `run.terminated.summary` (a schema change, and recordings made before it would have none); working it out in the browser for the comparison (the route returns figures, not events, and the timeline is a PDF).

## D6. One row per model

**Decision**: The per-provider rows `provider:<name>` are replaced by one row per model in the registry (`config/models.yaml`), with id `model:<key>`, in registry order. A cloud model's row makes the existing one-word probe (`strands_probe`) with a 30 s limit. All cloud probes run at the same time with `asyncio.gather`, and the fixed checks run alongside them, with PNG export still after Typst. A cloud model whose provider has no credential is not applicable ("No key in .env for Google Gemini", or "No AWS credentials" for Bedrock), so a missing optional key is not reported as a broken model. A local model's row checks that Ollama has the model pulled, from one tags call made by the `ollama` row. In Cloud mode local rows are not applicable. Row names are the model label with a verb: "claude-sonnet-5 via Bedrock answers", "qwen3.5:9b pulled in Ollama".

**Rationale**: Owner decision 6. Probing per model finds a retired model id such as the Gemini 2.5 Pro entry's `NotFoundError`, which one probe per provider only finds when it happens to pick that model. Running the probes at the same time keeps a full pre-flight within 60 s (SC-006): the slowest probe bounds the model rows, and the compile runs alongside.

**Alternatives considered**: one row per provider listing each model in its detail line (keeps the old ids, but one line cannot say which of several models failed and why, and the header needs a status per model).

## D7. The stored result, version 2

**Decision**: `runs/preflight.json` moves to `schema: 2`. It holds `run_mode`, `ran_at` (the last full pre-flight, or null when only rechecks have run), and the rows. Each row keeps `id, name, status, detail, elapsed_ms` and adds `checked_at` and a `subject`: `{kind: "model", model_key, provider}`, `{kind: "env", login_missing: [...], keys_missing: {provider: name}}`, or `{kind: "fixed"}`. The old `essential`, `status`, `passed`, and `applicable` fields are dropped from the file: essentialness depends on the seats in force, so it is worked out when read (D8). A schema 1 file fails to load and reads as "not run yet".

**Rationale**: The header must be worked out against the seats in force when the page loads (FR-014), so the file stores facts, not verdicts. Structured `subject` fields let the header ask "is this model on a seat" and "is this missing key a seat's provider" without parsing detail text.

**Alternatives considered**: keeping schema 1 and re-deriving essentialness by parsing ids and detail lines (brittle, and it would read the login pair out of a sentence).

## D8. The header policy

**Decision**: A new module `app/preflight/header.py` holds the policy as one function over the stored rows, the effective seat configuration, and the run mode. It is the only place that decides the dot:

- **Red** when a row failed for: a model a seat is on; `ollama` while a seat is on a local model in Laptop mode; `typst`; `png`; `disk`; `env` with a missing key for a seat's provider, or a missing login pair in Cloud mode. Also red, derived without a row, when a seat is on a local model in Cloud mode.
- **Amber** when nothing is red and a row failed for: `tunnel`; `family` (D9); `intro-recording`; `replays`.
- **Grey** when nothing is red or amber and either no pre-flight has run or a seat's model has no row.
- **Green** otherwise, with the count of failed rows that do not matter for the current seats in the tooltip.

Tooltips: red "Pre-flight: gemini-3.8-flash via Google did not answer (Estimator seat), 21 Sep 2026, 09:12"; amber "Pre-flight: the Reviewer shares the Writer's model family, 21 Sep 2026, 09:12"; green "Pre-flight: checks for the current seats pass, 1 unused model failed, 21 Sep 2026, 09:12"; grey "Pre-flight: not run yet" or "Pre-flight: gemma4:12b (Reviewer seat) not checked yet". The stamp is the newest `checked_at` among the rows that decided the state.

Every caller that renders the dot (the page helper, the Introduction page, `/api/meta`, the Pre-flight payload, and the recheck reply) calls this one function with `registry.effective_config()`.

**Rationale**: FR-014 to FR-019 in one place, testable as a table of cases without a server.

## D9. Rows worked out when read

**Decision**: The `family` row ("Reviewer and Writer on different model families") is not stored. It is built each time the result is read, from `registry.family_warning()` over the seats in force. It fails with the existing warning text when they share a family. The `intro-recording` row (the pinned public run's events are on this machine) and the `replays` row (every dataset has a recording or golden log, naming any that has neither) are checked in the full pre-flight and stored. Today every dataset has one and the pinned recording is present, so both pass.

**Rationale**: The family pairing changes with every seat change and every restart, and it costs nothing to work out. Recordings change only when runs are added, which can only make the replays row pass.

## D10. The recheck

**Decision**: A new route `POST /api/preflight/recheck` with body `{ "model": "<key>" }`. The Settings page calls it after a seat change succeeds, as a second request, so the swap applies at once (decision 8). The server rechecks the model's row (a probe for a cloud model; the `ollama` row and the model's pulled row for a local model) and the `env` row, merges them into the stored result by id with the recheck's `checked_at`, saves, and replies with the rechecked rows and the header state. The existing `/api/seats/{seat}` route is unchanged.

Full runs and rechecks share one `asyncio.Lock` for writes. A recheck waits for a running full pre-flight and then runs (FR-024). A full run started while a recheck holds the lock waits for it. A second full run while one is running is still refused with 409, which is now tracked by its own flag. A recheck is not a run: it emits no event and writes nothing under a run's folder. The probe's tokens are not metered into any run (FR-023).

**Rationale**: Owner decisions 7 to 9. Keeping the recheck out of the seat route keeps that route's S5 contract and its reply time.

**Alternatives considered**: running the recheck inside `POST /api/seats/{seat}` (blocks the swap's reply for up to 35 s); a background task with the page polling for the result (FR-026 forbids the timer).

## D11. Which pages update the dot in place

**Decision**: The Settings page sets its header dot's status, glyph, and title from the recheck reply, as `preflight.js` already does from a full run. Other open pages show the new state on their next load.

**Rationale**: Pushing the state to other pages needs a stream or a timer. The spec's assumptions keep it out.

## D12. Screenshots

**Decision**: The fixtures `tests/fixtures/preflight-all-pass.json` and `preflight-one-fail.json` are rewritten in schema 2. They keep the export's eight visible rows as closely as the new row set allows: two cloud model rows carrying the export's provider row names and detail texts, then Ollama, Typst, PNG, tunnel, disk, and `.env`. The capture app's seats are set so that the fixture's model rows are the seats' models. The rows this change adds (local model rows, family, Introduction recording, replays) are masked in `tests/visual/masks.py` with the reason and the slice, as S7 masked the header. The Demo states `demo-running` and `demo-terminated` show working time, which in the planted inconsistency golden log excludes the clarification wait. If their elapsed text or termination eyebrow differs from the reference beyond the tolerance, that region is masked with the reason. `docs/design-deviations.md` records both.

**Rationale**: Principle XIII keeps the screenshot comparison. Principle XVIII allows added rows in the export's own component family. The mask records the addition instead of hiding it.

## D13. The constitution amendment

**Decision**: Principle II gains one sentence: "The Demo page's Elapsed figure is the one display-only clock: it advances between events from the working time the events give, freezes while the run waits on the human, stops at `run.terminated`, and no state, event, or other figure depends on it." Version 1.2.0 to 1.3.0 (MINOR, materially expanded guidance), with a Sync Impact Report. `CLAUDE.md` rule 3 adds: "The one exception is the display-only Elapsed clock (constitution II)." `docs/spec-input.md` moves to 0.8 with a changelog entry for sections 2.2 and 2.4, recording the two S7 decisions this supersedes: a seat swap no longer leaves the stored result alone, and a laptop may go green without a login pair.

**Rationale**: Owner decision 1 and principles X and XIX: the controlled documents change first.

## D14. Testing the clock

**Decision**: The clock is tested in the browser suite (`pytest -m visual`) with Playwright's clock control (`page.clock.install()`, `page.clock.run_for()`), which makes timers and `Date.now()` deterministic. Three kinds of test. Unit-style checks call `S1Reducer.reduce` and `S1Clock.valueAt` in the page over every golden log and assert the working time and holds at every event. A replay of the planted inconsistency golden log at 1x and 4x asserts the tick rate, the hold during the clarification wait, and the final value. A stubbed live run reloaded mid-run asserts FR-009. Python tests cover the run clock fields, the pre-flight rows, the header policy, the recheck, and the credential marker.

**Rationale**: The project tests its browser code through Playwright, and there is no JavaScript test runner to add (principle XV). Playwright's clock control is part of the Playwright package already installed.
