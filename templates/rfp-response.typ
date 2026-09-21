// Response template for the compiled bid response (S4). Filled by pandoc: the variables are
// prospect-name, logo-path (empty selects the wordmark), primary-colour, version. Letter, single
// column, the brand colour on the cover and the headings. Provenance markers come from #prov.

#let brand = rgb("$primary-colour$")

#set page(paper: "us-letter", margin: (x: 22mm, y: 20mm), numbering: "1")
#set text(font: ("Inter", "Segoe UI", "Helvetica", "Arial"), size: 10.5pt)
#set par(justify: false, leading: 0.6em)
#set heading(numbering: none)
#show heading.where(level: 1): it => block(above: 1.2em, below: 0.6em)[#text(size: 20pt, fill: brand, weight: 600)[#it.body]]
#show heading.where(level: 2): it => block(above: 1.4em, below: 0.5em)[#text(size: 13.5pt, fill: brand, weight: 600)[#it.body]]
#show heading.where(level: 3): it => block(above: 1em, below: 0.4em)[#text(size: 11.5pt, weight: 600)[#it.body]]

#set table(inset: 6pt, stroke: (x, y) => if y == 0 { (bottom: 0.7pt + brand) } else { (bottom: 0.4pt + luma(210)) })
#show table.cell.where(y: 0): set text(weight: 600)
#set terms(hanging-indent: 1.5em)
#let horizontalRule = line(start: (25%, 0%), end: (75%, 0%))
#let divider = if "divider" in std { divider } else { horizontalRule }

// A provenance marker: a small superscript letter beside its figure, plus metadata that
// `typst query "<prov>"` reports with the page and the position of the marker. The number n is the
// marker's identifier; the label is what is printed, made once in app/compile/markers.py. Numbers
// were printed until 2026-09-21, when a superscript 1 after 79,063.75 was read as a digit of the
// price (roadmap decision 36).
//
// Compiled with `--input markers=text`, the marker is written as " [a]" in the running text instead.
// That compile is never shown to anyone: it exists so the page text handed to the Reviewer reads
// "79,063.75 [a]". Extracted from the page as displayed, the superscript is glued to its figure, and
// while markers were numbers the same price read 79,063.751, 79,063.752 and 79,063.753, which the
// Reviewer failed as three different prices in 14 of the 22 runs that spent their whole review
// budget. No dollar signs in this comment: the file is a pandoc template, where a dollar sign opens a
// variable.
#let prov(n, label, src) = if sys.inputs.at("markers", default: "super") == "text" [ \[#label\]] else [#super(text(size: 6.5pt, fill: brand, weight: 600)[#label])#context [#metadata((n: n, src: src, page: here().page(), x: here().position().x.pt(), y: here().position().y.pt()))<prov>]]

// Cover
#block(width: 100%, inset: (top: 30mm, bottom: 12mm))[
$if(logo-path)$
  #image("$logo-path$", width: 38%)
$else$
  #text(size: 30pt, fill: brand, weight: 700)[$prospect-name$]
$endif$
  #v(10mm)
  #text(size: 22pt, weight: 600)[Bid response]
  #v(2mm)
  #text(size: 12pt, fill: luma(90))[Prepared for $if(client-name)$$client-name$$else$$prospect-name$$endif$ · draft version $version$]
  #v(4mm)
  #line(length: 100%, stroke: 1.2pt + brand)
]
#pagebreak()

$body$
