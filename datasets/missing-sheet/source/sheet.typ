// Shared frame for the Clean run drawing set. Fictional project; see ../README.md.

#let project-name = "Quillbrook Public Library, Main Floor Electrical Fit-out"
#let project-address = "2150 Heron Crescent, Quillbrook, Alberta"
#let owner-name = "Quillbrook Public Library Board"
#let consultant = "Brightline Consulting Engineers Ltd."
#let project-number = "BCE-26-114"
#let issue-date = "2026-09-08"

#let ink = rgb("#1a1a1a")
#let faint = rgb("#8a8a8a")

// Metres to page length on the floor plans: 1 m = 9 mm.
#let m(v) = v * 9mm

#let title-block(number, title, scale) = block(
  width: 100%, height: 100%, stroke: 0.8pt + ink, inset: 0pt,
  grid(
    columns: 1fr,
    rows: (auto, auto, auto, 1fr, auto, auto, auto),
    block(inset: 8pt, width: 100%, stroke: (bottom: 0.5pt + ink))[
      #text(size: 11pt, weight: "bold")[#consultant] \
      #text(size: 7.5pt)[Electrical engineering. Project #project-number]
    ],
    block(inset: 8pt, width: 100%, stroke: (bottom: 0.5pt + ink))[
      #text(size: 7pt, fill: faint)[PROJECT] \
      #text(size: 10pt, weight: "bold")[#project-name] \
      #text(size: 8pt)[#project-address] \
      #v(3pt)
      #text(size: 7pt, fill: faint)[OWNER] \
      #text(size: 9pt)[#owner-name]
    ],
    block(inset: 8pt, width: 100%, stroke: (bottom: 0.5pt + ink))[
      #text(size: 7pt, fill: faint)[REVISIONS] \
      #table(
        columns: (0.5fr, 2fr, 1.2fr), stroke: 0.4pt + ink, inset: 3pt,
        text(size: 7pt, weight: "bold")[Rev], text(size: 7pt, weight: "bold")[Description], text(size: 7pt, weight: "bold")[Date],
        text(size: 7.5pt)[0], text(size: 7.5pt)[Issued for tender], text(size: 7.5pt)[#issue-date],
      )
    ],
    [],
    block(inset: 8pt, width: 100%, stroke: (top: 0.5pt + ink))[
      #text(size: 7pt, fill: faint)[SCALE] \
      #text(size: 9pt)[#scale]
    ],
    block(inset: 8pt, width: 100%, stroke: (top: 0.5pt + ink))[
      #text(size: 7pt, fill: faint)[SHEET TITLE] \
      #text(size: 11pt, weight: "bold")[#title]
    ],
    block(inset: 8pt, width: 100%, stroke: (top: 0.5pt + ink), fill: rgb("#f2f2f2"))[
      #text(size: 7pt, fill: faint)[SHEET] \
      #text(size: 26pt, weight: "bold")[#number]
    ],
  ),
)

#let sheet(number: "", title: "", scale: "As noted", body) = {
  set page(width: 17in, height: 11in, margin: 0.35in)
  set text(font: "Arial", size: 8pt, fill: ink)
  block(
    width: 100%, height: 100%, stroke: 1.2pt + ink,
    grid(
      columns: (1fr, 3.1in),
      block(width: 100%, height: 100%, inset: 14pt, body),
      title-block(number, title, scale),
    ),
  )
}

// Floor plan primitives. Coordinates in metres from the north-west corner.
#let at(x, y, body) = place(top + left, dx: m(x), dy: m(y), body)

#let room(x, y, w, h, name, area: none) = {
  at(x, y, rect(width: m(w), height: m(h), stroke: 1.6pt + ink))
}

#let room-label(x, y, name, area) = at(x, y, box(
  inset: 2pt, fill: white,
  align(center)[#text(size: 8.5pt, weight: "bold")[#upper(name)] \ #text(size: 6.5pt)[#area m²]],
))

// 2x4 troffer, drawn 1.2 m by 0.6 m with a diagonal.
#let troffer(x, y) = {
  at(x - 0.6, y - 0.3, rect(width: m(1.2), height: m(0.6), stroke: 0.9pt + ink))
  at(x - 0.6, y - 0.3, line(start: (0pt, 0pt), end: (m(1.2), m(0.6)), stroke: 0.6pt + ink))
}

#let exit-sign(x, y) = at(x - 0.55, y - 0.3, box(
  width: m(1.1), height: m(0.6), stroke: 0.9pt + ink, fill: rgb("#dcdcdc"),
  align(center + horizon, text(size: 5.5pt, weight: "bold")[EXIT]),
))

#let ebu(x, y) = {
  at(x - 0.5, y - 0.3, rect(width: m(1.0), height: m(0.6), stroke: 0.9pt + ink))
  at(x - 0.42, y - 0.22, circle(radius: m(0.14), fill: ink))
  at(x + 0.14, y - 0.22, circle(radius: m(0.14), fill: ink))
}

#let switch(x, y) = at(x - 0.25, y - 0.35, text(size: 10pt, weight: "bold")[\$])

#let receptacle(x, y) = {
  at(x - 0.3, y - 0.3, circle(radius: m(0.3), stroke: 0.9pt + ink, fill: white))
  at(x - 0.1, y - 0.42, line(start: (0pt, 0pt), end: (0pt, m(0.84)), stroke: 0.8pt + ink))
  at(x + 0.1, y - 0.42, line(start: (0pt, 0pt), end: (0pt, m(0.84)), stroke: 0.8pt + ink))
}

#let tag(x, y, label) = at(x, y, text(size: 6pt, fill: rgb("#2b4c7e"), weight: "bold")[#label])

#let door(x, y, horizontal: true) = if horizontal {
  at(x, y - 0.12, rect(width: m(1.0), height: m(0.24), fill: white, stroke: none))
} else {
  at(x - 0.12, y, rect(width: m(0.24), height: m(1.0), fill: white, stroke: none))
}

#let north-arrow(x, y) = at(x, y, align(center)[
  #polygon(fill: ink, (m(0.5), 0pt), (m(1.0), m(1.4)), (m(0.5), m(1.0)), (0pt, m(1.4))) \
  #text(size: 8pt, weight: "bold")[N]
])

#let scale-bar(x, y) = {
  at(x, y, rect(width: m(5), height: m(0.25), fill: ink, stroke: 0.6pt + ink))
  at(x + 5, y, rect(width: m(5), height: m(0.25), fill: white, stroke: 0.6pt + ink))
  at(x - 0.1, y + 0.45, text(size: 6.5pt)[0])
  at(x + 4.8, y + 0.45, text(size: 6.5pt)[5])
  at(x + 9.6, y + 0.45, text(size: 6.5pt)[10 m])
  at(x, y - 0.8, text(size: 6.5pt, weight: "bold")[GRAPHIC SCALE])
}
