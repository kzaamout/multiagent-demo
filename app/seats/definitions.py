"""What each seat may see and use, and how its instructions are loaded.

The roster table in docs/spec-input.md 4.3 is the source. Scopes are enforced by the context
builder (app/live/context.py); tools are enforced when the agent is built.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.config import ROOT

SEATS_DIR = ROOT / "config" / "electrical-bid" / "seats"
PLACEHOLDERS = ("name", "review_max_cycles", "long_lead_days")
_PLACEHOLDER = re.compile(r"(?<!\{)\{([a-z_]+)\}(?!\})")

# Context material kinds. Every item placed in a context slice has exactly one kind.
REQUEST_DOCUMENTS = "request_documents"
KNOWLEDGE_FILE = "knowledge_file"
READINESS_CHECKLIST = "readiness_checklist"
BRIEF = "brief"
DRAWING_PAGES = "drawing_pages"
ESTIMATING_CONVENTIONS = "estimating_conventions"
ESTIMATOR_OUTPUT = "estimator_output"
SPECIALIST_OUTPUTS = "specialist_outputs"
TOOL_RESULTS = "tool_results"
AGENT_REASONING = "agent_reasoning"
PRICE_FIXTURE = "price_fixture"
TEMPLATE = "template"
DRAFT = "draft"
REVIEWER_CRITERIA = "reviewer_criteria"
FINDINGS = "findings"
RUN_STATE = "run_state"

ALL_KINDS = frozenset(
    {
        REQUEST_DOCUMENTS,
        KNOWLEDGE_FILE,
        READINESS_CHECKLIST,
        BRIEF,
        DRAWING_PAGES,
        ESTIMATING_CONVENTIONS,
        ESTIMATOR_OUTPUT,
        SPECIALIST_OUTPUTS,
        TOOL_RESULTS,
        AGENT_REASONING,
        PRICE_FIXTURE,
        TEMPLATE,
        DRAFT,
        REVIEWER_CRITERIA,
        FINDINGS,
        RUN_STATE,
    }
)


@dataclass(frozen=True)
class SeatDefinition:
    agent_id: str
    instructions_file: str
    tools: tuple[str, ...]
    sees: frozenset[str]

    def may_see(self, kind: str) -> bool:
        return kind in self.sees


SEAT_DEFINITIONS: dict[str, SeatDefinition] = {
    "orchestrator": SeatDefinition(
        "orchestrator",
        "orchestrator.md",
        (),
        frozenset({BRIEF, RUN_STATE, FINDINGS, READINESS_CHECKLIST, SPECIALIST_OUTPUTS, DRAFT}),
    ),
    "intake": SeatDefinition(
        "intake",
        "intake.md",
        ("prepare_documents", "document_parse_pdf", "document_extract_attachments"),
        frozenset({REQUEST_DOCUMENTS, KNOWLEDGE_FILE, READINESS_CHECKLIST}),
    ),
    "estimator": SeatDefinition(
        "estimator",
        "estimator.md",
        ("vision_read_drawing", "quantity_calculate"),
        frozenset({BRIEF, DRAWING_PAGES, ESTIMATING_CONVENTIONS, FINDINGS}),
    ),
    "pricing": SeatDefinition(
        "pricing",
        "pricing.md",
        ("price_list_lookup",),
        frozenset({ESTIMATOR_OUTPUT, KNOWLEDGE_FILE, FINDINGS}),
    ),
    "writer": SeatDefinition(
        "writer",
        "writer.md",
        ("template_render", "compile_trigger"),
        frozenset({BRIEF, SPECIALIST_OUTPUTS, TEMPLATE, KNOWLEDGE_FILE, FINDINGS}),
    ),
    "reviewer": SeatDefinition(
        "reviewer",
        "reviewer.md",
        (),
        frozenset({BRIEF, DRAFT, REVIEWER_CRITERIA}),
    ),
}


class InstructionsError(ValueError):
    pass


def load_instructions(
    agent_id: str,
    *,
    name: str,
    review_max_cycles: int,
    long_lead_days: int,
    seats_dir: Path = SEATS_DIR,
) -> str:
    """Read a seat's instructions and fill the per-run placeholders.

    Only the three known placeholders are replaced. JSON examples in the files use braces too,
    so replacement is literal rather than str.format, and any other single-brace lower-case
    word is an error so a typo cannot reach a model.
    """
    definition = SEAT_DEFINITIONS[agent_id]
    text = (seats_dir / definition.instructions_file).read_text(encoding="utf-8")
    values = {
        "name": name,
        "review_max_cycles": str(review_max_cycles),
        "long_lead_days": str(long_lead_days),
    }
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    leftover = sorted(set(_PLACEHOLDER.findall(text)))
    if leftover:
        raise InstructionsError(f"{definition.instructions_file}: unknown placeholders {leftover}")
    return text
