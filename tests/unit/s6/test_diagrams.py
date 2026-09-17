"""The three diagrams carry the parts the spec names and parse as SVG (spec FR-003, FR-004)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from app.intro.diagrams import diagrams

EM_DASH = chr(0x2014)


def _parsed() -> dict[str, ET.Element]:
    return {name: ET.fromstring(d.svg) for name, d in diagrams().items()}


def test_three_diagrams_parse_and_have_no_em_dash() -> None:
    found = diagrams()
    assert set(found) == {"architecture", "loop", "demo-vs-production"}
    for d in found.values():
        ET.fromstring(d.svg)
        assert EM_DASH not in d.svg and EM_DASH not in d.text
        assert 'data-diagram="' + d.name + '"' in d.svg


def test_architecture_names_every_band_and_part() -> None:
    text = diagrams()["architecture"].text
    for part in (
        "RENDERERS",
        "Web UI",
        "Slack",
        "future",
        "EVENT STREAM",
        "ORCHESTRATOR",
        "Intake",
        "Handoff",
        "retry N of M",
        "AGENTS",
        "Orchestrator",
        "Reviewer",
        "TOOLS",
        "drawing reader",
        "price list",
        "template",
        "MODEL PROVIDERS",
        "Bedrock",
        "Local",
        "one door",
        "You",
    ):
        assert part in text, part
    assert "chain of thought" not in text


def test_loop_reproduces_the_strip_with_labelled_backward_arrows_and_exits() -> None:
    text = diagrams()["loop"].text
    for stage in ("Intake", "Plan", "Work", "Assemble", "Review", "Handoff"):
        assert stage in text
    for label in ("Review to Work", "Review to Assemble", "Work to Intake", "retry N of M"):
        assert label in text
    for exit_name in ("Reviewer passed", "Review limit reached", "Blocker escalated", "Not ready"):
        assert exit_name in text
    svg = diagrams()["loop"].svg
    assert svg.count('marker-end="url(#arrow-red)"') == 3, "three backward arrows"


def test_demo_vs_production_draws_the_bands_twice_with_badges() -> None:
    text = diagrams()["demo-vs-production"].text
    assert text.count("ORCHESTRATOR") == 2 and text.count("MODEL PROVIDERS") == 2
    assert "DEMO" in text and "YOUR AWS ACCOUNT" in text
    for badge in (
        "AgentCore Runtime",
        "AgentCore Gateway",
        "AgentCore Memory",
        "AgentCore Observability",
        "AgentCore Identity",
        "laptop browser",
        "knowledge file",
    ):
        assert badge in text, badge
