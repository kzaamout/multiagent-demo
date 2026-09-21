# Data model: Lettered provenance markers

Nothing here is an event. The event schema (`docs/schema/events-v1.1.0.md`) and every payload stay as they are (FR-009).

## Marker label (new, derived)

The text shown for a marker on every surface.

| Property | Rule |
|---|---|
| Derived from | the marker's number `n`, an integer from 1 |
| Alphabet | lowercase a to z, all 26 (decision 3b) |
| Sequence | bijective base 26: 1 a, 26 z, 27 aa, 28 ab, 52 az, 53 ba, 702 zz, 703 aaa (decision 4a) |
| Uniqueness | one label per number; no two markers in a draft share one |
| Computed in | `marker_label(n)` in `app/compile/markers.py`, and nowhere else (FR-002) |
| Invalid input | `n` below 1 raises `ValueError`; markers are numbered from 1, so this is a programming error |

## MarkerDraft (changed)

One tag in the draft, before the compile. `app/compile/markers.py`.

| Field | Type | Change |
|---|---|---|
| `n` | int | unchanged: the marker's number in document order |
| `tag_id` | str | unchanged: `t01`, `t02`, and so on |
| `source_id` | str | unchanged: the short source id the tag names |
| `value` | str | unchanged: the figure the tag wraps |
| `label` | str | **new**: `marker_label(n)` |

## Marker (changed)

One marker on the compiled pages, as `markers.json` records it. `app/compile/pipeline.py`.

| Field | Type | Change |
|---|---|---|
| `n` | int | unchanged |
| `tag_id` | str | unchanged |
| `source_id` | str | unchanged |
| `page` | int | unchanged: 1-based page number |
| `x`, `y` | float | unchanged: position in pixels at 150 ppi |
| `label` | str | **new**: the label the page prints for this marker |

A `markers.json` written before this change has no `label`. Readers treat a missing or empty `label` as "show `n`" (FR-007).

## Compiled (unchanged)

`compiled.json` and the `artifact.compiled` payload keep `marker_count` and `unresolved: list[int]`; `unresolved` lists marker numbers, which are identifiers.

## Page text (changed content, same shape)

`pages.json` stays a list of strings, one per page. Inside the strings, a marker reads ` [a]` where it read ` [1]`.
