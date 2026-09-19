# Splitting the Estimator: a plan for approval

Status: proposal, written 2026-09-19 for the owner's decision (roadmap decision 28: the Estimator stays on
a local model, and the seat is split before a hosted model is considered for it). Nothing here is built.

## Why this seat

The price is the one thing the team still gets wrong after phase 1 of `specs/010-seat-reliability`. Against
the reference price computed by `app/runs/reference.py`, a run with Qwen 3.5 9B as the Estimator is a
median 21.5 percent off over 94 priced runs, and 15 percent off on the latest bed. With Claude in the seat
it is 0.3 percent off over 18. Pricing and the Writer now copy their figures under exact checks, so what is
left is the takeoff: the list of materials and quantities the Estimator reads off the drawings. No check on
figures can reach a miscount, which is why this is a question of the seat's shape and not of more engine
work.

## Where the takeoff goes wrong

Each reference line of the Clean run family, by how the drawings supply it, and how often the takeoff had
it right. 104 takeoffs on Qwen 3.5 9B and 19 on Claude Sonnet 5.

| Material | How the drawings give the quantity | Qwen 3.5 9B | Claude |
|---|---|---|---|
| Dry-type transformer | one item on the single-line | 97% | 100% |
| Panelboard | one item on the single-line | 77% | 100% |
| Exit signs | stated in the panel schedule's text, "(4)" | 76% | 89% |
| Troffers | four figures in the schedule's text to add | 68% | 89% |
| Receptacles | eight figures in the schedule's text to add | 68% | 84% |
| Battery units | stated in the schedule's text, "(3)" | 63% | 89% |
| Feeder | a length written on the single-line | 60% | 94% |
| Conduit, EMT 21 mm | a rule: 25 m for each of 11 circuits in use | 18% | 100% |
| Conductor #12 | a rule: three conductors for each metre of that conduit | 16% | 100% |
| Branch breakers | 11 in use plus 4 spares, no waste | 9% | 78% |
| Switches | symbols on the lighting plan, nowhere in text | 8% | 42% |

Three different failures hide in the bottom four lines, and only one of them is about seeing.

1. **A rule the seat must apply and a calculator that cannot help.** The commonest wrong conduit figure is
   18.9, the feeder's length reused, in 16 takeoffs; the next is the line left out. `quantity_calculate` adds
   a list of counts and cannot multiply, so "11 circuits at 25 m, three conductors each" is arithmetic the
   seat does in its head, against its own instruction never to.
2. **A category the seat must choose.** The commonest wrong breaker figure is 16, in 45 of 104 takeoffs:
   the correct 15, sent to the calculator as a device, which carries 2 percent waste and rounds up. The
   reference carries none. The count was right and the waste class was a guess.
3. **Counting symbols on a plan.** Switches exist only as marks on E-101. This is the one line that is truly
   about vision, and it is hard for every model: Claude has it right 42 percent of the time.

Almost everything else is stated in the text layer of the schedules. On this drawing set the takeoff is
mostly reading a table and applying a rule, and the seat is asked to do both while also looking at five
page images, comparing ratings, watching for missing sheets, and writing a bill of materials in a strict
shape, in one reply.

## Three ways to change the seat

### A. Split by kind of evidence (recommended, after B)

Three seats where there is one, each seeing only what its job needs.

- **Schedule Reader.** Sees the text of the schedule sheets (the materials schedule, each panel schedule)
  and the single-line. No images. Returns the scheduled materials, the quantity each schedule states and
  where, each panel's ratings on both sheets, and the circuits in use and spare. Any text model can hold it.
- **Plan Counter.** Sees the plan sheets as images, and the list of materials to count from the Schedule
  Reader. Returns a count per material per sheet with a confidence. It counts and does nothing else.
- **Takeoff Assembler.** Sees both outputs and the conventions, no drawings. Applies the rules through the
  calculator, builds the bill of materials in the schedule's words, and raises the concerns and blockers.

What the engine then does in code, because both numbers are now data: compare the schedule's count with
the plan's count for each material, and compare each panel's rating between the single-line and its
schedule. A disagreement becomes a concern generated from the two figures instead of something a model
has to notice. The missing-sheet and rating checks built in phase 1 stay as they are.

- Handover accuracy: better than today's, because each handover is a typed list the engine can hold
  against the next seat's output, as it now does between the Estimator and Pricing. The risk moves to the
  Schedule Reader misreading a table, which a text model does far more reliably than a vision model reads
  a plan, and which a unit test on the dataset's own sheets can pin.
- Speed: three dispatches in place of one. The Schedule Reader and the Plan Counter can run together in the
  Orchestrator's plan, but one graphics card runs one model at a time, so expect the Estimator stage to
  take about one and a half times as long as today. The Plan Counter reads two or three sheets, not five.
- Cost to build: the largest of the three. Two new agent ids, seat definitions and context slices, stub
  agents and regenerated golden logs for every dataset, roster names and cards in the interface, and the
  appraisal workflow's equivalent seats to be decided. New ids are additions, so recorded runs keep
  replaying, but the goldens are re-recorded in the same slice (working rule 13).

### B. Keep one seat and move the two non-vision failures into the tool (do this first)

- Give `quantity_calculate` a way to state a rule: a quantity that is a count times an allowance times a
  number of conductors, with the tool doing the multiplication and showing it. The seat supplies "11
  circuits, 25 m each, 3 conductors" and copies the result, which the figure checks then hold it to.
- Let the conventions say which waste class each scheduled material belongs to, and let the calculator
  read it, as it now reads the unit hours. The seat stops choosing a category.

This is phase 1 work under another name: a calculation and a lookup handed back to code. It is two days at
most, needs no new seat, and the replay method used today can measure it before any live run. On the
figures above it addresses three of the four worst lines and leaves switches. It is also needed by option
A's Takeoff Assembler in any case, so it is not wasted if the split follows.

### C. Split by part of the building

One Estimator instance each for lighting, for power and devices, and for distribution and feeders, merged by
concatenation. Each reply is a third the size, which helps a small model with the output shape. But every
instance still reads images, applies rules, picks categories and counts symbols, so every failure above
survives in all three, and the handover has to de-duplicate lines that cross groups, such as conduit. I
do not recommend it.

## Recommendation

B now, measured, then A if the price is still outside the target. B is cheap and its evidence is direct. A
is the right shape for the seat but costs a slice of its own, and B will show how much of A is still needed:
if conduit, wire and breakers come right, what remains is the symbol count, and the split can be as small
as carving out the Plan Counter alone.

One caution the owner has raised before and which applies here. The schedules in the synthetic drawing
set carry clean text with counts in brackets. A prospect's drawings may be scans with no text layer at
all. Nothing in A or B parses the synthetic set's wording in code: the Schedule Reader is a model reading a
table, and the tool changes are arithmetic and a lookup in the conventions. A deterministic parser for
"(16 troffers)" would score well on these datasets and mean nothing on a real file, and is not proposed.

## How it will be tested

- Unit tests for each tool change, with the negative cases: a rule with a missing factor, a material the
  conventions give no waste class, a seat that passes a category the conventions contradict.
- Replay before live runs, as on 2026-09-19: the recorded Estimator prompt of a Clean run and of a Planted
  inconsistency run, five times each on the old tool and the new, scored line by line against the
  reference.
- Then a bed of twelve on the same seats and models as `figures-check-2`, so the two are comparable.

Targets, fixed before the runs, for the local Estimator on the Clean run family:

| Measure | Today | After B | After A |
|---|---|---|---|
| Takeoff lines right | 51 to 62% | 80% | 90% |
| Conduit, conductor and breaker lines right | 9 to 18% | 85% | 90% |
| Median price difference from the reference | 15 to 21% | 8% | 3% |
| Priced runs within 5 percent | 18 of 94 | half | three quarters |
| Runs stopped at the Estimator | 2 of 12 | no higher | no higher |
| Estimator stage wall time | as measured | no higher | up to 1.5 times |

What would make me stop: B leaving the rule lines under 50 percent right would mean the seat is not
applying the rule even when the tool does the arithmetic, which is a model limit and an argument for the
hosted model after all. A raising the stop rate would mean the handovers cost more than the focus gains.

## Questions for the owner

1. B first, then A only if needed, as recommended? Or A directly?
2. If A: are three seats acceptable on the roster and in the demo's story, or should the split stay
   invisible, shown as one Estimator card with three steps inside it?
3. If A: which local model for the Schedule Reader? It needs no vision, so Llama 3.1 8B and DeepSeek R1 14B
   become candidates, and the sweep would have to measure them.
4. Should the appraisal workflow get the same split when it is built, or is this electrical only?
5. Is a 1.5 times longer Estimator stage acceptable in a live demo?
6. Are the targets above the right ones, in particular 3 percent as the price difference worth stopping at?
7. Should takeoff accuracy stay out of the accuracy score for these measurements too, as decided on
   2026-09-19, and be read from the price tables only?
