# Phase 1 items 1 to 3: deterministic support for the failing seats

**The whole road is `plan.md` beside this file.** This covers the first three items of its phase 1, which
are built and under test. Phase 1 also holds tool descriptions and the Intake clarification pairing, which
are not built yet.


**Branch**: `009-model-sweep` | **Date**: 2026-09-18 | **Owner instruction**: do the deterministic fixes first, and test them on the worst performing seat and model.

## Why

The 105 run sweep says the three seats that hold several jobs in one reply fail three to four times more often than the three that do one narrow thing.

| Seat | Jobs in one reply | Accepted first time | Stops its runs |
|---|---|---|---|
| orchestrator, reviewer, pricing | 1 | 83 to 99% | 0 to 6% |
| estimator | 3 | 40% | 23% |
| intake | 4 | 35% | 12% |
| writer | 4 | 24% | 43% |

Three of the largest remaining failures are cases where the engine already knows the right answer and only uses it to refuse the model:

| Failure | Count | What the engine already has |
|---|---|---|
| a specialist concern missing from Assumptions | 32 | the concerns, structured, in the run's own events |
| a figure with no provenance tag | 23 | every specialist output, with its source id |
| a blocker naming a sheet that is present | 17 | the prepared manifest, listing every sheet |

Each is the model being asked to remember or judge something the system can compute. The research the owner brought in reaches the same conclusion from the other direction: remove from the model the things that do not need a model, and ground reflection in deterministic verification rather than asking a model to check itself.

These three are done before any seat is split, because they need no new agent, no change to the roster or the six cards the demo shows, and no re-recorded golden logs.

## What changes

### 1. A blocker that names a present sheet is refused with the evidence

The Estimator raised 17 blockers on datasets that plant none, several naming a sheet that was in the set and had been parsed at Intake minutes earlier. A new check reads the prepared manifest, finds any sheet identifier the blocker names, and refuses the reply when that sheet exists, quoting where it is. The seat then reads it instead of stopping the run for a human.

Conservative by design: it fires only when the blocker names something the manifest lists. A blocker about a genuinely absent sheet, which is the whole point of the Missing sheet dataset, passes through untouched.

### 2. An untagged figure is refused with the tag to use

Today the refusal says which amounts have no tag. It does not say what to tag them with, so the Writer guesses and often fails again. The check now searches the offered context for each untagged amount and, when the amount appears under exactly one source, names it: tag this figure with that source id. Where an amount appears under two sources or none, the refusal says so plainly and asks the Writer to choose.

The system does not write the tag itself. Provenance is the demo's integrity claim, and a tag inserted by string matching could attribute a number to the wrong specialist while looking authoritative. The deterministic part is the lookup; the attribution stays with the Writer.

### 3. The assumptions the Writer must carry are given to it, not remembered

The specialist concerns already exist as structured data before the Writer is called. They are added to its context as a prepared block, each concern with its source, under an instruction to carry every one into the Assumptions section. The existing check then verifies what was handed over rather than what was recalled.

## What does not change

No new seats, no new agent ids, no roster or event schema change, so the golden logs, the six agent cards, the Introduction team page and the recorded runs all keep working. Hyperparameters stay as the registry sets them.

## How this is tested

**The bed is the worst configuration with a real sample.** `writer=qwen3.5 9b` stops 38% of its 80 runs and is accepted first time on 27%, the worst of any pair with more than six runs. Two pairs look worse, `estimator=gemma4 12b` at 100% and `estimator=qwen3.5 4b` at 50%, but both rest on six runs and their refusals are output limits rather than anything these fixes touch, so they would not measure the change.

**Datasets** are Clean run, Planted inconsistency and Missing price, the three that reach the Writer, plus Missing sheet to prove the blocker check does not break the scenario that depends on a real blocker.

**The comparison is against what is already recorded**, not against a fresh control, since 80 runs of the current behaviour exist and re-running them would cost eight hours for a number we have. Runs record their instruction version and the report separates them, so before and after do not blend.

**Targets, written down before the runs so they cannot be moved afterwards:**

| Measure | Now | Target |
|---|---|---|
| Writer stops its run | 38% | under 20% |
| provenance_tags refusals per Writer run | 0.29 | under 0.10 |
| concern_dropped refusals per Writer run | 0.40 | under 0.10 |
| invented blockers on datasets that plant none | 17 across the sweep | zero in the check runs |
| Missing sheet still reaches `blocker_escalated` | yes | unchanged |

**Size**: 12 runs, three per dataset, roughly one hour. Enough to move a 38% rate visibly, not enough to settle a small difference, and that limit is stated rather than hidden.

**How we know it is useful rather than merely different.** Every measure above already comes out of `scripts/model_report.py` and `scripts/prompt_review.py` without new instrumentation. The fixes are useful if the Writer's stop rate falls and the two refusal categories shrink, while the Missing sheet scenario still produces its escalated blocker and no run passes that should have failed. The last is the trap worth naming: a change that makes runs pass by weakening a check would show as a falling stop rate and would be a regression, so the dataset correctness checks have to hold at or above their current level for the result to count.

## Evidence

Unit tests for each of the three checks, including the negative case for each: a genuinely missing sheet still blocks, an ambiguous figure is not attributed, a concern already carried is not demanded twice. Then the 12 runs, with the before and after numbers recorded in the roadmap.
