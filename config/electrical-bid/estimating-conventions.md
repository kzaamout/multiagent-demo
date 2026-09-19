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
- Branch circuit wire: estimate 25 metres average run per circuit for commercial floor plates under 1000 square metres, 35 metres above, unless plans allow measurement. Mark confidence low when using this rule. Do not work the length out yourself: send quantity_calculate the number of circuits as the count, the metres per circuit as `each`, and the conductors per run as `times`, and copy what it returns.
- Conduit follows specification; if unspecified, EMT for interior branch, rigid PVC below grade, and flag the assumption.
- Add 5 percent waste on wire and conduit, 2 percent on devices and fixtures, none on equipment. quantity_calculate applies this itself from the category in the material table below, so the class a scheduled material belongs to is not a judgment the takeoff makes. A material the table does not list uses the category the call passes.

## Labour
- Use NECA-style unit labour hours per line where available in the conventions table below; otherwise estimate per line and mark confidence low.
- Roll up hours per BOM group. Apply a crew composition and productivity factor from the knowledge file; if absent, assume 1 journeyman to 1 apprentice and productivity 1.0, and flag it.
- Report total hours, and hours per group, separately from cost. Pricing owns cost.

## Ambiguities and blockers
Raise a blocker, do not guess, when:
- A panel appears on the single-line with no schedule, or a schedule references a panel not on the single-line.
- A level or area named in scope has no floor plan.
- A page is marked unreliable by Intake and a needed quantity depends on it.
Raise a concern (proceed, but flag) when a quantity is inferred by rule rather than counted, when a specification is absent and a default material was used, or when a main breaker or bus rating disagrees between the single-line and a schedule. For a rating disagreement, proceed on the single-line value, and state both values and both sheet references in the concern.

## Output format
Structured BOM as described, followed by a labour summary, followed by a list of assumptions and a list of concerns, each with a drawing reference. Every figure must be traceable to a sheet or to a named rule in this file.

## Materials: unit labour hours and waste class (demo table, illustrative)
quantity_calculate reads this table itself and applies it to every line whose description it finds here: the hours, and the category that sets the waste. A line it cannot find takes no hours from the table, carries confidence low, and uses the category the call passes.

| Item | Unit | Category | Hours |
|---|---|---|---|
| Duplex receptacle, 15A, incl. box and device | each | device | 0.5 |
| Single-pole switch | each | device | 0.4 |
| 2x4 LED troffer | each | fixture | 0.75 |
| Exit sign, LED | each | fixture | 0.6 |
| Emergency battery unit with heads | each | fixture | 1.0 |
| 20A branch circuit breaker, install | each | equipment | 0.3 |
| 42-circuit panelboard, 225A, surface | each | equipment | 8.0 |
| Dry-type transformer, 75 kVA | each | equipment | 12.0 |
| EMT 21 mm, run | metre | conduit | 0.12 |
| Copper conductor #12 THHN | metre | wire | 0.02 |
| Feeder, 3C plus ground, 100A in EMT | metre | conduit | 0.45 |
