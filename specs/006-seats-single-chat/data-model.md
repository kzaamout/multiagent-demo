# Data model: Seats, single model, and chat (S5)

Entities and their rules. Event payloads are the frozen 1.1.0 schema and are referenced, not restated.

## SeatOverride (in memory, registry)

| Field | Type | Rule |
|---|---|---|
| seat | agent id | one of the workflow's seats |
| model_key | string | a key in `config/models.yaml` `models`; its provider must be available |

Lifetime: from the swap until process exit. `effective_config()` returns the models configuration with overrides applied; `models.yaml` on disk is never changed.

## SeatView (served by `/api/seats`)

| Field | Type | Rule |
|---|---|---|
| seat | agent id | |
| card | Agent | the seat's live name (idle names when no run), role, model object |
| model_key | string | the effective key |
| dependency | string | the note shown on the row |
| warning | string or empty | "Reviewer shares the Writer's model family" when true |
| options | list of ModelOption | every model in the registry |

ModelOption: `{ key, label, provider, provider_label, available: bool, reason: string }`. `reason` is "no credentials in .env", "Ollama not detected at startup", or "" when available. Never a credential value.

Family rule: two models share a family when their provider and the first token of `model_id` before a digit or dot match (claude, gemini, llama, qwen, gemma, grok).

## Single-model run

Same `RunState` and recording as a Team run, with:

| Field | Value |
|---|---|
| mode | `single` on `run.started` and in `meta.json` |
| roster | one Agent, agent id `single`, role "Single model", model chosen in the composer |
| stages | `stage.changed` into intake, work, assemble, handoff, all forward; Plan and Review never entered |
| task | one `task.dispatched` and one `task.completed`, task id `single` |
| result | `{ headline, summary, total, output_path }` where `output_path` is `drafts/single-v1.md` |
| exit | `single_complete`, or a control exit (`stopped`, `cost_ceiling`) |

SingleReply (seat reply shape): `{ headline: string, summary: string, markdown: string, total: string or null }`. The markdown is committed to `drafts/single-v1.md`. No provenance tags are required or checked.

## Comparison (read from recordings)

| Field | Type | Rule |
|---|---|---|
| dataset_id | string | |
| team | RunFigures or null | newest terminated Team recording for the dataset |
| single | RunFigures or null | newest terminated Single-model recording for the dataset |

RunFigures: `{ run_id, started_at, exit, est_cost, elapsed_ms, model_label, output_path or null, summary or "" }`. For a Single-model run `model_label` is the single seat's label and `summary` is the result summary; for a Team run `model_label` is empty.

Ordering: by `started_at` in `meta.json`; only recordings with an `exit` count.

## Chat request and reply (out of band)

Request: `{ run_id, agent_id, messages: [{ role: "user" | "assistant", text }] }`. The last message must be from the user.

Reply: `{ text, model: Model, tokens_in, tokens_out, est_cost }`.

Rules: allowed when the run is paused or terminated, or when `run_id` is a recording with a prompt bundle for the seat; refused with 409 otherwise and 404 when no bundle exists for that seat in that run. The system prompt is the bundle's `system` plus `context_slice` plus one read-only line. No tools. Nothing is written or emitted.

## State transitions touched

- Team run: unchanged, plus `model.changed` at any stage while live.
- Single-model run: intake, work, assemble, handoff, terminated; `run.paused` and `run.resumed` allowed between events as today.
