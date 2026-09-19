# Sterling AI multi-agent orchestration demo

A sales demo in which several AI agents, under an Orchestrator, take a business request from intake to a reviewed deliverable that a human approves. Read `CLAUDE.md` first.

Slice S1, the event spine and stubbed loop, is built. Slice S2, the live team on Clean run, is built and verified live. Slice S3, the failure paths and the presenter controls, is built and verified live on all five datasets. The page renders only from the event stream.

## Set it up

Five seats run on local models through Ollama and cost nothing. The Estimator runs on Claude Sonnet 5 through Amazon Bedrock, which reads the drawings far more accurately and costs roughly 30 to 40 US cents per run. A per-run cost ceiling stops any run whose estimated spend passes it. Setup takes about half an hour on a new laptop, most of it downloading the two local models.

### What you need first

- **A laptop** running Windows 10 or 11, macOS, or Linux, with an internet connection and about 20 GB of free disk space.
- **A graphics card with 12 GB of memory** for a comfortable pace. The local seats use Qwen 3.5 9B and Gemma 4 12B, each between 7 and 9 GB in memory, loaded one at a time. With less graphics memory they run on the processor and a run takes much longer.
- **An AWS account with Amazon Bedrock** for the Estimator. See "Getting AWS access keys" below.
- **The code.** Clone the repository or unzip a copy, and open a terminal in its folder.

You do not need to install Python, uv, or Ollama yourself. The setup script installs them.

### Seat models

| Seat | Model | Why |
|---|---|---|
| Orchestrator, Intake, Pricing, Writer | Qwen 3.5 9B, local | Calls tools reliably and follows the reply formats |
| Estimator | Claude Sonnet 5 on Bedrock, thinking off | Reads quantities from drawing pages accurately; local models misread them |
| Reviewer | Gemma 4 12B, local | A different model family from the Writer, reads images |

The seats are set in `config/models.yaml`. The Settings page is a preview until slice S5: its selectors do nothing and its model labels are the design's cloud examples, not the running seats. Until then, change a seat by editing its `model` in that file, run the setup script to pull any new local model, and restart the server. The Demo page always shows the models a run actually uses.

Set the cost ceiling in `.env`, for example `COST_CEILING=1.00`. It is an estimate from token counts and model prices, checked after every model call, so a run can pass it by at most one call. The default is 5.00.

### Getting AWS access keys

1. In the AWS console, open IAM and create a user for the demo. Give it the AWS managed policy `AmazonBedrockFullAccess`, or a narrower policy with `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`, `aws-marketplace:Subscribe`, `aws-marketplace:Unsubscribe`, and `aws-marketplace:ViewSubscriptions`. The setup checks also use `bedrock:GetInferenceProfile`, `bedrock:GetFoundationModelAvailability`, `bedrock:GetUseCaseForModelAccess`, and `iam:SimulatePrincipalPolicy` when allowed.
2. Create an access key for the user. AWS shows the secret once.
3. Once per AWS account or organization, submit Anthropic's first-time use case form: in the Bedrock console, open the model catalog, choose a Claude model, and submit the use case details.
4. Make sure the AWS account has a valid payment method.
5. Run the setup script, which asks for the keys and checks access without calling a model.

Claude is enabled for the account automatically on the first call, which accepts the model's licence terms. The first few minutes after that can return access denied while the subscription completes.

`config/models.yaml` also defines Gemini 2.5 Pro for the Reviewer and Claude for the other seats, the all-cloud choices from 2026-09-15, in a comment under the seats. A Gemini key comes from https://aistudio.google.com/apikey.

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

1. **Credentials.** It creates `.env` from `.env.example` and asks only for the keys the configured seats need, which is none while every seat is local. Secrets are typed with hidden input, saved only to `.env`, and never printed. `.env` is ignored by git.
2. **Ollama.** It installs Ollama if it is missing, after asking: winget on Windows, the official install script on Linux. It starts Ollama and pulls every seat model.
3. **Seat providers.** It confirms that every seat's provider is configured.
4. **Provider access.** When a seat uses a cloud model, it confirms the keys work and the model can be enabled, without calling a model or spending money.

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

### The shared login

Set `DEMO_USERNAME` and `DEMO_PASSWORD` in `.env` and the Demo, Settings, and Pre-flight pages ask for them; the Introduction page stays public. There is one pair for everyone, kept in `.env` only, and a sign-in lasts until the server restarts. Leave both empty on a laptop that is not exposed and nothing asks. The pre-flight reports the pair as missing until it is set.

### Run modes

`RUN_MODE=laptop` (the default) runs everything on this machine with the local models through Ollama, exposed on demo day through the tunnel below. `RUN_MODE=cloud` is for an always-on cloud host with cloud providers only: local models are greyed in Settings and in the composer, a seat still on one refuses a live run, and the pre-flight says so. Move those seats in Settings or in `config/models.yaml` before running in Cloud mode.

### The tunnel

The demo answers at the Sterling AI subdomain from the presenter laptop through a Cloudflare Tunnel.

1. Install cloudflared: `winget install Cloudflare.cloudflared` on Windows, or the release from GitHub. It does not update itself on Windows.
2. In the Cloudflare dashboard, create a remotely managed tunnel and route the public hostname to `http://localhost:8000`.
3. Put the hostname in `.env` as `TUNNEL_HOSTNAME` and the tunnel token as `CLOUDFLARE_TUNNEL_TOKEN`.
4. Start the app, then run `scripts/tunnel.ps1` (or `scripts/tunnel.sh`) in a second terminal. It stays in the foreground; Ctrl+C stops it.

The hostname and the tunnel are still to be supplied by the owner. Until then the pre-flight's tunnel row reads "No tunnel hostname in .env" and counts for nothing.

### Pre-flight

Open http://localhost:8000/preflight before every meeting and press **Run pre-flight**. Each row turns green with one line, or red with what failed:

| Row | What it checks |
|---|---|
| A provider responds (one row per cloud provider a seat uses, or whose key is present) | One minimal model call through the seat's model; a fraction of a cent on a cloud provider |
| Ollama reachable, models present | Ollama answers and every local seat model is pulled |
| Typst present, test compile | pandoc and Typst compile a fixture proposal under `runs/preflight/` |
| Page PNG export | The same compile wrote its page images |
| Tunnel reachable from outside | The login page answers through the public hostname |
| Disk space | At least 5 GB free on the drive holding the runs folder |
| .env completeness | The login pair and the credentials of every cloud provider a seat uses |

The dot beside Pre-flight in every header shows the last result: grey means not run yet, green means every check passed, orange means only a non-essential check failed (the tunnel, or a provider no seat uses), red means an essential check failed. It is stored in `runs/preflight.json` and survives a restart; nothing re-runs by itself.

### The leave-behind

After the meeting, one command writes what the prospect keeps:

```
uv run python scripts/leave_behind.py            # the newest run that finished its job
uv run python scripts/leave_behind.py --run <id> --out <folder>
```

It writes `proposal.pdf` (the run's last compiled version), `run-timeline.pdf` (rendered from the event log) with the run's `metrics.json` beside it, and `introduction.pdf` (the Introduction page) to `runs/<run id>/leave-behind/` unless `--out` says otherwise, and prints the paths. Sending them is by hand; the command only produces the files.

### A live run

1. Choose **01 · Clean run** in the composer and press **Run**. The Estimator's call costs a few tens of cents; the other seats are free. The first call to each local model waits while Ollama loads it.
2. Intake should ask one question, about bid security. Answer it in the banner, for example "No bid security required", and resume.
3. The team works through Plan, Work, Assemble, and Review. The draft appears in the artifact panel.
4. At Handoff, approve the proposal. The run ends.

Run Clean run a second time and Intake does not ask again, because the answer is stored in `knowledge/fictional-prospect-ltd.md`. Delete that file to hear the question again.

### The five scenarios

All five datasets have curated inputs and run on real models. Each one is derived from Clean run with a single planted defect, described in its own README under `datasets/`.

| Dataset | What it shows | Where it ends | Typical spend |
|---|---|---|---|
| 01 Clean run | The whole loop, one question at Intake, one approval | `reviewer_pass` | about $0.30 |
| 02 Planted inconsistency | A rating that disagrees between two sheets: the Estimator proceeds on the single-line and flags it, the Reviewer fails v1 and routes the rework | `reviewer_pass` after one rework | about $0.50 |
| 03 Missing sheet | A panel with no schedule: the Estimator raises a blocker and the run pauses on the blocker card. Escalate ends the run, Answer resumes it | `blocker_escalated`, or `reviewer_pass` when answered | $0.13 escalated, about $0.42 answered |
| 04 Missing price | An item with no supplier price: Pricing reports an unpriced exception and the draft excludes it | `reviewer_pass` | about $0.30 |
| 05 Not ready | A request with no closing date and no specification: Intake stops the run before any specialist is paid | `not_ready` | none, Intake is local |

Presenter controls in the composer: **Pause** holds the run before the next step and reads Resume, **Stop** ends it at once, and **Dry intake** runs Intake alone and stops with the readiness verdict, which costs nothing.

`COST_CEILING` in `.env` stops a run once its estimated spend passes the ceiling, and the termination card names the spend and the ceiling.

To run every dataset on stubbed agents at no cost, add `AGENT_MODE=stub` to `.env` and restart the server.

### Model sweep

`uv run python scripts/sweep.py config/sweep/stage-1.yaml --worker laptop` runs every configuration in a plan, one run at a time, through the same API the Demo page uses: a baseline seat assignment, each listed model on each listed seat one at a time, and each `whole` model on every seat. Combinations a model cannot serve are skipped (a text-only model on the Estimator or the Reviewer). Clarifications take their proposed default, a blocker is escalated, Handoff is approved by the sweep, and a run past `max_minutes` is stopped. Jobs are claimed in `runs/_sweep/<label>.jsonl`, so a second machine pointed at the same runs folder takes the next unclaimed job; `--dry-run` lists the jobs. Each run then carries `sweep.json` saying which job it was. Read the results with `uv run python scripts/model_report.py --write`, which refreshes `docs/model-performance.md`, the raw rows in `docs/model-performance-runs.csv`, and the column definitions in `docs/model-performance-columns.md`. A sweep occupies Ollama, so live runs from the Demo page crawl while it goes.

### Teaching a seat

`uv run python scripts/prompt_review.py --write` reads every recorded run and says what each seat is still getting wrong, then writes `docs/prompt-review.md`. It suggests and never edits. Each finding quotes the real refusal, names the runs, and drafts the example block in the shape the seat files use, leaving one line blank: what the seat should have sent instead. That line is a judgment about the trade's conventions, so a person writes it. Paste the finished block into `config/electrical-bid/seats/<seat>.md`, which changes that seat's recorded instruction version, and the report then keeps runs before and after the lesson apart. Refusals against wording you have already rewritten drop out on the next run of the review, so the list shrinks as you teach.

### If something goes wrong

| Symptom | Fix |
|---|---|
| PowerShell says running scripts is disabled | Use the command exactly as shown, with `-ExecutionPolicy Bypass` |
| `uv` is not found right after setup installed it | Open a new terminal and run the setup again |
| `uv sync` fails with access denied, and the folder is in OneDrive | Pause OneDrive syncing and run the setup again |
| Run is refused with "Live run unavailable" | The message names the seat and the missing provider. Run the setup again to see what to fix |
| A seat cannot reach Ollama | Start the Ollama app, or run the setup again, which starts it and pulls missing models |
| A run is very slow | The models are running on the processor. Close other programs that use the graphics card, or use a laptop with 12 GB of graphics memory |
| With cloud models, the first Bedrock call fails with AccessDeniedException | Check the use case form, the Marketplace permissions, and the payment method above; a new subscription can take up to 15 minutes |
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
- Model performance per seat, from every run: `docs/model-performance.md` (`uv run python scripts/model_report.py --write`)
- Appearance: `design/` (never edited), deviations in `docs/design-deviations.md`
- Slices and decisions: `docs/roadmap.md`
- Event schema: `docs/schema/events-v1.0.0.md`
- Dependencies and why: `docs/dependencies.md`
