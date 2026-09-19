# Model performance columns

Generated with `docs/model-performance.md` and `docs/model-performance-runs.csv` by `uv run python scripts/model_report.py --write`. The CSV holds one row per run and seat, raw; the report's tables aggregate those rows by seat, model and settings.

## Columns of the report tables

- **Seat**: the seat the row is about; one seat per row, so a model that held two seats appears twice
- **Model**: the model label the seat ran on, as the run's events record it
- **Settings**: the hyperparameters the seat ran with, recorded per run: temperature, num_ctx, think, max_tokens; 'not recorded' for runs before capture
- **Prompt**: the version of the seat's instructions the run used, so runs before and after a seat was taught something do not blend; 'not recorded' for runs before capture
- **Runs**: runs in which the seat made at least one call or reply on this model with these settings
- **Calls**: model calls the seat made across those runs, from meter.update events
- **Stopped runs**: times the seat ran out of attempts and the run ended because of it; the ranking uses this as a share of the model's runs, so a model is not favoured for having been tried less
- **Accuracy**: checks met over checks defined: the dataset's own expectations of the seat, or the golden match where the dataset defines none for it (app/runs/expectations.py)
- **First time**: share of accepted replies that needed no correction
- **Corrections**: replies accepted on the second attempt, after one refusal
- **Tokens in per call**: average prompt tokens per call
- **Tokens out per call**: average completion tokens per call
- **Seconds per call**: average wall time per call, measured around the call
- **Cost per run**: estimated spend per run from the registry's prices; zero for local models

## Extra columns of the local model table

The same meanings as above, except where a per-model view changes them.

- **Seats**: how many different seats this model held across the runs counted
- **Tested models**: how many different models have held this seat
- **Prompt versions**: how many versions of this seat's instructions are recorded, which is how often the wording had to change to get the seat working
- **Runs**: recordings the model appears in at all, counted once however many seats it filled in that run
- **Stopped runs**: runs this model ended by running out of attempts in any seat, with the share of its runs
- **Tokens in/out per call**: average prompt and completion tokens per call, across its seats

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
- **instructions**: the version of the seat's instructions the run used (app/seats/definitions.py)
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
- **stopped_run**: 1 when this seat ran out of attempts and the run ended because of it, else 0
- **reasons**: refusal reasons by category, as name=count separated by semicolons
- **checks_met**: correctness checks the seat met in the run
- **checks_total**: correctness checks defined for the seat on the dataset
- **checks**: each check as name=1 or name=0 separated by semicolons

## How Accuracy is scored

Each dataset README states its planted defect and what each seat should do about it. `app/runs/expectations.py` turns that into checks per seat: Intake stops the not-ready request naming the deadline and the specification; the Estimator raises the LP-2 blocker on Missing sheet and names E-001 and E-002 on Planted inconsistency; Pricing reports the exit sign unpriced on Missing price; the Writer's first draft carries the disagreement or the exclusion; the Reviewer fails the flawed first draft and passes the clean one; the Orchestrator takes the golden route. A seat with no check on a dataset is scored on the run's golden match, and a dataset without a golden scores nothing.

## What Accuracy does not measure, and the price tables that do

Accuracy never looks at a number. Every check above is about behaviour: did the run stop, reach Work, raise the blocker, carry the concern, pass review. A Clean run whose only Estimator check is that no blocker was raised scores 100 percent with a price a fifth too high. The price tables measure the number, for scenarios whose drawings state their own quantities, and are kept out of Accuracy and out of the ranking on purpose (owner decision 2026-09-19). The reference is computed by `app/runs/reference.py` from the counted quantities with the app's own calculator and price lookup, and each run stores its comparison under `price_check` in its `metrics.json`.

- **Estimator model**: the model in the Estimator seat, whose takeoff drives the price
- **Priced runs**: runs on a scenario with a reference price that reached a priced total
- **Median price difference**: the middle value of the run's total minus the reference total, as a percentage of the reference, sign ignored. The reference is what the app's own calculator and price lookup give for the quantities the drawings state, 36,882.58 CAD on the Clean run
- **Within 5%, Within 25%**: priced runs whose total is that close to the reference, either way
- **Lowest, Highest**: the most a total fell below the reference and the most it rose above it
- **Median labour difference**: the same measure for the takeoff's labour hours against the reference hours, 139.85 on the Clean run
- **Takeoff lines right**: of the materials the drawings schedule, the share whose quantity in the takeoff is within about one percent of the reference quantity. The takeoff is the Estimator's list of materials and quantities read off the drawings; it is not a price

## How the best local model is chosen

Among local (Ollama) models with at least 5 runs on the seat: fewest stopped runs first, then the highest accuracy, then the highest first-time rate, then the fastest call (owner decision 2026-09-17).
