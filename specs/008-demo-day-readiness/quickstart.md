# Quickstart: validating S7

Run from the worktree root on branch `008-demo-day-readiness`. The `.env` there points `RUNS_DIR` and `DATASETS_DIR` at the main checkout.

## Prerequisites

- `uv sync` done; Chromium for Playwright installed (`uv run playwright install chromium`).
- Typst and pandoc on the path (the compile rows).
- For the live pre-flight: Ollama running with the seat models pulled, AWS credentials for the Estimator's seat, `DEMO_USERNAME` and `DEMO_PASSWORD` set, and, when the owner has supplied them, `TUNNEL_HOSTNAME` and `CLOUDFLARE_TUNNEL_TOKEN` with the tunnel started by `scripts/tunnel.ps1`.

## Gates

```
uv run python scripts/check.py
uv run pytest -m visual
```

Expected: all gates green; the visual suite passes for the existing states plus `preflight-all-pass` and `preflight-one-fail`.

## Story 1, pre-flight

Scripted: `uv run pytest tests/unit/s7 tests/integration/s7/test_preflight_api.py -q`. Expected: classification, storage, the four header states on the three pages, the running lock, and no marker from `.env` in any detail line.

Live: start the app, sign in, open `/preflight`, press Run pre-flight. Expected within 60 s: green rows with the seat models named, the confirmation "All checks pass" with the mode and time, and a green dot on Demo and Settings. Stop Ollama and run again: the Ollama row is red, the dot is red. Unset the tunnel hostname and run again: the tunnel row is grey and counts for neither.

## Story 2, login

Scripted: `uv run pytest tests/integration/s7/test_login_guard.py -q`. Expected: redirects on the three pages, 401 on the API, the public list untouched, a wrong pair refused, a right pair admitted, and open pages when `.env` has no pair.

Live: in a private window open `/demo`. Expected: the login page; a wrong password shows one line; the right one lands on Demo.

## Story 3, run mode

Scripted: `uv run pytest tests/unit/s7/test_run_mode.py -q`. Expected: Cloud mode greys every local model with the note, a local seat refuses a live run, the Ollama row is not applicable.

Live: set `RUN_MODE=cloud`, restart, open Settings. Expected: local entries greyed with "not offered in Cloud mode".

## Story 4, tunnel

Scripted: `uv run pytest tests/unit/s7/test_tunnel_check.py -q`. Expected: pass on 200 with the answer time, "Tunnel not connected" on a transport error, the HTTP status otherwise, not applicable with no hostname.

Live (when the owner has supplied the values): `scripts/tunnel.ps1`, then open `https://<hostname>/introduction` from a phone off the wifi. Expected: the Introduction page without a login; `/demo` asks for the login.

## Story 5, build stamp

`uv run pytest tests/integration/s7/test_build_stamp.py -q`. Expected: every page header and `/api/meta` carry the current short hash and commit date.
