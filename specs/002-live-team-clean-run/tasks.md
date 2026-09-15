# Tasks: Live team on the clean run (S2)

**Input**: `specs/002-live-team-clean-run/` spec, plan, research

**Tests**: included; they are the Part A evidence.

## Phase 1: Setup

- [x] T001 Add strands-agents[litellm,ollama]==1.55.1 and pypdfium2==5.13.0; set uv copy link mode for OneDrive in `pyproject.toml`
- [x] T002 Record S2 dependencies in `docs/dependencies.md`
- [x] T003 Ignore `knowledge/` in `.gitignore`
- [x] T004 Write `config/models.yaml`: providers, models with ids, labels, image input, temperature support, prices with source date; seat defaults marked pending owner confirmation

## Phase 2: Foundational

- [x] T005 Seat definitions and instruction loading in `app/seats/definitions.py` with tests
- [x] T006 Context slices with roster scoping in `app/live/context.py` with tests
- [x] T007 Reply shapes, validation, and payload conversion in `app/live/replies.py` with tests
- [x] T008 Rename tools to underscore names in `config/electrical-rfp/seats/*.md` and `app/seats/definitions.py`
- [x] T009 `AgentSource` protocol in `app/agents/source.py`; `StubAgentSource` wrapping S1 scenarios; Orchestrator consumes the protocol; all S1 tests and golden comparisons stay green
- [x] T010 Live clock behaviour in the Orchestrator: offsets from wall time, no fixture marks

## Phase 3: US5 Live agents on the unchanged spine (P1, Part A)

- [x] T011 [US5] Quantity calculator, price lookup with totals, markdown template and tag parsing, draft commit in `app/tools/` with tests
- [x] T012 [US5] `app/live/documents.py`: pypdfium2 text per page, legibility heuristic, page PNG rendering; tests on committed synthetic PDFs in `tests/fixtures/s2/`
- [x] T013 [US5] `app/live/strands_tools.py`: per-run tool closures for the seven tools with argument and result summaries
- [x] T014 [US5] `app/live/seat_call.py`: build a Strands Agent per call, `SequentialToolExecutor`, hooks for tool calls and per-call usage, progress lines from streamed text, reply validation with one retry, provider error handling
- [x] T015 [US5] `app/live/materials.py`: dataset inputs, knowledge file, config files, and run outputs as `Material` items with source event ids
- [x] T016 [US5] `app/live/source.py`: `LiveAgentSource` for intake, plan proposal with validation and fallback, work tasks, assemble, review, headline
- [x] T017 [US5] `tests/support/scripted_model.py`: scripted Strands model replaying per-seat turns including tool use
- [x] T018 [US5] `tests/integration/s2/test_live_path.py`: live source with the scripted model on the synthetic dataset; events validate; stage sequence and exit match the Clean run golden log; tool calls, progress, meters, prompt bundles present
- [x] T019 [US5] Invalid reply twice terminates as stopped with the seat named; provider exception terminates as stopped without credential text

## Phase 4: US3 Roles are real in real bundles (P1, Part A)

- [x] T020 [US3] Test on recorded bundles from the scripted live run: each seat's context slice holds exactly its scope; the Reviewer's holds no specialist output, tool result, or knowledge file; tools per seat match the roster

## Phase 5: US2 Ask once (P1, Part A mechanism)

- [x] T021 [US2] Persistent knowledge store with seeding and append in `app/orchestrator/knowledge_store.py` with tests
- [x] T022 [US2] Live mode reads the store at Intake and appends answers; test: two scripted runs, the second Intake context contains the answer and the engine refuses to re-ask an answered question id (it becomes an assumption with the stored answer)

## Phase 6: US4 Providers from .env (P2, Part A)

- [x] T023 [US4] `app/live/providers.py`: availability from boto3 credentials, `GEMINI_API_KEY`, `XAI_API_KEY`, Ollama tags; Strands model factory from `config/models.yaml`
- [x] T024 [US4] `GET /api/providers` (booleans and reasons only); `POST /api/runs` refuses live mode naming the seat when a provider is unavailable; the page shows the refusal
- [x] T025 [US4] Extend the leak test to the registry response, live bundles, and recordings

## Phase 7: US6 Draft text in the artifact panel (P3, Part A)

- [x] T026 [US6] Run file endpoint and draft text view with in-place refresh
- [x] T027 [US6] Browser test: a scripted live run shows v1 draft text in the panel

## Phase 8: Part B (waits for the owner's inputs)

- [ ] T028 Owner: curate `datasets/clean-run/` inputs, fixtures, and knowledge seed per `datasets/README.md`
- [ ] T029 Owner: credentials in `.env` for Bedrock and Gemini; Ollama with the chosen local model pulled
- [x] T030 Owner: confirm the four model questions in the plan (answered 2026-09-15)
- [ ] T031 Live Clean run from the Demo page; record it; replay compare against the golden stage sequence and exit
- [ ] T032 Second live run for the same client; no repeated clarification; `knowledge.appended` present in the first
- [ ] T033 Screenshot comparison and all S1 gates green; update `docs/roadmap.md` S2 status
