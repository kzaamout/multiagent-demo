"""The compiler skip names the missing tool (spec FR-016)."""

from __future__ import annotations

import pytest

from app.compile import pipeline
from tests.conftest import _skip_without_compiler


def test_tools_available_reports_both_tools() -> None:
    found = pipeline.tools_available()
    assert set(found) == {"pandoc", "typst"}


def test_skip_reason_names_the_missing_tool(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    monkeypatch.setattr(pipeline, "tools_available", lambda: {"pandoc": "3.10.2", "typst": None})

    class Item:
        keywords = {"compiler": True}
        markers: list[pytest.MarkDecorator] = []

        def add_marker(self, marker: pytest.MarkDecorator) -> None:
            self.markers.append(marker)

    item = Item()
    _skip_without_compiler([item])  # type: ignore[list-item]
    assert item.markers and item.markers[0].kwargs["reason"] == "compiler missing: typst"


def test_missing_tool_on_path_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert pipeline.tools_available() == {"pandoc": None, "typst": None}
