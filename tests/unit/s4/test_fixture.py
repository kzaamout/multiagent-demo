"""The stub fixture draft carries the tags every stub run compiles with (spec FR-014)."""

from __future__ import annotations

from pathlib import Path

from app.tools.template import find_tags

FIXTURE = Path(__file__).resolve().parents[3] / "app" / "agents" / "stubs" / "fixtures" / "draft-fixture.md"


def test_fixture_draft_tags_parse() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    tags = find_tags(text)
    assert len(tags) >= 8
    assert {t.source_id for t in tags} == {"takeoff", "pricing"}
    assert tags[0].tag_id == "t01" and tags[-1].tag_id == f"t{len(tags):02d}"
    assert chr(0x2014) not in text


def test_fixture_draft_has_a_tag_in_a_table_cell_and_a_heading() -> None:
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    assert any(line.startswith("|") and "|src:" in line for line in lines)
    assert any(line.startswith("## ") and "|src:" in line for line in lines)
