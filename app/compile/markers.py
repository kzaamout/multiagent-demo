"""Provenance tags become lettered markers on the page (spec 0.7 section 2.6, S4 decision 2a, 013).

A tag `{{value|src:id}}` in the draft is replaced by its value followed by a raw Typst call
`#prov(n, "a", "id")`, which the response template renders as a small superscript letter and records
with `#metadata(...)<prov>` so `typst query` can report where each marker landed. Markers are
numbered in document order, which is also the order `app.tools.template.find_tags` assigns tag ids,
so marker n is tag t<nn> and the panel resolves it through `draft.committed.provenance_tags`.

The number stays the marker's identifier. What a reader sees is its label, a letter, because a
superscript digit after an amount reads as another digit of it (roadmap decision 36).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from app.tools.template import TAG

APPENDIX_HEADING = "## Provenance"


def marker_label(n: int) -> str:
    """Marker n as lowercase letters, counted as spreadsheet columns are: 1 a, 26 z, 27 aa, 28 ab."""
    if n < 1:
        raise ValueError(f"markers are numbered from 1, not {n}")
    letters: list[str] = []
    while n:
        n, rest = divmod(n - 1, 26)
        letters.append(chr(ord("a") + rest))
    return "".join(reversed(letters))


@dataclass(frozen=True)
class MarkerDraft:
    n: int
    tag_id: str
    source_id: str
    value: str
    label: str


def prepare_markdown(markdown: str) -> tuple[str, list[MarkerDraft]]:
    """Replace every tag with its value plus a marker call; return the markdown and the markers."""
    markers: list[MarkerDraft] = []

    def replace(match: re.Match[str]) -> str:
        n = len(markers) + 1
        value = match.group(1).strip()
        source_id = match.group(2).strip()
        label = marker_label(n)
        markers.append(MarkerDraft(n=n, tag_id=f"t{n:02d}", source_id=source_id, value=value, label=label))
        return f'{value}`#prov({n}, "{label}", "{source_id}")`{{=typst}}'

    return TAG.sub(replace, markdown), markers


def appendix(markers: list[MarkerDraft], headlines: Mapping[str, str] | None = None) -> str:
    """The printed provenance list: one line per marker with its source id and, when known, the
    headline of the specialist output behind it. Unknown sources say so rather than guessing."""
    headlines = headlines or {}
    if not markers:
        return "No figures carry a provenance marker in this version."
    lines = ["| Marker | Source | Output |", "|---|---|---|"]
    for m in markers:
        headline = headlines.get(m.source_id)
        lines.append(f"| {m.label} | {m.source_id} | {headline if headline else 'unresolved'} |")
    return "\n".join(lines)


def with_appendix(markdown: str, markers: list[MarkerDraft], headlines: Mapping[str, str] | None) -> str:
    """Append the marker table to the draft's Provenance section, adding the section when absent."""
    table = appendix(markers, headlines)
    head, sep, tail = markdown.partition(f"\n{APPENDIX_HEADING}")
    if not sep:
        return markdown.rstrip("\n") + f"\n\n{APPENDIX_HEADING}\n\n{table}\n"
    return f"{head}{sep}{tail.rstrip()}\n\n{table}\n"
