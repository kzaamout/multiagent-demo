# HTTP API additions for S7

Additive to the S1, S3, S5, and S6 contracts. Errors keep the `{ "error": string }` body.

## Login guard (middleware)

Active only when `DEMO_USERNAME` and `DEMO_PASSWORD` are set. Public without a session: `GET /login`, `POST /login`, `/static/...`, `/introduction`, `/introduction.pdf`, `/public/...`, and `GET /demo?public=1&run=<pinned>`. Otherwise:

- Page paths (`/`, `/demo`, `/settings`, `/preflight`, and any path without `/api/` that is not public): 303 to `/login?next=<path with query>`.
- Everything else: 401 `{ "error": "sign in required" }`.

## GET /login

200 HTML, the login page. With `?error=1` the page carries the line "Wrong username or password." in the meta text style. With `?next=<path>` the form carries it as a hidden field.

## POST /login

Form fields `username`, `password`, optional `next`.

- Right pair: 303 to `next` when it starts with a single `/`, else `/demo`; `Set-Cookie: sterling_session=<token>; HttpOnly; SameSite=Lax; Path=/`.
- Wrong pair: 303 to `/login?error=1` (with `next` kept), no cookie.
- Guard off (no credentials in `.env`): 303 to `/demo`.

## GET /api/preflight

200 `{ "status": "pending" | "pass" | "warn" | "fail", "run_mode": "laptop" | "cloud", "ran_at": string | null, "passed": int, "applicable": int, "checks": [CheckResult], "running": bool }`. With no stored result, `checks` lists every check in order with status `pending` and detail "Pending".

## POST /api/preflight/run

Runs every check, stores the result, and returns the same body as `GET /api/preflight` with status 200 when done. 409 `{ "error": "a pre-flight is already running" }` while one runs. Never returns a credential value.

## GET /api/meta (extended)

`preflight` becomes the stored overall status (`pending`, `pass`, `warn`, `fail`) and the body gains `run_mode`.

## GET /api/seats and /api/providers (extended behaviour)

In Cloud mode every Ollama option is `available: false` with `reason` and `note` "not offered in Cloud mode"; `/api/providers` reports the same reason for `ollama`.

## Pages

Every protected page's header carries the pre-flight dot substituted server-side from the stored result: `data-status`, the glyph, and the title.

## Scripts

`scripts/tunnel.ps1` and `scripts/tunnel.sh`: read `CLOUDFLARE_TUNNEL_TOKEN` from `.env`, exit 2 with one line when it is empty or cloudflared is not on the path, else run `cloudflared tunnel run --token <token>` in the foreground.
