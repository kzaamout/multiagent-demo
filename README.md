# Sterling AI multi-agent orchestration demo

A sales demo in which several AI agents, under an Orchestrator, take a business request from intake to a reviewed deliverable that a human approves. Read `CLAUDE.md` first.

Slice S1, the event spine and stubbed loop, is built. Slice S2 part A, the live team, is built: datasets with curated inputs run on real models, and the rest run on stubbed agents. The page renders only from the event stream.

## Set it up

One command installs everything a presenter laptop needs: uv and the Python dependencies, a `.env` with the model credentials, Ollama and the local seat model, and a check that every seat's provider is reachable. It asks before installing anything, reads credentials with hidden input, and never prints them.

Windows, from the repository folder:

```
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

macOS or Linux:

```
sh scripts/setup.sh
```

You need AWS access keys with Amazon Bedrock access to Claude Sonnet 5 in ca-central-1, and a Google Gemini API key. Run the setup again at any time; it only fills in what is missing and repeats the checks. Options: `--yes` installs without asking, `--no-prompt` never asks, `--skip-ollama`, `--skip-network-checks`, `--browser-tests`. On macOS, install Ollama from https://ollama.com/download first; the script pulls the model.

## Run it

```
uv run uvicorn app.main:app --port 8000
```

On Windows, set `PYTHONUTF8=1` in the terminal first. A curated dataset, such as 01 Clean run, runs live on real models and costs money per run; set `AGENT_MODE=stub` in `.env` to run everything on stubs.

Open http://localhost:8000/demo. The full validation walk-through is in `specs/001-event-spine-stubbed-loop/quickstart.md`.

## Check it

```
uv run python scripts/check.py      # ruff, format, mypy, tests, em-dash lint, .env leak test
uv run playwright install chromium  # once
uv run pytest -m visual             # screenshot comparison and browser end-to-end tests
```

## Where things are

- Behaviour: `docs/spec-input.md`, `specs/001-event-spine-stubbed-loop/`
- Appearance: `design/` (never edited), deviations in `docs/design-deviations.md`
- Slices and decisions: `docs/roadmap.md`
- Event schema: `docs/schema/events-v1.0.0.md`
- Dependencies and why: `docs/dependencies.md`
