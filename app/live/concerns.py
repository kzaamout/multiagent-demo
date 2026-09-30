"""A draft carries every specialist concern that names a sheet (owner decision 23, 2026-09-17).

The Writer's instructions say every assumption and concern from the specialists goes in the
assumptions section. The local Writer dropped the Estimator's rating concern in most runs on
2026-09-17, so the planted disagreement never reached the Reviewer and the demo's rejection
moment did not happen. This check is deterministic: for each concern that names sheets in its
own sentence, every one of them must appear in the draft's Assumptions section; for a concern
that names sheets only in its reference field, one of them is enough; and a line that repeats
the concern's own sentence carries it whatever sheets it names. A draft that fails goes back to
the Writer with the concern quoted, like any other rejected reply.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

SHEET = re.compile(r"\b[A-Z]{1,2}-?\d{3}[A-Z]?\b")
ASSUMPTIONS_HEADING = re.compile(r"^##\s+Assumptions\b.*$", re.MULTILINE | re.IGNORECASE)
NEXT_HEADING = re.compile(r"^##\s+", re.MULTILINE)


def sheets_in(text: str) -> list[str]:
    """Sheet ids named in a drawing reference, in order, without duplicates."""
    return list(dict.fromkeys(SHEET.findall(text or "")))


def assumptions_section(markdown: str) -> str | None:
    """The body of the draft's Assumptions section, or None when the draft has none."""
    match = ASSUMPTIONS_HEADING.search(markdown)
    if match is None:
        return None
    rest = markdown[match.end() :]
    following = NEXT_HEADING.search(rest)
    return rest[: following.start()] if following else rest


def concern_problems(
    markdown: str, concerns: Iterable[Mapping[str, Any]], role: str = "Estimator"
) -> list[str]:
    """One sentence per specialist concern the draft's Assumptions section does not carry."""
    problems: list[str] = []
    section = assumptions_section(markdown)
    for concern in concerns:
        text = str(concern.get("text", "")).strip()
        # What the Writer must carry is the concern's own sentence, so the sheets to look for are the ones
        # that sentence names. The reference field is the fallback for a concern that names none, and it
        # is offered as advice, never required: a concern reading "225 A on E-002 does not match ... on
        # E-002" with a reference field of "E-001, E-002" was refused three times for an E-001 its own
        # words never mention, while the draft carried it faithfully.
        filed = sheets_in(str(concern.get("drawing_ref", "")))
        own = sheets_in(text)
        sheets = own or filed
        if not sheets:
            continue
        advise = list(dict.fromkeys(sheets + filed))
        quoted = text[:90].rstrip() + ("..." if len(text) > 90 else "")
        if section is None:
            problems.append(
                f'the draft has no Assumptions section, so the {role}\'s concern is not carried: "{quoted}" '
                f"(sheets {', '.join(advise)}). Add an Assumptions section with one line for this concern naming the sheets"
            )
            continue
        # Run 8b817f67: a concern whose sentence named no sheet, filed against three, was refused twice,
        # once copied word for word and once reworded naming two of the three, and the run stopped.
        # A copy of the concern's own sentence is the concern whatever sheets it names. For a concern
        # filed against sheets its sentence never names, one line has to use the concern's own words:
        # one sheet alone is not enough, because two concerns filed against the same sheet would then
        # pass on a line that carries only one of them.
        if _words(text) and _words(text) in _words(section):
            continue
        if own:
            carried = all(s in section for s in sheets)
        else:
            carried = any(_line_carries(line, text, sheets) for line in section.splitlines())
        if not carried:
            naming = ", ".join(advise) if own else "at least one of " + ", ".join(advise)
            problems.append(
                f'the {role}\'s concern is not carried in the Assumptions section: "{quoted}". '
                f"Add one line for it there, in your own words, naming {naming} and keeping any "
                "figures the concern states"
            )
    return problems


def _words(text: str) -> str:
    """Text as lower-case words and numbers only, so a copied sentence matches across punctuation and wrapping."""
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _telling(text: str) -> set[str]:
    """The words of four letters or more, and every number, which carry what a sentence is about."""
    return {w for w in _words(text).split() if len(w) >= 4 or w.isdigit()}


def _line_carries(line: str, concern: str, sheets: list[str]) -> bool:
    """One line of the section uses half of the concern's telling words, or a third when it also names one
    of the sheets. Run 11086d33 carried a concern nearly word for word on a line that named no sheet."""
    wanted = _telling(concern)
    if not wanted:
        return False
    shared = len(wanted & _telling(line))
    if shared * 2 >= len(wanted):
        return True
    return shared * 3 >= len(wanted) and any(s in line for s in sheets)


def specialist_concerns(events: Iterable[Any]) -> list[tuple[str, Mapping[str, Any]]]:
    """(role, concern) for every concern in the latest completed output of each specialist."""
    latest: dict[str, Mapping[str, Any]] = {}
    for event in events:
        if event.type == "task.completed":
            latest[str(event.payload.get("agent_id", ""))] = event.payload
    found: list[tuple[str, Mapping[str, Any]]] = []
    for agent_id, role in (("estimator", "Estimator"), ("pricing", "Pricing")):
        result = latest.get(agent_id, {}).get("result")
        if isinstance(result, Mapping):
            for concern in result.get("concerns") or []:
                if isinstance(concern, Mapping):
                    found.append((role, concern))
    return found
