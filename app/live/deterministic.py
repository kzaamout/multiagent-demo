"""Work the engine can do exactly, so a seat is not asked to remember or judge it (spec 010).

Three of the largest failures on this team were the model being asked for something the run already
knows. The Estimator raised blockers for sheets that were in the set and had been parsed minutes earlier.
The Writer was told which figures had no provenance tag but not which source to tag them with, so it
guessed. The Writer was asked to remember every specialist concern when the concerns were sitting in the
event log in structured form.

Each function here answers one of those from recorded data. None of them writes into a deliverable: a
provenance tag inserted by string matching could attribute a number to the wrong specialist while looking
authoritative, and provenance is the claim the whole demo rests on. The engine does the lookup and the
seat still makes the attribution.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

# A sheet as the trade writes it: one or two letters, a dash, digits. E-001, LP-2, M-101.
SHEET = re.compile(r"\b([A-Z]{1,2}-\d{1,3})\b")
MONEY = re.compile(r"\$[\d,]+(?:\.\d{2})?")
SOURCE_HEADING = re.compile(r"\(source id:\s*([a-z0-9_]+)\)", re.I)


def sheets_named(text: str) -> list[str]:
    """Every sheet identifier a piece of text names, in the order it names them."""
    return list(dict.fromkeys(SHEET.findall(text.upper())))


def present_sheets(prepared: Any) -> set[str]:
    """Sheet identifiers the run actually holds, from the prepared manifest.

    Both the sheet number read from the title block and the prepared file's own name count, because a
    sheet whose title block could not be read is still a sheet the seat can open.
    """
    found: set[str] = set()
    for sheet in getattr(prepared, "sheets", []) or []:
        for value in (getattr(sheet, "sheet_number", ""), getattr(sheet, "sheet_id", "")):
            found.update(SHEET.findall(str(value).upper()))
    return found


MISSING_WORDS = ("missing", "not in", "not included", "absent", "not present", "no schedule", "not provided")
CLAUSE = re.compile(r"[.;]|\bbut\b|\bthough\b|\balthough\b|\bwhile\b|\bhowever\b", re.I)


def _claims_of_absence(description: str) -> list[str]:
    """The clauses of a blocker that say something is not there.

    A blocker usually names a sheet it can see as well as the one it cannot: "LP-2 appears on E-001 but
    its schedule E-003 is not in the set". Only the second clause is a claim of absence, and judging the
    whole sentence at once would refuse a blocker for a sheet that really is missing.
    """
    return [c for c in CLAUSE.split(description) if any(w in c.lower() for w in MISSING_WORDS)]


def blocker_names_a_present_sheet(description: str, prepared: Any) -> str | None:
    """A blocker claiming a sheet is missing, when the run holds that sheet.

    Returns the refusal, or None when the blocker stands. Conservative in three ways, because refusing a
    real blocker is worse than letting an invented one through: it reads only the clauses claiming
    absence, it ignores identifiers that are not shaped like this set's sheet numbers (a panel called
    LP-1 is not a sheet), and it stays silent unless every sheet claimed missing is one the run holds.
    """
    if not description:
        return None
    held = present_sheets(prepared)
    if not held:
        return None
    prefixes = {sheet.split("-", 1)[0] for sheet in held}
    claimed = [
        sheet
        for clause in _claims_of_absence(description)
        for sheet in sheets_named(clause)
        if sheet.split("-", 1)[0] in prefixes
    ]
    if not claimed or not all(sheet in held for sheet in claimed):
        return None
    names = ", ".join(dict.fromkeys(claimed))
    return (
        f"this blocker says {names} is missing, and {names} is in the drawing set: it was prepared and "
        "read at Intake, and you can open it. Read it with vision_read_drawing and finish the takeoff. "
        "Raise a blocker only for a sheet the drawing index lists that the set does not contain"
    )


def sources_of_figure(figure: str, offered_context: str) -> list[str]:
    """Which offered sources contain this figure, by the headings the context slice is built from.

    The context slice carries each specialist output under a heading naming its source id. A figure that
    appears under exactly one of them can be attributed without guessing; one appearing under several, or
    none, cannot, and the seat is told which case it is.
    """
    sections: list[tuple[str, str]] = []
    position = 0
    for match in SOURCE_HEADING.finditer(offered_context):
        if sections:
            sections[-1] = (sections[-1][0], offered_context[position : match.start()])
        sections.append((match.group(1).lower(), ""))
        position = match.end()
    if sections:
        sections[-1] = (sections[-1][0], offered_context[position:])
    # A specialist output reaches the Writer as JSON, where a price is 31338.31 with no currency symbol
    # and no thousands separator, while the draft writes $31,338.31. Comparing the two as written found
    # nothing and the advice then told the Writer that a real Pricing total did not belong in the
    # document, which is worse than saying nothing at all. The comparison is on the number.
    number = figure.lstrip("$").replace(",", "").rstrip(".")
    if not number:
        return []
    whole = number.split(".")[0]
    pattern = re.compile(
        rf"(?<![\d.]){re.escape(number)}(?![\d])|(?<![\d.]){re.escape(whole)}(?:\.0+)?(?![\d])"
        if "." not in number
        else rf"(?<![\d.]){re.escape(number)}(?![\d])"
    )
    return sorted({name for name, body in sections if pattern.search(body.replace(",", ""))})


def tag_advice(untagged: Iterable[str], offered_context: str) -> str | None:
    """For each untagged figure, the source to tag it with when exactly one offered output carries it."""
    known: list[str] = []
    ambiguous: list[str] = []
    missing: list[str] = []
    for figure in dict.fromkeys(untagged):
        sources = sources_of_figure(figure, offered_context)
        if len(sources) == 1:
            known.append(f"{{{{{figure}|src:{sources[0]}}}}}")
        elif sources:
            ambiguous.append(f"{figure} appears in {' and '.join(sources)}, so choose the one it came from")
        else:
            missing.append(figure)
    parts: list[str] = []
    if known:
        parts.append("write these exactly: " + ", ".join(known))
    if ambiguous:
        parts.append("; ".join(ambiguous))
    if missing:
        parts.append(
            "these are in no output you were given, so they cannot be tagged and do not belong in the "
            "document: " + ", ".join(missing)
        )
    return ". ".join(parts) if parts else None


def assumptions_block(concerns: Iterable[tuple[str, Mapping[str, Any]]]) -> str:
    """The assumptions the Writer must carry, prepared from the concerns rather than left to memory.

    Handing the seat the sentences turns remembering into copying, which is the difference between the
    Writer's largest failure and no failure at all. The wording stays the specialist's own.
    """
    lines: list[str] = []
    for role, concern in concerns:
        text = str(concern.get("text", "")).strip()
        if not text:
            continue
        reference = str(concern.get("drawing_ref", "") or "").strip()
        lines.append(f"- {text}" + (f" ({reference})" if reference else "") + f" [from the {role}]")
    if not lines:
        return ""
    return (
        "## Assumptions to carry\n"
        "Every line below is a concern a specialist raised on this job. Each one goes into the "
        "Assumptions section of your draft, in your own sentence, keeping the figures and the sheet "
        "names as written. A concern you leave out is a disagreement the reader never sees.\n"
        + "\n".join(lines)
    )
