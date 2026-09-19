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

**1.7 A number is checked where it is born.** Approved 2026-09-18 (owner decisions 1a, 2a, 3a). Built in `app/live/figures.py`. The owner challenged the tag rule twice, and was right both times. First: finding "figures that need a tag" with a pattern over dollar signs is a judgment forced on code, and it was being patched one exemption at a time, for zeros, for the labour rate, for line extensions. Second, when I proposed replacing it with a check that Pricing's four totals appear in the draft: numbers that add up prove nothing about where they came from. The recorded runs settled it. In five runs with gemma4 12b at Pricing the lookup tool returned an error, the model wrote every price itself, 60 lines in all, and the reply was accepted because the only question asked was whether the tool had been called. Three of those documents passed review, one carrying an invented total of $28,728.61 under a valid tag. A tag says which output a number was copied from, never that the output is true. So the protection moves to the three places a number changes hands, and each is a lookup by equality, not a judgment:

- *Tool to specialist.* Every unit price, extension and total in Pricing's reply equals what `price_list_lookup` returned in that turn, to the cent; a line the tool returned unpriced carries no price; the totals are those of one call that priced every line. The Estimator's quantities and labour hours equal `quantity_calculate`'s. A failed call supports nothing, and no longer counts as a use of the tool.
- *Specialist to specialist.* Pricing's quantities are the Estimator's.
- *Specialists to draft.* Every dollar amount in the draft, tagged or not, exists in something the Writer was given. This replaces the rule that every amount must carry a tag. The tagged-figure check (1.6) and the refusal of a draft with no tags at all both stay.

Full tool results are kept in `runs/<id>/tool-results.jsonl`, because the event carries a summary of 200 characters, which serves the feed and cannot support a comparison.

What the replay taught before any live run (`scripts/replay_figures.py`, no model cost, 133 Pricing replies and 131 committed drafts). My first matching keyed Pricing lines on the line reference and refused 34 honest replies: seats reuse one drawing reference for every line read from a sheet. Keyed on description, it refused 14 more at the handover: the Estimator repeats a material once per group. A reply line is now held against every tool line it could be a copy of and stands when it equals any one, and wording only finds the candidates while the figures must still be equal. With that, 6 of 133 Pricing replies would be refused, the five above and one that priced a line the fixture does not carry, and 1 handover where a quantity of 32 stood against the Estimator's 5. No honest reply is refused. At the Writer, the old rule had refused 67 replies and the new one would refuse 5 of those; of 131 committed drafts, 4 hold an amount found nowhere upstream, and two of them carry $36,882.58, the amount in the worked example in the Writer's own instructions, in runs where Pricing's total was $21,077.33 and $22,132.12. A few-shot example with a realistic number leaks, and the tag rule could never see it.

What this cannot check is a count read from a drawing. Totals for the clean job ranged from about $22,000 to $49,000 across runs because the takeoffs differed. Confidence flags, the Reviewer and the human at Handoff are the controls there, and no deterministic check should pretend otherwise. The Estimator's calculator check could not be replayed, since the counts it was given were never recorded, so its false-refusal rate is known only from live runs: a rise in stopped runs at the Estimator loosens the check rather than being explained away.

**1.8 A concern that a sheet is missing, when it is, goes back as a blocker.** Built 2026-09-18, found while measuring the Missing sheet scenario. That scenario escalated 3, then 2, then 1 of 3 runs across three beds, and I suspected the removal of the seats' progress lines had taken away reasoning the Estimator needed. The first run of the six-run check said otherwise. The Estimator wrote "Panel schedule LP-2 (E-003) referenced on E-001 and E-102 but not in drawing set per drawing index" as a concern and finished the takeoff. It saw the problem exactly and filed it in the wrong place. Six of the seven recorded runs that failed to escalate did the same. The rule that sends a blocked concern back looks for the words blocked or cannot be counted, and none of these concerns used them. The conventions make a panel with no schedule a blocker, and the manifest settles whether the sheet is absent, so `concern_names_an_absent_sheet` is the mirror of 1.1: a concern or assumption that claims something is missing and names a sheet, shaped like this set's sheets, that the manifest does not hold. Replayed over 111 recorded takeoffs it is silent on all 103 from the other four datasets and catches 6 of the 8 on Missing sheet. That first version also required a word such as missing or absent, and the fifth run of the check slipped past it with "schedule E-003 will be provided later and is not required for initial tender". A list of words for absence is a guess about phrasing, the same mistake as the tag rule in 1.7, and the manifest is the evidence. With the word list removed the check is still silent on all 103 and catches 8 of 9. The six-run check itself ran on the code before this item, so it measures the fault and not the fix; the fix is measured by the Missing sheet runs inside the figures-check bed and by a second six-run batch.

One live finding on 1.7 in the same batch. A run stopped at the Estimator because `quantity_calculate` returned 0 hours, the items having carried no unit hours, and the seat wrote 350.64 hours of its own. The check was right to refuse it, and wrong in how: it said only that the figures differed, the seat sent the same reply again, and the third attempt broke the shape. The refusal now says why the tool returned nothing and what to put in the call. A check that refuses without saying how to recover converts an invented number into a stopped run, which is safer and no more useful.

**1.9 The calculator owns the unit labour hours table.** Built 2026-09-18, and the most consequential finding of the phase. The 1.7 check did what it was built for on its first live runs and stopped two of two Clean runs at the Estimator: `quantity_calculate` had returned 0 hours because the seat passed no unit hours, and the seat wrote 457.5 labour hours of its own on a job of about 114. Told exactly what to change in the call, it called again without them. Looking back through the recorded runs, 36 of 119 accepted takeoffs, 30 percent, carried a labour total the seat wrote after the tool returned 0, anywhere from 20 to 875 hours, and where the seat did pass unit hours they were its own reading of the table, with one takeoff at 2,927 hours. Labour is priced by the hour at 95 dollars, so this was the largest silent error in the price, and much of why totals for the same clean job ran from about 22,000 to 49,000 dollars. None of it was visible: every figure carried a valid tag.

The check alone would have turned a silent error into a stopped run, which is safer and no more useful. The cause was a lookup handed to a model. The table is in the conventions file, so `app/tools/unit_hours.py` parses it from there, one place for the number, and `calculate` applies it to every line whose description it finds, whatever the seat passed. A seat's own unit hours are used only for a line the table does not list, and each returned line says where its hours came from, so such a line carries confidence low as the conventions require. Matching is on words with the units of one kind: "M10 EMT 21 mm (branch circuits)" finds "EMT 21 mm, run", while "EMT 35 mm", a 30-circuit panelboard and the single word "Panelboard" find nothing, because a wrong figure stated with the table's authority is worse than a line flagged as having none. Over 1,458 recorded bill of materials lines, 90 percent find a row, and the rest are mostly items the table really does not list. This is the same move as `price_list_lookup` owning the prices, and it is decision 1b arriving by a better door: the engine does not overwrite the seat's reply, the tool simply stops asking the seat for a number it can look up.

Two smaller repairs from the same runs. A failed tool call now records what the error was, where the run used to say only that there was one, and the refusal for a takeoff or a priced reply written after a failed call tells the seat the call failed and what the arguments must be. The bed begun under the label `figures-check` was stopped after two runs, both stopped at the Estimator for this cause, and restarted as `figures-check-2` on the code with this item, since three more hours measuring a state known to be broken would have bought nothing.

**1.10 The Reviewer reads the figure, not the figure with its marker glued on.** Built 2026-09-18. This corrects the premise of 1.6. I wrote there that the Writer was mistyping Pricing's totals, citing a draft that carried $36,882.581. The Writer never wrote that. The compiled page shows each tagged figure with a small superscript marker, and the text extracted from that page glues the marker to the figure: one price tagged five times reached the Reviewer as $79,063.751, $79,063.752, $79,063.753, $79,063.754 and $79,063.755, and it failed the draft for stating five prices. Across the recorded runs, 113 of the Reviewer's 125 blocker findings say figures disagree; in 54 of the 91 runs that reached review the page text carries an amount with three or more decimals that the Writer's draft never did; and 14 of the 22 runs that spent their whole review budget failed on a disagreement that exists only in that text. The largest failure on this team for two days was the team's own page text. The text now comes from a second compile, never shown to anyone, in which the template writes the marker as " [n]" after the figure, so the Reviewer reads "$79,063.75 [1]" and can still cite the marker. The displayed page, its superscripts and the hover positions are untouched. The Reviewer's instructions say what the bracket is and that a marker is never part of a figure. What 1.6 still does is real, since a tagged amount should be in the output it names, but most of what it was built to stop was not happening.

Three smaller faults came out of the same live runs, each of which had been refusing or mispricing correct work:

- The tagged-figure check of 1.6 compared a figure's text, and JSON drops a trailing zero, so Pricing's 13284.8 was not the Writer's $13,284.80. Five of the eight refusals that check ever issued were false, and one stopped a run whose takeoff was within a hundredth of an hour of the reference. Figures are now compared as numbers, to the cent.
- Writers put the dollar sign outside the tag, "${{42,161.07|src:pricing}}", in 30 of 137 drafts. Every amount check looks for a dollar sign on the number, so those drafts were not checked at all. They are now read as if the sign were inside.
- One takeoff in twelve copies the materials schedule's mark into the description, "M1 2x4 LED troffer". The price lookup matches a description exactly, so every line came back unpriced and a proposal went out priced at labour alone; 11 recorded lookups priced nothing. The lookup now tries the description again without a leading schedule mark. The material's name must still match word for word.

The lesson for the plan's method: every one of these was found by reading a live run's records within minutes of it finishing, and none by the aggregate tables, which had been reporting the symptom, retries exhausted on figure findings, accurately for two days. A refusal category or a finding that dominates the tables deserves one run read end to end before anything is built against it.

**Tests.** Unit tests per check with a negative case each, which is where the risk is: refusing a real blocker, attributing a figure to the wrong specialist, demanding a concern already carried, or accepting a grade the model never justified. Phase 1's blocker check already failed this way once and the existing integration tests caught it.

**Measure.** 12 runs on `writer=qwen3.5 9b`, the worst pair with a real sample. Targets set beforehand: Writer stops under 20% against 38%, provenance and dropped-concern refusals under 0.10 per Writer run, no invented blockers, Missing sheet still exits `blocker_escalated`, dataset correctness at or above current. For 1.4 and 1.5 a further 12 runs with Intake and the Estimator watched.

**Measured, 2026-09-19, items 1.7 to 1.10.** The same bed as before, every seat on Qwen 3.5 9B and the Reviewer on Gemma 4 12B, three runs each of Clean run, Planted inconsistency, Missing price and Missing sheet, under the label `figures-check-2`. It was restarted three times in its first hour, each time after one or two runs, because reading those runs end to end kept finding a fault in the engine; the early runs are kept under `figures-check-2-early` and are not in these figures. The targets were fixed in `config/sweep/figures-check.yaml` before any run.

| | `deterministic-check` | `figures-check-2` |
|---|---|---|
| Runs ending the way the scenario expects | 8 of 12 | 10 of 12 |
| Runs that spent their whole review budget | 2 | 0 |
| Review verdicts that failed the draft | 8 of 16 | 1 of 8 |
| Retries used | 6 | 1 |
| Writer replies refused | 16 of 32 | 4 of 12 |
| Writer refusals over tags or amounts | 14 | 2, both the source id `knowledge` |
| Accepted specialist replies differing from their recorded tool result | not recorded | 0 |
| Estimator replies refused over figures | not checked | 2 of 20 |
| Pricing replies refused | 0 of 13 | 0 of 9 |
| Missing sheet runs escalated | 1 of 3 | 3 of 3 |
| Median price difference from the reference | 23.4% | 15.0% |
| Priced runs within 25 percent of the reference | 4 of 8 | 7 of 8 |

Every target was met: amount refusals at the Writer under 0.15 per reply (none), no accepted Pricing reply differing from its tool, figure refusals at the specialists under 0.25 per reply (0.10 at the Estimator, none at Pricing), and passes at or above the earlier bed's. The one review failure in the bed was false: the Reviewer said a total did not equal the sum of its parts and wrote the correct sum in its own evidence. Both stopped runs were on Missing price, and both were a correct refusal with advice that did not help: a source id the Writer invented for the knowledge file, refused without saying which ids were valid, and a panelboard sent to the calculator under a category that carries waste, refused without saying the call could be corrected. Both wordings were fixed after the bed.

Missing sheet, six runs before item 1.8 and six after, the same bed:

| | `missing-sheet-check`, before | `missing-sheet-fixed`, after |
|---|---|---|
| Escalated, which is the right ending | 3 of 6 | 6 of 6 |
| Passed review with no blocker raised | 2 | 0 |
| Stopped | 1 | 0 |
| Blocker raised by the seat unaided | 4, one in the run that then stopped | 2 |
| Blocker raised after the check sent the concern back | not built | 4 |

So the fall from 3 of 3 to 1 of 3 was real and not noise, the cause was a concern filed where a blocker belonged and not the loss of the progress lines, and the seat on its own still gets it right only a third of the time: four of the six escalations are the check's doing. With the three Missing sheet runs inside the bed, the scenario has escalated nine times in nine since the fix.

What the bed says is still wrong, and what no item in this phase touches. Planted inconsistency passed first time in all three runs, where the scenario expects the Reviewer to fail the first draft on the 200 A against 225 A disagreement: the draft carries it and the Reviewer lets it through. Intake's grading refusals were 6 of 19 replies against 2 of 17, which may be noise. And the price is still a median 15 percent from the reference, which is the local Estimator misreading the drawings: with Claude in that seat the same measure is 0.3 percent over 18 runs. No deterministic check reaches a miscount, so that gap is a model choice or a split of the seat, not more engine work.

**1.11 The Reviewer is told what the engine checked, and never what to find.** Built 2026-09-19 (owner decision). The one review failure in the `figures-check-2` bed was false: a blocker saying the total did not equal the sum of its parts, with the correct sum written in its own evidence. Replayed four times as recorded, that review raised the false blocker again once. By the time a draft is reviewed every amount has been held against its source, so the Reviewer's context now ends with a short note of facts: every amount appears in something the Writer was given, Pricing's figures are the price tool's own, the tool's sum of material, markup and labour with the numbers, and what the engine did not check. The owner was explicit that the note must not discourage arithmetic findings, because the engine checks four totals and a document can do other sums, so it says the facts "do not limit what you may find" and a test refuses any wording such as do not raise. Replayed four times with the note, the false blocker did not recur.

**Planted inconsistency never fails its first review: investigated and taught at two seats, 2026-09-19.** The scenario expects the Reviewer to fail the first draft on the 200 A against 225 A main breaker and route it to the Estimator. Over 19 recorded first reviews with Gemma 4 12B in the seat, the defect is lost at every link: the Estimator raised the rating concern in 11, the first draft carried both ratings in 7, and the Reviewer raised it in none, including none of the 7 where both ratings were on the page in front of it. Its pass summary was word for word the same sentence in 7 of them. Replaying one of those 7 reviews from its recorded prompt and page images, with nothing else changed:

| Reviewer | Draft | Caught the rating, as major, routed to the Estimator |
|---|---|---|
| Gemma 4 12B, instructions as recorded | carries both ratings | 0 of 4 |
| Gemma 4 12B, the rule moved into the instructions as a first step | carries both ratings | 4 of 4 |
| Qwen 3.5 9B, instructions as recorded | carries both ratings | 4 of 4 |
| Gemma 4 12B, the rule as a first step | clean draft, no disagreement | 0 of 4 invented, 4 passes |
| Qwen 3.5 9B, instructions as recorded | clean draft, no disagreement | 1 of 4 failed on an invented arithmetic blocker |

So it is the wording and not the model. The rule already exists, as a paragraph under check 3 of the criteria file, a reference the seat is told to work through. Stated as the first thing the seat does, with the four things a resolved disagreement must contain, the same model applies it every time. Qwen catches it unprompted but invents arithmetic findings, so Gemma with the step is the better seat. The cost: a Reviewer that applies the rule also applies it to a disagreement the Estimator invents on a clean job, as one Clean run draft showed ("switch count on lighting plan (5 symbols) differs from panel schedule circuits (4)"), and that run would be sent back to the Estimator to recount, which is the right thing to happen and costs a retry. Genuine cases of that are about one or two in 83 local takeoffs on scenarios that plant no disagreement. The owner approved the Reviewer wording on 2026-09-19 (decision 1a) and it is applied.

The link before it was the Estimator, which raised the rating concern in 11 of those 19 runs. Its checklist before replying compared device counts with the panel schedule and said nothing about ratings; the rule sat only in the conventions file. One line was added to that checklist (owner decision 2a), tested first by replaying a real Planted inconsistency takeoff from its recorded prompt, drawings and tools:

| Estimator instructions | Scenario | Raised the rating concern with both values |
|---|---|---|
| as they stood | Planted inconsistency | 1 of 5 |
| with the checklist line | Planted inconsistency | 5 of 5, four of them naming both sheets in the sentence |
| with the checklist line | Clean run, where the ratings agree | 0 of 4 invented a disagreement |

The same finding twice in one day, at two seats: a rule kept in a reference file the seat is told to follow is applied now and then, and the same rule written as a step in the seat's own checklist is applied every time. The middle link, the Writer carrying the concern, was handled by item 1.3, which hands it the concerns to carry. Whether the whole chain now holds is measured by the Planted inconsistency runs in the `writer-reviewer-rerun` sweep: the scenario expects the first review to fail on the rating and the run to pass after one rework.

**1.12 An item the knowledge file answers needs no question.** Built 2026-09-19, found in the first hour of
the `writer-reviewer-rerun` sweep. Intake's instructions are emphatic that an answer in the client
knowledge file settles an item whatever the request says, that the seat grades it assumed, quotes the entry
in the note and asks nothing, and that rule 1 comes first. The engine then demanded a clarification for
that item anyway, because the check counted every not-pass item the checklist leaves open. So the seat was
refused for obeying its first rule: 9 refusals on 2026-09-19, every one on a correctly graded reply, one
per run on almost every run of the sweep. `closed_by_knowledge` now exempts a graded item whose note names
an entry the knowledge file really holds. The id must exist in the file, so a seat cannot close a gap by
claiming an answer that was never given.

Beside it, one piece of curation under roadmap decision 22. A Missing sheet run had written
`q_drawing_index: Assume E-003 is missing and will be provided later if needed` into the shared client
knowledge file at 00:40 that morning. Every later run of any scenario read it: Intake graded the drawing
index assumed "per knowledge file entry q_drawing_index" on the Clean run, and one Planted inconsistency
draft told the prospect in its executive summary that "the proposal assumes E-003 is missing and will be
provided later", on a job where no sheet is missing. That is the failure decision 22 describes, returning
by the same route, and the guard it set is curation: the line was removed, with the file kept as
`knowledge/fictional-prospect-ltd.md.bak-2026-09-19` beside it. The knowledge file is local and never
committed. A scenario that plants a defect will keep writing its answer to the shared file, so this needs
watching after any batch of Missing sheet runs, or a rule that an answer naming a sheet is not stored.

Both were found by reading one run of a sweep that had 37 runs still to go, and the sweep was stopped and
restarted rather than measure 37 Writers and Reviewers through a wasted Intake attempt and a false sentence
in every draft. Five runs were discarded, relabelled `writer-reviewer-rerun-pre-1.12`, about an hour.

**Queued, found during the `writer-reviewer-rerun` sweep and not fixed while it was in flight.** The
refusal for a dropped concern ends "naming the sheets E-002 and the values that disagree" whatever the
concern says. In 54 of the 62 such refusals on record no quoted concern was about disagreeing values, so
the seat was told to add something that does not exist: "Exit sign quantity includes a spare listed on
schedule" has no two values. The sentence was written for the rating disagreement, which is the case that
prompted the check, and it never generalised. Fix in `app/live/concerns.py` when the sweep ends, by naming
the sheets and quoting the concern's own words instead. Nothing runs against this until then, because
changing a check the Writer is measured against mid-sweep mixes code states, which cost three restarts of
the previous bed.

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
