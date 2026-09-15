#import "sheet.typ": *

#show: sheet.with(number: "E-000", title: "Legend, Drawing Index, General Notes", scale: "Not to scale")

#let head(t) = text(size: 11pt, weight: "bold")[#t]
#let cell(t) = text(size: 8pt)[#t]
#let hcell(t) = text(size: 8pt, weight: "bold")[#t]

#grid(
  columns: (1fr, 1fr), gutter: 22pt,
  [
    #head[DRAWING INDEX]
    #v(2pt)
    #table(
      columns: (0.8fr, 3fr, 0.6fr, 1.2fr), stroke: 0.5pt + ink, inset: 4pt,
      hcell[Sheet], hcell[Title], hcell[Rev], hcell[Issued],
      cell[E-000], cell[Legend, Drawing Index, General Notes], cell[0], cell[2026-09-08],
      cell[E-001], cell[Single-Line Diagram], cell[0], cell[2026-09-08],
      cell[E-002], cell[Panel Schedule LP-1], cell[0], cell[2026-09-08],
      cell[E-003], cell[Panel Schedule LP-2], cell[0], cell[2026-09-08],
      cell[E-101], cell[Lighting Plan, Main Floor], cell[0], cell[2026-09-08],
      cell[E-102], cell[Power Plan, Main Floor], cell[0], cell[2026-09-08],
    )
    #v(10pt)
    #head[LEGEND]
    #v(2pt)
    #table(
      columns: (1.1fr, 3fr), stroke: 0.5pt + ink, inset: 5pt, align: horizon,
      hcell[Symbol], hcell[Meaning],
      box(width: 14mm, height: 7mm, { place(dx: 1mm, dy: 1.3mm, rect(width: 10.8mm, height: 5.4mm, stroke: 0.9pt + ink)); place(dx: 1mm, dy: 1.3mm, line(start: (0pt, 0pt), end: (10.8mm, 5.4mm), stroke: 0.6pt + ink)) }), cell[Type M1: 2x4 LED troffer, recessed in T-bar ceiling],
      box(width: 14mm, height: 7mm, place(dx: 2mm, dy: 1.3mm, box(width: 9.9mm, height: 5.4mm, stroke: 0.9pt + ink, fill: rgb("#dcdcdc"), align(center + horizon, text(size: 5.5pt, weight: "bold")[EXIT])))), cell[Type M2: exit sign, LED, running man pictogram],
      box(width: 14mm, height: 7mm, { place(dx: 2mm, dy: 1.3mm, rect(width: 9mm, height: 5.4mm, stroke: 0.9pt + ink)); place(dx: 2.7mm, dy: 2mm, circle(radius: 1.26mm, fill: ink)); place(dx: 7.9mm, dy: 2mm, circle(radius: 1.26mm, fill: ink)) }), cell[Type M3: emergency battery unit with two remote-capable heads],
      text(size: 11pt, weight: "bold")[\$], cell[Type M4: single-pole switch, 15A, 1200 mm above finished floor],
      box(width: 14mm, height: 7mm, { place(dx: 4.3mm, dy: 0.8mm, circle(radius: 2.7mm, stroke: 0.9pt + ink)); place(dx: 6.1mm, dy: 0mm, line(start: (0pt, 0pt), end: (0pt, 7mm), stroke: 0.8pt + ink)); place(dx: 7.9mm, dy: 0mm, line(start: (0pt, 0pt), end: (0pt, 7mm), stroke: 0.8pt + ink)) }), cell[Type M5: duplex receptacle, 15A, 125V, CSA 5-15R, 400 mm above finished floor],
      text(size: 7pt, fill: rgb("#2b4c7e"), weight: "bold")[LP-1-1], cell[Circuit tag: panel LP-1, circuit 1],
      box(width: 14mm, height: 7mm, place(dx: 1mm, dy: 3.5mm, line(start: (0pt, 0pt), end: (12mm, 0pt), stroke: (paint: ink, thickness: 1.2pt, dash: "dashed")))), cell[Feeder route, see single-line diagram],
    )
    #v(10pt)
    #head[ABBREVIATIONS]
    #v(2pt)
    #text(size: 8pt)[
      AFF: above finished floor. EMT: electrical metallic tubing. MDP: main distribution panel. THHN: thermoplastic high heat-resistant nylon-coated conductor. Cu: copper. 1P, 3P: one pole, three pole. VA: volt-amperes. kVA: kilovolt-amperes.
    ]
  ],
  [
    #head[MATERIALS SCHEDULE]
    #v(2pt)
    #text(size: 7.5pt)[Descriptions are the Owner's standard material descriptions for this project. Use them as written.]
    #v(2pt)
    #table(
      columns: (0.5fr, 3fr, 0.8fr, 1fr), stroke: 0.5pt + ink, inset: 4pt,
      hcell[Mark], hcell[Description], hcell[Unit], hcell[Section],
      cell[M1], cell[2x4 LED troffer], cell[each], cell[26 51 00],
      cell[M2], cell[Exit sign, LED], cell[each], cell[26 52 00],
      cell[M3], cell[Emergency battery unit with heads], cell[each], cell[26 52 00],
      cell[M4], cell[Single-pole switch], cell[each], cell[26 27 26],
      cell[M5], cell[Duplex receptacle, 15A, incl. box and device], cell[each], cell[26 27 26],
      cell[M6], cell[20A branch circuit breaker], cell[each], cell[26 24 16],
      cell[M7], cell[42-circuit panelboard, 225A, surface], cell[each], cell[26 24 16],
      cell[M8], cell[Dry-type transformer, 75 kVA], cell[each], cell[26 22 13],
      cell[M9], cell[Feeder, 3C plus ground, 100A in EMT], cell[metre], cell[26 05 00],
      cell[M10], cell[EMT 21 mm], cell[metre], cell[26 05 33],
      cell[M11], cell[Copper conductor \#12 THHN], cell[metre], cell[26 05 19],
      cell[M12], cell[30-circuit panelboard, 100A, surface], cell[each], cell[26 24 16],
      cell[M13], cell[Feeder, 4C plus ground, 100A in EMT], cell[metre], cell[26 05 00],
      cell[M14], cell[100A 3-pole breaker], cell[each], cell[26 24 16],
    )
    #v(10pt)
    #head[GENERAL NOTES]
    #v(2pt)
    #set text(size: 8pt)
    + The work is the electrical fit-out of the main floor of an existing single-storey building. The base building shell is complete. There is no demolition.
    + Supply and install materials as listed on the materials schedule and specified in Division 26. Conduit fittings, boxes, supports, and connectors are incidental to the listed materials and are not measured separately.
    + Branch circuits: three \#12 THHN copper conductors (line, neutral, bond) in 21 mm EMT per circuit. Circuit runs are not dimensioned. Allow an average run of 25 m per branch circuit shown in use on panel schedule LP-1. Spare breakers are not wired.
    + Feeder F1 is dimensioned on the single-line diagram.
    + Transformer T1 secondary conductors to panel LP-1, and the T1 bonding connection to the existing building ground bus, are part of the transformer installation.
    + The work does not penetrate any fire-rated separation.
    + Fire alarm, data, and security systems are by others and are not part of this contract.
    + Coordinate a shutdown of the existing MDP with the Owner, outside library opening hours, to connect feeder F1 to the existing spare breaker.
    + Test every circuit and provide a typed panel directory for LP-1.
  ],
)
