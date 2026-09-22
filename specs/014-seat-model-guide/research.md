# Research: Seat model guide on Settings

Measured on 2026-09-21 against the 389 run folders under the main checkout's `runs/`, from this worktree with `RUNS_DIR` pointing there.

## D1. Instruction accuracy is the report's first-time figure, from `metrics.json`

- **Decision**: instruction accuracy for a seat and a model is `accepted_first_time / replies`, summed over the seat rows of every counted run's metrics. One function, `instruction_accuracy(first_time, replies)` in `app/runs/guide.py`, computes it, and the report's `Group.first_time_rate` calls it, so the figure is worked out one way (FR-014).
- **Rationale**: `replies` counts every reply cycle the seat was asked for, including the refused final attempt of a run that stopped (`app/runs/metrics.py`), so `accepted_first_time / replies` is exactly "first attempts accepted over first attempts" (decision 2b). The report's "First time" column is already this division; its written definition ("share of accepted replies that needed no correction") understates the denominator and is corrected. For the 30 runs recorded before the attempt log existed, `metrics.json` already reconstructs the counts from the rejected reply files, which the attempt log alone cannot.
- **Alternatives considered**: counting `attempt == 1` lines in `seat-calls.jsonl` directly. Rejected: it misses the 30 older runs and is a second calculation of the same number, which rule 15 forbids.

## D2. The runs counted are the report's runs, less the live one

- **Decision**: `metrics_of(folder)` moves from `scripts/model_report.py` to `app/runs/guide.py` unchanged in behaviour: a folder with an event log counts; its `metrics.json` is used when it has the current fields, and otherwise its metrics are worked out from the event log; folders whose name starts with `_` are skipped. The report and the page both call it. The page leaves out one folder only: the run this app is running now (`Registry.live.run_id` while `is_live()`).
- **Rationale**: 9 of 389 folders have no `metrics.json` and an event log that never reaches `run.terminated` (runs cut off by closing the app, and any sweep run still going). The report counts them today, with the replies they made, and its price table even has an "unfinished" row. Excluding them from the page only would break SC-002; excluding them from the report too would drop evidence the owner already relies on and change the report beyond what this work was asked to do. The live run is left out so the figures hold still during a demo, which is what decision 8a ("cached until a run ends") was for.
- **Alternatives considered**: counting only folders with `metrics.json` or a terminated log, in both places. Rejected for the reasons above.

## D3. One record per seat and model label, across settings and instruction versions

- **Decision**: the guide sums seat rows by `(agent_id, model label)`, ignoring settings and instruction version (decision 3a). A seat row counts toward `runs` when it made a call or a reply, as the report's `collect` already rules. A record's model label is matched to a registry model by its `label`.
- **Rationale**: the menu offers registry models, and every model label recorded in runs today matches a registry label exactly (claude-sonnet-5 via Bedrock, qwen3.5 9b and 4b, gemma4 12b, llama3.1 8b, deepseek-r1 14b, all local). A label that matches no registry model cannot be chosen, so it is never a pick (FR-006).
- **Alternatives considered**: matching on provider and model id. Rejected: `metrics.json` seat rows carry the label and provider but not the model id.

## D4. Ranking by the Wilson lower bound

- **Decision**: among models of one kind with at least 5 runs on the seat, the pick has the highest Wilson score lower bound at 95% (z = 1.959963984540054) on `first_time` successes out of `replies` trials. Ties go to more replies, then to the model's position in `config/models.yaml`. The page and the report show the plain share, rounded to a whole percent by one function, `whole_percent(first_time, replies)`, that the report's column also uses, so both round alike.
- **Rationale**: decision 5c. On today's data the rule picks qwen3.5 9b at the Orchestrator (390 of 397, bound 0.964) over gemma4 12b (13 of 13, bound 0.772), which a plain share would reverse. A model with zero replies has no bound and cannot be a pick. The threshold of 5 runs reuses the report's `MIN_RUNS_FOR_BEST`, which moves to the guide module and is imported by the report.
- **Alternatives considered**: a Bayesian prior (Beta(1,1)) mean. Rejected: the owner chose the confidence range, and the Wilson bound needs no prior to explain.

## D5. `weights: open | proprietary` in the registry

- **Decision**: each model in `config/models.yaml` gains `weights: open` or `weights: proprietary`. `ModelSpec` gains `weights: str | None`; `ModelConfig.load` rejects any other value and leaves it `None` when absent. A model with `None` is never a pick, and the report names it as not classified. Values: the three Bedrock Claude models, both Gemini models and Grok are proprietary; qwen3.5 9b and 4b, gemma4 12b, llama3.1 8b, granite4.1 8b and deepseek-r1 14b are open.
- **Rationale**: decision 6a. "Open" means the weights are published and can be run locally, whatever other terms the licence sets; that is the distinction a prospect weighing a local deployment cares about. The field is set by hand, never derived from the provider, so an open model served from a cloud provider would stay open.
- **Alternatives considered**: deriving the kind from the provider (Ollama is open). Rejected by decision 6a.

## D6. Seat needs, in one place

- **Decision**: `needs_image_input(agent_id)` moves into `app/seats/definitions.py`, with the rule the report's "Seats and what they need" table already applies: the seat sees drawing pages or compiled page text beside its images (the Estimator, the Reviewer), or it is the Single-model seat. The report's table and the guide both call it. A model whose registry entry has `image_input: false` is never a pick for such a seat.
- **Rationale**: FR-006 and constitution V. Tool calling is not checked: the registry has no field for it, and the report's own probe of Ollama's capability list shows every pulled local model takes tools. If a model without tool calling is ever added, the registry gains the field then.
- **Alternatives considered**: adding a `tool_calls` field now. Rejected: it would be true for every model and tested against nothing.

## D7. A per-folder cache, checked on each request, with no timer

- **Decision**: the registry holds one `SeatGuide` object for its runs folder. On each request it lists the run folders and stats each one's `metrics.json` (or, when absent, its `events.jsonl`) for modification time and size. A folder whose signature is unchanged keeps its cached seat rows; only new or changed folders are read. When no signature changed since the last request, the aggregated records are returned as they are, without summing again.
- **Rationale**: FR-012, SC-004 and decision 8a. Measured: listing and statting 389 folders takes 0.025 s; reading and aggregating every run cold takes 0.36 s, and 0.17 s warm, so a first load stays well inside the 1 second target and a repeat load costs one directory scan. The check runs only when the page asks, so there is no timer and no watcher (constitution II and FR-012). A run that ends writes `metrics.json`, which changes its folder's signature, so the next load includes it. A run still going in another process changes its event log and is re-read on the next load, as the report would read it.
- **Alternatives considered**: a filesystem watcher (the `watchdog` package). Rejected under constitution XV: a new dependency and a background thread to save 25 milliseconds. Invalidating only when this app's run ends. Rejected: it misses runs finished by a sweep in another process.

## D8. The guide travels with `GET /api/seats`

- **Decision**: each row of `Registry.seat_table()` gains a `guide` object with `current`, `open` and `proprietary`, and the table gains a top-level `guide` object with the number of runs counted and the 5-run threshold. See `contracts/seats-guide.md`. Percentages come from the server, already rounded.
- **Rationale**: the Settings page already loads this table on open and again after every swap, so the button's figure follows a swap with no extra request (spec User Story 1, scenario 6). The Demo page also loads the table for its composer and ignores the new keys.
- **Alternatives considered**: a separate `GET /api/seats/guide`. Rejected: two requests per load and per swap, and a response that would carry every seat and model pair to let the page find the current model's figure, which is the leaderboard the constitution parks.

## D9. Layout inside the export's component family

- **Decision**: the seat row keeps its three columns and their widths. Under the model button and the dependency note, a guide block spans the second and third columns with two lines in 13 px meta grey (#75758a, the export's `.page-sub` and `.menu-note` colour): a kind label ("Top open model", "Top proprietary model") and its value ("qwen3.5 9b, local · 94% (212 of 226 replies)", or the reason no model is named). The model button shows the current model's figure after its name in the `.menu-note` style (12 px grey) that the open menu already uses beside each option; the button may grow to two lines for the longest labels rather than cut the model's name. A second `page-sub` line under the title defines instruction accuracy and gives the run count; a paragraph in the same meta style under the status line carries the foot note.
- **Rationale**: constitution XVIII allows an addition the spec requires when it matches the export's own component family, and forbids rearranging. Widening the 320 px select column would rearrange the row; wrapping the button for a long label keeps the name whole (constitution V). Measured against the export capture: a 27 character label at 15 px is about 195 px and "94% (29 of 31)" at 12 px about 81 px, which with padding and the chevron slightly exceeds the 292 px inside the button for the longest labels only.
- **Alternatives considered**: a fourth column; a line under the agent card. Both rearrange the export's row.

## D10. The screenshot comparison hides the additions

- **Decision**: the `settings` and `settings-dropdown` captures inject a style that hides the guide block, the button figure, the under-title guide line and the foot note, listed in `tests/visual/masks.py` beside the masks with the reason and "kept". A Playwright test in `tests/visual/test_e2e_ui.py` checks that the additions render, with the right text, on a seeded runs folder.
- **Rationale**: the additions change every row's height, so no rectangle mask can cover them; what remains comparable (header, title, cards, buttons, dependency notes, menu) is still compared against the export (constitution XIII).
- **Alternatives considered**: recapturing the reference with the additions. Rejected: the references are the export, which is never redesigned.

## D11. The report's names and new section

- **Decision**: in `scripts/model_report.py`, the display label "First time" becomes "Instruction accuracy" and "Accuracy" becomes "Behaviour accuracy" in every table, heading and sentence, with both definitions corrected; the CSV column names do not change. A new section, "Top models per seat", follows the column definitions and precedes "Best local model per seat": one row per Settings seat with the top open model, its instruction accuracy and runs, and the top proprietary model with the same, from `app/runs/guide.py`, followed by the registry models not classified as open or proprietary, or "none". The report computes the picks with no live run to exclude.
- **Rationale**: FR-013, FR-014, FR-015 and the clarification of 2026-09-21. The owner's ranking for the best local model keeps its substance; its sentence names the new labels.

## D12. Nothing touches a run

- **Decision**: no event type, payload, schema version, golden log, seat instruction or model call changes. The guide reads recorded files only.
- **Rationale**: FR-017 and decision 7a. The picks are configuration advice, like the model menu's availability, not run state, so principle II's "nothing renders that was not emitted" is not engaged: the Demo page's run rendering is untouched.
