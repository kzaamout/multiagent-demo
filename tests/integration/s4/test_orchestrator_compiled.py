"""The Orchestrator emits artifact.compiled right after the commit and before the Reviewer (spec FR-001)."""

from __future__ import annotations

import pytest

from app.agents.stubs import clean_run
from app.config import Settings
from tests.conftest import run_scenario

pytestmark = pytest.mark.compiler


async def test_compiled_follows_the_commit_before_any_review(settings: Settings) -> None:
    events = await run_scenario(clean_run.SCENARIO, settings, record=True)
    types = [e.type for e in events]
    commit = types.index("draft.committed")
    compiled = types.index("artifact.compiled")
    between = {t for t in types[commit + 1 : compiled]}
    assert between <= {"meter.update"}, "only the commit's meter delta sits between the commit and the pages"
    first_review = next(i for i, e in enumerate(events) if e.stage == "review")
    assert compiled < first_review
    assert events[compiled].actor == "system"


async def test_handoff_package_names_the_final_version(settings: Settings) -> None:
    events = await run_scenario(clean_run.SCENARIO, settings, record=True)
    compiled = [e for e in events if e.type == "artifact.compiled"][-1].payload
    package = next(e for e in events if e.type == "handoff.ready").payload["package"]
    assert package["pdf_path"] == compiled["pdf_path"]
    assert package["page_images"] == compiled["page_images"]
