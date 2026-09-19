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
| **Sees** | the material list from the Schedule Reader, the legend, the plan sheets as images |
| **Does not see** | the Schedule Reader's counts, the brief's quantities, the conventions, prices |
| **Tools** | `vision_read_drawing` |
| **Returns** | `counts`, `sheets_read`, `notes` |

`counts` is one row per material per sheet, with a count and a confidence. It counts and does nothing else.

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

**M2. Plan Counter alone.** As above, with the material list as its input. Measured on the same sheets:
does it count 9 switches and 45 troffers, and does it never report a material it was not given?

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

The symbol count. Switches are marks on a plan and nothing here makes them easier to see. The Plan Counter
does only that job, which is the best chance it has, but if it still reads 8 percent of switch counts
correctly then that line needs a different model or a human, and no further splitting will help.
