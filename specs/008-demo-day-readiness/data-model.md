# Data model: Demo-day readiness (S7)

Entities and their rules. Nothing here is an event; the 1.1.0 schema is untouched.

## Check (code, fixed order)

| Field | Type | Rule |
|---|---|---|
| id | string | stable machine id: `provider:<name>` (for example `provider:bedrock`), `ollama`, `typst`, `png`, `tunnel`, `disk`, `env` |
| name | string | display copy: "<Provider label> responds", "Ollama reachable, models present", "Typst present, test compile", "Page PNG export", "Tunnel reachable from outside", "Disk space", ".env completeness" |
| essential | bool | see research D2; a provider row is essential when a seat uses it |
| timeout_s | float | 30 per provider probe, 10 tunnel, 60 compile, 5 Ollama |

Order on the page: provider rows in the registry's provider order, then ollama, typst, png, tunnel, disk, env.

## CheckResult

| Field | Type | Rule |
|---|---|---|
| id | string | the Check id |
| name | string | the Check name |
| status | `pass`, `fail`, `skip` | `skip` means not applicable in this mode or configuration |
| detail | string | one line; never a credential value or a provider's message text |
| essential | bool | copied from the Check |
| elapsed_ms | int | wall time of the check |

## PreflightResult (`runs/preflight.json`)

| Field | Type | Rule |
|---|---|---|
| schema | int | 1 |
| run_mode | `laptop`, `cloud` | from settings |
| ran_at | ISO 8601 with offset | when the run started |
| status | `pass`, `warn`, `fail` | derived: fail if an essential check failed, else warn if any failed, else pass |
| passed | int | count of `pass` |
| applicable | int | count of `pass` plus `fail` |
| checks | list of CheckResult | in Check order |

A missing or unreadable file, or one whose `schema` is not 1, is `pending`.

## HeaderState (derived per request)

| Overall | data-status | glyph | title |
|---|---|---|---|
| pending | `pending` | ○ | "Pre-flight: not run yet" |
| pass | `pass` | ✓ | "Pre-flight: all checks pass, <stamp>" |
| warn | `warn` | ! | "Pre-flight: <first failed name> failed (non-essential), <stamp>" |
| fail | `fail` | ✕ | "Pre-flight: <first essential failed name> failed, <stamp>" |

Stamp format: "<d> <Mon> <yyyy>, <hh:mm>" in the server's local time, the export's "14 Sep 2026, 08:12".

## Login and Session

| Field | Type | Rule |
|---|---|---|
| demo_username, demo_password | str | from `.env`; both empty means the guard is off |
| token | str | `secrets.token_urlsafe(32)`, kept in a process-memory set with its creation time |
| cookie | `sterling_session` | HttpOnly, SameSite=Lax, path `/`; no Max-Age, so the browser drops it when closed |

Public paths (no session needed): `/login`, `/static/...`, `/introduction`, `/introduction.pdf`, `/public/...`, `/demo` with `public=1` and `run=<settings.public_run_id>`. Pages (`/`, `/demo`, `/settings`, `/preflight`) redirect 303 to `/login?next=<path>`; everything else answers 401.

## RunMode

`Settings.run_mode`, `laptop` (default) or `cloud`, from `RUN_MODE`; any other value stops startup with "RUN_MODE must be laptop or cloud". In Cloud mode the registry's availability for `ollama` is `Availability("ollama", False, "not offered in Cloud mode")` without a probe.

## Tunnel settings

`Settings.tunnel_hostname` from `TUNNEL_HOSTNAME` (may be empty). `CLOUDFLARE_TUNNEL_TOKEN` is read only by the tunnel scripts, never by the app.

## State transitions touched

None in the run engine. The pre-flight has one transition: no result to a stored result, replaced on every run.
