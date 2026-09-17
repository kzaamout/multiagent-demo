// Introduction leave-behind template (S6). Filled by pandoc: title. The product's ink colour on
// headings, Letter, single column, diagrams as full-width images, the same family as the bid
// response template.

#let ink = rgb("#17171c")
#let grey = rgb("#75758a")

#set page(paper: "us-letter", margin: (x: 22mm, y: 20mm), numbering: "1")
#set text(font: ("Inter", "Segoe UI", "Helvetica", "Arial"), size: 10.5pt)
#set par(justify: false, leading: 0.62em)
#set heading(numbering: none)
#show heading.where(level: 1): it => block(above: 1.6em, below: 0.7em)[#text(size: 22pt, fill: ink, weight: 600)[#it.body]]
#show heading.where(level: 2): it => block(above: 1.3em, below: 0.5em)[#text(size: 14pt, fill: ink, weight: 600)[#it.body]]
#show heading.where(level: 3): it => block(above: 1em, below: 0.4em)[#text(size: 11.5pt, weight: 600)[#it.body]]
#set table(inset: 6pt, stroke: (x, y) => if y == 0 { (bottom: 0.7pt + ink) } else { (bottom: 0.4pt + luma(210)) })
#show table.cell.where(y: 0): set text(weight: 600)
#show image: it => block(width: 100%, above: 0.8em, below: 0.8em)[#it]
#let horizontalRule = line(start: (25%, 0%), end: (75%, 0%))
#let divider = if "divider" in std { divider } else { horizontalRule }

#block(width: 100%, inset: (top: 26mm, bottom: 10mm))[
  #text(size: 30pt, fill: ink, weight: 700)[$title$]
  #v(4mm)
  #text(size: 12pt, fill: grey)[Sterling AI · a multi-agent system that takes a business request from intake to a reviewed, human-approved deliverable]
  #v(4mm)
  #line(length: 100%, stroke: 1.2pt + ink)
]
#pagebreak()

$body$
