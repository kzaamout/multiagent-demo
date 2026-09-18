# Seat reliability: a four phase plan

**Branch**: `009-model-sweep` | **Date**: 2026-09-18 | **Owner instruction**: a multi-phase improvement plan, deterministic changes first, then the agent, the seat and the outer loop, with the tests that say whether each helped.

`spec.md` beside this file covers phase 1 items 1 to 3 in detail and is already built. This is the whole road.

## The evidence the plan answers to

From 105 sweep runs plus everything recorded before them.

| Seat | Jobs in one reply | First time | Stops its runs | Largest failures |
|---|---|---|---|---|
| orchestrator | 1 | 99% | 0% | 3 invalid JSON |
| reviewer | 1 | 95% | 2% | 1 wrong shape |
| pricing | 1, through a tool | 83% | 6% | 3 tool skipped |
| estimator | 3 | 40% | 23% | 73 narration, 17 invented blockers, 11 tool skipped |
| intake | 4 | 35% | 12% | 83 grading, 20 narration |
| writer | 4 | 24% | 43% | 32 dropped concerns, 23 untagged, 18 invalid JSON |

Two facts shape every phase. Narrow seats are three to four times more reliable than broad ones, in this system, on this hardware. And the largest failures are not reasoning failures: they are the model being asked to remember, judge or restate something the run already holds exactly.

## How the phases are ordered

Cheapest and most reversible first, and nothing moves to the next phase until the last one is measured. Each phase states what it expects to change before it runs, so a result cannot be reinterpreted afterwards. The order is deliberate: deterministic work removes failures outright, agent work makes a seat better at what remains, seat work changes the shape of the team, and outer loop work is how this keeps happening without me.

A rule that applies throughout: a falling stop rate with falling accuracy is a weakened check, not an improvement. Every phase reports both.

## Phase 1: let the engine answer what it already knows

The model stops being asked for things that are computable. No new seats, no roster change, no re-recorded goldens.

**1.1 A blocker naming a sheet the run holds is refused with the evidence.** Built. Targets 17 invented blockers.

**1.2 An untagged figure comes back with the tag to write.** Built. Targets 23 provenance refusals.

**1.3 The Writer is handed the assumptions it must carry.** Built. Targets 32 dropped concerns.

**1.4 Tool descriptions say when to use a tool and when not to.** Built. Ours say what a tool does and stop there: "Total counts and lengths, apply the waste factors, and roll up labour hours." None says that a reply is refused if the tool was not called, or that the seat must not do the arithmetic itself. The research's example is the pattern: a bare "Calculate margin" against a description naming the preconditions and the cases it is wrong for. Rewrite the descriptions for `quantity_calculate`, `price_list_lookup` and `vision_read_drawing`, each saying when to call it, what must be true first, and what not to use it for. Targets 23 tool-skipped refusals across the Estimator and Pricing.

**1.5 A graded checklist item carries its clarification.** Built, but narrower than planned, and the reason matters. Intake's largest failure by far, 83 refusals, is "items are not pass but there are 0 clarifications". I wrote above that the engine could build the stub from the checklist entry. It cannot: a gap needs a clarification only when the checklist leaves it open, so the items that trigger these refusals are exactly the ones with no default to propose, and the question wording has to come from the request. Authoring them would put invented words in front of a prospect. What the engine can do, and now does, is hand back the skeleton with the question ids already correct, one object per gap, so the second attempt is filling rather than composing. The same division as the tag advice: the engine does the lookup, the seat writes the content.

**1.6 A draft's figures agree with each other and with Pricing.** Approved 2026-09-18 after the phase 1 measurement. Six of twelve runs ended `retry_exhausted` and every one of the 23 blocker findings said the same thing: the total in the executive summary does not match the pricing summary, the material cost differs between sections, the parts do not sum to the whole. The Writer is copying Pricing's totals by hand into three places. Pricing's `cost_summary` is the truth and is already structured, so the check compares every figure the draft repeats against it and against itself, and refuses a draft whose numbers disagree, naming the section and the figure. This is phase 1 work, not phase 2: it is code doing something a model should not be asked to do. I first wrote it as part of 2.1, which was wrong.

**Tests.** Unit tests per check with a negative case each, which is where the risk is: refusing a real blocker, attributing a figure to the wrong specialist, demanding a concern already carried, or accepting a grade the model never justified. Phase 1's blocker check already failed this way once and the existing integration tests caught it.

**Measure.** 12 runs on `writer=qwen3.5 9b`, the worst pair with a real sample. Targets set beforehand: Writer stops under 20% against 38%, provenance and dropped-concern refusals under 0.10 per Writer run, no invented blockers, Missing sheet still exits `blocker_escalated`, dataset correctness at or above current. For 1.4 and 1.5 a further 12 runs with Intake and the Estimator watched.

## Teaching, which runs alongside every phase

Not a phase, because it never finishes. `scripts/prompt_review.py` reads the refusals a seat still produces on the wording it runs on now, and the lesson is written into that seat's instructions by a person (decision 23). It has already taken Pricing from fifteen tool-skipping refusals to none and removed narration at three seats.

**Approved 2026-09-18: the Estimator, from its fourteen refusals in the phase 1 runs.** Seven narration, five wrong shape, one broken JSON, one tool skipped. It is now the seat producing the most refusals on the team, having been overtaken by nothing else improving. Its earlier lessons covered narration, and narration is still its largest failure, so this one has to work differently from a fourth worked example: the reviewer's own output should say which shape it is getting wrong.

## Phase 2: make each seat better at what is left

Changes inside a seat's own loop. Still no new seats.

**2.1 The Writer returns sections, not one object holding a document.** Approved 2026-09-18, to follow 1.6 and only if 1.6 leaves the problem standing. Its 18 invalid-JSON refusals come from wrapping a whole markdown document in a JSON string, which is the fragile case, and it produces 987 output tokens per call, the most of any seat. Returning the sections the template already names, assembled by the existing `template_render`, makes each reply smaller and the JSON simpler. This is an output-shape change, not a split: one seat, one dispatch.

**2.2 A bounded self-check before the reply is sent.** The research's shape is generate, verify deterministically, reflect only on failure, repair once or twice, escalate past that. We have the verification and the repair loop, but the seat learns it failed only after a refusal costs an attempt. Letting a seat run the same deterministic checks itself before replying converts a refusal into a self-correction. The risk is cost: an extra call per reply, and this hardware has no spare capacity, so it is measured on wall clock as well as on failures.

**2.3 Per-seat settings, now that we know hyperparameters matter.** Held constant through the sweep by instruction, which was right for comparing models and leaves this unexplored. The Estimator runs at model-default temperature because its registry line has no temperature, an accident of the Bedrock entry rather than a choice. DeepSeek reasons at length with no way to turn it off. Sweep one seat at a time over temperature and context window with the model fixed.

**Tests.** The existing suites cover the reply shapes; 2.1 needs the compile path proved for sectioned output, and the visual suite re-run since the artifact panel renders the result. 2.2 needs a test that the self-check cannot pass a reply the engine would refuse, or it is theatre.

**Measure.** Same 12 run bed, Writer first. 2.1 expects invalid JSON near zero and output tokens per call down by half. 2.2 expects first-time acceptance up and total wall clock not worse by more than a fifth. 2.3 expects nothing in particular, which is why it is a sweep and not a change.

## Phase 3: change the shape of the team

Only reached if phases 1 and 2 leave a seat still failing, and only for the seat that does. Each split is a real cost: new agent ids, re-recorded golden logs, a changed roster, more cards than the design export was built for, and the same configuration work again for the appraisal workflow in S8.

**3.1 Intake grades, then a second seat asks.** One seat grades every checklist item with a note. A second turns the grades into the brief, the clarifications and the verdict. Targets the cross-field consistency failure that 1.5 attacks from the other side; if 1.5 works, this is not needed.

**3.2 The Writer drafts, then a second seat tags and checks.** Targets the two largest Writer failures at once. The tagger sees the draft and the specialist outputs and nothing else, which is a narrow job of the kind that already succeeds here.

**3.3 The Estimator reads sheets, then takes off.** One seat returns a structured summary per sheet, run once per sheet and naturally parallel; a second builds the takeoff from those summaries. Targets the 19000-token prompts and makes sheet coverage explicit rather than something a model can claim. The accuracy risk is real: the second seat sees text where it used to see the image, so it must be able to ask for a re-read rather than guess.

**Tests.** Each split needs its golden logs re-recorded, the seat table re-read afterwards, and a before-and-after on the same 12 run bed. A split that does not move the seat's stop rate by at least a third gets reverted rather than kept for tidiness.

**Measure, and the honest prior.** The seat table says five different models all fail at the Writer, which points at the job rather than the model, so I expect 3.2 to pay. I expect 3.1 not to be needed if 1.5 lands. I have no prior on 3.3.

## Phase 4: make the improvement loop the system's own

So this continues without someone reading refusal logs by hand.

**4.1 A comparison across prompt versions.** Every run records the instruction version of every seat, so the report can already separate before and after. What it cannot do is say whether a difference is real. Add the comparison to `scripts/model_report.py`: for a seat, two versions, the stop rate and first-time rate of each with the run counts beside them, and an explicit statement when the counts are too small to tell. That is the honest half of A/B testing, without claiming significance we cannot support on twelve runs.

**4.2 Trajectory evaluation, not just outcome.** We measure whether the answer was right and whether the run took the golden route. We do not measure whether a seat chose the right tool with the right arguments, which the research separates out and which our tool-skipped refusals only catch at the extreme. Tool choice per seat is already in the events; it needs a check, not new instrumentation.

**4.3 A regression gate for prompt edits.** Teaching a seat currently has no safety net: the Intake edit may have made that seat slower, and I only noticed because I was watching. A small scripted suite, run against a prompt change before it is committed, that replays recorded seat inputs and asserts the reply still parses and still satisfies its requirements.

**4.5 The engine's version recorded beside the prompt's.** Found on 2026-09-18 and it undermines the tables until fixed. Every run records the instruction version of each seat, so teaching a seat separates before from after. Almost all of phase 1 was engine code, not seat wording, and that changes no version at all, so the reasons table pools runs from before and after a fix and reports as "still worth fixing" things that are already fixed: Intake showed 109 grading refusals on the day the last twelve produced two. A hash over the files that decide seat behaviour, recorded per run like the prompt version, makes every later comparison honest.

**4.4 Golden logs re-recorded from current behaviour.** They match 23 of 105 runs and were generated from stubs written in the first slice, with a roster of models we no longer use. Until they are re-recorded, route drift means nothing, which is why the reviewer reports it as an observation rather than a lesson. This is S9's job and should stay there, but phases 2 and 3 both invalidate goldens again, so the order matters: re-record last.

**Tests.** Each of these is a tool for us rather than the demo, so unit tests and one worked example each. 4.3 is itself a test harness and needs to be proved to fail when given a prompt that breaks a requirement.

## What the retry budget is not

Asked on 2026-09-18 and answered by the data: raising it would change nothing. All six exhausted runs stopped with `stop_reason: no_progress` after one retry from a budget of three, so the budget was never what ended them. The engine stopped them because a review cycle failed to reduce the blocker findings. Seat attempts are the same story: two to three cut stops from five in twelve to one, and a fourth has nothing left to bite on at one in twelve. A seat that reproduces the same disagreement on every attempt is not short of attempts, which is the argument for 1.6.

## What would make me stop

If phase 1 moves the Writer's stop rate below 20%, phase 3.2 is not worth its cost and the plan should stop at phase 2. If phase 1 changes nothing measurable, the deterministic theory is wrong for this system and phase 3 should be brought forward rather than continuing to phase 2. Either way the next decision is yours, on numbers, not on my expectation.
