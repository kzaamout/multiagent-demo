# Splitting the Estimator: what gets built

Approved 2026-09-19 (owner decisions 1a, 2a, 3a, 4a, 5b, 6a on `plan.md`). Three seats where there is one,
all visible on the roster, the Schedule Reader's model chosen by a sweep, golden logs re-recorded in this
slice, the appraisal workflow left to S8, and the disagreement between two sources raised by the engine
rather than noticed by a model.

## Why this shape

Almost every quantity in this job is written down, not drawn. The panel schedule's circuit descriptions say
"Lighting, reading room (16 troffers)" and "Receptacles, children's area (6)", and those figures sum to the
reference counts. Its header states the bus rating, the main breaker, the circuits in use and the spares.
The materials schedule on the index sheet gives each material's exact description and unit. Only switches
exist purely as symbols on a plan.

The failures follow that line exactly. Over 104 recorded takeoffs the seat had schedule-stated counts right
about two thirds of the time and the symbol count right 8 percent of the time. Worse, it read "42-circuit
panelboard" as 42 circuits in use where the schedule says 11, and once option B gave the calculator a
multiplier that single misreading became 3,307 metres of conduit against a reference of 289. A rule is only
as good as its count, and the count comes from reading a table while holding five drawings in mind.

So the split is by kind of evidence: one seat reads text, one looks at images, one assembles. It is not a
split by part of the building, which would leave every failure present in all three.

## The three seats

### Schedule Reader (`schedule_reader`)

| | |
|---|---|
| **Sees** | the brief, the text of every prepared sheet, the estimating conventions |
| **Does not see** | page images, prices, the knowledge file, the other specialists' output |
| **Tools** | `document_parse_pdf` |
| **Returns** | `materials`, `panels`, `scheduled_counts`, `feeders`, `sheets_read`, `concerns` |

- `materials`: one row per scheduled material, with the mark, the description and the unit exactly as the
  schedule writes them. This is the vocabulary every later seat uses.
- `panels`: one row per panel, carrying the bus rating and main breaker **as the single-line states them**
  and **as that panel's own schedule states them**, in separate fields, each with its sheet. It records
  both and reconciles nothing.
- `scheduled_counts`: every material the schedule states a count for, with the count and the sheet, summed
  from the circuit descriptions where that is where the figure lives.
- `feeders`: tag, description, length in metres, sheet.
- `concerns`: what it could not read, never a guess.

Refused when: it reports a figure for a sheet it did not parse; a rating is reported for a panel with no
sheet; the reply is not the shape.

### Plan Counter (`plan_counter`)

| | |
|---|---|
| **Sees** | the material list from the Schedule Reader, the legend as reference images, the plan sheets as images |
| **Does not see** | the Schedule Reader's counts, the brief's quantities, the conventions, prices |
| **Tools** | `vision_read_drawing` |
| **Returns** | `counts`, `sheets_read`, `notes` |

`counts` is one row per material per sheet, with **the number of marks it saw** and a confidence. It never
applies a waste factor, and it never reports a quantity: waste belongs to the calculator, and a seat that
counted 9 switches correctly and reported the 10 that waste makes of them would be scored as wrong twice
over, once for the count and once for doing the Assembler's job.

**The legend reaches it as images, by construction.** The legend is drawn on the index sheet, and the text
layer of that sheet keeps the words and loses the marks: the switch symbol survives as a bare dollar sign
and the troffer symbol as nothing at all. So a seat reading text can never learn what to look for, which is
why the one line that exists only as marks sits at 12 percent correct while everything stated in words
sits near 87. The engine finds the legend sheet from the prepared manifest, crops each symbol and its
meaning to its own reference image, and attaches those ahead of any plan sheet. Cropping matters: a whole
legend page at a tenth of the scale is not a reference. Nothing is curated by hand, because every real
drawing set carries a legend and a curated set of symbols would score well here and mean nothing on a
prospect's scan.

Measured before building, twelve replays of a recorded takeoff, six each way, with the whole legend page
attached rather than crops:

| | As the seat runs today | With the legend attached |
|---|---|---|
| Switch line left out of the takeoff | 3 of 6 | 0 of 5 |
| Counted within two of the nine on the plan | 1 of 3 counted | 3 of 5 counted |
| Median count when it counted | 15 | 11 |
| Runs that failed outright | 0 | 1 |

The commonest failure was not miscounting but giving up, and the legend stopped that: every replay
attempted the count and the counts moved towards the truth. It did not make them right, and it cost one
run of six, which is the argument for giving it to a seat that does nothing else rather than to today's
Estimator, already carrying five sheets and a strict reply shape.

**It must not see `scheduled_counts`.** If it can read the schedule's figure it will copy it, and the
comparison below becomes two seats agreeing with themselves. This is enforced where the context slice is
built, not asked for in the prompt.

Refused when: it reports a count for a sheet it did not open; it reports a material the Schedule Reader did
not list.

### Takeoff Assembler (`takeoff`)

| | |
|---|---|
| **Sees** | the brief, both specialist outputs, the engine's comparison, the estimating conventions, findings |
| **Does not see** | the drawings, in any form |
| **Tools** | `quantity_calculate` |
| **Returns** | today's Estimator shape: `headline`, `summary`, `bom`, `labour`, `assumptions`, `concerns`, or a `blocker` alone |

It applies the conventions' rules through the calculator, builds the bill of materials in the schedule's
words, and raises the blockers. Every check that stands on the Estimator today moves here unchanged: the
quantities and hours must be the calculator's, a blocker must not name a sheet the run holds, a concern
that names an absent sheet is a blocker, and a passed check is not a concern.

## What the engine does, because both numbers are now data

After both specialists complete, and before the Assembler is dispatched, the engine compares:

- **Each material's count**, the schedule's against the plan's. A difference beyond one unit becomes a
  concern naming both figures and both sources.
- **Each panel's ratings**, the single-line's against that panel's schedule. A difference becomes a concern
  naming both values and both sheets.

These are generated concerns, handed to the Assembler the way the Writer is handed the assumptions it must
carry. The Planted inconsistency scenario then turns on a comparison of two recorded numbers rather than on
a model noticing something, which is what it has failed to do in 4 of 14 runs even after this week's
changes. The Assembler may add concerns of its own; it may not drop a generated one.

## Build order

**M1. Schedule Reader alone.** Seat definition, context kinds for sheet text, reply model and checks,
instructions, roster entry, model entry. Measured by replaying a recorded Intake prompt's sheets: does it
return 45 troffers, 30 receptacles, 11 circuits in use, 225 A on E-001 and 200 A on E-002?

**M2. Plan Counter alone.** As above, with the material list as its input, and with the legend cropped to
one reference image per symbol. Measured on the same sheets: does it count 9 switches and 45 troffers, does
it report the marks it saw rather than a quantity, and does it never report a material it was not given?
The cropping is measured too, against the whole page, since the page alone moved the count only partway.

**M3. The Assembler and the comparison.** The Estimator's checks move across, the engine's comparison is
built, the Orchestrator's plan gains two sub-tasks with `depends_on`, the six stub files gain the new
seats, the golden logs are re-recorded with `scripts/regen_golden.py`, and the three front end files that
hardcode the roster order, colours and names are updated.

**M4. Measurement.** A sweep over the text-only models for the Schedule Reader, which is the first seat
that Llama 3.1 8B and DeepSeek R1 14B can hold, then a twelve-run bed on the same footing as
`estimator-tools` so the three beds compare directly.

## Tests

- Unit tests per reply check, each with its negative case: a count for an unparsed sheet, a rating with no
  sheet, a material the Schedule Reader never listed, a plan count that equals the schedule's.
- A unit test that the legend crops are found and attached from the prepared manifest, and that a drawing
  set whose index sheet carries no legend still dispatches the seat rather than failing.
- A unit test that the Plan Counter's context slice cannot contain `scheduled_counts`, since the whole
  comparison rests on it.
- Unit tests for the comparison: equal counts produce nothing, a difference of one unit produces nothing, a
  real difference produces a concern naming both figures, and a panel whose two ratings differ produces a
  concern naming both sheets.
- An integration test on the Planted inconsistency fixture: the comparison raises the rating concern
  without any model noticing it, the Assembler carries it, and the first review fails on it.
- Replay tests for each seat from recorded prompts, scored against the reference, before any live run.
- The golden replay tests, re-recorded, still comparing stage sequence and termination exit.

## Targets, fixed before the runs

For the local models on the Clean run family, against `estimator-tools` as the baseline.

| Measure | Today | After the split |
|---|---|---|
| Takeoff lines right | 57% | 90% |
| Conduit, conductor and breaker lines right | 50% | 90% |
| Circuits in use read correctly | not measured | every run |
| Median price difference from the reference | to be set by the bed | 3% |
| Priced runs within 5 percent | 6 of 42 | three quarters |
| Runs stopped in the work stage | 2 of 12 | no higher |
| Planted inconsistency first review fails on the defect | 8 of 14 | every run |

## What would make me stop

Three seats stopping more runs than one did would mean the handovers cost more than the focus gains, and
the right answer would be two seats, a Schedule Reader feeding today's Estimator. A Schedule Reader that
misreads the tables would be worse than the seat it replaces, since everything downstream would then be
confidently wrong; M1 measures that before anything else is built.

## What this does not fix

The symbol count, in full. Switches are marks on a plan, and the legend experiment moved the seat from
leaving them out to counting them badly. The Plan Counter does only that job, with the symbols in front of
it, which is the best chance it has. If it still cannot count marks then that line needs a different model
or a human, and no further splitting will help.
