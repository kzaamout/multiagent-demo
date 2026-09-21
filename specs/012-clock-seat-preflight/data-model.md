# Data model: Presenter clock and seat-aware pre-flight

Nothing here is an event. The event schema stays at 1.1.0 and no golden log changes.

## Clock view (browser, derived, never stored)

Worked out by the reducer from the run's events on every render (research D1, D2).

| Field | Type | Meaning |
|---|---|---|
| `workMs` | integer | Working time at the latest event: `ts(latest) - ts(run.started)` less the held time before it. 0 before `run.started`. |
| `lastTsMs` | integer | The latest event's timestamp in milliseconds. |
| `running` | boolean | `run.started` seen, no `run.terminated`, and no hold open. |
| `ended` | boolean | `run.terminated` seen. |
| `workAtHandoffMs` | integer or null | Working time at `handoff.ready`, for the termination card while approval waits. |

### Holds

| Hold key | Opens | Closes |
|---|---|---|
| `ask:<event_id>` | `clarification.asked` without `blocker` | `clarification.answered` for the last of its `question_ids` |
| `blocker:<blocker_id>` | `clarification.asked` with `blocker` | `clarification.answered` with `question_id == blocker_id` |
| `pause` | `run.paused` | `run.resumed` |
| `handoff` | `handoff.ready` | `human.approved` |

Held time is the union of open intervals: a hold that opens while another is open adds nothing until every hold has closed. `run.terminated` closes all holds at its own timestamp.

**Invariants**: `workMs` never decreases from one event to the next. `workMs` at `run.terminated` equals the final value the Elapsed figure shows (SC-003, SC-011).

## Working time on the server (`app/runs/working_time.py`, research D15)

The same hold table in Python, never stored. `working_times(events)` gives the working time at each event in milliseconds; `working_ms(events)` gives the last. The comparison figures carry it as `working_ms`; the run timeline prints it per event.

## Clock anchor (browser, presentation state in `demo.js`)

| Field | Type | Meaning |
|---|---|---|
| `kind` | `live`, `replay`, or null | Null for fixed views: nothing ticks. |
| `runNowMs` | integer | Live: the run clock's `now` from the server, in milliseconds. |
| `pace` | number | Live: the run clock's pace (1 for a live team run, `STUB_PACE` for a stubbed run). |
| `receivedAt` | number | Live: `performance.now()` when the server's `now` arrived. |
| `arrivedAt` | number | Replay: `performance.now()` when the latest event arrived. |
| `speed` | 1 or 4 | Replay: the chosen speed. |
| `shownMs` | integer | The highest value shown in this run; the figure never goes below it. Reset with the view. |

Value at `t` (research D3): live `workMs + max(0, runNowMs + (t - receivedAt) * pace - lastTsMs)`; replay `workMs + (t - arrivedAt) * speed`; either only while `running`, else `workMs`; then `max(shownMs, value)`.

## Run clock reading (server, in two responses)

```json
{ "now": "2026-09-21T15:04:05.123Z", "pace": 1.0 }
```

`now` is the run's `Clock.now_ts()`: the timestamp of the current offset on the run's own clock, in the event `ts` format. `pace` is `Clock.pace`.

## Stored pre-flight result, schema 2 (`runs/preflight.json`)

```json
{
 "schema": 2,
 "run_mode": "laptop",
 "ran_at": "2026-09-21T09:12:00-06:00",
 "checks": [
  {
   "id": "model:gemini-3-8-flash",
   "name": "gemini-3.8-flash via Google answers",
   "status": "fail",
   "detail": "gemini-3.8-flash did not answer (NotFoundError)",
   "elapsed_ms": 10301,
   "checked_at": "2026-09-21T09:14:40-06:00",
   "subject": { "kind": "model", "model_key": "gemini-3-8-flash", "provider": "google" }
  },
  {
   "id": "env",
   "name": ".env completeness",
   "status": "fail",
   "detail": "Missing DEMO_USERNAME, DEMO_PASSWORD",
   "elapsed_ms": 0,
   "checked_at": "2026-09-21T09:12:00-06:00",
   "subject": { "kind": "env", "login_missing": ["DEMO_USERNAME", "DEMO_PASSWORD"], "keys_missing": {} }
  }
 ]
}
```

| Field | Rule |
|---|---|
| `schema` | 2. Any other value fails to load; the page reads "not run yet". |
| `ran_at` | Time of the last full pre-flight. Null when only rechecks have written the file. |
| `checks[].id` | `model:<registry key>`, or one of `ollama`, `typst`, `png`, `tunnel`, `disk`, `env`, `intro-recording`, `replays`. Stable once shipped. |
| `checks[].status` | `pass`, `fail`, or `skip` (not applicable). |
| `checks[].detail` | One line. Never a credential value, never a provider's message text: an exception's class name at most. |
| `checks[].checked_at` | When this row was last checked, by a full run or a recheck. |
| `checks[].subject.kind` | `model`, `env`, or `fixed`. |
| `subject.model_key`, `subject.provider` | Model rows only. |
| `subject.login_missing` | Env row only: which of `DEMO_USERNAME`, `DEMO_PASSWORD` are unset. Names only. |
| `subject.keys_missing` | Env row only: provider to the missing key's name (`GEMINI_API_KEY`) or `AWS credentials`, for every provider in the registry except Ollama. |

**The env row on read**: its stored `status` and `detail` are replaced when the result is read. It fails when the login pair is incomplete, in either mode, or when a key is missing for a provider a seat in force is on. The detail names exactly those. A missing key for a provider no seat uses is not a failure. That provider's model rows already say "No key in .env" and are not applicable.

**Merge rule** (recheck): rows are replaced by `id`. Rows the recheck did not touch keep their `checked_at`. `ran_at` is left as it was. With no stored file, a recheck writes a file with `ran_at: null` and only its rows.

## Rows worked out when read (never stored)

| Id | Name | Fails when |
|---|---|---|
| `family` | Reviewer and Writer on different model families | `registry.family_warning()` over the seats in force is not empty |

## Header state (derived on every read, never stored)

| Field | Type | Meaning |
|---|---|---|
| `status` | `pending`, `pass`, `warn`, `fail` | Grey, green, amber, red. The values are the ones `.pf-dot[data-status]` already styles. |
| `glyph` | string | ○, ✓, !, ✕ |
| `title` | string | One line; see research D8 for each form. |

Inputs: the stored result (or none), the effective seat configuration, the run mode, and the derived rows. The policy is in research D8. The same function serves every caller.

## Pre-flight payload (`GET /api/preflight`, `POST /api/preflight/run`)

The stored rows plus the derived rows, each with `seats` (the seat ids on that model, model rows only), then `ran_at`, `stamp`, `run_mode`, `passed`, `applicable`, `running`, and `header`. `passed` and `applicable` count rows with status `pass`, and with `pass` or `fail`. The confirmation shows when `passed == applicable`. See `contracts/http-api.md`.
