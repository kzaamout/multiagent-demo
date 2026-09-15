# HTTP and stream contract (S1)

All JSON. Errors return `{ "error": string }` with a 4xx status. No authentication in S1 (S7 adds the shared login).

## Pages (static, flattened from the export)

| Path | Page |
|---|---|
| `GET /` | redirects to `/demo` |
| `GET /login` | Login; Sign in posts nothing in S1 and navigates to `/demo` |
| `GET /demo` | Demo |
| `GET /settings` | Settings |
| `GET /preflight` | Pre-flight |
| `GET /static/...` | stylesheet, scripts, fonts, images |

Every page header carries the build stamp substituted server-side.

## Metadata

`GET /api/meta` returns `{ build: { hash, date }, preflight: "pending", stub_pace: number, workflow: "electrical_rfp" }`.

## Datasets

`GET /api/datasets` returns `[{ id, number, label, has_golden, has_recording, replay_source: "recording" | "golden" | null }]` in spec order.

## Runs

`POST /api/runs` body `{ dataset_id, workflow: "electrical_rfp", mode: "team", names?: { seat: name } }`. Returns `201 { run_id, stream_url, retry_budget, cost_ceiling }`. Refuses with 409 while another run is live.

`GET /api/runs/{run_id}` returns `{ run_id, dataset_id, workflow, mode, status, exit, retry_budget, cost_ceiling, roster, started_at, event_count }`.

`GET /api/runs/{run_id}/events` returns the full event list as JSON (used to rebuild the page on reload and by the raw drawer export).

`POST /api/runs/{run_id}/answers` body `{ answers: [{ question_id, answer, action: "answer" | "escalate" }] }`. Valid while the run is paused for the human. Returns `202`.

`POST /api/runs/{run_id}/decision` body `{ decision: "approve" | "edit" | "reject", notes }`. Valid at Handoff. S1 accepts `approve` only; others return 400 with a reason naming the slice that adds them.

`POST /api/runs/{run_id}/pause`, `POST /api/runs/{run_id}/resume`, `POST /api/runs/{run_id}/stop`. Present for the state machine tests; the composer buttons stay disabled in S1.

`GET /api/prompts/{prompt_ref}` returns the prompt bundle from the run folder or the stub registry.

## Replay

`POST /api/replays` body `{ dataset_id, speed: 1 | 4 }`. Returns `201 { session_id, run_id, source: "recording" | "golden", stream_url, event_count }`. Returns 404 when the dataset has neither.

## Stream

`GET /api/streams/{stream_id}/events` is a server-sent event stream. `stream_id` is a live `run_id` or a replay `session_id`.

- Each message: `id: <seq>`, `event: <type>`, `data: <event JSON>`.
- A comment line `: keepalive` every 15 seconds.
- Resume: `Last-Event-ID` header or `?since=<seq>` replays events after that `seq` from the run's list before continuing live.
- The stream closes after `run.terminated` is sent.
- For a replay session, events are sent at the recorded gaps divided by `speed`, with the original ids.

## Recording layout

```
runs/<run_id>/
  meta.json
  events.jsonl
  prompts/<prompt_ref>.json
  knowledge.md
```
