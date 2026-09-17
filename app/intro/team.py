"""The team grid: eight agent cards (S6 decision 5a).

The six seats take their name pair and blurb from the content file, their role from the roster,
their model label from the registry's current seat table, and owns, sees and tools from the seat
definitions, so a card cannot disagree with the engine (constitution V). The two appraisal seats
do not exist in the roster until S8; their cards come from the content file with a swap-in note.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.config import ROOT
from app.intro.content import CONTENT_DIR
from app.orchestrator.roster import SEAT_BY_ID, colour_for
from app.seats import definitions as d

SEAT_ORDER = ("orchestrator", "intake", "estimator", "pricing", "writer", "reviewer")
SEAT_FILES = ROOT / "config" / "electrical-bid" / "seats"
SWAP_NOTE = "appraisal workflow only"

KIND_WORDS: dict[str, str] = {
    d.REQUEST_DOCUMENTS: "the request documents and drawing sheets",
    d.KNOWLEDGE_FILE: "the client knowledge file",
    d.READINESS_CHECKLIST: "the readiness checklist",
    d.BRIEF: "the brief",
    d.DRAWING_PAGES: "the drawing sheets",
    d.ESTIMATING_CONVENTIONS: "the estimating conventions",
    d.ESTIMATOR_OUTPUT: "the Estimator's output",
    d.SPECIALIST_OUTPUTS: "every specialist output",
    d.TOOL_RESULTS: "raw tool results",
    d.AGENT_REASONING: "agent reasoning",
    d.PRICE_FIXTURE: "the price list",
    d.TEMPLATE: "the response template",
    d.DRAFT: "the draft",
    d.PAGE_TEXT: "the compiled pages",
    d.REVIEWER_CRITERIA: "the reviewer criteria",
    d.FINDINGS: "the Reviewer's findings routed to it",
    d.RUN_STATE: "the run state",
}
TOOL_WORDS: dict[str, str] = {
    "document_parse_pdf": "document parser",
    "document_extract_attachments": "attachment lister",
    "prepare_documents": "document preparation",
    "vision_read_drawing": "drawing reader",
    "quantity_calculate": "quantity calculator",
    "price_list_lookup": "price list lookup",
    "template_render": "response template",
    "compile_trigger": "document compiler",
}

_BOLD_LINE = re.compile(r"^\*\*(?P<names>[^*,]+?),\s*(?P<role>[^*]+?)\.\*\*\s*(?P<blurb>.+)$")
_SWAP = re.compile(r"\*\*(?P<names>[^*,]+?),\s*(?P<role>[^*]+?)\*\*\s*\((?P<blurb>[^)]+)\)")


@dataclass(frozen=True)
class TeamCard:
    agent_id: str
    names: str
    role: str
    model: str
    blurb: str
    owns: str
    sees: str
    tools: str
    colour: str
    initials: str
    swap_in: bool = False


def _content_entries() -> tuple[dict[str, tuple[str, str, str]], list[tuple[str, str, str]]]:
    """(role -> (names, role, blurb)) for the bold paragraphs, and the appraisal (names, role, blurb) pairs."""
    text = (CONTENT_DIR / "04-the-team.md").read_text(encoding="utf-8")
    seats: dict[str, tuple[str, str, str]] = {}
    swaps: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        match = _BOLD_LINE.match(line)
        if match:
            seats[match.group("role").strip()] = (
                match.group("names").strip(),
                match.group("role").strip(),
                match.group("blurb").strip(),
            )
            continue
        if "swaps the two specialists" in line:
            for found in _SWAP.finditer(line):
                swaps.append(
                    (found.group("names").strip(), found.group("role").strip(), found.group("blurb").strip())
                )
    return seats, swaps


OWNS: dict[str, str] = {
    "orchestrator": "The plan, the assignments, every stage change, all contact with the human, and the decision to stop.",
    "intake": "The brief, the readiness verdict, and the questions the human is asked.",
    "estimator": "The bill of materials and the labour hours, with a concern for every disagreement in the drawings.",
    "pricing": "Every priced line, the markup, and the exceptions and long-lead items.",
    "writer": "The deliverable, every figure tagged with the specialist output it came from.",
    "reviewer": "The verdict, the findings by severity, and where each one goes.",
}
"""What each seat owns, in plain words that follow the seat files in config/electrical-bid/seats/."""


def _owns(agent_id: str) -> str:
    return OWNS.get(agent_id, "")


def _initials(names: str) -> str:
    first = names.split("/")[0].strip()
    return first[:1].upper()


def team_cards(seat_table: dict[str, Any] | None = None) -> list[TeamCard]:
    """Eight cards in the grid's order. `seat_table` is the registry's current table for model labels."""
    labels: dict[str, str] = {}
    for row in (seat_table or {}).get("seats", []):
        card = row.get("card") or {}
        model = card.get("model") or {}
        if isinstance(model, dict) and row.get("seat"):
            labels[str(row["seat"])] = str(model.get("label", ""))
    entries, swaps = _content_entries()
    cards: list[TeamCard] = []
    for agent_id in SEAT_ORDER:
        seat = SEAT_BY_ID[agent_id]
        names, role, blurb = entries.get(seat.role, (" / ".join(seat.names), seat.role, ""))
        definition = d.SEAT_DEFINITIONS[agent_id]
        order = list(KIND_WORDS)
        sees = ", ".join(
            KIND_WORDS.get(k, k)
            for k in sorted(definition.sees, key=lambda k: order.index(k) if k in order else 99)
        )
        tools = ", ".join(TOOL_WORDS.get(t, t) for t in definition.tools) or "none, on purpose"
        cards.append(
            TeamCard(
                agent_id=agent_id,
                names=names,
                role=role,
                model=labels.get(agent_id) or seat.default_model.label,
                blurb=blurb,
                owns=_owns(agent_id),
                sees=sees or "nothing",
                tools=tools,
                colour=colour_for(agent_id),
                initials=_initials(names),
            )
        )
    for index, (names, role, blurb) in enumerate(swaps):
        agent_id = ("case", "market")[index] if index < 2 else f"swap{index}"
        cards.append(
            TeamCard(
                agent_id=agent_id,
                names=names,
                role=role,
                model=SWAP_NOTE,
                blurb=blurb[0].upper() + blurb[1:] + ".",
                owns=blurb[0].upper() + blurb[1:] + ".",
                sees="its own slice of the appraisal order, like every specialist",
                tools="the appraisal fixtures' lookups",
                colour=colour_for(agent_id),
                initials=_initials(names),
                swap_in=True,
            )
        )
    return cards
