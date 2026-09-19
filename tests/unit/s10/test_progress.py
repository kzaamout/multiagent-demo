"""The engine writes the feed's progress lines, so no seat is asked to narrate (spec 010).

Asking every seat for a progress line before each tool call produced the largest single failure on the
team: a seat treating that line as its whole reply. The engine knows what is being called and on what, so
it writes the line and the instruction leaves the prompts.
"""

from __future__ import annotations

import pathlib

import pytest

from app.live.seat_call import progress_for

SEATS = pathlib.Path("config/electrical-bid/seats")


@pytest.mark.parametrize(
    ("tool", "arguments", "expected"),
    [
        ("vision_read_drawing", {"sheet": "E-101"}, "Reading sheet E-101"),
        ("document_parse_pdf", {"file": "prepared/E-001.pdf"}, "Reading prepared/E-001.pdf"),
        ("price_list_lookup", {"items": [1] * 47}, "Pricing the bill of materials, 47 lines"),
        ("template_render", {"sections": {}}, "Filling the response template"),
        ("document_extract_attachments", {}, "Listing what the request came with"),
    ],
)
def test_the_line_names_the_thing_the_tool_was_given(
    tool: str, arguments: dict[str, object], expected: str
) -> None:
    assert progress_for(tool, arguments) == expected


def test_an_unknown_tool_still_reads_as_english() -> None:
    """A tool added later must not produce a blank line or a raw identifier in the feed."""
    assert progress_for("some_new_tool", {}) == "Some new tool"


def test_no_seat_is_told_to_write_a_progress_line() -> None:
    """The instruction is gone, including from the worked examples that used to repeat it."""
    for path in sorted(SEATS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        assert "write the progress line" not in text, f"{path.name} still asks for one"
        assert "write one progress line" not in text, f"{path.name} still asks for one"
        if "Progress" in text:
            assert "feed writes its own line" in text, f"{path.name} says nothing about who narrates"
