# Model performance columns

Generated with `docs/model-performance.md` and `docs/model-performance-runs.csv` by `uv run python scripts/model_report.py --write`. The CSV holds one row per run and seat, raw; the report's tables aggregate those rows by seat, model and settings.

## Columns of the report tables

- **Seat**: the seat the row is about; one seat per row, so a model that held two seats appears twice
- **Model**: the model label the seat ran on, as the run's events record it
- **Settings**: the hyperparameters the seat ran with, recorded per run: temperature, num_ctx, think, max_tokens; 'not recorded' for runs before capture
- **Runs**: runs in which the seat made at least one call or reply on this model with these settings
- **Calls**: model calls the seat made across those runs, from meter.update events
- **Stopped runs**: times the seat's reply was refused twice in a row and the run ended because of it
- **Accuracy**: checks met over checks defined: the dataset's own expectations of the seat, or the golden match where the dataset defines none for it (app/runs/expectations.py)
- **First time**: share of accepted replies that needed no correction
- **Corrections**: replies accepted on the second attempt, after one refusal
- **Tokens in per call**: average prompt tokens per call
- **Tokens out per call**: average completion tokens per call
- **Seconds per call**: average wall time per call, measured around the call
- **Cost per run**: estimated spend per run from the registry's prices; zero for local models

## Columns of model-performance-runs.csv

- **run_id**: the run folder under runs/
- **started_at**: when the run started, from run.started
- **dataset_id**: the scenario dataset the run used
- **exit**: how the run ended: reviewer_pass, retry_exhausted, blocker_escalated, not_ready, cost_ceiling, stopped, single_complete, dry_intake
- **golden_match**: true when the run's stage sequence and exit match the dataset's golden log, false when not, empty when the dataset has no golden
- **sweep_label**: the sweep plan the run belongs to, from runs/<id>/sweep.json; empty for a hand-started run
- **sweep_config**: the sweep configuration: baseline, seat=model, or all=model
- **sweep_varied_seat**: the seat the configuration changed from the baseline, or all
- **sweep_repeat**: which repeat of the configuration on the dataset, from 0
- **sweep_worker**: the machine that ran the job
- **seat**: the seat the row is about
- **role**: the seat's display role
- **model**: the model label the seat ran on
- **provider**: bedrock, google, xai or ollama
- **temperature**: the sampling temperature, or 'fixed by the provider' or 'model default'
- **num_ctx**: the context window requested from Ollama, or 'model default'
- **think**: whether the model's thinking mode was on, or 'model default'
- **max_tokens**: the output limit requested, or 'model default'
- **calls**: model calls the seat made in the run
- **tokens_in**: prompt tokens across the seat's calls
- **tokens_out**: completion tokens across the seat's calls
- **wall_ms**: wall time across the seat's calls, milliseconds
- **est_cost**: estimated spend for the seat in the run, USD
- **tool_calls**: tools the seat called
- **replies**: structured replies the seat produced
- **accepted_first_time**: replies accepted without a correction
- **corrections**: replies accepted on the second attempt
- **invalid_twice**: replies refused twice, which stops the run
- **reasons**: refusal reasons by category, as name=count separated by semicolons
- **checks_met**: correctness checks the seat met in the run
- **checks_total**: correctness checks defined for the seat on the dataset
- **checks**: each check as name=1 or name=0 separated by semicolons

## How Accuracy is scored

Each dataset README states its planted defect and what each seat should do about it. `app/runs/expectations.py` turns that into checks per seat: Intake stops the not-ready request naming the deadline and the specification; the Estimator raises the LP-2 blocker on Missing sheet and names E-001 and E-002 on Planted inconsistency; Pricing reports the exit sign unpriced on Missing price; the Writer's first draft carries the disagreement or the exclusion; the Reviewer fails the flawed first draft and passes the clean one; the Orchestrator takes the golden route. A seat with no check on a dataset is scored on the run's golden match, and a dataset without a golden scores nothing.

## How the best local model is chosen

Among local (Ollama) models with at least 5 runs on the seat: fewest stopped runs first, then the highest accuracy, then the highest first-time rate, then the fastest call (owner decision 2026-09-17).
