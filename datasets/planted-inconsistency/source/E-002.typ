#import "sheet.typ": *

#show: sheet.with(number: "E-002", title: "Panel Schedule LP-1", scale: "Not to scale")

#let c(t) = text(size: 7.5pt)[#t]
#let h(t) = text(size: 7.5pt, weight: "bold")[#t]

// Circuit: (description, load VA, breaker). Odd circuits on the left, even on the right.
#let circuits = (
  "1": ("Lighting, reading room (16 troffers)", 640, "20A/1P"),
  "2": ("Receptacles, reading room west and north walls (5)", 900, "20A/1P"),
  "3": ("Lighting, children's area (12 troffers)", 480, "20A/1P"),
  "4": ("Receptacles, reading room south and east walls (5)", 900, "20A/1P"),
  "5": ("Lighting, lobby (4) and program room (6) (10 troffers)", 400, "20A/1P"),
  "6": ("Receptacles, children's area (6)", 1080, "20A/1P"),
  "7": ("Lighting, staff workroom (4), electrical room (1), washrooms (2) (7 troffers)", 280, "20A/1P"),
  "8": ("Receptacles, lobby (2) and program room (4)", 1080, "20A/1P"),
  "9": ("Exit signs (4) and emergency battery units (3)", 50, "20A/1P"),
  "10": ("Receptacles, staff workroom (6)", 1080, "20A/1P"),
  "11": ("Spare", 0, "20A/1P"),
  "12": ("Receptacles, electrical room (1) and washrooms (1)", 360, "20A/1P"),
  "13": ("Spare", 0, "20A/1P"),
  "14": ("Spare", 0, "20A/1P"),
  "16": ("Spare", 0, "20A/1P"),
)
#let row(n) = {
  let key = str(n)
  if key in circuits {
    let (d, va, b) = circuits.at(key)
    (c(key), c(d), c(if va == 0 { "" } else { str(va) }), c(b))
  } else {
    (c(key), c("Space"), c(""), c(""))
  }
}

#text(size: 12pt, weight: "bold")[PANEL SCHEDULE LP-1]
#v(4pt)
#table(
  columns: (1fr, 1fr, 1fr, 1fr), stroke: 0.5pt + ink, inset: 5pt,
  h[Panel: LP-1, new], h[Voltage: 120/208 V, 3 phase, 4 wire], h[Bus: 225 A], h[Main: 200 A main breaker],
  c[Type: 42-circuit panelboard], c[Mounting: surface], c[Location: electrical room], c[Fed from: transformer T1, sheet E-001],
  c[Interrupting rating: 10 kA], c[Breakers: bolt-on], c[Circuits in use: 11], c[Spare breakers: 4, not wired],
)
#v(6pt)
#grid(
  columns: (1fr, 1fr), gutter: 10pt,
  table(
    columns: (0.35fr, 3fr, 0.6fr, 0.7fr), stroke: 0.5pt + ink, inset: 3.2pt,
    h[Ckt], h[Description], h[VA], h[Breaker],
    ..range(1, 43, step: 2).map(row).flatten(),
  ),
  table(
    columns: (0.35fr, 3fr, 0.6fr, 0.7fr), stroke: 0.5pt + ink, inset: 3.2pt,
    h[Ckt], h[Description], h[VA], h[Breaker],
    ..range(2, 43, step: 2).map(row).flatten(),
  ),
)
#v(6pt)
#grid(
  columns: (1fr, 1fr), gutter: 10pt,
  table(
    columns: (2fr, 1fr), stroke: 0.5pt + ink, inset: 4pt,
    h[Load summary], h[VA],
    c[Lighting, 45 troffers at 40 W], c[1800],
    c[Exit signs and emergency battery units], c[50],
    c[Receptacles, 30 at 180 VA], c[5400],
    h[Total connected load], h[7250],
  ),
  [
    #text(size: 8pt, weight: "bold")[SCHEDULE NOTES]
    #set text(size: 7.5pt)
    + Provide a 20A/1P bolt-on breaker for every circuit in use and for every spare listed. Spaces have no breaker.
    + Device and fixture counts in the circuit descriptions match sheets E-101 and E-102.
  ],
)
