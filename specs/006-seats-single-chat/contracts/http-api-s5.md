# HTTP API additions for S5

Additive to `specs/001-event-spine-stubbed-loop/contracts/http-api.md` and `specs/003-failure-paths-controls/contracts/controls.md`. Errors keep the `{ "error": string }` body.

## GET /api/seats

The live seat table for Settings and the composer's model dropdown.

Response 200: `{ "seats": [SeatView], "models": [ModelOption], "note": "Changes apply at the next stage." }` as defined in `data-model.md`. Credential values never appear; availability is a boolean and a reason.

## POST /api/seats/{seat}

Body: `{ "model": "<model key>" }`.

- 200 `{ "seat", "model": Model, "warning": string, "applied": "next-dispatch" | "next-run" }`. While a run is live, `model.changed` is emitted on the run's stream before this returns.
- 400 unknown model key or unknown seat.
- 409 the model's provider is not available.

## POST /api/runs (extended)

Body gains `"mode": "team" | "single"` (default team) and `"model": "<model key>"` (Single mode only; defaults to the Orchestrator's effective model). Response gains `"mode"`. A 409 still means a run is in progress.

## GET /api/runs/{run_id} (extended)

`"mode"` reports the run's mode instead of the fixed "team".

## GET /api/datasets/{dataset_id}/comparison

Response 200: the Comparison object from `data-model.md`. 404 for an unknown dataset. Reads recordings only.

## POST /api/chat

Body: `{ "run_id", "agent_id", "messages": [{ "role", "text" }] }`.

- 200 `{ "text", "model": Model, "tokens_in", "tokens_out", "est_cost" }`.
- 404 unknown run, unknown seat, or no prompt bundle for that seat in that run.
- 409 the run is live and not paused.
- 502 the model could not be reached (one line, no provider text).

Guarantees: no file under `runs/` changes, no event is emitted, no meter moves. A test digests the run folder before and after a chat.

## Stream (unchanged)

`model.changed` arrives on the run's stream like any event, with actor `system` and the current stage.
