# Splitting the Estimator: the evidence, and what I would do

Measured overnight on 2026-09-19 and 2026-09-20, unattended, at the owner's instruction to build the case
for or against the split before he decides. Everything here was run on the local seats as shipped, Qwen 3.5
9B throughout with Gemma 4 12B reviewing, and scored against `app/runs/reference.py`, which recomputes what
the job should cost from the quantities the dataset's README states, using the app's own calculator and
price lookup.

Nothing in this file is built into the engine. The prototype lives in `scripts/split_prototype.py` and
`specs/011-estimator-split/prototype/`, stands in for the Orchestrator, and touches no seat definition, no
roster, and no golden log.

## The recommendation, first

**Build the Schedule Reader. Do not build the Plan Counter or the Takeoff Assembler.** Two seats, not
three, and not for the reason the plan gave.

The gain is not accuracy. On the Clean run the two seat shape is better by one line in eleven, which over
nine runs against eight is suggestive and not conclusive, and on Planted inconsistency it is worse. The
gain is that **the disagreement the demo turns on becomes data instead of an observation**, and that a fact
the combined seat gets wrong 63 percent of the time is read correctly in 16 seconds by a seat that does
nothing else.

## What was measured

### The seat as it stands, twice over

Two twelve run beds, `stop-fixes` and `stop-fixes-2`, on the same code and the same four scenarios. The
first gave a median price 1.6 percent from the reference and I reported it. The second gave 2.0 percent
but with errors of 21, 27 and 38 percent among them, and three stopped runs against one.

Over all 24 runs the price errors are 0.3, 0.3, 0.9, 1.1, 1.4, 1.5, 1.6, 1.8, 2.0, 9.4, 21.0, 26.6, 27.2,
27.3 and 38.2 percent. The median of 1.8 describes none of them: nine runs are within two percent and five
are over twenty. **The seat is bimodal, not accurate.** Quoting its median, as I did, was misleading, and
one bed of twelve was not enough to act on.

### The three seat shape, as specified

Built and run three times over, with the handover corrected between each. It never worked.

- Given two independent counts and asked to choose, the Assembler emitted a bill of materials line for each
  and once a quantity of minus one.
- Given a settled list of quantities and told to copy them, it wrote 38.715 troffers where the list said 45,
  and 1.04 transformers where it said 1.
- Scores across eight runs: 7, 8, 3, 7, 2, 3, 2, and one outright failure.

A seat that must reproduce the strict takeoff shape from someone else's figures is not an easier job than
doing the takeoff. It is the same job with a worse starting point.

### The two seat shape

The Schedule Reader's figures handed to today's Estimator, which keeps its drawings and its tools.

| Clean run, takeoff lines right of 11 | One seat | Two seats |
|---|---|---|
| Runs | 8 | 9 |
| Scores | 8, 2, 7, 9, 10, 8, 9, 8 | 8, 10, 9, 10, 8, 8, 3, 9, 9 |
| Median | 8 | 9 |
| Mean | 7.6 | 8.2 |
| Nine or better | 3 of 8 | 5 of 9 |
| Worst | 2 | 3 |
| Labour hours within 5 percent | 3 of 7 | 4 of 9 |
| Typical seconds | 50 to 60 | 70 to 260 |

| Planted inconsistency, real drawings | One seat | Two seats |
|---|---|---|
| Scores | 8, 8, 10, 8 | 7, 9, 7, 3 |
| Median | 8 | 7 |

The two seat shape wins the Clean run and loses the planted one, on four runs each. On this evidence the
accuracy case is **not proven**, and I will not claim it.

### The Schedule Reader alone

This is where the evidence is unambiguous. Ten runs across both datasets, 16 to 28 seconds each.

| Fact | Right |
|---|---|
| Circuits in use, 11 | every run |
| Spare breakers, 4 | every run |
| Both panel ratings, each with its sheet | every run |
| Exit signs, 4 | every run |
| All eleven materials, with mark, description and unit | every run |
| Troffers, 45, summed across four circuit rows | most runs |
| Receptacles, 30 | about half |

On the real planted drawings it recorded, every time:

```
schedule E-002:    main breaker 200 A, bus 225 A
single-line E-001: main breaker 225 A, bus 225 A
```

Both values, both sheets, as fields. **The engine can then compare two numbers and write the concern
itself.** Today that depends on the Estimator noticing, which it does in 10 of 14 live runs, and on the
Reviewer acting on it, which it does in 8 of 10. Two model judgements in series, each about four fifths
reliable, where one comparison in code would do.

The facts it never gets wrong are the ones that do the most damage when wrong. The circuits in use drive
every conduit and wire figure through the conventions' rule; one run of the live bed read the panel's
42 circuit capacity instead of its 11 in use and produced 3,307 metres of conduit against a reference of
289, and a price 38 percent over.

### The Plan Counter

Six runs. Two did the work, taking 76 and 84 seconds, counted all eleven materials and got the troffers
exactly right. Four gave up in 9 to 28 seconds with zeros, a partial list, or nothing. The switch count,
the one line that exists only as marks, came out 9, then 19, against a true 9.

**And it is not needed on these drawings.** The Schedule Reader, which sees no images at all, counted the
switches correctly at nine by reading the dollar sign characters the symbols leave in the lighting plan's
text layer. A Plan Counter earns its place only on scanned drawings with no text layer, which is a real
prospect case and not one the demo set contains.

### The legend as reference images

The owner's suggestion, measured on twelve replays before any of this. Attaching the legend page changed
the failure from giving up to trying: the switch line was left out of 3 of 6 takeoffs without it and 0 of 5
with it, and the median count moved from 15 towards the 9 on the plan. It did not make the count right and
it cost one run of six. It belongs to a seat that does nothing but count, if one is ever built.

## What this cost, and what it says about handovers

Five faults, all mine, every one in the plumbing between seats and none in a seat's reading:

1. The truth table expected the two ratings to disagree on every dataset. They disagree only where the
   scenario plants it, so correct readings were scored wrong.
2. The schedule names a material by a mark, and the reply writes it as "M1 (troffers)". Matching the whole
   string found nothing, the settled list lost most of its materials, and the Assembler invented quantities.
3. A material with no stated count vanished from the handover instead of being passed on as undecided.
4. The counts were handed over without saying they were before waste, so the seat copied 45 troffers where
   the reference wants the calculator's 46.
5. The run folder supplying the prepared sheets was a Clean run while the dataset argument said Planted
   inconsistency, so four runs read the wrong drawings.

Each cost a batch and a restart. **The seats were more reliable than the plumbing between them**, and that
is the real cost of splitting: not the extra dispatch, but that every handover is a new contract with its
own units, its own names, and its own chances to be silently wrong. The figure checks this week gave tool
results that treatment. A seat to seat handover needs the same.

## What I would build

1. **The Schedule Reader as a real seat**, text only, no images, with `document_parse_pdf`. Its output is a
   typed reply, and the engine checks it the way it checks a tool result: every figure it reports must name
   a sheet it parsed, and the marks it uses must be the ones its own materials list declares.
2. **The engine compares the two ratings** and writes the concern. That makes the Planted inconsistency
   scenario deterministic at the point it still fails, which is the single most valuable outcome here.
3. **The Estimator keeps everything else**, including the drawings and the calculator, and receives the
   schedule's figures as counts before waste, stated as such.
4. **Nothing else.** No Plan Counter until a dataset without a text layer exists, and no Assembler at all.

Milestone one is the Schedule Reader measured alone against the same six facts, before it is wired in. If
it does not hold at six of six on the ratings and the circuits in use across a dozen runs, stop.

## What I would not claim

That this makes the price right. The switch count and the breaker count are missed by both shapes in almost
every run, and they are 2 of 11 lines. The honest summary is that the split makes one class of failure
impossible and leaves the rest where it is.
