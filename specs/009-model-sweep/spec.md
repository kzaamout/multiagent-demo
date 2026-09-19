# Model sweep and performance record

**Branch**: `009-model-sweep` | **Date**: 2026-09-17 | **Owner decisions**: 1a, 2a, 3b, 4a, 5a, 6b, 7 (custom ranking), 8a, 9a, 10a, plus the modality tables and the local-only constraint.

A maintenance slice, not a demo slice: nothing on the Demo page changes. It answers the owner's request that every run record how each seat's model performed under which settings, that a sweep of local models across seats be run and recorded, and that the performance report say what its columns mean, name the best local model per seat, and show the rejection reasons for every seat and model pair.

## What changes

1. **Every seat call records its settings** (decision 5a). `SeatModel` carries the resolved temperature, context window, thinking flag and output limit; every line of `seat-calls.jsonl` and every seat row of `metrics.json` carries them. The report groups by seat, model and settings, so a later change of a setting starts a new row instead of blending into the old one.
2. **Correctness per seat** (decision 7). `app/runs/expectations.py` turns each dataset README's expected behaviour into checks per seat; `metrics.json` records each check met or not, plus the run's golden match. Accuracy in the report is checks met over checks defined.
3. **The sweep** (decisions 1a, 3b, 4a, 8a, 9a, 10a). `scripts/sweep.py` runs a plan file through the API the Demo page uses: baseline, one seat varied at a time, every seat on one model; ineligible pairs skipped by modality; clarifications answered with their defaults; blockers escalated; Handoff approved by the sweep and recorded as such in `runs/<id>/sweep.json`; a run past the plan's `max_minutes` stopped; jobs claimed in `runs/_sweep/<label>.jsonl` so a second machine can share the plan. Stage 1 is `config/sweep/stage-1.yaml`: the Clean run, five local models, 24 runs. Later stages add the dataset that stresses each seat for the pairs that passed stage 1, then repeats for the finalists.
4. **Local models added** (decision 2a): `qwen3.5:4b` and `deepseek-r1:14b` in the registry, pulled on the reference laptop. DeepSeek is text only, so it never takes the Estimator or the Reviewer.
5. **The report** (decisions 6b, 7). `docs/model-performance.md` gains what the columns mean, the best local model per seat ranked by fewest stopped runs, then accuracy, then first-time rate, then speed, among models with at least five runs on the seat, and a rejection reasons table with every pair. `docs/model-performance-runs.csv` holds one raw row per run and seat with dataset, exit, golden match, sweep job, settings and every count. `docs/model-performance-columns.md` defines every column of both. The modality tables (models and what they take, seats and what they need) are generated from the registry, Ollama's capability list and the seat definitions.

## Known limit

Temperature is a property of the seat in `config/models.yaml`, not of the sweep, and the Estimator's line carries none because Bedrock's sonnet-5 rejects a non-default one. A local model put in that seat therefore runs at the model default while the other seats run at 0.1. The runs record it and the report groups by settings, so within-seat comparisons stay like for like; only across-seat comparison would be affected. Setting a temperature per seat from a sweep plan would need the seat API to take one, which is not built.

## Not in scope

Hyperparameter variation (constant for now), parallel runs on one machine (the card holds one model), cloud models in the sweep, a UI for any of this, and any change to event types or the schema.

## Evidence

Unit tests for the checks, the plan expansion and claims, the ranking, the CSV, and settings capture. Stage 1 recorded on the reference laptop and folded into the report; the roadmap decision entry records the counts and what the data said.
