# Each seat in detail, on the Clean run

What every seat receives, does, calls, and returns, taken from one real recorded run of the Clean run
dataset, and what that dataset can and cannot tell you about the quality of each seat's work.

The run is `a509601c`, from the `stop-fixes` bed of 2026-09-19: every seat on Qwen 3.5 9B, the Reviewer on
Gemma 4 12B. It ended `reviewer_pass` with no rework, 9 of 11 takeoff lines matching the dataset's
reference quantities, and a price 1.4 percent under the reference. It is a good run, not a perfect one,
which makes it more useful here than a lucky one.

Where each piece lives in the repository:

| What | Where |
|---|---|
| What a seat may see, and its tools | `app/seats/definitions.py`, `SEAT_DEFINITIONS` |
| The prompt each seat runs on | `config/electrical-bid/seats/<seat>.md` |
| The reference files a seat is given | `config/electrical-bid/` (checklist, conventions, reviewer criteria, template) |
| The tools themselves | `app/live/strands_tools.py`, with the logic in `app/tools/` |
| The reply shape and its checks | `app/live/replies.py` |
| The checks that need recorded data | `app/live/figures.py`, `app/live/deterministic.py`, `app/live/concerns.py` |
| What the dataset expects of each seat | `app/runs/expectations.py` |
| What the job should cost | `app/runs/reference.py`, from `datasets/clean-run/README.md` |
| Every prompt and reply of a run | `runs/<id>/prompts/*.json`, `responses/`, `rejected/`, `tool-results.jsonl` |

## The run in one view

```
prepare_documents (engine, no model)  8 calls, 9 sheets from 7 files
  INTAKE      9 parse calls -> brief, readiness (ready_with_assumptions), 0 questions
  ORCHESTRATOR                -> plan: t1 takeoff, t2 pricing depends_on t1
  ESTIMATOR   5 drawing reads, 1 calculator call -> 11 bill of materials lines, 136.65 hours
  PRICING     1 price lookup            -> 11 priced, 0 exceptions, total 36,381.35 CAD
  WRITER      1 template call (errored), 1 compile -> draft v1, 24 provenance tags
  REVIEWER    3 page images + page text -> pass, no findings
  HANDOFF     approved by the sweep
```

---

## Intake, "Anna"

**Before it runs.** `prepare_documents` splits every PDF into one file per sheet and writes
`prepared/manifest.md` with each sheet's number, title, discipline, issue stamp, revision date and
legibility. It is deterministic, has no model call, and records `unknown` rather than guessing. In this run
it made 8 calls and produced 9 sheets from 7 files, with no unknown title block fields.

**Input.** A context slice of 7,399 characters: the prepared manifest and the request documents, the client
knowledge file, and the readiness checklist. It does not see the drawings as images, prices, or any other
seat's output.

**Task.** "Read prepared/manifest.md, then grade the request against every item of the readiness checklist,
including the drawing set and consistency checks, reading sheets with document_parse_pdf on
prepared/<sheet>.pdf. Raise one clarification for each item that is not pass."

**Tools.** `document_parse_pdf` nine times, once per prepared sheet and request document.

**Output.** A brief of fourteen fields (project, client, site address, scope, deliverables, bid format,
deadline, drawing set, drawing pages, specification, alternates, bonding, unreliable pages, knowledge used),
a readiness verdict with a grade and note for each of 21 checklist items, and a list of clarifications. Here:
client "Quillbrook Public Library Board", deadline "Friday, 29 January 2027 at 2:00 p.m. Mountain Time",
verdict `ready_with_assumptions`, one item not passed, and no questions asked.

**Refused when.** The verdict contradicts its own grades; an item is not pass with no clarification and the
checklist leaves it open and the knowledge file does not answer it; it grades fewer items than the checklist
has; it passes the specification item when no specification was provided; the reply is not JSON.

**What the Clean run tests.** One check: the verdict is `ready` or `ready_with_assumptions`. That is thin.
The scenario's real intent is richer and is not machine-checked: section 8 of the invitation says the Owner
has not confirmed bid security, and the dataset expects exactly one blocking clarification on it the first
time, and none on a later run because the answer is in the knowledge file. In this run the item was graded
`assumed` against the stored answer and no question was asked, which is the second-run behaviour and correct.

---

## Orchestrator, "Oscar" or "Olivia"

**Input.** The brief, the run state, the readiness checklist, the specialist outputs as they arrive,
findings, and the draft. **Tools.** None, deliberately.

**Output.** A plan of sub-tasks with dependencies, and every routing decision after it. Here: `t1` takeoff
to the Estimator with no dependency, `t2` pricing to Pricing depending on `t1`.

**Refused when.** A sub-task names a seat that cannot hold one, the ids are not unique, Assemble does not
depend on every specialist, or Pricing does not wait for the Estimator.

**What the Clean run tests.** The golden match: the stage sequence and the termination exit against
`datasets/clean-run/golden-events.jsonl`. It is the only seat whose check is the route itself.

---

## Estimator, "Elias" or "Elena"

**Input.** 6,972 characters: the brief, the drawing sheets (as a list it can open, not as images up front),
and the estimating conventions. It never sees prices, Pricing's output, or the knowledge file.

**Task.** "Sub-task t1: Takeoff from drawings."

**Tools.** `vision_read_drawing` five times, once per sheet, each returning the page as an image plus its
text layer. Then `quantity_calculate` once with 11 items, returning 11 lines and 136.65 hours. The
calculator reads the conventions' material table itself: it applies the unit labour hours, and the waste
class, and it multiplies a rule such as 25 metres for each of 11 circuits with 3 conductors each.

**Output.** A headline, a two sentence summary, a bill of materials of 11 lines each with group,
description, quantity, unit, drawing reference, confidence and a note, labour hours in total and per group,
assumptions, and concerns. Or a blocker alone.

**Refused when.** A quantity or labour figure is not the calculator's; a line in the bill of materials never
reached the calculator; a concern describes something the conventions call a blocker; a blocker names a
sheet the run holds; a concern names a sheet or a panel schedule the run does not hold, which is a blocker;
the takeoff is empty; the reply is not JSON or lacks a required field.

**What the Clean run tests.** One check: no blocker was raised. That is almost silent, and it is why the
price is measured separately.

**What the dataset actually knows, and where the quality lives.** The README's reference table gives the
counted quantity for all eleven materials, and `app/runs/reference.py` recomputes the job with the app's own
calculator and price lookup, reproducing the README's 139.85 hours and 36,882.58 CAD to the cent. Every run
is scored against it and the comparison is stored as `price_check` in `runs/<id>/metrics.json`. This run:

| The takeoff said | Reference | |
|---|---|---|
| Feeder, 3C plus ground, 100A in EMT, 18.9 m | 18.9 | right |
| EMT 21 mm, 288.8 m | 288.8 | right |
| Copper conductor #12 THHN, 866.3 m | 866.3 | right |
| 42-circuit panelboard, 1 | 1 | right |
| Dry-type transformer, 1 | 1 | right |
| 2x4 LED troffer, 46 | 46 | right |
| Exit sign, LED, 5 | 5 | right |
| Emergency battery unit, 4 | 4 | right |
| Duplex receptacle, 31 | 31 | right |
| 20A branch circuit breaker, 11 | 15 | wrong, it counted the circuits in use and omitted the 4 spares |
| Single-pole switch, 5 | 10 | wrong, there are 9 symbols on the lighting plan |
| Labour 136.65 hours | 139.85 | 2.3 percent low, following from the two wrong lines |

The two wrong lines are the two the drawings do not state in words. The breakers are "11 in use plus 4
spares" in the panel schedule's header, and the switches exist only as symbols on E-101.

---

## Pricing, "Pavel" or "Priya"

**Input.** 5,269 characters: the Estimator's output and the client knowledge file. It never sees the
drawings or the brief.

**Task.** "Sub-task t2: Price the BOM."

**Tools.** `price_list_lookup` once with 11 lines, the markup rate, the labour hours and the labour rate,
returning 11 priced and 0 exceptions plus the four totals.

**Output.** A priced bill of materials, a cost summary, exceptions, and the rates it used with their source.
Here: material 20,347.48, markup 3,052.12 at 15 percent, labour 12,981.75 for 136.65 hours at 95, total
36,381.35 CAD, no exceptions, both rates cited to the knowledge file.

**Refused when.** The lookup returned nothing in the turn, or the call failed; a unit price, an extension or
a total differs from the tool's to the cent; a line the tool returned unpriced carries a price; a quantity
differs from the Estimator's.

**What the Clean run tests.** One check: Pricing completed. The real assurance is the figure checks, which
hold every number against the tool's own result, so an invented price cannot survive whatever the dataset
says. Pricing has not been refused in any recent bed.

---

## Writer, "Wesley" or "Willa"

**Input.** 10,775 characters: the brief, every specialist output labelled with its source id, the response
template, the client knowledge file, and a block of the assumptions it must carry, prepared by the engine
from the specialists' concerns so that carrying them is copying rather than remembering.

**Task.** "Assemble draft v1 of the proposal."

**Tools.** `template_render` to fill the template, `compile_trigger` to commit and compile. In this run the
first template call errored on unknown section names and the seat recovered without a refusal.

**Output.** The full draft as markdown with provenance tags, a one line note, and any gaps. Here: 24 tags,
note "Schedule of values removed; all figures tagged."

**Refused when.** The body carries no usable provenance tags; a tag names a source it was not given; a
tagged amount is not in the output it names; a dollar amount appears in nothing it was given, except a
schedule of values subtotal the engine can recompute from the Estimator's groups and Pricing's extensions; a
specialist concern is missing from Assumptions; the draft does not compile.

**What the Clean run tests.** One check: a draft v1 was committed. Everything else about the Writer is
enforced by the checks above rather than by the dataset.

---

## Reviewer, "Rafael" or "Rosa"

**Input.** 10,226 characters plus 3 page images: the brief, the text of each compiled page, the reviewer
criteria, and a note of what the engine verified before the draft reached it, stated as facts with the price
tool's own sum and with no instruction about what to raise. In the page text each provenance marker is
written in brackets after its figure, from a second compile made only for reading, because on the displayed
page the superscript marker is glued to the figure and one price then reads as several. In this run the
markers were numbers, as in [1]; since 2026-09-21 they are letters, as in [a], on the page and in its text
(roadmap decision 36).

**Task.** "Review draft v1 against the brief and the reviewer criteria."

**Tools.** None. It cannot fix anything or rerun anything.

**Output.** A verdict, a summary, and findings, each with a severity, evidence, and where it routes. Here:
pass, no findings.

**Refused when.** The reply is not the verdict shape. It is the least constrained seat by design.

**What the Clean run tests.** One check, and the strictest in the dataset: the first review passed with no
blocker and no major finding. This is the seat where the Clean run does real work, because a Reviewer that
invents findings fails here immediately.

---

## What the Clean run does and does not measure

**It measures the route.** Intake to Plan to Work to Assemble to Review to Handoff, one pass, no rework, exit
`reviewer_pass` with zero retries. Any deviation shows up in the golden match and in the Orchestrator's
check.

**It measures restraint.** Four of its six checks are that nothing went wrong: no blocker, no failed review,
no missing draft. The scenario plants no defect, so a seat that invents one fails.

**It does not measure correctness of any number**, and by design: `app/runs/expectations.py` never looks at a
figure. That is why the price is a separate measure with its own section in `docs/model-performance.md`, and
why this run scores 6 of 6 seat checks while being wrong about two materials.

**Where to look for a seat's quality, in order.** The seat checks in `metrics.json` say whether it behaved.
The `price_check` in the same file says whether the numbers are right. The refusals in `seat-calls.jsonl`
say what it got wrong on the way and what it was told. The prompts and replies in `prompts/` and
`responses/` say exactly what it saw and wrote. Every one of those is recorded for every run.

**The other datasets exist because this one is silent on defects.** Planted inconsistency tests whether a
disclosed disagreement survives to the Reviewer, Missing price whether a gap is stated rather than invented,
Missing sheet whether a blocker stops the run, and Not ready whether Intake refuses to start. Their checks
in `app/runs/expectations.py` are correspondingly specific.
