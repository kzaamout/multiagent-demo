# Sterling AI multi-agent orchestration demo

A sales demo in which several AI agents, under an Orchestrator, take a business request from intake to a reviewed deliverable that a human approves. Read `CLAUDE.md` first.

Slice S1, the event spine and stubbed loop, is built. Slice S2, the live team on Clean run, is built and waiting for its first live run. Datasets with curated inputs run on real models; the rest run on stubbed agents. The page renders only from the event stream.

## Set it up

Setup takes about fifteen minutes on a new laptop, most of it downloading the local model.

### What you need first

- **A laptop** running Windows 10 or 11, macOS, or Linux, with an internet connection and about 12 GB of free disk space.
- **Memory for the local model.** Llama 3.1 8B uses about 7 GB. It runs fast on a graphics card with 8 GB or more of memory, and slowly on the processor otherwise.
- **The code.** Clone the repository or unzip a copy, and open a terminal in its folder.
- **An AWS account with Amazon Bedrock.** The Orchestrator, Intake, Estimator, and Writer seats run Claude Sonnet 5 through Bedrock in ca-central-1. See "Getting AWS access keys" below.
- **A Google Gemini API key.** The Reviewer seat runs Gemini 2.5 Pro. Create a key at https://aistudio.google.com/apikey.

You do not need to install Python, uv, or Ollama yourself. The setup script installs them.

### Getting AWS access keys

1. In the AWS console, open IAM and create a user for the demo, or use an existing one.
2. Give the user Bedrock permissions. The simplest is the AWS managed policy `AmazonBedrockFullAccess`. A narrower policy needs these actions:
   - `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream`, to run the seats.
   - `aws-marketplace:Subscribe`, `aws-marketplace:Unsubscribe`, and `aws-marketplace:ViewSubscriptions`, so Bedrock can enable Claude on the first call.
   - Optional, for the setup checks: `bedrock:GetInferenceProfile`, `bedrock:GetFoundationModelAvailability`, `bedrock:GetUseCaseForModelAccess`, and `iam:SimulatePrincipalPolicy`.
3. Create an access key for the user and keep the key ID and secret for the setup script. AWS shows the secret once.
4. Once per AWS account or organization, submit Anthropic's first-time use case form: in the Bedrock console, open the model catalog, choose a Claude model, and submit the use case details.
5. Make sure the AWS account has a valid payment method. Bedrock bills Claude through AWS Marketplace.

Claude is enabled for the account automatically on the first live call, which accepts the model's licence terms. The setup script tells you if anything above is missing.

### Run the setup script

Windows, in PowerShell, from the repository folder:

```
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

macOS or Linux, from the repository folder:

```
sh scripts/setup.sh
```

On macOS, install Ollama from https://ollama.com/download and start it before running the script. Ollama publishes no scripted install for macOS.

The script works through four steps and prints `ok`, `warn`, or `FAIL` for each check:

1. **Credentials.** It creates `.env` from `.env.example` and asks for the AWS access key ID, the AWS secret access key, and the Gemini API key. Secrets are typed with hidden input, saved only to `.env`, and never printed. `.env` is ignored by git.
2. **Ollama.** It installs Ollama if it is missing, after asking: winget on Windows, the official install script on Linux. It starts Ollama and pulls Llama 3.1 8B.
3. **Seat providers.** It confirms that every seat's provider is configured.
4. **Provider access.** It confirms the AWS keys and the Gemini key work, and that Claude Sonnet 5 can be enabled, without calling a model or spending money.

It ends with "Ready for live runs" or with the list of what is still missing. Run it again at any time: it keeps what is already set and repeats the checks.

Options, added after the command:

| Option | Effect |
|---|---|
| `--yes` | Install without asking |
| `--no-prompt` | Never ask; report what is missing |
| `--skip-ollama` | Leave Ollama alone |
| `--skip-network-checks` | Skip the AWS and Gemini access checks |
| `--browser-tests` | Also install Chromium for the visual tests |

To enter credentials by hand instead, copy `.env.example` to `.env` and fill in the values. Do not paste keys into chats, tickets, or commits.

## Run it

Windows, in PowerShell:

```
$env:PYTHONUTF8 = "1"
uv run uvicorn app.main:app --port 8000
```

macOS or Linux:

```
uv run uvicorn app.main:app --port 8000
```

Open http://localhost:8000/demo. The server reads `.env` when it starts, so restart it after changing `.env`.

### A live run

1. Choose **01 · Clean run** in the composer and press **Run**. It runs on real models and costs money; the meters show the estimated spend as it goes.
2. Intake should ask one question, about bid security. Answer it in the banner, for example "No bid security required", and resume.
3. The team works through Plan, Work, Assemble, and Review. The draft appears in the artifact panel.
4. At Handoff, approve the proposal. The run ends.

Run Clean run a second time and Intake does not ask again, because the answer is stored in `knowledge/fictional-prospect-ltd.md`. Delete that file to hear the question again.

The other datasets have no curated inputs yet and run on stubbed agents at no cost. To run every dataset on stubs, add `AGENT_MODE=stub` to `.env` and restart the server.

### If something goes wrong

| Symptom | Fix |
|---|---|
| PowerShell says running scripts is disabled | Use the command exactly as shown, with `-ExecutionPolicy Bypass` |
| `uv` is not found right after setup installed it | Open a new terminal and run the setup again |
| `uv sync` fails with access denied, and the folder is in OneDrive | Pause OneDrive syncing and run the setup again |
| Run is refused with "Live run unavailable" | The message names the seat and the missing provider. Run the setup again to see what to fix |
| Pricing cannot reach Ollama | Start the Ollama app, or run the setup again, which starts it |
| The first Bedrock call fails with AccessDeniedException | Check the use case form, the Marketplace permissions, and the payment method above; a new subscription can take up to 15 minutes |
| A key in `.env` seems ignored | A Windows or shell environment variable with the same name wins over `.env`. The setup script warns about this; remove the environment variable |
| Port 8000 is in use | Start with `--port 8001` and open that port instead |
| Garbled characters on Windows | Run `$env:PYTHONUTF8 = "1"` in the terminal before starting |

## Check it

```
uv run python scripts/check.py      # ruff, format, mypy, tests, em-dash lint, .env leak test
uv run playwright install chromium  # once
uv run pytest -m visual             # screenshot comparison and browser end-to-end tests
```

## Where things are

- Behaviour: `docs/spec-input.md`, `specs/001-event-spine-stubbed-loop/`, `specs/002-live-team-clean-run/`
- Setup: `scripts/setup.py`, with `scripts/setup.ps1` and `scripts/setup.sh` as bootstraps; models and seats in `config/models.yaml`
- Datasets: `datasets/`, with the Clean run inputs described in `datasets/clean-run/README.md`
- Appearance: `design/` (never edited), deviations in `docs/design-deviations.md`
- Slices and decisions: `docs/roadmap.md`
- Event schema: `docs/schema/events-v1.0.0.md`
- Dependencies and why: `docs/dependencies.md`
