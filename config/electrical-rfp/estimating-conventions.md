# Estimating conventions: electrical

Read by the Estimator. These are demo conventions modelled on common commercial electrical practice in Alberta. They are not a substitute for the contractor's own standards; production use replaces this file with the client's conventions.

## Reading order
1. Legend, to confirm symbols.
2. Single-line, to establish the distribution tree: service, main, distribution panels, branch panels, transformers, feeders.
3. Panel schedules, to count circuits, breaker sizes, and loads per panel.
4. Floor plans, to count devices, fixtures, and to measure or estimate branch circuit runs.
5. Specifications, to confirm materials, conduit type, and any owner-specified manufacturers.

## Bill of materials structure
Group lines under: Service and distribution; Feeders; Branch circuits and devices; Lighting; Fire alarm and low voltage (only if in scope); Grounding and bonding; Miscellaneous (firestopping, demolition, testing). Every line: description, quantity, unit, drawing reference (sheet and detail), confidence (high, medium, low), and a note if quantity was inferred rather than counted.

## Quantity rules
- Devices and fixtures are counted from floor plans, cross-checked against panel schedules where circuits are labelled.
- Feeder lengths: if not dimensioned, estimate from plan scale plus 10 percent for vertical drops and terminations, and mark confidence medium.
- Branch circuit wire: estimate 25 metres average run per circuit for commercial floor plates under 1000 square metres, 35 metres above, unless plans allow measurement. Mark confidence low when using this rule.
- Conduit follows specification; if unspecified, EMT for interior branch, rigid PVC below grade, and flag the assumption.
- Add 5 percent waste on wire and conduit, 2 percent on devices.

## Labour
- Use NECA-style unit labour hours per line where available in the conventions table below; otherwise estimate per line and mark confidence low.
- Roll up hours per BOM group. Apply a crew composition and productivity factor from the knowledge file; if absent, assume 1 journeyman to 1 apprentice and productivity 1.0, and flag it.
- Report total hours, and hours per group, separately from cost. Pricing owns cost.

## Ambiguities and blockers
Raise a blocker, do not guess, when:
- A panel appears on the single-line with no schedule, or a schedule references a panel not on the single-line.
- Main breaker or bus rating disagrees between the single-line and a schedule (state both values and both sheet references).
- A level or area named in scope has no floor plan.
- A page is marked unreliable by Intake and a needed quantity depends on it.
Raise a concern (proceed, but flag) when a quantity is inferred by rule rather than counted, or when a specification is absent and a default material was used.

## Output format
Structured BOM as described, followed by a labour summary, followed by a list of assumptions and a list of concerns, each with a drawing reference. Every figure must be traceable to a sheet or to a named rule in this file.

## Unit labour hours (demo table, illustrative)
| Item | Unit | Hours |
|---|---|---|
| Duplex receptacle, 15A, incl. box and device | each | 0.5 |
| Single-pole switch | each | 0.4 |
| 2x4 LED troffer | each | 0.75 |
| Exit sign, LED | each | 0.6 |
| Emergency battery unit with heads | each | 1.0 |
| 20A branch circuit breaker, install | each | 0.3 |
| 42-circuit panelboard, 225A, surface | each | 8.0 |
| Dry-type transformer, 75 kVA | each | 12.0 |
| EMT 21 mm, run | metre | 0.12 |
| Copper conductor #12 THHN | metre | 0.02 |
| Feeder, 3C plus ground, 100A in EMT | metre | 0.45 |
