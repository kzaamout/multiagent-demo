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

SEATS_WITH_TOOLS = ("intake", "estimator", "pricing", "writer")


def spec_of(name: str, tmp_path: Path) -> dict[str, Any]:
    """The tool as Strands hands it to a model: its description and its argument schema."""
    made: list[object] = []
    for seat in SEATS_WITH_TOOLS:
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


def test_every_tool_offered_to_a_seat_says_when_to_use_it(tmp_path: Path) -> None:
    """A description that says only what a tool does leaves the seat to guess when to reach for it.

    Not a style rule: the seats that skipped a tool, or decided about a sheet they had not opened, were
    reading descriptions that named the action and stopped. Length is a crude proxy, so the real check is
    that each one says something about when, or when not.
    """
    when_words = ("before", "first", "once", "not a", "do not", "cannot", "refused", "while")
    seen: set[str] = set()
    for seat in SEATS_WITH_TOOLS:
        for tool in build_tools(
            seat,
            files=DatasetFiles(tmp_path),
            log=ToolLog(),
            prospect_name="Fictional Prospect Ltd.",
            prepared_dir=tmp_path,
            project="a project",
            supplier_order=[],
            long_lead_days=21,
        ):
            name = str(getattr(tool, "tool_name", ""))
            if name in seen:
                continue
            seen.add(name)
            text = str((getattr(tool, "tool_spec", {}) or {}).get("description", "")).lower()
            assert any(word in text for word in when_words), f"{name} says what it does but not when"
    assert len(seen) == 7, f"every tool the team holds is covered, found {sorted(seen)}"
