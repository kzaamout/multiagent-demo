"""The Compare strip's figures carry compute time (spec 012 decision 13, research D15, SC-012)."""

from __future__ import annotations

import pytest

from app.agents.stubs import planted_inconsistency
from app.config import Settings
from app.runs.comparison import comparison
from app.runs.working_time import working_ms
from tests.conftest import run_scenario

pytestmark = pytest.mark.dataset


async def test_a_team_recording_shows_working_time_shorter_by_its_waits(settings: Settings) -> None:
    events = await run_scenario(planted_inconsistency.SCENARIO, settings, record=True)
    team = comparison(settings.runs_dir, "planted-inconsistency")["team"]
    assert team is not None
    assert team["working_ms"] == working_ms(events)
    # The golden scenario waits 12 s on the clarification batch and 1 s on the Handoff approval.
    assert team["elapsed_ms"] - team["working_ms"] == 13000
