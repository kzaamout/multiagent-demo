---

description: "Task list for slice S7: demo-day readiness"
---

# Tasks: Demo-day readiness (S7)

**Input**: Design documents from `specs/008-demo-day-readiness/`

**Prerequisites**: plan.md, spec.md, research.md (D1 to D11), data-model.md, contracts/http-api-s7.md, quickstart.md

**Tests**: Included. The spec's success criteria name scripted tests per story, three visual states, and a marker test for credentials (constitution XIII, XVI, XVII).

**Organization**: One phase per user story in priority order. Shared files (`app/main.py`, `app/config.py`, `app/runs/registry.py`, `app.css`, the Demo and Settings headers, `capture_app.py`, `masks.py`) receive new routes, one middleware, new fields, placeholders, and appended rules only, so the S6 branch rebases cleanly.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1 to US5)
- Paths are relative to the worktree root `C:\Users\Khobaib\OneDrive\Desktop\code\multiagent-demo-s7`

## Path Conventions

Single web application: `app/` (engine, API, static pages), `scripts/` (presenter tools), `tests/` (unit, integration, visual, fixtures).

---

## Phase 1: Setup

**Purpose**: Settings fields, `.env.example`, and test folders every story reads.

- [x] T001 In `app/config.py` add `run_mode: str = "laptop"`, `demo_username: str = ""`, `demo_password: str = ""`, `tunnel_hostname: str = ""` to `Settings`, read `RUN_MODE` (accept `laptop` or `cloud`, else `ValueError("RUN_MODE must be laptop or cloud")`), `DEMO_USERNAME`, `DEMO_PASSWORD`, `TUNNEL_HOSTNAME` in `load_settings`
- [x] T002 [P] In `.env.example` add commented, documented lines for `DEMO_USERNAME`, `DEMO_PASSWORD`, `RUN_MODE`, `TUNNEL_HOSTNAME`, `CLOUDFLARE_TUNNEL_TOKEN` with placeholders and one line each on what reads them
- [x] T003 [P] Create `tests/unit/s7/__init__.py` and `tests/integration/s7/__init__.py`

---

## Phase 2: User Story 2 - One shared login (Priority: P1)

**Goal**: The guard, the login routes, and the wired login page.

**Independent Test**: `tests/integration/s7/test_login_guard.py`.

- [x] T004 [US2] Create `app/auth.py`: `SessionStore` (create, has, in-memory set of tokens with creation times), `credentials_match(settings, username, password)` using `hmac.compare_digest` on both fields, `is_public(path, query, settings)` implementing research D6 (reads `getattr(settings, "public_run_id", None)`), `is_page(path)`, `COOKIE = "sterling_session"`, and `guard(settings, store)` returning an async middleware callable that redirects pages with 303 to `/login?next=<path>` and answers 401 JSON otherwise; the guard is inert when either credential is empty
- [x] T005 [US2] In `app/main.py` register the middleware from `app.auth`, add `POST /login` (form fields per contracts/http-api-s7.md: right pair sets the cookie HttpOnly SameSite=Lax Path=/ and redirects to a relative `next` or `/demo`; wrong pair redirects to `/login?error=1` keeping `next`; guard off redirects to `/demo`), and make `GET /login` substitute `{{LOGIN_ERROR}}` and `{{LOGIN_NEXT}}`
- [x] T006 [US2] In `app/web/pages/login.html` make the form `method="post" action="/login"`, the Sign in control a `<button type="submit" class="btn-signin">`, add a hidden `next` input `{{LOGIN_NEXT}}`, and an error line `<p class="login-error" data-part="login-error">{{LOGIN_ERROR}}</p>` that is empty when there is no error; append `.login-error` (meta text style, `#b30000`) to `app/web/static/css/app.css`
- [x] T007 [P] [US2] Tests in `tests/integration/s7/test_login_guard.py`: with credentials, `/demo`, `/settings`, `/preflight`, `/` redirect to `/login?next=...`; `/api/meta` and `POST /api/runs` answer 401; `/login`, `/static/css/app.css`, `/introduction`, `/introduction.pdf`, `/public/run/x/events`, and `/demo?public=1&run=<pinned>` (with a settings object carrying `public_run_id`) are not redirected or 401; wrong pair redirects to `/login?error=1` without a cookie; right pair sets the cookie and admits the three pages; `next` off-site lands on `/demo`; without credentials nothing redirects
- [x] T008 [P] [US2] Unit tests in `tests/unit/s7/test_auth.py`: `is_public` table, `credentials_match` rejects a wrong length and a wrong pair, the store forgets nothing until a new instance, the login page with `?error=1` carries the line and never the submitted values

**Checkpoint**: the login screenshot still matches; the guard test is green.

---

## Phase 3: User Story 1 - Pre-flight (Priority: P1)

**Goal**: The package, the routes, the page, and the header dot on every protected page.

**Independent Test**: `tests/unit/s7/test_preflight_runner.py`, `tests/unit/s7/test_preflight_checks.py`, `tests/integration/s7/test_preflight_api.py`, plus the three visual states.

- [x] T009 [US1] Create `app/preflight/runner.py`: dataclasses `CheckResult(id, name, status, detail, essential, elapsed_ms)` and `PreflightResult(schema=1, run_mode, ran_at, status, passed, applicable, checks)` with `to_json`/`from_json`; `overall(checks)` per research D2; `RESULT_FILE = "preflight.json"`, `load_result(runs_dir) -> PreflightResult | None` (None on missing, unreadable, or schema not 1), `save_result(runs_dir, result)`; `HeaderState(status, glyph, title)` and `header_state(result | None)` per data-model.md; `format_stamp(ran_at)` as "<d> <Mon> <yyyy>, <hh:mm>" local time; `pending_checks(ctx)` listing every check in order with status `pending`
- [x] T010 [US1] Create `app/preflight/checks.py`: `CheckContext(settings, config, availability, seat_model_factory, probe, fetch, disk_usage, compile)` with production defaults; `Check(id, name, essential, timeout_s, run)`; `checks_for(ctx) -> list[Check]` in the order of data-model.md (provider rows per research D3, then ollama, typst, png, tunnel, disk, env); each check returns a `CheckResult` and never raises; details exactly as research D3, D4, D8, D9 and data-model.md; provider failures carry the exception class name or "no answer within 30 s", never message text
- [x] T011 [US1] Create `app/preflight/fixture.md` (a short proposal: title, executive summary paragraph, a three-row schedule table, no provenance tags, no em dash) and `app/preflight/__init__.py` exporting `run_preflight`, `load_result`, `header_state`, `pending_checks`, `CheckContext`
- [x] T012 [US1] In `app/preflight/runner.py` add `async def run_preflight(ctx) -> PreflightResult`: runs the checks in order with `asyncio.wait_for` per `timeout_s` (a timeout becomes a `fail` with "no answer within <n> s"), the PNG row reading the compile row's outcome, saves and returns the result
- [x] T013 [P] [US1] Unit tests in `tests/unit/s7/test_preflight_runner.py`: overall pass/warn/fail/pending, `load_result` on missing, corrupt, and wrong-schema files, `header_state` for the four states with the export's glyphs and titles, `format_stamp`, `run_preflight` with scripted checks stores the file, a check that raises becomes a fail with its class name, a check that hangs becomes a timeout fail
- [x] T014 [P] [US1] Unit tests in `tests/unit/s7/test_preflight_checks.py`: provider rows chosen from seats and keys with essential set accordingly, provider detail from a scripted probe, ollama pass/fail from a scripted tags response, typst and png rows from a scripted `Compiled` and from a `CompileError`, disk pass and fail around 5 GB and unreadable, env completeness listing the missing names per mode, and a marker planted in the environment (`GEMINI_API_KEY`, `DEMO_PASSWORD`) never appearing in any detail line
- [x] T015 [US1] In `app/main.py` add `GET /api/preflight` and `POST /api/preflight/run` per contracts/http-api-s7.md (a `running` flag and an `asyncio.Lock` on `app.state`; 409 while running; the context built from `cfg`, `registry.effective_config()`, `registry.availability`, and `strands_model_for`, with `create_app` gaining a `preflight_context: Callable[[], CheckContext] | None` override for tests); make `page()` substitute `{{PREFLIGHT_STATUS}}`, `{{PREFLIGHT_GLYPH}}`, `{{PREFLIGHT_TITLE}}` from `header_state(load_result(cfg.runs_dir))`; `/api/meta` reports `preflight` from the same and adds `run_mode`
- [x] T016 [US1] Replace the static dot in the headers of `app/web/pages/demo.html`, `app/web/pages/settings.html`, and `app/web/pages/preflight.html` with `data-status="{{PREFLIGHT_STATUS}}" title="{{PREFLIGHT_TITLE}}">{{PREFLIGHT_GLYPH}}`; in `preflight.html` enable the button (`id="run-preflight"`), give the rows container `id="pf-rows"`, add the confirmation block (`id="pf-confirmation"`, hidden by default, the export's markup: 56 px circle with ✓, "All checks pass", the mode line) and load `/static/js/preflight.js`; append `.pf-confirmation`, `.check-dot[data-status]`, `.check-detail[data-status]`, `.btn-pf[disabled]` rules to `app.css`
- [x] T017 [US1] Create `app/web/static/js/preflight.js`: on load `GET /api/preflight` and render rows (dot colour, glyph, detail, detail colour per status: pass `#003c33`/`#212121`, fail `#b30000`/`#b30000`, pending and skip `#d9d9dd`/`#75758a`), the confirmation only when `status === "pass"` with "<Mode> mode · <passed> of <applicable> · <stamp>", and the page's own header dot; the button posts `/api/preflight/run`, reads "Running" while it waits, re-renders from the reply, and shows a 409 or network error as one line under the button
- [x] T018 [P] [US1] Fixtures `tests/fixtures/preflight-all-pass.json` and `tests/fixtures/preflight-one-fail.json`: schema 1, `run_mode` laptop, `ran_at` 2026-09-14T08:12:00 local, eight checks with the export's row names and detail texts (Bedrock and Gemini as the two provider rows), the one-fail file with the tunnel row failed and detail "Tunnel not connected" (status warn)
- [x] T019 [US1] In `tests/visual/capture_app.py` add `prepare: str | None` to `AppState`, states `preflight-all-pass` and `preflight-one-fail`, and a `prepare` mapping parameter on `capture()` called before each state's navigation and a `cleanup` after; in `tests/visual/test_screenshots.py` bind the callbacks to the module's runs folder (copy the fixture to `preflight.json`, remove it after) and add the two names to the parametrize list; in `tests/visual/masks.py` add the two states with the header mask and a mask over the confirmation's stamp text if the local time zone changes its width
- [x] T020 [P] [US1] Integration tests in `tests/integration/s7/test_preflight_api.py`: with an injected context of scripted checks, `GET /api/preflight` pending shape, `POST /api/preflight/run` stores the file and returns the result, a second POST during a slow run answers 409, the header dot on `/demo`, `/settings`, `/preflight` reads pending, pass, warn, fail from the stored file, `/api/meta.preflight` agrees, and a marker planted in `.env` (`DEMO_PASSWORD`, `GEMINI_API_KEY`) appears in none of `/api/preflight`, `/api/meta`, `/api/seats`, `/api/providers`, or the stored file

**Checkpoint**: three pre-flight states match the export; the pending dot still renders on a fresh checkout.

---

## Phase 4: User Story 3 - Laptop and Cloud mode (Priority: P2)

**Goal**: Cloud mode greys local models everywhere the registry is read.

**Independent Test**: `tests/unit/s7/test_run_mode.py`.

- [x] T021 [US3] In `app/runs/registry.py` make `availability` return `Availability("ollama", False, "not offered in Cloud mode")` for `ollama` when `settings.run_mode == "cloud"` without probing, and make `model_options` use that reason as `reason` and `note` for Ollama entries in Cloud mode
- [x] T022 [US3] In `app/preflight/checks.py` make the Ollama row `skip` with "Local models are not used in Cloud mode" in Cloud mode unless a seat is on Ollama, then `fail` with "<seats> still on local models; move them in Settings"
- [x] T023 [P] [US3] Tests in `tests/unit/s7/test_run_mode.py`: `load_settings` accepts laptop and cloud and refuses another value with the one-line message; in Cloud mode `seat_table()` greys every Ollama option with the note, `provider_report()` lists the reason, `unavailable_seats` names a local seat, and the Ollama check is skip or fail as above; in Laptop mode the injected availability is served unchanged

---

## Phase 5: User Story 4 - Tunnel (Priority: P2)

**Goal**: The tunnel starts from `.env`, the check reads it, the record names the dependency.

**Independent Test**: `tests/unit/s7/test_tunnel_check.py`.

- [x] T024 [P] [US4] Create `scripts/tunnel.ps1` and `scripts/tunnel.sh`: read `CLOUDFLARE_TUNNEL_TOKEN` from `.env` at the repository root without printing it, exit 2 with "CLOUDFLARE_TUNNEL_TOKEN is empty in .env" or "cloudflared is not on the path" as applicable, else run `cloudflared tunnel run --token <token>` in the foreground
- [x] T025 [P] [US4] Tests in `tests/unit/s7/test_tunnel_check.py`: with an injected `fetch`, pass "<hostname> answered in <n> ms" on 200, fail "Tunnel not connected" on a transport error, fail "HTTP <status> from the tunnel" otherwise, skip "No tunnel hostname in .env" with an empty hostname; the check is non-essential
- [x] T026 [P] [US4] In `docs/dependencies.md` add the cloudflared row (2026.9.1 verified 2026-09-17, winget `Cloudflare.cloudflared`, the problem it solves, the cost of doing without) and, under not adopted, a locally managed tunnel config and quick tunnels with the reasons in research D8
- [x] T027 [P] [US4] In `README.md` add sections: the shared login (`DEMO_USERNAME`, `DEMO_PASSWORD`), run modes (`RUN_MODE`), the tunnel (create it in the Cloudflare dashboard, route the hostname to `http://localhost:8000`, paste the token, run the script), and the pre-flight (what each row checks and what green, orange, and red mean)

---

## Phase 6: User Story 5 - Build stamp verified (Priority: P3)

- [x] T028 [P] [US5] Test in `tests/integration/s7/test_build_stamp.py`: read `git rev-parse --short HEAD` and `git log -1 --format=%cs` from the repository root and assert every page header (`/demo`, `/settings`, `/preflight`) carries "build <hash> · <date>" and `/api/meta.build` matches; skip with a reason when git is not available

---

## Phase 7: Polish and records

- [x] T029 In `docs/design-deviations.md` add a "Slice S7 (2026-09-17)" section: the login error line and the hidden `next` field, the not-applicable (grey) row with its own line, the confirmation's mode word from `RUN_MODE`, the header dot substituted server-side, the provider rows chosen from the seats rather than the export's fixed pair, the Introduction link in the header still inert until S6 merges
- [x] T030 In `docs/roadmap.md` S7 add the status entry: what was built, the ten defaults, the live pre-flight on the reference laptop with its rows, the deferred leave-behind and avatars, and the open tunnel values
- [x] T031 Run `uv run python scripts/check.py` (capture the exit code separately) and `uv run pytest -m visual`; fix until green
- [x] T032 On the reference laptop with `.env` complete, run the pre-flight live from the page, record the row details and time in the roadmap status, and note any check that could not be exercised (the tunnel until the owner supplies its values)
- [x] T033 Check `git status` shows only S7 files, stage them by name, commit, push only `008-demo-day-readiness`, and message `multiagent-demo-aa` with the public route allow-list, the header placeholders S6's Introduction page may adopt, and the `public_run_id` read

---

## Dependencies

- Phase 1 before everything.
- US2 (Phase 2) before US1's integration tests, because the API tests build the app with credentials off and the guard must exist to be off.
- US1 engine (T009 to T012) before its routes and page (T015 to T017), before its tests (T013, T014, T020 can be written in parallel with the engine and run after).
- US3 depends on T010 (the Ollama check) and T021.
- US4 and US5 are independent of each other and of US3.
- Phase 7 last.

## Parallel opportunities

- T002, T003 with T001.
- T007, T008 while T004 to T006 are written.
- T013, T014, T018, T020 while T009 to T017 are written.
- T024 to T028 together.

## Implementation strategy

MVP is US2 plus US1: a laptop that signs in and goes green. US3, US4, US5 follow in one pass. The leave-behind command is not in this task list; it is scheduled after S6 merges.
