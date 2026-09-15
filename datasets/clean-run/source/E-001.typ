#import "sheet.typ": *

#show: sheet.with(number: "E-001", title: "Single-Line Diagram", scale: "Not to scale")

#let node(x, y, w, h, body, fill: white, dash: none) = place(top + left, dx: x, dy: y, box(
  width: w, height: h, stroke: (paint: ink, thickness: 1.4pt, dash: dash), fill: fill, inset: 6pt,
  align(center + horizon, body),
))
#let wire(x1, y1, x2, y2, dash: none) = place(top + left, line(start: (x1, y1), end: (x2, y2), stroke: (paint: ink, thickness: 1.6pt, dash: dash)))
#let label(x, y, body) = place(top + left, dx: x, dy: y, body)

#text(size: 12pt, weight: "bold")[SINGLE-LINE DIAGRAM]
#v(4pt)
#box(width: 100%, height: 150mm, {
  // Existing utility service and MDP, shown dashed.
  node(20mm, 8mm, 70mm, 22mm, [#text(weight: "bold")[UTILITY SERVICE (EXISTING)] \ 347/600 V, 3 phase, 4 wire], dash: "dashed")
  wire(55mm, 30mm, 55mm, 44mm, dash: "dashed")
  node(10mm, 44mm, 90mm, 34mm, [#text(size: 9pt, weight: "bold")[MDP (EXISTING)] \ Main distribution, 600 A bus \ 347/600 V, 3 phase, 4 wire \ Base building service room], dash: "dashed")
  // Existing spare breaker used for F1.
  node(60mm, 84mm, 36mm, 14mm, [#text(size: 7.5pt)[100 A / 3P \ existing spare]], fill: rgb("#f0f0f0"))
  wire(78mm, 78mm, 78mm, 84mm)
  wire(96mm, 91mm, 166mm, 91mm)
  // Feeder F1.
  label(108mm, 95mm, block(width: 50mm, text(size: 7.5pt)[
    #text(weight: "bold")[FEEDER F1, NEW] \
    Feeder, 3C plus ground, 100A in EMT \
    3 \#3 Cu plus \#8 Cu bond in 35 mm EMT \
    Length: 18 m, MDP to T1
  ]))
  // Transformer T1.
  node(166mm, 74mm, 62mm, 34mm, [#text(size: 9pt, weight: "bold")[T1, NEW] \ Dry-type transformer, 75 kVA \ 600 V delta primary \ 120/208 V wye secondary \ Floor mounted, electrical room])
  wire(228mm, 91mm, 260mm, 91mm)
  label(230mm, 78mm, block(width: 36mm, text(size: 7pt)[Secondary conductors \ part of T1 installation]))
  // Panel LP-1.
  node(260mm, 66mm, 58mm, 50mm, [#text(size: 9pt, weight: "bold")[LP-1, NEW] \ 42-circuit panelboard \ 225 A bus, 225 A main breaker \ 120/208 V, 3 phase, 4 wire \ Surface mounted, electrical room \ See schedule E-002])
  // Ground.
  wire(197mm, 108mm, 197mm, 122mm)
  wire(189mm, 122mm, 205mm, 122mm)
  wire(192mm, 125mm, 202mm, 125mm)
  wire(195mm, 128mm, 199mm, 128mm)
  label(208mm, 119mm, text(size: 7pt)[Bond to existing building ground bus])
  // Scope boundary.
  place(top + left, dx: 104mm, dy: 40mm, rect(width: 220mm, height: 100mm, stroke: (paint: rgb("#2b4c7e"), thickness: 1pt, dash: "dash-dotted")))
  label(108mm, 43mm, text(size: 7.5pt, fill: rgb("#2b4c7e"), weight: "bold")[SCOPE OF THIS CONTRACT])
})
#v(6pt)
#text(size: 9pt, weight: "bold")[NOTES]
#set text(size: 8pt)
+ Existing equipment is shown dashed and is not part of this contract, except the connection of feeder F1 to the existing spare 100 A / 3P breaker in MDP.
+ Ratings on this diagram agree with panel schedule LP-1, sheet E-002: 225 A bus, 225 A main breaker, 120/208 V, 3 phase, 4 wire.
+ Panel LP-1 is sized for a future second-floor fit-out. The main floor connected load is on sheet E-002.
