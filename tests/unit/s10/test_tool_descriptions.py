"""A tool description says when to reach for it, not only what it does (spec 010, phase 1.4).

Twenty three refusals across the Estimator and Pricing were a seat writing numbers it should have taken
from a tool. The descriptions said what each tool did and stopped there, leaving the seat to infer that
calling it was compulsory. These tests pin the three facts a description has to carry: that the tool is
required, what must be true before calling it, and what it is not for.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.live.materials import DatasetFiles
from app.live.strands_tools import ToolLog, build_tools


def spec_of(name: str, tmp_path: Path) -> dict[str, Any]:
    """The tool as Strands hands it to a model: its description and its argument schema."""
    made: list[object] = []
    for seat in ("estimator", "pricing"):
        made += build_tools(
            seat,
            files=DatasetFiles(tmp_path),
            log=ToolLog(),
            prospect_name="Fictional Prospect Ltd.",
            prepared_dir=tmp_path,
            project="a project",
            supplier_order=[],
            long_lead_days=21,
        )
    for tool in made:
        if getattr(tool, "tool_name", getattr(tool, "__name__", "")) == name:
            return dict(getattr(tool, "tool_spec", {}) or {})
    raise AssertionError(f"{name} is not offered to the seat")


def description(name: str, tmp_path: Path) -> str:
    return str(spec_of(name, tmp_path).get("description", ""))


@pytest.mark.parametrize(
    ("tool", "required", "not_for"),
    [
        ("quantity_calculate", "refused", "Do not add, multiply"),
        ("price_list_lookup", "refused", "not a price from the fixture"),
    ],
)
def test_a_tool_a_reply_depends_on_says_it_is_required(
    tool: str, required: str, not_for: str, tmp_path: Path
) -> None:
    spec = spec_of(tool, tmp_path)
    text = str(spec.get("description", ""))
    assert required in text, "the description says the reply is refused without it"
    assert not_for in text, "and says what the seat must not do instead"
    # Strands lifts the Args block out of the docstring into the schema, so the guidance added above it
    # must not have cost the seat its argument documentation.
    properties = spec["inputSchema"]["json"]["properties"]
    assert all(p.get("description") for p in properties.values()), "every argument is still described"


def test_the_drawing_reader_says_an_unread_sheet_is_not_a_missing_sheet(tmp_path: Path) -> None:
    """Seventeen invented blockers came from a seat deciding about a sheet it had not opened."""
    text = description("vision_read_drawing", tmp_path)
    assert "not a missing sheet" in text
    assert "drawing index" in text, "it says what a real missing sheet looks like"
