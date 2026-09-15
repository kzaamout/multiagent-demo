# Scenario datasets

Each subfolder is one selectable scenario in the Demo composer dropdown. A dataset is complete when it has:

- `README.md`: the scenario, the planted defects and where they are, the expected stage sequence, the expected termination exit, and what the presenter should say when the defect fires.
- `inputs/`: the request files (email or PDF) at the top level, and the drawing set under `inputs/drawings/` (PDF, one file per sheet or one multi-page file). Name each sheet file by its sheet number, for example `E-001.pdf`, because the tools refer to sheets by file name.
- `fixtures/`: `supplier-prices.csv` (item code, description, unit, price, supplier, lead time days), and any other fixture the specialists need.
- `knowledge.seed.md`: per-scenario copy of the knowledge file seed, so runs do not pollute each other.
- `brand.yaml`: `prospect_name`, `logo_path`, `primary_colour` for the deliverable cover.
- Live mode: a dataset runs live when it has at least one request file in `inputs/`, at least one PDF in `inputs/drawings/`, and `fixtures/supplier-prices.csv`. Otherwise it runs on the S1 stubs. `AGENT_MODE=stub` in `.env` forces stubs for every dataset.
- `golden-events.jsonl`: the recorded event log of a verified live run, used by the replay-and-compare tests. Compare stage sequence and termination exit; do not compare model text.

## Curation checklist (owner tasks)
- [ ] Choose a public electrical tender from Alberta Purchasing Connection or MERX as the base request text. Rewrite it into a fictional project so nothing is traceable to a real bidder. Keep the structure and language realistic.
- [ ] Source a small commercial electrical drawing set: legend, single-line, two or three panel schedules, two floor plans, a short Division 26 specification. Options: manufacturer or college training sets with permissive licences, or commission a drafting freelancer for a clean original set (preferred, and it allows planting defects cleanly).
- [ ] Build `supplier-prices.csv` from public catalogue pricing. Around 150 items covering everything the drawings call for. Three fictional supplier names matching the knowledge seed.
- [ ] Create the Clean run dataset first and verify a full pass live before deriving the others. A synthetic stand-in exists since 2026-09-15 (see `clean-run/README.md`); replace it with the curated set when available.
- [x] REMINDER, the trap: in Planted inconsistency, change the main breaker rating on one panel schedule to 200A while the single-line shows 225A for that panel. Document sheet numbers in that README. Also remove one required item (for example, exit signs) from the price fixture in Missing price. Never plant a defect without writing it in the README; anyone demoing must know where it is. Done 2026-09-15 on the synthetic set: E-002 200 A against E-001 225 A; Missing price lacks `Exit sign, LED`.
- [x] Missing sheet: delete the panel schedule for a panel that appears on the single-line. Done 2026-09-15 on the synthetic set: panel LP-2 with schedule E-003 absent.
- [x] Not ready: strip the deadline and the specification section from the request. Done 2026-09-15 on the synthetic set.
- [ ] Prospect own: leave empty apart from README and brand.yaml template. Populate per prospect, run Dry intake, record a clean run for Replay.
- [ ] Record `golden-events.jsonl` for each scenario after a verified live run.
- [ ] Fictional prospect brand for the five stock scenarios (name, simple logo).

The four failure datasets were derived from the synthetic Clean run set on 2026-09-15 (S3). Each keeps its own copy of the Typst sources in `source/`, so a curated owner set can replace any one of them. The five stock scenarios share the prospect Fictional Prospect Ltd. and therefore one knowledge file: run Clean run first, and the failure scenarios will not pause on the bid security question.
