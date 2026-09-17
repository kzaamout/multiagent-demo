# Research: Seats, single model, and chat (S5)

Every unknown in the plan's Technical Context resolved, with the alternative rejected. Dated 2026-09-16.

## D1. Where the seat override lives

- Decision: the registry keeps `overrides: dict[seat, model_key]` in memory and exposes `effective_config()`, a `ModelConfig` with the override applied to `seats`. `strands_model_for(effective, seat)` builds the model as today. Nothing writes `config/models.yaml`.
- Rationale: owner decision 5; constitution X keeps configuration files under version control, not under a button.
- Alternatives: writing `models.yaml` (rejected by the owner); a settings file under `runs/` (a second source of truth that drifts, rule 15).

## D2. Availability once at startup

- Decision: `check_availability` runs once when the registry is built and the result is cached; `/api/seats` and `/api/providers` serve the cache. Ollama models are those the cache saw. Tests inject the availability map, so no network call happens in the suite.
- Rationale: owner decision 7 and the roadmap's deferral of health checks to S7; a page load must not wait on a provider.
- Alternatives: a check per page load (rejected; S7 owns health).

## D3. Applying a swap to a live run

- Decision: `Orchestrator.change_model(seat, agent, seat_model)` updates `self.roster[seat]`, calls `scenario.swap_seat_model(seat, seat_model)` on a live source (no-op on a stub), and emits `model.changed` as a system event at the current stage with `from_model` and `to_model`. Later events from that seat carry the new model on their actor because `_relay` reads the roster; the next prompt bundle names the new model because `_bundle` reads `seat_models`. A call already in flight finishes on the old model.
- Rationale: spec 2.3 and criterion 6; the event is the visible fact, the roster is the single source the cards read.
- Alternatives: swapping at the dispatch itself (the card would lag the presenter's click; rejected); restarting the seat's in-flight call (waste and a visible stall; rejected).

## D4. The Single-model run inside the Orchestrator

- Decision: `Orchestrator(mode="single")` runs `run_single()`: `run.started` with mode single and a one-seat roster; `stage.changed` into intake; `task.dispatched` for task id `single`; `stage.changed` into work; the source's `single()` yields progress, tool calls, and `task.completed` with the output; `stage.changed` into assemble, then handoff; `run.terminated` with `single_complete`. Pause, Stop, and the cost ceiling work through the existing gates and meter path. The output markdown is saved under `drafts/single-v1.md` and named in the result so the Compare strip can read it through the run files route.
- Rationale: spec section 5 lists exactly these events; reusing the Orchestrator keeps recording, replay, gates, and metrics identical to a Team run.
- Alternatives: a separate single-run class (duplicates recording and control code; rejected).

## D5. The Single-model actor

- Decision: seat `single`, role "Single model", names Simon and Sofia, colour `#6b5e7a`, in both workflows. Instructions in `config/electrical-bid/seats/single.md`: one prompt that reads the manifest, takes off, prices with the lookup tool, and writes the proposal, with no review and no tags. Tools: the union of the Intake, Estimator, Pricing, and Writer tools. Scope: request documents, knowledge file, readiness checklist, drawing pages, estimating conventions, template. Reply shape `SingleReply { headline, summary, markdown, total }`. Its model is chosen in the composer and defaults to the Orchestrator's effective seat model.
- Rationale: owner decisions 1, 2, 3, 10; constitution V (identity is the seat, the model is an attribute).
- Alternatives: the Orchestrator's card with a different label (rejected by the owner).

## D6. The comparison source

- Decision: `app/runs/comparison.py` scans `runs/` for the newest terminated recording per mode for a dataset (from `meta.json`: `dataset_id`, `mode`, `exit`, `started_at`) and reads `est_cost`, `elapsed_ms`, exit, model, and, for a Single-model run, the `task.completed` result and the output path from `events.jsonl`. `/api/datasets/{id}/comparison` serves it; the Demo page fetches it on load, on dataset change, and after `run.terminated`.
- Rationale: owner decision 4; recordings are the only durable record (constitution VIII) and already carry the mode.
- Alternatives: keeping the comparison in the browser session (lost on reload; rejected).

## D7. Chat as an out-of-band call

- Decision: `POST /api/chat` with `run_id`, `agent_id`, and the message history. The server finds the seat's last prompt bundle for that run (in memory for a live or replayed run, else `runs/<id>/prompts/`), builds a fresh Strands Agent with no tools whose system prompt is the bundle's system text plus the context slice and a line stating the chat is read-only, and returns the reply text with tokens and estimated cost. It refuses unless the run is paused or terminated, or is a recording. Nothing is written under `runs/`, no event is emitted, no meter is updated. The panel keeps the history and drops it on close.
- Rationale: spec 2.7 and owner decisions 8 and 9; constitution IV (not the human door) and the non-goal on changing instructions mid-run.
- Alternatives: server-side chat sessions (state to clear and leak; rejected); reusing the seat's tools in chat (a chat could then read files and look like work; rejected).

## D8. Settings comparison with live labels

- Decision: the visual test builds the app with a test model configuration whose seat defaults carry the export's labels and an injected availability map matching the export's greyed entries, so the comparison checks layout and dropdown rendering against the references while the real page shows the live models. Recorded as an S5 deviation.
- Rationale: constitution V (truthful labels on the real page) and XIII (the comparison stays meaningful).
- Alternatives: masking every label (hides the dropdown content the comparison exists to check; rejected).

## D9. Meters completion

- Decision: the detail row gains "Latency" from `latency_ms`; the comparison line renders from the comparison route; the ceiling bar and detail row otherwise stay as built in S1.
- Rationale: spec 2.2; the figures already exist in events.
