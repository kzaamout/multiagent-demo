# Clean run

**Status.** Synthetic stand-in curated on 2026-09-15 so live runs can start before the owner's curated set exists. The project, owner, consultant, people, and addresses are fictional. Replace the `inputs/` and `fixtures/` contents with the owner's set when it arrives, keep this README in step, and re-record the golden log after a verified live run.

Scenario: complete request, complete drawing set, every bill of materials item priced.
Planted defects: none.
Open item by design: section 8 of the invitation says the Owner has not confirmed bid security and tenderers must confirm it before submitting. Intake raises this as the one blocking clarification, so the presenter answers it in the banner and the answer is appended to the knowledge file.
Expected sequence: Intake (Ready with assumptions, one blocking clarification on bid security, answered in the banner) > Plan > Work (Estimator, then Pricing) > Assemble > Review pass > Handoff.
Expected exit: reviewer_pass, retry count 0.
Presenter note: suggested answer "No bid security required." Run it a second time for the same prospect to show the question is not asked again; the stored answer appears as an accepted assumption. To hear the question again, delete `knowledge/fictional-prospect-ltd.md`. This dataset is also the source of the public Replay on the Introduction tab.

## Project

Quillbrook Public Library, main floor electrical fit-out. Tender QPLB-2026-07, closing 2:00 p.m. Mountain Time, 29 January 2027. If a demo falls after that date, move the date forward in `source/invitation-to-tender.typ` and recompile, or Intake grades the deadline as passed and the run ends not ready.

Scope: new 100 A feeder from a spare breaker in the existing MDP to a new 75 kVA transformer, a new 225 A 42-circuit panel LP-1, LED troffers, exit signs, emergency battery units, switches, receptacles, and branch wiring.

## Files

| Path | What it is |
|---|---|
| `inputs/invitation-to-tender.pdf` | Two pages: scope, tender documents, closing, addressee, form of tender (lump sum, no schedule of values), site visit, questions, no alternates, bid security open, insurance, schedule, contract |
| `inputs/division-26-specification.pdf` | Two pages: section list and requirements for conductors, raceways, transformer, panelboard, devices, lighting, emergency lighting |
| `inputs/drawings/E-000.pdf` | Drawing index, legend, abbreviations, materials schedule, general notes |
| `inputs/drawings/E-001.pdf` | Single-line diagram with feeder F1 length |
| `inputs/drawings/E-002.pdf` | Panel schedule LP-1 with device counts per circuit and load summary |
| `inputs/drawings/E-101.pdf` | Lighting plan, main floor |
| `inputs/drawings/E-102.pdf` | Power plan, main floor |
| `fixtures/supplier-prices.csv` | 52 catalogue items from Supplier A, B, and C, including near misses that must not be substituted |
| `source/*.typ` | Typst sources for every PDF |
| `brand.yaml` | Prospect brand for the deliverable cover |
| `golden-events.jsonl` | Golden log recorded from the stubbed run; stage sequence and exit match this scenario |

No `knowledge.seed.md`: runs use the workflow seed in `config/electrical-rfp/knowledge-file.seed.md` (markup 15 percent, labour 95 CAD per hour, Supplier A, B, C).

## Why this set stays clean

- The materials schedule on E-000 uses the exact descriptions and units of the price fixture, because the price lookup matches exact descriptions only. Every scheduled item has one listing, with lead times under the 28 day threshold.
- Every readiness checklist item is present except bid security: legend, index, revisions, single-line, a schedule for the only panel, a plan for the only level, Division 26, deadline, addressee, bid format, site visit, questions deadline, alternates, insurance.
- Ratings agree between E-001 and E-002. Counts on the plans match the circuit descriptions on E-002.
- Branch run lengths are stated as an allowance (25 m per circuit in use), so the Estimator counts rather than guesses.
- No fire-rated penetrations, no demolition, fire alarm and data by others, and secondary conductors are part of the transformer installation, so nothing needs a line the fixture lacks.
- The request asks for no schedule of values, which would need group markup arithmetic in the draft.

## Reference figures

For checking a live run by eye. The team's figures may differ slightly and still be correct; the golden comparison checks only the stage sequence and exit.

| Material | Counted | With waste | Unit price (CAD) | Supplier |
|---|---|---|---|---|
| 2x4 LED troffer | 45 | 46 | 142.00 | Supplier C |
| Exit sign, LED | 4 | 5 | 96.00 | Supplier C |
| Emergency battery unit with heads | 3 | 4 | 238.00 | Supplier C |
| Single-pole switch | 9 | 10 | 12.90 | Supplier B |
| Duplex receptacle, 15A, incl. box and device | 30 | 31 | 18.40 | Supplier B |
| 20A branch circuit breaker | 15 | 15 | 26.75 | Supplier A |
| 42-circuit panelboard, 225A, surface | 1 | 1 | 1,890.00 | Supplier A |
| Dry-type transformer, 75 kVA | 1 | 1 | 6,450.00 | Supplier A |
| Feeder, 3C plus ground, 100A in EMT | 18 m | 18.9 m | 48.50 | Supplier B |
| EMT 21 mm | 275 m | 288.8 m | 4.85 | Supplier B |
| Copper conductor #12 THHN | 825 m | 866.3 m | 0.92 | Supplier B |

With the app's quantity and price tools and the workflow seed rates: material 20,518.98, markup 3,077.85, labour 139.85 hours at 95 is 13,285.75, total 36,882.58 CAD excluding GST.

## Regenerating the PDFs

Typst 0.15.1 with Arial installed. From `datasets/clean-run`:

```
typst compile source/invitation-to-tender.typ inputs/invitation-to-tender.pdf
typst compile source/division-26-specification.typ inputs/division-26-specification.pdf
typst compile source/E-000.typ inputs/drawings/E-000.pdf
```

and the same for E-001, E-002, E-101, and E-102. `tests/integration/s2/test_clean_run_dataset.py` checks legibility, the materials schedule against the fixture, ratings, counts, and the open bid security item.
