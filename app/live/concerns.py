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
        sheets = sheets_in(str(concern.get("drawing_ref", "")))
        if not sheets:
            continue
        text = str(concern.get("text", "")).strip()
        quoted = text[:90].rstrip() + ("..." if len(text) > 90 else "")
        if section is None:
            problems.append(
                f'the draft has no Assumptions section, so the {role}\'s concern is not carried: "{quoted}" '
                f"(sheets {', '.join(sheets)}). Add an Assumptions section with one line for this concern naming the sheets"
            )
            continue
        missing = [s for s in sheets if s not in section]
        if missing:
            problems.append(
                f'the {role}\'s concern is not carried in the Assumptions section: "{quoted}". '
                f"Add one line for it there naming the sheets {', '.join(sheets)} and the values that disagree"
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
