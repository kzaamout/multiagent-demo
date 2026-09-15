// Shared frame for the Clean run request documents. Fictional project; see ../README.md.
#let doc(title: "", reference: "", body) = {
  set page(paper: "us-letter", margin: (x: 0.9in, y: 0.85in),
    header: context if counter(page).get().first() > 1 [
      #set text(size: 8pt, fill: rgb("#555555"))
      Quillbrook Public Library Board #h(1fr) #reference
    ],
    footer: context [
      #set text(size: 8pt, fill: rgb("#555555"))
      #title #h(1fr) Page #counter(page).display() of #counter(page).final().first()
    ],
  )
  set text(font: "Arial", size: 10pt)
  set par(justify: false, leading: 0.62em, spacing: 0.9em)
  show heading.where(level: 1): it => block(above: 1.2em, below: 0.6em, text(size: 11.5pt, weight: "bold")[#it.body])
  body
}
