"""Blockers on live runs with scripted seats: Answer, Escalate, and the single route back to Intake (S3, US2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agents.base import HumanScript
from app.orchestrator.driver import drive
from app.runs.golden import read_golden, transitions
from app.schema.events import Event
from tests.integration.s2 import live_harness as h
from tests.support.scripted_model import Turn, reply

GOLDEN = Path(__file__).resolve().parents[3] / "datasets" / "missing-sheet" / "golden-events.jsonl"
DESCRIPTION = "Panel LP-2 appears on single-line E-001 but its schedule E-003 is not in the drawing set."


def blocker(route_back_to: str | None = None, needs_human: bool = True) -> Turn:
    body: dict[str, Any] = {
        "description": DESCRIPTION,
        "needs_human": needs_human,
        "route_back_to": route_back_to,
    }
    return reply({"blocker": body})


def of_type(events: list[Event], type_: str) -> list[Event]:
    return [e for e in events if e.type == type_]


async def test_escalate_ends_with_the_missing_item(tmp_path: Path) -> None:
    turns = h.full_turns(blocking=False)
    turns["estimator"] = [h.estimator_turns()[0], blocker()]
    orchestrator = h.build(tmp_path, turns, "30000000-0000-4000-8000-000000000301")
    await drive(orchestrator, HumanScript(answers={}, blocker_action="escalate", decision="approve"))
    events = orchestrator.events
    asked = of_type(events, "clarification.asked")
    assert len(asked) == 1 and asked[0].payload["blocker"]["description"] == DESCRIPTION
    last = events[-1]
    assert last.payload["exit"] == "blocker_escalated"
    assert [m["item"] for m in last.payload["summary"]["missing"]] == [DESCRIPTION]
    assert transitions(events) == transitions(read_golden(GOLDEN))
    assert not of_type(events, "knowledge.appended")


async def test_answer_reaches_the_estimator_and_stays_run_local(tmp_path: Path) -> None:
    answer = "Treat LP-2 as a 30-circuit 100 A panelboard with one 20 A circuit for the program room."
    turns = h.full_turns(blocking=False)
    turns["estimator"] = [h.estimator_turns()[0], blocker(), *h.estimator_turns()]
    orchestrator = h.build(tmp_path, turns, "30000000-0000-4000-8000-000000000302")
    await drive(
        orchestrator,
        HumanScript(answers={}, blocker_action="answer", blocker_answer=answer, decision="approve"),
    )
    events = orchestrator.events
    assert events[-1].payload["exit"] == "reviewer_pass"
    answered = of_type(events, "clarification.answered")
    assert len(answered) == 1 and answered[0].payload["action"] == "answer"
    estimator = [x for x in orchestrator.bundles.values() if "the Estimator on an electrical" in x.system]
    pricing = [x for x in orchestrator.bundles.values() if "Pricing on an electrical" in x.system]
    assert any(answer in x.task for x in estimator), "the answer is in the blocked specialist's task"
    assert pricing and not any(answer in x.model_dump_json() for x in pricing), "Pricing never sees the brief"
    assert answer not in h.KnowledgeStore(tmp_path / "knowledge").read(h.CLIENT)
    assert not of_type(events, "knowledge.appended")


async def test_route_back_to_intake_once_then_a_blocker(tmp_path: Path) -> None:
    turns = h.full_turns(blocking=False)
    turns["intake"] = h.intake_turns(blocking=False) + h.intake_turns(blocking=False)
    turns["estimator"] = [
        h.estimator_turns()[0],
        blocker("intake", needs_human=False),
        blocker("intake", needs_human=False),
    ]
    orchestrator = h.build(tmp_path, turns, "30000000-0000-4000-8000-000000000303")
    await drive(orchestrator, HumanScript(answers={}, blocker_action="escalate", decision="approve"))
    events = orchestrator.events
    backward = [(a, b) for a, b, d in transitions(events) if d == "backward"]
    assert backward == [("work", "intake")], "one route back to Intake"
    assert len(of_type(events, "clarification.asked")) == 1, "the second route back became a blocker"
    assert events[-1].payload["exit"] == "blocker_escalated"
