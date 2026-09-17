"""Review routing on live runs with scripted seats: rework to the Estimator, rework to the Writer, and the
review limit stopping on a repeated finding or at the ceiling (S3 US1, S3b US1)."""

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


def fail(
    route_to: str,
    agent_id: str,
    evidence: str = "Scope section, second paragraph",
    extra: list[tuple[str, str]] | None = None,
) -> Turn:
    findings: list[dict[str, Any]] = [
        {
            "id": "f1",
            "severity": "major",
            "text": FINDING,
            "evidence": evidence,
            "route_to": route_to,
            "agent_id": agent_id,
        }
    ]
    for fid, where in extra or []:
        findings.append(
            {
                "id": fid,
                "severity": "major",
                "text": "A figure is wrong.",
                "evidence": where,
                "route_to": route_to,
                "agent_id": agent_id,
            }
        )
    return reply({"verdict": "fail", "summary": "Fail. One rating contradicts itself.", "findings": findings})


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


async def test_a_repeated_finding_stops_review(tmp_path: Path) -> None:
    """Cycle 2 has fewer serious findings than cycle 1 but repeats one of them on the same evidence and route."""
    turns = h.full_turns(blocking=False)
    turns["writer"] = h.writer_turns() * 2
    first = fail("assemble", "writer", extra=[("f2", "Pricing summary table, total row")])
    turns["reviewer"] = [first, fail("assemble", "writer")]
    orchestrator = h.build(tmp_path, turns, "30000000-0000-4000-8000-000000000403")
    await drive(orchestrator, SCRIPT)
    last = orchestrator.events[-1]
    assert last.payload["exit"] == "retry_exhausted"
    assert last.payload["summary"]["stop_reason"] == "repeated_finding"
    assert last.payload["summary"]["unresolved_findings"] == ["f1"]
    assert last.payload["summary"]["retries"]["count"] == 1
    assert "a finding repeated from the previous cycle" in (last.reason or "")


async def test_progress_every_cycle_stops_at_the_ceiling(tmp_path: Path) -> None:
    """Four serious findings, then three, two, and one: every cycle makes progress, so the ceiling is the stop."""
    turns = h.full_turns(blocking=False)
    turns["writer"] = h.writer_turns() * 4
    turns["reviewer"] = [
        fail(
            "assemble",
            "writer",
            extra=[
                ("f2", "Scope, third paragraph"),
                ("f3", "Exclusions, item 2"),
                ("f4", "Assumptions, item 3"),
            ],
        ),
        fail(
            "assemble",
            "writer",
            evidence="Assumptions, item 1",
            extra=[("f2", "Exclusions, item 4"), ("f3", "Schedule of values, row 2")],
        ),
        fail(
            "assemble",
            "writer",
            evidence="Pricing summary, markup line",
            extra=[("f2", "Cover, project name")],
        ),
        fail("assemble", "writer", evidence="Executive summary, first sentence"),
    ]
    orchestrator = h.build(tmp_path, turns, "30000000-0000-4000-8000-000000000404")
    await drive(orchestrator, SCRIPT)
    events = orchestrator.events
    last = events[-1]
    assert last.payload["exit"] == "retry_exhausted"
    assert last.payload["summary"]["stop_reason"] == "max_cycles"
    assert [e.payload["count"] for e in events if e.type == "retry.incremented"] == [1, 2, 3]
    assert [e.payload["version"] for e in events if e.type == "draft.committed"] == [1, 2, 3, 4]
