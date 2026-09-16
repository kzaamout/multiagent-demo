"""Review routing on live runs with scripted seats: rework to the Estimator, rework to the Writer, and an
exhausted retry budget (S3, US1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.agents.base import HumanScript
from app.orchestrator.driver import drive
from app.runs.golden import read_golden, transitions
from app.schema.events import Event
from tests.integration.s2 import live_harness as h
from tests.support.scripted_model import Turn, reply

pytestmark = pytest.mark.dataset

GOLDEN = Path(__file__).resolve().parents[3] / "datasets" / "planted-inconsistency" / "golden-events.jsonl"
FINDING = "Section 3 states a 200 A main breaker for LP-1; the bill of materials and E-001 show 225 A."
SCRIPT = HumanScript(answers={}, decision="approve")


def fail(route_to: str, agent_id: str) -> Turn:
    finding: dict[str, Any] = {
        "id": "f1",
        "severity": "major",
        "text": FINDING,
        "evidence": "Scope section, second paragraph",
        "route_to": route_to,
        "agent_id": agent_id,
    }
    return reply(
        {"verdict": "fail", "summary": "Fail. One rating contradicts itself.", "findings": [finding]}
    )


def dispatched_after_retry(events: list[Event]) -> list[str]:
    retry = next(e.seq for e in events if e.type == "retry.incremented")
    return [e.payload["agent_id"] for e in events if e.type == "task.dispatched" and e.seq > retry]


async def test_fail_routed_to_the_estimator_reworks_and_passes(tmp_path: Path) -> None:
    turns = h.full_turns(blocking=False)
    turns["estimator"] = h.estimator_turns() + h.estimator_turns()
    turns["writer"] = h.writer_turns() + h.writer_turns()
    turns["reviewer"] = [fail("work", "estimator"), *h.reviewer_turns()]
    orchestrator = h.build(tmp_path, turns, "30000000-0000-4000-8000-000000000401")
    await drive(orchestrator, SCRIPT)
    events = orchestrator.events
    assert transitions(events) == transitions(read_golden(GOLDEN))
    assert events[-1].payload["exit"] == "reviewer_pass"
    assert events[-1].payload["summary"]["retries"]["count"] == 1
    assert dispatched_after_retry(events) == ["estimator", "writer"], (
        "only the routed specialist reworks, then the Writer reassembles"
    )
    estimator_bundles = [b for b in orchestrator.bundles.values() if "Estimator on an electrical" in b.system]
    assert any(FINDING in b.model_dump_json() for b in estimator_bundles), (
        "the finding is in the rework context"
    )
    assert not any(
        FINDING in b.model_dump_json() for b in orchestrator.bundles.values() if "Pricing on an" in b.system
    )
    assert [e.payload["version"] for e in events if e.type == "draft.committed"] == [1, 2]


async def test_fail_routed_to_assemble_reworks_only_the_writer(tmp_path: Path) -> None:
    turns = h.full_turns(blocking=False)
    turns["writer"] = h.writer_turns() + h.writer_turns()
    turns["reviewer"] = [fail("assemble", "writer"), *h.reviewer_turns()]
    orchestrator = h.build(tmp_path, turns, "30000000-0000-4000-8000-000000000402")
    await drive(orchestrator, SCRIPT)
    events = orchestrator.events
    assert ("review", "assemble", "backward") in transitions(events)
    assert dispatched_after_retry(events) == ["writer"], "no specialist reworks"
    assert events[-1].payload["exit"] == "reviewer_pass"


async def test_three_fails_exhaust_the_budget(tmp_path: Path) -> None:
    turns = h.full_turns(blocking=False)
    turns["writer"] = h.writer_turns() * 3
    turns["reviewer"] = [fail("assemble", "writer")] * 3
    orchestrator = h.build(tmp_path, turns, "30000000-0000-4000-8000-000000000403")
    await drive(orchestrator, SCRIPT)
    last = orchestrator.events[-1]
    assert last.payload["exit"] == "retry_exhausted"
    assert last.payload["summary"]["unresolved_findings"] == ["f1"]
    assert "retry budget is spent" in (last.reason or "")
