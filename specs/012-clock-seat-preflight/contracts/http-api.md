# HTTP API changes for 012

Additive to the S1, S3, S5, S6, and S7 contracts, except where marked **changed**. Errors keep the `{ "error": string }` body. No response carries a credential value.

## POST /api/runs (extended)

The reply gains `clock`, the run's own clock read when the reply is built (research D4):

```json
{ "run_id": "...", "mode": "team", "stream_url": "...", "review_max_cycles": 4, "retry_budget": 2, "cost_ceiling": 5.0,
  "clock": { "now": "2026-09-21T15:04:05.123Z", "pace": 1.0 } }
```

## GET /api/meta (extended and changed)

- Gains `live_run_clock`: `{ "now": string, "pace": number }` when `live_run_id` is set, else `null`.
- **Changed**: `preflight` is the header status worked out from the stored rows and the seats in force (research D8), not a status stored with the result.

## GET /api/preflight (changed)

```json
{
 "run_mode": "laptop",
 "ran_at": "2026-09-21T09:12:00-06:00",
 "stamp": "21 Sep 2026, 09:12",
 "passed": 16,
 "applicable": 17,
 "running": false,
 "header": { "status": "pass", "glyph": "✓", "title": "Pre-flight: checks for the current seats pass, 1 unused model failed, 21 Sep 2026, 09:14" },
 "checks": [
  { "id": "model:bedrock-sonnet-5", "name": "claude-sonnet-5 via Bedrock answers", "status": "pass",
    "detail": "claude-sonnet-5 answered in 2275 ms", "elapsed_ms": 2275, "checked_at": "...",
    "subject": { "kind": "model", "model_key": "bedrock-sonnet-5", "provider": "bedrock" }, "seats": ["estimator"] }
 ]
}
```

- `checks` is every stored row in the page's order (research D6), then the derived `family` row. Model rows carry `seats`, the seat ids on that model now.
- The top-level `status` and the rows' `essential` field are removed. The page reads `header` for its own dot.
- With no stored result, `checks` lists every row with status `pending` and detail "Pending", and `header.status` is `pending`.
- The env row's `status` and `detail` are worked out on read (data model, "The env row on read").

## POST /api/preflight/run (changed)

Runs every check, the model probes at the same time (research D6), stores the result, and returns the `GET /api/preflight` body. If a recheck is running, it waits for it. 409 `{ "error": "a pre-flight is already running" }` only while another full pre-flight runs.

## POST /api/preflight/recheck (new)

Body `{ "model": "<registry key>" }`.

- Rechecks that model's row (a probe for a cloud model; the `ollama` row and the model's pulled row for a local model) and the `env` row. Merges them into the stored result and saves.
- Waits for a running full pre-flight or recheck, then runs (FR-024).
- 200 `{ "checks": [the rechecked rows as in GET /api/preflight], "header": { "status", "glyph", "title" } }`.
- 400 `{ "error": "unknown model <key>" }` for a key not in the registry.
- Emits no event. Writes nothing under any run's folder. Adds nothing to any run's meters, cost, metrics, or seat calls.
- Behind the login guard like every other `/api/` route.

## Pages (changed behaviour)

Every page's header dot (`{{PREFLIGHT_STATUS}}`, `{{PREFLIGHT_GLYPH}}`, `{{PREFLIGHT_TITLE}}`) is substituted from the header state worked out against the seats in force when the page is served.

## GET /api/datasets/{dataset_id}/comparison (extended)

`team` and `single` each gain `working_ms`, the recording's compute time: its working time worked out from its events (research D15). `elapsed_ms` stays, the recorded total. The Compare strip and the comparison line read `working_ms`.

## Unchanged

`POST /api/seats/{seat}` keeps its S5 contract and reply time. The recheck is a separate request the Settings page makes after the swap succeeds.
