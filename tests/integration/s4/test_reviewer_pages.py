"""The Reviewer receives the page images and the page text, never the markdown (spec FR-007, FR-008)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from app.agents.base import HumanScript
from app.orchestrator.driver import drive
from app.runs.registry import LiveUnavailable
from tests.integration.s2 import live_harness as h

pytestmark = [pytest.mark.compiler, pytest.mark.dataset]

SCRIPT = HumanScript(answers={"q_service_voltage": "120/208 V"}, decision="approve")
RUN_ID = "50000000-0000-4000-8000-000000000501"


async def test_reviewer_bundle_carries_pages_and_page_text(tmp_path: Path) -> None:
    turns = h.full_turns(blocking=False)
    orchestrator = h.build(tmp_path, turns, RUN_ID)
    await drive(orchestrator, SCRIPT)
    events = orchestrator.events
    verdict = next(e for e in events if e.type == "review.verdict")
    assert verdict.prompt_ref is not None
    bundle = orchestrator.bundles[verdict.prompt_ref]
    compiled = next(e for e in events if e.type == "artifact.compiled").payload
    assert bundle.images == compiled["page_images"] and len(bundle.images) >= 1
    assert "## Page 1 text (source id: page-1)" in bundle.context_slice
    assert "Proposal" in bundle.context_slice, "the page text carries the document's words"
    assert "## Draft v1" not in bundle.context_slice and "{{" not in bundle.context_slice
    assert "## Reviewer criteria" in bundle.context_slice and "## Brief" in bundle.context_slice
    # The scripted model saw one image block per page on its first message.
    reviewer_model = cast(Any, orchestrator.scenario).seat_models["reviewer"].strands_model
    first = reviewer_model.messages[0]
    images = [b for m in first for b in m.get("content", []) if "image" in b]
    assert len(images) == len(bundle.images)
    assert all(
        b["image"]["format"] == "png" and b["image"]["source"]["bytes"][:8] == b"\x89PNG\r\n\x1a\n"
        for b in images
    )
    # The recorded bundle on disk says the same.
    saved = json.loads(
        (tmp_path / "runs" / RUN_ID / "prompts" / f"{verdict.prompt_ref}.json").read_text(encoding="utf-8")
    )
    assert saved["images"] == bundle.images


async def test_reviewer_without_image_input_refuses_the_run(tmp_path: Path) -> None:
    turns = h.full_turns(blocking=False)
    with pytest.raises(LiveUnavailable) as caught:
        h.build(tmp_path, turns, RUN_ID, image_input={"reviewer": False})
    assert "Reviewer" in caught.value.problems[0] and "page images" in caught.value.problems[0]
