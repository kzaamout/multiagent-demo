# Contract: provenance markers

The surfaces a marker appears on, and what each promises. The label rule is in `../data-model.md`.

## 1. The draft tag (unchanged)

The Writer writes `{{value|src:source_id}}`. It never writes a marker or a label.

## 2. The template call

`app.compile.markers.prepare_markdown` replaces each tag with its value followed by a raw Typst call:

```text
before: 36860.5`#prov(1, "pricing")`{=typst}
after:  36860.5`#prov(1, "a", "pricing")`{=typst}
```

`templates/rfp-response.typ` defines `#let prov(n, label, src)`:

| Compile | Prints | Records |
|---|---|---|
| displayed (default, `markers=super`) | `label` as a superscript, 6.5 pt, brand colour, weight 600 | `metadata((n, src, page, x, y))<prov>`, unchanged |
| reading (`--input markers=text`) | ` [label]` in the running text | nothing |

`label` is always lowercase letters, so it needs no escaping inside a Typst string.

## 3. `markers.json`

Written beside the pages of each version, one object per marker, in document order:

```json
[
 {"n": 1, "tag_id": "t01", "source_id": "pricing", "page": 2, "x": 612.4, "y": 301.7, "label": "a"}
]
```

`label` is new and is added last. A consumer MUST accept a file without it.

## 4. The overlay button (Demo page and the Introduction frame)

`app/web/static/js/render.js` `placeMarkers`, for each marker `m`:

| Attribute | Value | Change |
|---|---|---|
| text | `m.label` when it is a non-empty string, else `String(m.n)` | changed |
| `data-marker` | `String(m.n)` | unchanged, an identifier |
| `data-tag` | `m.tag_id` | unchanged |
| `data-source-event`, `data-unresolved`, `title`, position | as today | unchanged |

Hover and click behaviour are unchanged (FR-010).

## 5. The Provenance table

The printed table keeps its three columns. The Marker column holds the label:

```text
| Marker | Source | Output |
|---|---|---|
| a | pricing | Costing complete |
| b | takeoff | Takeoff complete |
```

## 6. The Reviewer

The page text it receives writes each marker as ` [label]` after its figure (section 2). Its seat instruction says a marker is a small superscript letter on the page image and the same letter in square brackets in the page text, that the marker is never part of the figure, and that a figure is cited by its page number and marker letter.
