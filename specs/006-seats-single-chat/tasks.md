---

description: "Task list for slice S5: seats, single model, and chat"
---

# Tasks: Seats, single model, and chat (S5)

**Input**: Design documents from `specs/006-seats-single-chat/`

**Prerequisites**: plan.md, spec.md, research.md (D1 to D9), data-model.md, contracts/http-api-s5.md, quickstart.md

**Tests**: Included. The spec's success criteria name scripted tests per story and one byte-identical folder test (constitution XIII and XVI).

**Organization**: One phase per user story in priority order. Shared files (`app/main.py`, `render.js`, `reducer.js`, `app.css`, `events.py`) receive new functions, routes, and appended rules only, so the S4 branch rebases cleanly.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1 to US4)
- Paths are relative to the worktree root `C:\Users\Khobaib\OneDrive\Desktop\code\multiagent-demo-s5`

## Path Conventions

Single web application: `app/` (engine, API, static pages), `config/` (seat files, registry), `tests/` (unit, integration, visual).

---

## Phase 1: Setup

**Purpose**: Test folders and the registry fixture every story reads.

- [ ] T001 Create `tests/unit/s5/__init__.py` and `tests/integration/s5/__init__.py`
- [ ] T002 [P] Create `tests/fixtures/models-export.yaml`, a models configuration whose seat defaults carry the export's labels (claude-sonnet via Bedrock, llama3.1 8b local, gemini-2.5-pro via Google) plus two greyed entries (grok-3 via xAI, claude-sonnet via Anthropic), for the Settings comparison (research D8)

---

## Phase 2: Foundational

**Purpose**: The registry changes every story depends on: availability cached once, per-seat overrides, effective configuration.

- [ ] T003 In `app/live/providers.py` add `family_of(spec) -> str` (provider plus the first token of `model_id` before a digit or dot) and `ModelConfig.with_seat(seat, model_key) -> ModelConfig`
- [ ] T004 In `app/runs/registry.py` add `overrides: dict[str, str]`, `availability` cached from `check_availability` once in `__init__` (injectable for tests), `effective_config()`, `set_seat_model(seat, key)` raising `ValueError` for an unknown key and `LiveUnavailable` for an unavailable provider, and `seat_table()` returning the SeatView list and ModelOption list of data-model.md (reason strings exactly "no credentials in .env" or "Ollama not detected at startup", never a credential value)
- [ ] T005 Make `build_orchestrator` and `strands_model_for` use `effective_config()` so the next run and the next dispatch read the override, in `app/runs/registry.py`
- [ ] T006 [P] Unit tests in `tests/unit/s5/test_registry_overrides.py`: override applied to `effective_config`, `models.yaml` untouched (file digest before and after), unknown key refused, unavailable provider refused, family detection for claude, gemini, llama, qwen, gemma, grok

**Checkpoint**: registry tests green; no route yet.

---

## Phase 3: User Story 1 - Swap a seat's model and see it everywhere (Priority: P1)

**Goal**: Settings live; a swap emits `model.changed` into the live run, updates every card within a second, and the next dispatch uses it.

**Independent Test**: `tests/integration/s5/test_model_swap.py` with scripted seats, and the Settings captures closed and open.

- [ ] T007 [US1] In `app/orchestrator/orchestrator.py` add `change_model(seat, agent, seat_model)`: update `self.roster[seat]`, call `self.scenario.swap_seat_model(seat, seat_model)` when the source has it, emit `model.changed` as a system event at the current stage with `from_model` and `to_model`; raise `RuntimeError` after termination
- [ ] T008 [P] [US1] In `app/live/source.py` add `swap_seat_model(seat, seat_model)` replacing `self.seat_models[seat]`; in `app/agents/source.py` add the optional protocol member and a no-op on `StubAgentSource`
- [ ] T009 [US1] In `app/main.py` add `GET /api/seats` and `POST /api/seats/{seat}` per `contracts/http-api-s5.md` (200 with `applied` next-dispatch or next-run and the family `warning`; 400 unknown; 409 unavailable); when a run is live build the seat model through the registry and call `change_model` before returning
- [ ] T010 [P] [US1] In `app/web/static/js/reducer.js` handle `model.changed` by replacing `view.roster[agent_id].model` (new case only) so feed cards, meters, and the termination card show the new label
- [ ] T011 [P] [US1] Create `app/web/static/js/settings.js`: fetch `/api/seats`, render one `seat-row` per seat with the agent card (56 px avatar), a `model-select` button, a `menu` of `menu-item` entries (greyed with `menu-note` reason and `aria-disabled` when unavailable), the dependency note, and the warning line; on choice POST and re-render; keep the export's markup classes from `app/web/static/css/app.css`
- [ ] T012 [US1] Rewrite `app/web/pages/settings.html` rows as a container filled by `settings.js`, keeping the header, title, "Changes apply at the next stage." line, and the eight seat order (six bid response seats then the two appraisal seats) so the comparison layout holds; remove the "Model swap arrives in slice S5" titles
- [ ] T013 [P] [US1] Append rules to `app/web/static/css/app.css` for the open seat menu (`.seat-select-col .menu`, `.menu-item[aria-disabled="true"]` grey `#93939f`, cursor not-allowed) and the warning line (`.seat-warning`, 13 px, `#b45309`)
- [ ] T014 [US1] Integration test `tests/integration/s5/test_model_swap.py`: on the live harness swap the Estimator between Intake and Work; assert one `model.changed` with from and to, the Estimator's later actors carry the new model, the next Estimator bundle's model label is the new one, and the Pricing seat is untouched; a swap after termination is refused; a Reviewer swap onto the Writer's family returns a warning string
- [ ] T015 [P] [US1] API test `tests/integration/s5/test_seats_api.py`: `/api/seats` lists options with availability and reasons and never a credential value; POST applies next-run when idle and returns 409 for a greyed provider
- [ ] T016 [US1] Visual: in `tests/visual/capture_app.py` add state `settings-dropdown` (open the Estimator menu by click), build the test app in `tests/visual/test_screenshots.py` with `ModelConfig.load(tests/fixtures/models-export.yaml)` and an injected availability map; add the new state to the parametrised list and any mask in `tests/visual/masks.py` with its reason

**Checkpoint**: US1 tests and the Settings comparison green.

---

## Phase 4: User Story 2 - Single-model run fills the Compare strip (Priority: P1)

**Goal**: A Single-model run with its own actor, four stage changes, exit `single_complete`, recorded and replayable; the Compare strip and comparison line read the recordings.

**Independent Test**: `tests/integration/s5/test_single_run.py` and `tests/unit/s5/test_comparison.py`.

- [ ] T017 [P] [US2] In `app/orchestrator/roster.py` add `Seat("single", "Single model", ("Simon", "Sofia"), "#6b5e7a", BEDROCK_SONNET, ("electrical_rfp", "appraisal"))`; keep `seats_for` returning the team seats only unless `include_single=True`, so Team rosters are unchanged
- [ ] T018 [P] [US2] Create `config/electrical-bid/seats/single.md`: one prompt for the whole job (read `prepared/manifest.md`, take off with `quantity_calculate`, price with `price_list_lookup`, write the proposal with `template_render`), no review, no provenance tags, reply shape `{"headline", "summary", "markdown", "total"}`; placeholders `{name}`, `{review_max_cycles}`, `{long_lead_days}` allowed; no em dashes
- [ ] T019 [P] [US2] In `app/seats/definitions.py` add seat `single` with tools `("prepare_documents", "document_parse_pdf", "document_extract_attachments", "vision_read_drawing", "quantity_calculate", "price_list_lookup", "template_render")` and scope `{REQUEST_DOCUMENTS, KNOWLEDGE_FILE, READINESS_CHECKLIST, DRAWING_PAGES, ESTIMATING_CONVENTIONS, TEMPLATE}`; in `app/live/strands_tools.py` add the `single` entry to `by_seat` with that union
- [ ] T020 [P] [US2] In `app/live/replies.py` add `SingleReply` (`headline: str`, `summary: str`, `markdown: str`, `total: str | None`) and route `parse_reply("single", ...)` to it; no provenance check
- [ ] T021 [US2] In `app/live/source.py` add `single(subtask)`: run `prepare_documents` first (reuse the Intake step's tool emits), build the bundle for seat `single`, stream progress and tool calls, commit the markdown to `drafts/single-v1.md` through `commit_draft`, and yield `task.completed` with result `{headline, summary, total, output_path}` and provenance from the tools used
- [ ] T022 [US2] In `app/orchestrator/orchestrator.py` add `mode: Literal["team", "single"] = "team"` to the constructor, record it in `run.started` and the recorder meta, and add `run_single()` per research D4 (intake, dispatch task `single`, work, the source's `single()`, assemble, handoff, `_terminate("single_complete", ...)`), dispatched from `run()` when mode is single; reasons for each step added to `DEFAULT_REASONS`; `_headline` already returns the Single-model sentence
- [ ] T023 [P] [US2] Create `app/agents/stubs/single_run.py`: a `StubScenario`-compatible source for any dataset id (fixture copy: one progress line, three tool calls, one completion with a short markdown output and a total) and register a `single_scenario_for(dataset_id)` in `app/agents/stubs/__init__.py`
- [ ] T024 [US2] In `app/runs/registry.py` extend `start_run(dataset_id, mode, model_key)` and `build_orchestrator(mode, model_key)`: for single mode build a one-seat roster from `roster.py`, the seat model from the chosen key (default the Orchestrator's effective key), the live source or the stub scenario; `is_live` covers both modes
- [ ] T025 [US2] In `app/main.py` extend `RunRequest` with `mode: Literal["team", "single"] = "team"` and `model: str | None = None`, pass them to `start_run`, return `mode`, and report `mode` on `GET /api/runs/{run_id}` from the orchestrator
- [ ] T026 [P] [US2] Create `app/runs/comparison.py` with `comparison(runs_dir, dataset_id) -> dict` per data-model.md: newest terminated recording per mode by `started_at`, `est_cost` and `elapsed_ms` from the last event's summary, `model_label` and `output_path` and `summary` from the Single-model `task.completed`
- [ ] T027 [US2] In `app/main.py` add `GET /api/datasets/{dataset_id}/comparison` (404 unknown dataset) serving `comparison()`
- [ ] T028 [P] [US2] In `app/web/pages/demo.html` enable the Single model segment (remove `is-unbuilt` and disabled), add the model `select` with id `single-model-select` and a `menu` shown only in Single mode, and give the compare body an inner container `compare-content`
- [ ] T029 [US2] In `app/web/static/js/demo.js` add `ui.runMode`, `ui.singleModel`, the mode switch handlers, the model menu built from `/api/seats` models (available only), `startRun` sending `mode` and `model`, and `loadComparison()` called on load, on dataset change, and after `run.terminated`, storing the result on `ctx.comparison`
- [ ] T030 [US2] In `app/web/static/js/render.js` add `renderComparison(ctx, ui)`: compare summary "<cost> · <m:ss>" or "no run yet", the body with the model label line, the output text loaded through the run files route, the line "No sources tagged, no review", and the comparison line "Team $X in m:ss · Single model $Y in m:ss, no review, no sources" or the empty text; call it from `renderAll`
- [ ] T031 [P] [US2] Append rules to `app/web/static/css/app.css` for `.compare-model` (13 px mono grey), `.compare-text` (max-height 120 px, overflow auto), `.compare-note`, and the composer model menu
- [ ] T032 [US2] Integration test `tests/integration/s5/test_single_run.py`: scripted single seat; assert mode single on `run.started`, the four `stage.changed` targets in order with direction forward, one `task.dispatched` and one `task.completed` with `output_path`, exit `single_complete`, the recording replays through `ReplaySession`, `metrics.json` carries seat `single`, and a Stop mid-run ends with `stopped`
- [ ] T033 [P] [US2] Unit test `tests/unit/s5/test_comparison.py` on two synthetic run folders: newest per mode chosen, figures read, missing mode gives null
- [ ] T034 [P] [US2] API test additions in `tests/integration/s5/test_seats_api.py`: `POST /api/runs` with mode single on a stub dataset returns 201 with mode single; the comparison route lists it after termination
- [ ] T035 [US2] Register the stub single scenario in `tests/unit/test_stubs_emit_only_agent_events.py` expectations only if `SCENARIOS` changes; otherwise add a test that the single stub emits agent message types only

**Checkpoint**: US2 tests green; a Single-model stub run from the Demo page shows Plan and Review bypassed and the Compare strip filled.

---

## Phase 5: User Story 3 - Meters complete (Priority: P2)

**Goal**: Latency in the detail row and the comparison line from recordings; the ceiling bar as built.

**Independent Test**: reduce a recorded run and compare the detail row with sums over `meter.update`.

- [ ] T036 [P] [US3] In `app/web/static/js/reducer.js` accumulate `latencyMs` per agent from `meter.update.latency_ms` (new field on the meter object)
- [ ] T037 [US3] In `app/web/static/js/render.js` add "Latency" after "Wall time" in the detail row stats and widen `.meter-detail` columns by one in `app/web/static/css/app.css` (appended override)
- [ ] T038 [P] [US3] Browser test addition in `tests/visual/test_e2e_ui.py`: open the Estimator meter on a golden replay and assert six stat labels including Latency

---

## Phase 6: User Story 4 - Ask an agent why (Priority: P2)

**Goal**: Read-only chat from a seat's recorded prompt bundle, out of band, cleared on close, never touching the run.

**Independent Test**: `tests/integration/s5/test_chat.py` with the byte-identical folder digest.

- [ ] T039 [P] [US4] Create `app/live/chat.py`: `find_bundle(registry, run_id, agent_id) -> PromptBundle | None` (live or replayed run bundles in memory, else `runs/<id>/prompts/*.json` newest for that seat by prompt_ref order), `chat_allowed(orchestrator | None, recording_exists) -> bool` (paused or terminated or recording), and `async chat(seat_model, bundle, messages) -> ChatReply(text, model, tokens_in, tokens_out, est_cost)` using a fresh Strands `Agent` with no tools, system prompt = bundle system + "\n\nContext of your last call:\n" + context slice + a read-only line; usage read from the result metrics; one attempt, errors mapped to a one-line reason
- [ ] T040 [US4] In `app/main.py` add `POST /api/chat` per the contract (404, 409, 502 cases) building the seat model from the registry's effective configuration for that seat (or the Single-model actor's recorded model when agent id is `single`)
- [ ] T041 [P] [US4] Create `app/web/static/js/chat.js`: open on a click of an agent card (`[data-part="agent-card"][data-agent]`) when `view.paused`, `view.terminated`, or replay mode; render the panel from the export's chat markup (header card, read-only note, message list, input with placeholder "Ask <name> about this run", footer with tokens and cost); POST `/api/chat` with the history; close button clears history and hides the panel; refuse with an inline note otherwise
- [ ] T042 [US4] In `app/web/pages/demo.html` replace the empty `chat-panel` aside with the panel skeleton (header, note, `chat-messages`, input row, footer) and load `chat.js`; in `app/web/static/js/render.js` add `data-agent` to `agentCard` and a `renderChat(ui)` that toggles the panel; append `.chat-*` rules to `app/web/static/css/app.css`
- [ ] T043 [US4] Integration test `tests/integration/s5/test_chat.py`: run the live harness to termination, digest every file under the run folder, chat with the Estimator through the API with a scripted reply, assert the reply text, tokens, and cost, assert the digest is identical and the event list unchanged, assert 409 while the run is live and unpaused, 404 for a seat without a bundle, and that `metrics.json` is unchanged
- [ ] T044 [P] [US4] Unit test `tests/unit/s5/test_chat_bundle.py`: `find_bundle` picks the newest bundle for a seat from a prompts folder and returns None for an unknown seat
- [ ] T045 [US4] Visual: add state `demo-terminated-chat` to `tests/visual/capture_app.py` (golden terminated prefix, click Elena's card, seed two messages through a `window.__s1chat.seed` hook used only by the capture) and to the parametrised list; masks with reasons for the seeded text if it differs from the export sample

**Checkpoint**: US4 tests green; the chat capture matches the export.

---

## Phase 7: Polish and records

- [ ] T046 Run `uv run python scripts/check.py` and `uv run pytest -m visual`; fix anything red
- [ ] T047 [P] Record one live Team run and one live Single-model run on Clean run from the Demo page under `COST_CEILING=1.00`; note run ids, spend, exits
- [ ] T048 [P] Add the S5 status entry with run ids and spend to `docs/roadmap.md` (own section only) and S5 decisions to `docs/design-deviations.md` (Settings labels fixture, chat panel, comparison line, model menu in the composer)
- [ ] T049 [P] Refresh `docs/model-performance.md` with `uv run python scripts/model_report.py --write`
- [ ] T050 Commit by name on `006-seats-single-chat` and push `006` only

---

## Dependencies and execution order

- Phase 1 and 2 before any story.
- US1 (Phase 3) first: it proves the registry and the roster propagation that US2 and US4 reuse.
- US2 (Phase 4) after T007 and T008 (roster and source hooks) and T004 (effective config).
- US3 (Phase 5) independent of US2 except the comparison line, which T030 renders; T036 to T038 can run any time after Phase 2.
- US4 (Phase 6) after T009 (registry seat models) and T022 (mode on the orchestrator, so chat can name the single actor's model).
- Phase 7 last.

## Parallel opportunities

- Phase 2: T003 and T006 in parallel with T004 once the function names are fixed.
- US1: T008, T010, T011, T013, T015 in parallel after T007.
- US2: T017, T018, T019, T020, T023, T026, T028, T031, T033 in parallel; T021, T022, T024, T025 sequential; T029 and T030 after T027.
- US4: T039, T041, T044 in parallel; T040 after T039; T042 after T041.

## Implementation strategy

MVP is US1: a live Settings page and `model.changed` reaching every card. Deliver US2 next, since the Compare strip is the roadmap outcome the prospect sees. US3 is small and can ride with US2. US4 last, because it depends on recorded bundles from the other two. Every phase ends on green gates.
