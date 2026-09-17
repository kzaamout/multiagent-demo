// Run timeline template (S4). Filled by pandoc: run-id, dataset. One row per event.

#set page(paper: "us-letter", margin: (x: 16mm, y: 16mm), numbering: "1")
#set text(font: ("Inter", "Segoe UI", "Helvetica", "Arial"), size: 8.5pt)
#set par(justify: false)
#show heading.where(level: 1): it => block(below: 0.6em)[#text(size: 18pt, weight: 600)[#it.body]]
#set table(inset: 4pt, stroke: (x, y) => if y == 0 { (bottom: 0.7pt + black) } else { (bottom: 0.3pt + luma(215)) })
#show table.cell.where(y: 0): set text(weight: 600)
#let horizontalRule = line(start: (25%, 0%), end: (75%, 0%))
#let divider = if "divider" in std { divider } else { horizontalRule }

#text(size: 9pt, fill: luma(90))[Run $run-id$ · dataset $dataset$]
#v(2mm)

$body$
