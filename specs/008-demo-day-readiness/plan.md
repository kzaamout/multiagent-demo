# Implementation Plan: Demo-day readiness (S7)

**Branch**: `008-demo-day-readiness` | **Date**: 2026-09-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/008-demo-day-readiness/spec.md`

## Summary

Add a pre-flight package that runs eight classified checks, stores the result as `runs/preflight.json`, and serves it to the Pre-flight page and to every header dot through the page helper and `/api/meta`. Add a session-cookie login from `.env` as one HTTP middleware with an allow-list of public routes taken from the S6 contract. Add `RUN_MODE` so Cloud mode greys local models in the registry, which Settings, the composer, and the live-run guard already read. Ship the Cloudflare Tunnel as two `.env` keys, one start script per platform, a README section, and a dependency record entry. Verify the build stamp with a test. Keep every edit to shared files additive so S6 rebases cleanly. The leave-behind command waits for S6.

## Verified versions and names (2026-09-17)

| Item | Verified | Source |
|---|---|---|
| cloudflared | 2026.9.1, released 2026-09-11; winget package `Cloudflare.cloudflared` at the same version; `cloudflared tunnel run --token <token>` or the `TUNNEL_TOKEN` environment variable | GitHub releases page, winget-pkgs manifests, Cloudflare run-parameters page |
| Export pre-flight states | `result` switch with `pending`, `one-fail`, `all-pass`; references `preflight-pending.png`, `preflight-all-pass.png`, `preflight-one-fail.png` already captured; dots `#003c33`, `#b30000`, `#d9d9dd`; detail colours `#212121`, `#b30000`, `#75758a`; glyphs ✓ ✕ ○; confirmation "All checks pass" over "Laptop mode · N of M · <stamp>" | `design/Preflight.html` decoded, `scripts/capture_export.py` |
| Header dot | `.pf-dot[data-status]` with pending, pass, warn, fail already styled in S1 | `app/web/static/css/app.css` |
| Compile pipeline | `compile_draft(run_folder, version, markdown, brand)` writes `artifacts/v<N>/` with PDF, page PNGs, `tool_versions`, `elapsed_ms`, `page_count` | `app/compile/pipeline.py` |
| Public routes after S7 | `/introduction`, `/introduction.pdf`, `/public/run/{id}/...`, `/static/...`, `/demo?public=1&run=<pinned>`; pinned id in `Settings.public_run_id` from `PUBLIC_RUN_ID` | `specs/007-introduction-replay/contracts/introduction.md`, research R7 |

One dependency is added (cloudflared, an external binary, not a Python package). Details in [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.13; vanilla JavaScript in the static pages; PowerShell and sh for the tunnel scripts

**Primary Dependencies**: FastAPI (one `http` middleware), Strands Agents (one fresh Agent with no tools per provider probe), httpx (tunnel and Ollama checks), boto3 (already present), the S4 compile pipeline; cloudflared as an external binary

**Storage**: `runs/preflight.json` (the stored result), `runs/preflight/artifacts/v1/` (the test compile), sessions in process memory, `.env` for credentials, mode, and tunnel values

**Testing**: pytest with injected check functions and a scripted seat model factory; httpx ASGI client for the login guard and the API; Playwright visual comparison for `login`, `preflight-pending`, `preflight-all-pass`, `preflight-one-fail`; one live pre-flight on the reference laptop

**Target Platform**: presenter laptop, Windows 11, Chrome, projector at 1920 by 1080; a small cloud host in Cloud mode

**Project Type**: web application (FastAPI server with static pages)

**Performance Goals**: a full pre-flight under 60 s on the laptop (each check has its own timeout: 30 s per provider probe, 10 s tunnel, 60 s compile); a page load reads the stored result in under a millisecond; the login redirect adds no measurable latency

**Constraints**: schema 1.1.0 untouched (pre-flight is not an event); the page renders the stored result, never guesses; credentials only in `.env` and never in a detail line; no em dashes; shared files touched additively (S6 in parallel); check ids, field names, `.env` names, and routes stable once shipped (rule 13)

**Scale/Scope**: one new package with eight checks, one auth module and middleware, four new routes, one page script, two placeholders in three page headers, two `.env` keys for the tunnel and three for login and mode, two scripts, three visual states added to the comparison

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | S7 compliance | Status |
|---|---|---|
| I Demo, not product | One shared login, no accounts; pre-flight reports, never repairs; the tunnel is a script and two keys | Pass |
| II Events only | Pre-flight is not a run and emits no event; the page renders a stored result, the dot is substituted server-side from the same file, no timer or inference | Pass |
| III One owner of state | The Orchestrator is untouched; the pre-flight runner owns only its own file | Pass |
| IV One door | Nothing here talks to the human inside a run | Pass |
| V Roles are real | Provider rows name the seat's real model; Cloud mode greys by mode, not by a label | Pass |
| VI Design for the failure | Each check has a timeout and a one-line failure; essential versus non-essential decides the dot | Pass |
| VIII Reliability | The pre-flight page verifies every dependency, as VIII requires | Pass |
| IX Writing rules | New copy lint-checked; row names are the export's | Pass |
| X, XI Controlled sources | `.env` holds mode, credentials, and tunnel values; nothing is written back | Pass |
| XII Vertical slices | Schema unchanged; adds a package, routes, and a middleware | Pass |
| XIII Acceptance recorded | Scripted tests per story, three visual states, one live pre-flight recorded in the roadmap | Pass |
| XV Dependencies | cloudflared recorded with a verified version and the cost of doing without | Pass |
| XVI Quality gates | Existing gates plus `tests/unit/s7/` and `tests/integration/s7/` | Pass |
| XVII Credentials | Login pair, token, and keys live in `.env`; the page and the result carry presence and class names only; a marker test proves it | Pass |
| XVIII Design wired, not redesigned | Pre-flight rows, confirmation, and the login form follow the export; the login error line and the not-applicable row are additions in the export's own meta text style (deviations recorded) | Pass |
| XIX Approval | Ten owner decisions of 2026-09-17 recorded in the spec | Pass |
| Non-goals | Per-user accounts: no. Credentials from the UI: the sign-in form carries the shared pair only and stores nothing. AgentCore: tunnel and laptop only | Pass |

Re-check after Phase 1 design: no new violation. The login guard's allow-list is read from the S6 contract, so the public page never needs a session.

## Project Structure

### Documentation (this feature)

```text
specs/008-demo-day-readiness/
  plan.md
  research.md
  data-model.md
  quickstart.md
  contracts/http-api-s7.md
  checklists/requirements.md
  tasks.md
```

### Source Code (repository root)

```text
app/
  preflight/__init__.py        exports
  preflight/checks.py          new: CheckContext, the eight checks, detail formatting
  preflight/runner.py          new: CHECKS order, run_preflight, load/save result, header_state
  preflight/fixture.md         new: the markdown the Typst check compiles
  auth.py                      new: Login pair from settings, SessionStore, is_public(path, query, settings), the middleware factory
  config.py                    new fields: run_mode, demo_username, demo_password, tunnel_hostname
  runs/registry.py             cloud mode: ollama availability forced off with the mode reason; model_options note
  main.py                      middleware registration; routes GET/POST /login, GET /api/preflight, POST /api/preflight/run; page() substitutes the dot placeholders; /api/meta preflight and run_mode
  web/pages/preflight.html     rows rendered by preflight.js; placeholders in the header
  web/pages/login.html         form posts to /login; error line; placeholders none (no header)
  web/pages/demo.html          header dot placeholders only
  web/pages/settings.html      header dot placeholders only
  web/static/js/preflight.js   new
  web/static/css/app.css       appended rules only (row states, confirmation, login error line, running button)
scripts/
  tunnel.ps1, tunnel.sh        new: start cloudflared with the token from .env
.env.example                   DEMO_USERNAME, DEMO_PASSWORD, RUN_MODE, TUNNEL_HOSTNAME, CLOUDFLARE_TUNNEL_TOKEN
docs/dependencies.md           cloudflared entry
docs/design-deviations.md      S7 entries
README.md                      login, mode, tunnel, pre-flight sections
tests/
  unit/s7/                     runner classification and storage, header state, auth rules, mode greying, env completeness, detail lines never carry a marker
  integration/s7/              login guard and public list, preflight routes with injected checks, build stamp, meta fields
  fixtures/preflight-all-pass.json, preflight-one-fail.json   stored results with the export's detail texts for the comparison
  visual/capture_app.py        states preflight-all-pass and preflight-one-fail with a prepare hook; masks for the new states
```

**Structure Decision**: single web application as before. New behaviour lands in new modules (`app/preflight/`, `app/auth.py`, `preflight.js`) and in new routes, one middleware, and new settings fields in the shared files, so the S6 branch's Introduction routes, public routes, and `public_run_id` field do not overlap.

## Delivery order

1. Settings fields and `.env.example`; auth module, middleware, login routes, login page wired; guard tests (US2).
2. Pre-flight package: results, storage, header state; the eight checks with injectable probes; unit tests (US1 engine).
3. Routes, page script, header placeholders on the three pages, `/api/meta`; visual states and fixtures; integration tests (US1 complete).
4. Run mode in the registry and the checks; tests (US3).
5. Tunnel scripts, README, dependency record; tunnel check tests (US4). Build stamp test (US5).
6. Deviations, roadmap status, gates, visual suite, one live pre-flight on the laptop, push `008`, message the peer.

## Complexity Tracking

No constitution violation to justify.
