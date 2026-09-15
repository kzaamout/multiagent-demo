# Contract: presenter controls (S3)

All routes exist except the `dry_intake` field, which is new. Responses are JSON. Errors use HTTP status and `{"error": "<one sentence>"}`.

## POST /api/runs

Body: `{"dataset_id": "missing-sheet", "dry_intake": false}`. `dry_intake` is optional and defaults to false.

- 201 `{"run_id": "...", "stream_id": "...", "mode": "live" | "stub"}`
- 409 when a run is already live, or when a live seat's provider is unavailable (the message names the seat)

## POST /api/runs/{run_id}/pause

- 202 when the run is running; the Orchestrator emits `run.paused` and dispatches nothing new until resume
- 202 and no event when the run is already paused, waiting on a human, at Handoff, or ended

## POST /api/runs/{run_id}/resume

- 202 when paused by the presenter; the Orchestrator emits `run.resumed`
- 202 and no event otherwise

## POST /api/runs/{run_id}/stop

- 202 in any state before termination; the run ends with `run.terminated` exit `stopped` within 5 s; results arriving later are discarded
- 202 and no event when the run has ended

## POST /api/runs/{run_id}/answers

Unchanged. For a blocker: `{"answers": [{"question_id": "<blocker_id>", "answer": "...", "action": "answer" | "escalate"}]}`.

## Page controls

- Pause button: posts pause while running and reads Pause; posts resume while paused by the presenter and reads Resume.
- Stop button: posts stop.
- Dry intake toggle: Off or On, sent as `dry_intake` with the next Run; locked while a run is live.
- Enabled states follow `data-model.md`.
