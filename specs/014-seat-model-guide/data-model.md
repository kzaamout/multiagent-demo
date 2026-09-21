# Data model: Seat model guide on Settings

Nothing here is stored. Every entity is worked out from the `metrics.json` (or event log) each run already writes and from `config/models.yaml`, when the Settings page or the report asks (FR-011).

## Model kind (registry field)

Added to each model in `config/models.yaml` and to `ModelSpec` in `app/live/providers.py`.

| Field | Type | Rule |
|---|---|---|
| `weights` | `"open"`, `"proprietary"`, or absent | Set by hand from the model's licence (decision 6a). `ModelConfig.load` raises `ValueError` naming the model for any other value. Absent means not classified: the model is never a pick, and the report names it. |

## Seat model record

One seat on one model label across every counted run (research D3). In `app/runs/guide.py`.

| Field | Type | From |
|---|---|---|
| `agent_id` | str | the seat row's `agent_id` |
| `model` | str | the seat row's model label |
| `runs` | int | seat rows with at least one call or one reply |
| `replies` | int | sum of `replies` |
| `first_time` | int | sum of `accepted_first_time` |

Derived:

- `share = instruction_accuracy(first_time, replies)`: `first_time / replies`, or `None` when `replies` is 0 (FR-002).
- `percent = whole_percent(first_time, replies)`: the share as a whole number, rounded as the report formats it (`f"{share * 100:.0f}"`), or `None`.
- `bound = wilson_lower(first_time, replies)`: the Wilson score lower bound at z = 1.959963984540054, or `None` when `replies` is 0 (FR-004).

## Seat pick

For one seat and one kind (open or proprietary).

| Field | Type | Rule |
|---|---|---|
| `status` | `"pick"`, `"no_runs"`, `"too_few_runs"` | `pick` when a candidate qualifies; `too_few_runs` when at least one candidate exists but none has 5 runs; `no_runs` when there is no candidate (FR-007) |
| `record` | Seat model record or none | present only with `pick` |
| `model_key` | str or none | the registry key of the picked model |

A **candidate** for a seat and a kind is a record for that seat whose model label matches a registry model with that `weights` value, and which meets the seat's needs: when `needs_image_input(seat)` is true, the registry model has `image_input: true` (FR-006). A candidate **qualifies** when `runs >= MIN_RUNS_FOR_BEST` (5) and `replies > 0` (FR-003).

Choice among qualifying candidates (FR-004): highest `bound`, then most `replies`, then earliest position in `config/models.yaml`.

## Seat guide row

For one Settings seat.

| Field | Type | Rule |
|---|---|---|
| `current` | Seat model record or none | the record for the seat's effective model (after any in-memory swap) at this seat, whatever its runs; none when it has no record (FR-010) |
| `open` | Seat pick | |
| `proprietary` | Seat pick | |

## Seat guide

| Field | Type | Rule |
|---|---|---|
| `runs` | int | counted runs (research D2) in which at least one seat made a model call or a reply, the report's "called a model" count; stub runs add nothing |
| `min_runs` | int | 5 |
| `rows` | seat to Seat guide row | for orchestrator, intake, estimator, pricing, writer, reviewer; never `single` |
| `unclassified` | list of str | labels of registry models with no `weights`, in registry order (report only) |

## Run folder cache entry

Held in memory by `SeatGuide`, one per run folder (research D7).

| Field | Type | Rule |
|---|---|---|
| `signature` | tuple | `(file name, st_mtime_ns, st_size)` of `metrics.json`, or of `events.jsonl` when there is no `metrics.json` |
| `seats` | list of seat rows or none | the folder's seat rows as `metrics_of` returns them; none when the folder cannot be read |

Lifecycle: an entry is created the first time a folder is seen, replaced when its signature changes, and dropped when the folder disappears. The aggregated records are recomputed only when the set of `(folder, signature)` pairs, less the live run, differs from the last request.
