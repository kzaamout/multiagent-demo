"""A brand colour the template cannot use becomes an assumption on the run (spec FR-013)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agents.stubs import clean_run
from app.compile.brand import DEFAULT_COLOUR
from app.config import Settings
from tests.conftest import run_scenario

pytestmark = pytest.mark.compiler


def _dataset(tmp_path: Path, colour: str) -> Path:
    folder = tmp_path / "dataset"
    folder.mkdir()
    (folder / "brand.yaml").write_text(
        f'prospect_name: "Acme"\nprimary_colour: "{colour}"\n', encoding="utf-8"
    )
    return folder


async def test_bad_colour_is_recorded_once_before_the_first_pages(settings: Settings, tmp_path: Path) -> None:
    folder = _dataset(tmp_path, "navy")
    events = await run_scenario(clean_run.SCENARIO, settings, record=True, dataset_folder=folder)
    assumptions = [
        e for e in events if e.type == "assumption.accepted" and e.payload["question_id"] == "brand_colour"
    ]
    assert len(assumptions) == 1
    assert assumptions[0].payload["default_used"] == DEFAULT_COLOUR and assumptions[0].stage == "assemble"
    types = [e.type for e in events]
    assert types.index("assumption.accepted", types.index("draft.committed")) < types.index(
        "artifact.compiled"
    )
    package = next(e for e in events if e.type == "handoff.ready").payload["package"]
    assert "brand_colour" in package["assumptions"]


async def test_a_good_colour_and_a_missing_logo_add_no_assumption(settings: Settings, tmp_path: Path) -> None:
    folder = _dataset(tmp_path, "#1F3A5F")
    events = await run_scenario(clean_run.SCENARIO, settings, record=True, dataset_folder=folder)
    assert not [
        e for e in events if e.type == "assumption.accepted" and e.payload["question_id"] == "brand_colour"
    ]
