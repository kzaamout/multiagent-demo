"""A draft carries every specialist concern that names a sheet (owner decision 23, 2026-09-17).

The Writer's instructions say every assumption and concern from the specialists goes in the
assumptions section. The local Writer dropped the Estimator's rating concern in most runs on
2026-09-17, so the planted disagreement never reached the Reviewer and the demo's rejection
moment did not happen. This check is deterministic: for each concern whose drawing reference
names sheets, every named sheet must appear in the draft's Assumptions section. A draft that
fails goes back to the Writer once with the concern quoted, like any other rejected reply.
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
        sheets = sheets_in(text) or filed
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
        missing = [s for s in sheets if s not in section]
        if missing:
            problems.append(
                f'the {role}\'s concern is not carried in the Assumptions section: "{quoted}". '
                f"Add one line for it there, in your own words, naming {', '.join(advise)} and keeping any "
                "figures the concern states"
            )
    return problems


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
