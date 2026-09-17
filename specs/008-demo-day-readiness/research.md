# Research: Demo-day readiness (S7)

Every unknown in the plan's Technical Context resolved, with the alternative rejected. Dated 2026-09-17.

## D1. Where the pre-flight result lives and how the dot reads it

- Decision: `run_preflight` writes `runs/preflight.json` (under `Settings.runs_dir`, so a worktree writes beside its recordings). The page helper in `main.py` loads the file on every page request and substitutes three placeholders in the header markup (`{{PREFLIGHT_STATUS}}`, `{{PREFLIGHT_GLYPH}}`, `{{PREFLIGHT_TITLE}}`) the way it substitutes the build stamp; `/api/meta` reports the same status. The Pre-flight page fetches `GET /api/preflight` for the rows.
- Rationale: owner decision 4; spec 2.4 says the stored result drives the indicator; a server-side substitution needs no script on Settings or Demo and survives a restart (constitution VIII); one file, one reader (rule 15).
- Alternatives: a script on every page polling the API (a timer the UI rule forbids); keeping the result in memory (lost on restart).

## D2. Check classification and the overall status

- Decision: each check carries `essential`. Status per check is `pass`, `fail`, or `skip` (not applicable in this mode or configuration). Overall: `fail` if any essential check failed, else `warn` if any check failed, else `pass`; `pending` when no result exists or the file cannot be read. Essential: every cloud provider a seat uses, Ollama when a seat uses it, Typst compile, PNG export, disk, `.env` completeness. Non-essential: the tunnel, a provider with a key present but no seat on it.
- Rationale: owner decision 6; spec 2.4's example (the tunnel unreachable in cloud mode is a warn).
- Alternatives: a fixed list of essential ids (would call Google essential when no seat uses it; rejected).

## D3. Provider rows

- Decision: one row per cloud provider in `config/models.yaml` that a seat uses or whose credentials are present, in the registry's provider order, named "<provider label> responds". The check builds the seat's Strands model through `strands_model_for(effective_config, seat)` for the first seat on that provider (or the provider's first model when only the key is present), and a fresh Strands Agent with no tools asks for the single word "ready" with a 30 s timeout. Detail: "<model label before ' via '> answered in <n> ms"; failure: "no answer within 30 s" or the exception's class name, never its message. Tests inject a scripted factory and a scripted probe; the conftest fixture that refuses real providers stays in force.
- Rationale: owner decision 5; constitution V (the row names the model the seat will really use) and XVII (no message text, since provider errors can echo a key).
- Alternatives: the setup script's metadata calls (never proves the model answers; rejected as the spec says "responds"); a fixed Bedrock and Gemini pair as in the export (untruthful when the Reviewer is on Gemma; rejected).

## D4. Typst and PNG rows from one compile

- Decision: the Typst check calls `compile_draft(runs_dir / "preflight", 1, fixture_markdown, Brand("Pre-flight", None, "#003c33"))`, which writes `runs/preflight/artifacts/v1/`. Detail: "typst <version>, <pages> pages in <s> s". The PNG check reads the same `Compiled`: "<n> PNGs written to runs/preflight/", failing with "no compile to export" when the compile failed and "export produced 0 files" when the page list is empty. The fixture is `app/preflight/fixture.md`, a short proposal with a heading, a paragraph, and a table, with no provenance tags.
- Rationale: reuses the S4 pipeline unchanged; the two rows are what the export shows; the outputs sit under the ignored runs folder.
- Alternatives: calling the private pandoc and Typst steps (a second entry point into the pipeline; rejected).

## D5. The login

- Decision: `Settings` gains `demo_username` and `demo_password` from `.env`. When both are set, an `http` middleware guards every request whose path is not public: pages redirect with 303 to `/login?next=<path>`; anything else answers 401 `{"error": "sign in required"}`. `POST /login` compares both values with `hmac.compare_digest`, creates a random token in an in-memory `SessionStore`, sets an HttpOnly SameSite=Lax cookie `sterling_session`, and redirects to `next` when it is a relative path, else `/demo`. A wrong pair re-renders the login page with one line. Restart clears every session. No logout, reset, or lockout.
- Rationale: owner decisions 2 and 3; non-goal on per-user accounts; XVII keeps the pair in `.env`.
- Alternatives: HTTP Basic (the browser's dialog is not the export's login page; rejected by the owner); a signed cookie without server state (survives restart, which the demo does not need, and adds a secret to manage; rejected).

## D6. What stays public

- Decision: the allow-list is `GET`/`POST /login`, `/static/`, `/introduction`, `/introduction.pdf`, `/public/`, and `/demo` when the query has `public=1` and `run` equal to `settings.public_run_id` (read with `getattr`, so the guard works before S6 merges and adopts S6's field when it lands). Everything else is protected, API routes included.
- Rationale: the S6 contract's "What S7 must keep public"; a guard on pages alone would leave `/api/runs` and `/api/chat` open through the tunnel.
- Alternatives: protecting only the three pages (decorative; rejected).

## D7. Run mode

- Decision: `RUN_MODE` in `.env`, `laptop` or `cloud`, validated in `load_settings`. In Cloud mode the registry's cached availability marks Ollama unavailable with reason "not offered in Cloud mode" without probing localhost, so `model_options`, `/api/seats`, the composer list, and `unavailable_seats` all follow; the Ollama pre-flight check is `skip` with "Local models are not used in Cloud mode" unless a seat is still on one, which is a `fail` naming the seats.
- Rationale: owner decision 7; spec 2.9; one lever (availability) already read by every consumer (S5 research D2).
- Alternatives: filtering Ollama models out of the registry in Cloud mode (they would vanish from Settings rather than grey; the spec says greyed).

## D8. Tunnel

- Decision: a remotely managed Cloudflare Tunnel: the owner creates it in the Cloudflare dashboard, routes the hostname to `http://localhost:8000`, and pastes the token into `.env` as `CLOUDFLARE_TUNNEL_TOKEN`; `TUNNEL_HOSTNAME` holds the public hostname. `scripts/tunnel.ps1` and `scripts/tunnel.sh` read `.env` and run `cloudflared tunnel run --token`. The pre-flight tunnel check fetches `https://<hostname>/login` with a 10 s timeout: pass "<hostname> answered in <n> ms", fail "Tunnel not connected" on a transport error or "HTTP <status> from the tunnel" otherwise, skip "No tunnel hostname in .env". cloudflared 2026.9.1 recorded in `docs/dependencies.md`.
- Rationale: owner decisions 1 and 8; the token is a credential and stays in `.env`; a locally managed tunnel needs a credentials file and an ingress config, a second place for the hostname.
- Alternatives: `config/cloudflared/config.yml` with ingress rules (duplicates the hostname; rejected); a `cloudflared` quick tunnel (random hostname each start; rejected).

## D9. Disk and `.env` completeness

- Decision: disk reads `shutil.disk_usage(runs_dir)`; pass "<n> GB free", fail "Under 5 GB free (<n> GB)". `.env` completeness lists missing names: `DEMO_USERNAME`, `DEMO_PASSWORD`, and for each cloud provider a seat uses, its `env_key` (Google, xAI) or "AWS credentials" when the boto3 chain resolves nothing; pass "All required keys present", fail "Missing <names>".
- Rationale: owner decisions 9 and 10.

## D10. Visual states

- Decision: `capture_app.states()` adds `preflight-all-pass` and `preflight-one-fail`, each with a `prepare` name; `capture()` accepts a `prepare` mapping of callbacks that the screenshot test binds to its runs folder, writing `tests/fixtures/preflight-all-pass.json` or `preflight-one-fail.json` there before the capture and removing the file after. The fixtures carry the export's detail texts and stamp ("14 Sep 2026, 08:12"), so the page renders the reference from data. The page renders stamps as "<d> <Mon> <yyyy>, <hh:mm>" local time.
- Rationale: constitution XVIII (a fixture may seed a test, never ship as logic); no query switch on the real page.
- Alternatives: a `?state=` switch on the page (design-time control in application logic; rejected).

## D11. Build stamp verification

- Decision: an integration test reads `git rev-parse --short HEAD` and `git log -1 --format=%cs` and asserts the header of each page and `/api/meta` carry them. `build_info` is unchanged.
- Rationale: the roadmap's "build stamp from git in every header" is built; S7 proves it.
