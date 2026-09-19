# What happens at each seat, from request to report

Read from the code on 2026-09-18: `app/orchestrator/orchestrator.py` for the routes, `app/seats/definitions.py`
for what each seat may see, `app/live/replies.py` for the reply shapes and their checks, `app/live/source.py`
for the requirements, and `config/electrical-bid/seats/*.md` for the instructions. The electrical bid
workflow; the appraisal workflow swaps two specialists and keeps everything else.

Two loops run here. The outer one is the Orchestrator moving the run through six stages and deciding where
it goes next. The inner one is each seat's own reason-and-call-tools loop, bounded by a schema check and
three attempts. A seat cannot change stage, talk to the human, dispatch work or end the run.

## The main line

```
   request files + drawings
            |
            v
  [ engine ] prepare_documents           deterministic, no model
            |  splits binders into one file per sheet, reads title blocks
            |  a field it cannot read is recorded "unknown", never guessed
            v
  ( INTAKE ) Anna / Arjun
            |  grades the checklist, writes the brief, asks what is open
            +-- not ready ------------------> EXIT not_ready
            +-- dry intake requested -------> EXIT dry_intake
            +-- open question --------------> pauses, human answers, resumes
            v  ready / ready with assumptions
  ( ORCHESTRATOR ) Oscar / Olivia
            |  plans sub-tasks and their dependencies
            v
  ( ESTIMATOR ) Elias / Elena            ( PRICING ) Pavel / Priya
            |  reads sheets, builds BOM         |  prices every line from the fixture
            |  raises blockers / concerns       |  waits for the BOM
            +-- blocker needing a human --> pauses
            |      +-- escalate ------------> EXIT blocker_escalated
            |      +-- answer --------------> continues
            +-- blocker routed to intake --> back to INTAKE, once only
            v
  ( WRITER ) Wesley / Willa
            |  assembles the document, tags every figure, carries every concern
            |  draft compiles to PDF and page images, or it is not a version
            v
  ( REVIEWER ) Rafael / Rosa
            |  judges the compiled pages, never the working
            +-- pass -----------------------> HANDOFF
            +-- fail -----------------------> rework, budget permitting
            |      +-- route to work -------> ESTIMATOR or PRICING, then WRITER again
            |      +-- route to assemble ---> WRITER again
            +-- budget spent ---------------> HANDOFF with findings unresolved
            v
  ( HANDOFF ) the human decides
            +-- approve --------------------> EXIT reviewer_pass / retry_exhausted
            +-- edit -----------------------> one recompile as the human, then exit
            +-- reject ---------------------> exit with the notes recorded

  At any point: presenter stops -> EXIT stopped
                estimated spend passes the ceiling -> EXIT cost_ceiling
```

## Seat by seat

### Intake Analyst

| | |
|---|---|
| **Sees** | the request documents, the client knowledge file, the readiness checklist |
| **Does not see** | any other seat's output, the drawings as images, prices |
| **Tools** | `document_parse_pdf`, `document_extract_attachments` |
| **Returns** | `brief`, `readiness` (verdict plus a grade and note per checklist item), `clarifications` |
| **Refused when** | the verdict contradicts its own grades; an item is graded not-pass with no clarification and the checklist leaves it open; it grades fewer items than the checklist has; it passes the specification item when no specification was provided; the reply is not JSON |

The brief is the only thing the specialists ever see of the request, so anything Intake omits is invisible
downstream. An item the knowledge file already answers is not a gap, even when the request says it must be
settled, because a human answered it on an earlier run for this client.

### Orchestrator

| | |
|---|---|
| **Sees** | the brief, the run state, the readiness checklist, specialist outputs, findings, the draft |
| **Tools** | none, on purpose |
| **Returns** | a plan of sub-tasks with dependencies, and every routing decision |
| **Refused when** | a sub-task names a seat that cannot hold one, the ids are not unique, Assemble does not depend on every specialist, or Pricing does not wait for the Estimator |

It is the only component that changes stage, speaks to the human, writes the knowledge file or ends the run.

### Estimator

| | |
|---|---|
| **Sees** | the brief, the drawing sheets as images, the estimating conventions, findings routed to it |
| **Does not see** | prices, Pricing's output, the knowledge file |
| **Tools** | `vision_read_drawing`, `quantity_calculate` (which reads the unit labour hours table itself, so the seat never supplies an hour figure the table holds) |
| **Returns** | either a takeoff (`headline`, `summary`, `bom`, `labour`, `assumptions`, `concerns`) or a `blocker` alone |
| **Refused when** | quantities did not come from the calculator, or a quantity or labour figure differs from what the calculator returned; a concern describes something the conventions call a blocker; a blocker names a sheet the run holds; a concern says a sheet is missing and the run really does not hold it, which the conventions make a blocker; the reply is not JSON or lacks required fields |

A rating disagreement between sheets is a concern, carried forward. A sheet listed in the index but absent
from the set is a blocker. A sheet it has not opened yet is neither.

### Pricing

| | |
|---|---|
| **Sees** | the Estimator's output, the knowledge file, findings routed to it |
| **Does not see** | the drawings, the brief |
| **Tools** | `price_list_lookup` |
| **Returns** | `priced_bom`, `cost_summary`, `exceptions`, `rates_used` |
| **Refused when** | no price came from the lookup tool, or the call failed; a unit price, extension or total differs from what the tool returned; a line the tool returned unpriced carries a price; a quantity differs from the Estimator's |

An item the fixture does not carry comes back as an unpriced exception, which the Writer states as an
exclusion. It is never a price invented to fill the gap.

### Writer

| | |
|---|---|
| **Sees** | the brief, every specialist output labelled with its source id, the template, the knowledge file, findings, and the assumptions block prepared from the concerns |
| **Does not see** | the drawings, the price fixture, and it cannot ask a specialist anything |
| **Tools** | `template_render`, `compile_trigger` |
| **Returns** | `markdown`, `note`, `gaps` |
| **Refused when** | the body carries no provenance tags; a tag names a source it was not given; a tagged amount is not in the output it names; a dollar amount appears in nothing the Writer was given; a specialist concern is missing from Assumptions; the draft does not compile |

Every figure carries `{{value|src:id}}` naming the output it came from. A figure it cannot trace stays out
of the document. It never computes a total; it uses the one Pricing supplied.

### Reviewer

| | |
|---|---|
| **Sees** | the brief, the compiled page images and their text, the reviewer criteria, and a note of what the engine verified before the draft reached it (every amount traced to its source, and the price tool's own sum), stated as facts that do not limit what it may find. In the text each provenance marker is written in brackets after its figure, as in $79,063.75 [1], because extracted from the displayed page the superscript reads as extra digits of the figure |
| **Does not see** | the team's working, the specialist outputs, the drawings |
| **Tools** | none |
| **Returns** | `verdict` (pass or fail), `summary`, `findings` each with a severity and where it routes |
| **Refused when** | the reply is not the verdict shape |

It judges the finished document only, and cannot fix anything. A different model family from the Writer, so
agreement has to be earned. A model that cannot read images is refused the seat outright.

## Every way a run can end

| Exit | Reached when | Stage reached |
|---|---|---|
| `reviewer_pass` | the Reviewer passed a draft and the human decided at Handoff | handoff |
| `retry_exhausted` | the review budget ran out; the package goes to Handoff with findings unresolved | handoff |
| `not_ready` | Intake failed an item the checklist marks blocking | intake |
| `dry_intake` | the presenter asked for readiness only | intake |
| `blocker_escalated` | a specialist raised a blocker needing a human, and the human escalated it | work |
| `cost_ceiling` | estimated spend passed the per-run ceiling; nothing further is dispatched | any |
| `stopped` | the presenter stopped it, or a seat gave three invalid replies in a row | any |
| `single_complete` | the Single-model comparison run finished; one model, no review | n/a |

## Every backward route

Three, and only three.

**Review to Work.** A failed review with a blocker or major finding routed to `work`. The named specialist
reworks that finding only, then the Writer assembles again. Costs one retry.

**Review to Assemble.** A failed review whose findings are all writing problems, or minor. Only the Writer
runs again. Costs one retry.

**Work to Intake.** A specialist found the brief itself incomplete, not the drawings. Allowed once per run;
a second attempt becomes a blocker for the human instead. Intake runs again, the plan is rebuilt, and the
specialists restart.

Minor findings never cause a rework. They ride to Handoff as notes on the package.

## The three places a run waits for a person

1. **An open clarification at Intake.** The run pauses, the question carries a proposed default, and the
   answer is written to the client knowledge file so the same question is never asked twice.
2. **A blocker needing a human at Work.** Answer and the specialist continues, or escalate and the run ends.
3. **Handoff.** Approve, edit once as the human with a recompile, or reject with notes.

## What is checked without a model

Deterministic checks decide a reply as firmly as the schema does: quantities and labour hours equal what
the calculator returned, prices, extensions and totals equal what the fixture lookup returned, Pricing's
quantities are the Estimator's, every dollar amount in the draft exists in something the Writer was given,
every tag names a source that exists and holds the figure, every specialist
concern reaches Assumptions, the draft compiles, a blocker does not name a sheet the run holds, and the
readiness verdict follows the grades. A seat gets three attempts against these; the third failure stops the
run.
