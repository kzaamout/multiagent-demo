# Readiness checklist: electrical RFP

Read by the Intake Analyst. Grade every item as present, present with concerns, or missing. Missing items marked (blocking) produce a Not ready verdict. Missing items marked (default) produce a clarification with the stated default, non-blocking unless the request itself says otherwise. Report confidence per drawing page.

## Request document
- Scope statement describing the electrical work requested (blocking)
- Submission deadline, present and in the future (blocking)
- Site or project address (default: use the address on the drawings if present, otherwise blocking)
- Owner or general contractor identified (default: "as stated in the request header")
- Bid format: lump sum, unit price, or schedule of values (default: lump sum)
- Bid security requirement stated, such as a bid bond (default: none required, flag for Handoff)
- Insurance requirements stated (default: none required, flag for Handoff)
- Site visit or pre-bid meeting date (default: none)
- Questions deadline or RFI process (default: none)
- Required alternates or unit prices (default: none)

## Drawing set
- Electrical legend and abbreviations sheet, typically E0 series (default: use standard IEEE/CSA symbols, flag)
- Single-line diagram (blocking)
- Panel schedules for every panel shown on the single-line (a panel with no schedule is a concern for the Estimator, who raises the blocker in Work; not a blocker at Intake)
- Electrical floor plans, power and lighting, for every level (blocking if any level referenced in scope has no plan)
- Specifications or a specification section list for Division 26 (blocking if absent and scope references specifications)
- Drawing index matching the sheets provided (default: infer index from sheet titles, flag)
- Revision and issue date on each sheet (default: treat all as issued for tender, flag)

## Consistency checks
- Every panel named on a panel schedule appears on the single-line, and vice versa
- Main breaker and bus ratings agree between the single-line and each panel schedule (any disagreement is a concern for the Estimator, not a blocker at Intake)
- Voltage and phase consistent across single-line, schedules, and floor plan notes
- Deadline consistent between request body and any attached instructions

## Legibility
- Each page receives a confidence score 0 to 1 from the parsing tool. Pages below 0.7 are listed as unreliable in the readiness verdict so the Estimator can distrust them and raise blockers rather than guess.

## Verdict rules
- Any blocking item missing: Not ready. List every missing item.
- No blocking items missing, one or more defaults used or concerns raised: Ready with assumptions. List every default and concern.
- Everything present, no concerns: Ready.
