from __future__ import annotations

from pathlib import Path

import pytest

from app.live.context import Material, build_context
from app.seats import definitions as d
from app.seats.definitions import SEAT_DEFINITIONS, InstructionsError, load_instructions

SPEC_TOOLS = {
    "orchestrator": (),
    "intake": ("document_parse_pdf", "document_extract_attachments"),
    "estimator": ("vision_read_drawing", "quantity_calculate"),
    "pricing": ("price_list_lookup",),
    "writer": ("template_render", "compile_trigger"),
    "reviewer": (),
}


@pytest.mark.parametrize("agent_id", sorted(SEAT_DEFINITIONS))
def test_instructions_load_with_placeholders_filled(agent_id: str) -> None:
    text = load_instructions(agent_id, name="Rosa", retry_budget=2, long_lead_days=28)
    assert text.startswith("You are Rosa")
    assert "{name}" not in text and "{retry_budget}" not in text and "{long_lead_days}" not in text
    assert chr(0x2014) not in text


def test_writer_tag_syntax_and_json_braces_survive() -> None:
    writer = load_instructions("writer", name="Willa", retry_budget=2, long_lead_days=28)
    assert "{{value|src:ID}}" in writer and "{{225 A|src:8f2a10c4}}" in writer
    pricing = load_instructions("pricing", name="Pavel", retry_budget=2, long_lead_days=28)
    assert "over 28 days" in pricing
    assert '{"headline"' in pricing


def test_unknown_placeholder_is_refused(tmp_path: Path) -> None:
    (tmp_path / "reviewer.md").write_text("You are {name}. Budget {retry_budgt}.", encoding="utf-8")
    with pytest.raises(InstructionsError, match="retry_budgt"):
        load_instructions("reviewer", name="Rosa", retry_budget=2, long_lead_days=28, seats_dir=tmp_path)


@pytest.mark.parametrize("agent_id", sorted(SPEC_TOOLS))
def test_tools_match_the_roster(agent_id: str) -> None:
    assert SEAT_DEFINITIONS[agent_id].tools == SPEC_TOOLS[agent_id]


def everything() -> list[Material]:
    return [
        Material(d.REQUEST_DOCUMENTS, "Request", "cover letter text"),
        Material(d.KNOWLEDGE_FILE, "Knowledge file", "markup 15 percent"),
        Material(d.READINESS_CHECKLIST, "Readiness checklist", "checklist"),
        Material(d.BRIEF, "Brief", "brief text", "evt-brief"),
        Material(d.DRAWING_PAGES, "Drawings", "E-001 page image"),
        Material(d.ESTIMATING_CONVENTIONS, "Conventions", "conventions"),
        Material(d.ESTIMATOR_OUTPUT, "Estimator output", "bom lines", "evt-est"),
        Material(d.SPECIALIST_OUTPUTS, "Pricing output", "priced bom", "evt-price"),
        Material(d.TOOL_RESULTS, "Tool results", "vision_read_drawing raw output"),
        Material(d.AGENT_REASONING, "Reasoning", "estimator chain of thought"),
        Material(d.PRICE_FIXTURE, "Price fixture", "csv rows"),
        Material(d.TEMPLATE, "Template", "template"),
        Material(d.DRAFT, "Draft v1", "draft markdown", "evt-draft"),
        Material(d.REVIEWER_CRITERIA, "Criteria", "criteria"),
    ]


EXPECTED = {
    "intake": {d.REQUEST_DOCUMENTS, d.KNOWLEDGE_FILE, d.READINESS_CHECKLIST},
    "estimator": {d.BRIEF, d.DRAWING_PAGES, d.ESTIMATING_CONVENTIONS},
    "pricing": {d.ESTIMATOR_OUTPUT, d.KNOWLEDGE_FILE},
    "writer": {d.BRIEF, d.SPECIALIST_OUTPUTS, d.TEMPLATE, d.KNOWLEDGE_FILE},
    "reviewer": {d.BRIEF, d.DRAFT, d.REVIEWER_CRITERIA},
}


@pytest.mark.parametrize("agent_id", sorted(EXPECTED))
def test_context_keeps_exactly_the_roster_scope(agent_id: str) -> None:
    ctx = build_context(agent_id, everything())
    assert ctx.kinds() == EXPECTED[agent_id]


def test_reviewer_bundle_excludes_the_team_working() -> None:
    rendered = build_context("reviewer", everything()).render()
    for secret in [
        "chain of thought",
        "raw output",
        "bom lines",
        "priced bom",
        "csv rows",
        "markup 15 percent",
    ]:
        assert secret not in rendered
    assert "draft markdown" in rendered and "criteria" in rendered


def test_nobody_but_the_orchestrator_sees_reasoning_or_tool_results() -> None:
    for agent_id in SEAT_DEFINITIONS:
        kinds = build_context(agent_id, everything()).kinds()
        assert d.AGENT_REASONING not in kinds
        assert d.TOOL_RESULTS not in kinds
        assert d.PRICE_FIXTURE not in kinds


def test_writer_context_labels_sources() -> None:
    rendered = build_context("writer", everything()).render()
    assert "(source id: evt-price)" in rendered
    assert "E-001 page image" not in rendered


def test_unknown_material_kind_is_refused() -> None:
    with pytest.raises(ValueError):
        Material("secrets", "x", "y")
