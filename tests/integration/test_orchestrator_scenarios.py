from __future__ import annotations

import asyncio
import dataclasses

import pytest

from app.agents.base import Emit, HumanScript
from app.agents.stubs import SCENARIOS
from app.agents.stubs._common import finding, meter, verdict
from app.agents.stubs._rfp_base import Bundles
from app.config import Settings
from app.orchestrator.clock import Clock
from app.orchestrator.driver import drive
from app.schema.events import Event, validate_run
from tests.conftest import START, make_orchestrator, run_scenario

EXPECTED = {
    "clean-run": ("reviewer_pass", 0),
    "planted-inconsistency": ("reviewer_pass", 1),
    "missing-sheet": ("blocker_escalated", 0),
    "missing-price": ("reviewer_pass", 0),
    "not-ready": ("not_ready", 0),
    "prospect-own": ("dry_intake", 0),
}


def of_type(events: list[Event], type_: str) -> list[Event]:
    return [e for e in events if e.type == type_]


@pytest.mark.parametrize("dataset_id", sorted(EXPECTED))
async def test_scenario_reaches_readme_exit(dataset_id: str, settings: Settings) -> None:
    events = await run_scenario(SCENARIOS[dataset_id], settings)
    assert validate_run(events) == []
    terminal = events[-1]
    assert terminal.type == "run.terminated"
    exit_value, retries = EXPECTED[dataset_id]
    assert terminal.payload["exit"] == exit_value
    assert terminal.payload["summary"]["retries"]["count"] == retries
    assert terminal.payload["summary"]["event_count"] == len(events)


async def test_planted_inconsistency_path(settings: Settings) -> None:
    events = await run_scenario(SCENARIOS["planted-inconsistency"], settings)
    backward = [e for e in of_type(events, "stage.changed") if e.payload["direction"] == "backward"]
    assert [(e.payload["from"], e.payload["to"]) for e in backward] == [("review", "work")]
    assert [e.payload["count"] for e in of_type(events, "retry.incremented")] == [1]
    assert len(of_type(events, "draft.committed")) == 2
    asked = of_type(events, "clarification.asked")
    assert len(asked) == 1 and asked[0].payload["question_ids"] == [
        "q_service_voltage",
        "q_led_retrofit_alternate",
    ]
    assert [e.payload["question_id"] for e in of_type(events, "assumption.accepted")] == ["q_bid_validity"]
    appended = of_type(events, "knowledge.appended")
    assert [e.payload["entries"][0]["question_id"] for e in appended] == [
        "q_service_voltage",
        "q_led_retrofit_alternate",
    ]
    assert all(events.index(k) > events.index(of_type(events, "clarification.answered")[0]) for k in appended)
    handoff = of_type(events, "handoff.ready")[0]
    assert handoff.payload["package"]["assumptions"] == ["q_bid_validity"]
    assert events[-2].type == "human.approved"


async def test_pricing_waits_for_estimator(settings: Settings) -> None:
    events = await run_scenario(SCENARIOS["clean-run"], settings)
    estimator_done = next(
        i for i, e in enumerate(events) if e.type == "task.completed" and e.payload["task_id"] == "t1"
    )
    pricing_first = next(
        i for i, e in enumerate(events) if e.type == "task.progress" and e.payload["task_id"] == "t2"
    )
    assert pricing_first > estimator_done
    assert not of_type(events, "knowledge.appended"), "no blocking question in Clean run"


async def test_missing_sheet_escalate_lists_what_is_missing(settings: Settings) -> None:
    events = await run_scenario(SCENARIOS["missing-sheet"], settings)
    answered = of_type(events, "clarification.answered")
    assert [e.payload["action"] for e in answered] == ["escalate"]
    assert not of_type(events, "knowledge.appended"), "blocker answers stay run-local"
    missing = events[-1].payload["summary"]["missing"]
    assert len(missing) == 1 and "LP-2" in missing[0]["item"]
    asked = of_type(events, "clarification.asked")[0]
    assert asked.payload["blocker"]["blocker_id"] == "b_lp2_schedule"


async def test_missing_sheet_answer_path_continues_to_pass(settings: Settings) -> None:
    script = HumanScript(blocker_action="answer", blocker_answer="Size LP-2 like LP-1", decision="approve")
    events = await run_scenario(SCENARIOS["missing-sheet"], settings, script)
    assert events[-1].payload["exit"] == "reviewer_pass"
    assert not of_type(events, "knowledge.appended")


async def test_not_ready_lists_two_missing_items_and_stops_before_plan(settings: Settings) -> None:
    events = await run_scenario(SCENARIOS["not-ready"], settings)
    stages = [e.payload["to"] for e in of_type(events, "stage.changed")]
    assert stages == ["intake"]
    summary = events[-1].payload["summary"]
    assert {m["item"] for m in summary["missing"]} == {"Division 26 specification", "Submission deadline"}
    assert summary["readiness_verdict"] == "not_ready"


async def test_prospect_own_is_a_dry_intake(settings: Settings) -> None:
    events = await run_scenario(SCENARIOS["prospect-own"], settings)
    assert events[-1].payload["summary"]["readiness_verdict"] == "ready_with_assumptions"
    assert not of_type(events, "plan.created")


async def test_missing_price_carries_minor_finding(settings: Settings) -> None:
    events = await run_scenario(SCENARIOS["missing-price"], settings)
    assert of_type(events, "handoff.ready")[0].payload["package"]["unresolved_findings"] == ["f1"]
    assert events[-1].payload["summary"]["unresolved_findings"] == ["f1"]


async def test_review_without_progress_goes_through_handoff_with_a_stop_reason(settings: Settings) -> None:
    """The same failing verdict twice: the second cycle reduces nothing, so review stops after one rework."""
    base = SCENARIOS["planted-inconsistency"]
    fail = base.review[0]
    scenario = dataclasses.replace(base, review=[fail, fail], assemble=[base.assemble[0]] * 2)
    events = await run_scenario(scenario, settings)
    assert events[-1].payload["exit"] == "retry_exhausted"
    assert [e.payload["count"] for e in of_type(events, "retry.incremented")] == [1]
    assert of_type(events, "retry.incremented")[0].payload["budget"] == settings.review_max_cycles - 1
    assert of_type(events, "handoff.ready")[0].payload["exit_determination"] == "retry_exhausted"
    summary = events[-1].payload["summary"]
    assert summary["unresolved_findings"] == ["f1", "f2"]
    assert summary["stop_reason"] == "no_progress"
    assert summary["retries"] == {"count": 1, "budget": settings.review_max_cycles - 1}
    assert "verdict is pass" not in (events[-1].reason or ""), "the closing reason matches the exit"
    assert "no progress in the last review cycle" in (events[-1].reason or "")
    assert "no progress in the last review cycle" in (of_type(events, "stage.changed")[-1].reason or "")


async def test_a_pass_carries_no_stop_reason(settings: Settings) -> None:
    events = await run_scenario(SCENARIOS["planted-inconsistency"], settings)
    assert events[-1].payload["exit"] == "reviewer_pass"
    assert events[-1].payload["summary"]["stop_reason"] is None


async def test_review_fail_routed_to_assemble_uses_backward_arrow(settings: Settings) -> None:
    base = SCENARIOS["clean-run"]
    b = Bundles("clean-run", "test")
    writing_fail = verdict(
        118000,
        False,
        [finding("w1", "major", "Section 2 is unclear.", "page 2", "assemble", "writer")],
        "",
        b.reviewer,
        meter(100, 0.0, 10),
    )
    scenario = dataclasses.replace(
        base, review=[[writing_fail], base.review[0]], assemble=[base.assemble[0], base.assemble[0]]
    )
    events = await run_scenario(scenario, settings)
    backward = [
        (e.payload["from"], e.payload["to"])
        for e in of_type(events, "stage.changed")
        if e.payload["direction"] == "backward"
    ]
    assert backward == [("review", "assemble")]
    assert events[-1].payload["exit"] == "reviewer_pass"


async def test_cost_ceiling_terminates_before_further_dispatch(tmp_path: object) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", cost_ceiling=0.10, agent_mode="stub")  # type: ignore[operator]
    events = await run_scenario(SCENARIOS["clean-run"], settings)
    assert events[-1].payload["exit"] == "cost_ceiling"
    breach = max(i for i, e in enumerate(events) if e.type == "meter.update")
    assert all(e.type != "task.dispatched" for e in events[breach + 1 :])
    assert events[breach + 1].type == "run.terminated"


async def test_work_to_intake_once_then_blocker(settings: Settings) -> None:
    base = SCENARIOS["missing-sheet"]
    b = base.intake[0].bundle
    route = Emit(
        "estimator",
        "blocker.raised",
        50000,
        {
            "blocker_id": "b_brief",
            "task_id": "t1",
            "agent_id": "estimator",
            "description": "The brief omits the service size.",
            "needs_human": False,
            "route_back_to": "intake",
        },
        b,
    )
    second = Emit(
        "estimator",
        "blocker.raised",
        60000,
        {
            "blocker_id": "b_brief2",
            "task_id": "t1",
            "agent_id": "estimator",
            "description": "The brief still omits the service size.",
            "needs_human": False,
            "route_back_to": "intake",
        },
        b,
    )
    scenario = dataclasses.replace(
        base,
        tasks={"t1": [route], "t2": base.tasks["t2"]},
        blocker_answer_continuation={"t1": [second]},
    )
    events = await run_scenario(scenario, settings, HumanScript(blocker_action="escalate"))
    backward = [
        (e.payload["from"], e.payload["to"])
        for e in of_type(events, "stage.changed")
        if e.payload["direction"] == "backward"
    ]
    assert backward == [("work", "intake")]
    asked = of_type(events, "clarification.asked")
    assert asked and asked[-1].payload["blocker"]["blocker_id"] == "b_brief2"
    assert events[-1].payload["exit"] == "blocker_escalated"
    assert not of_type(events, "retry.incremented")


async def test_stop_while_waiting_for_human(settings: Settings) -> None:
    orchestrator = make_orchestrator(SCENARIOS["planted-inconsistency"], settings)
    task = asyncio.create_task(orchestrator.run())
    await asyncio.wait_for(orchestrator.human_needed.wait(), 5)
    orchestrator.stop()
    await asyncio.wait_for(task, 5)
    assert orchestrator.events[-1].payload["exit"] == "stopped"
    assert validate_run(orchestrator.events) == []


async def test_pause_holds_dispatch_until_resume(settings: Settings) -> None:
    clock = Clock(START, pace=2000.0)
    orchestrator = make_orchestrator(SCENARIOS["clean-run"], settings, clock=clock)
    orchestrator.pause()
    task = asyncio.create_task(orchestrator.run())
    await asyncio.sleep(0.3)
    stage_changes = [e for e in orchestrator.events if e.type == "stage.changed"]
    assert stage_changes == [], "no stage change while paused"
    assert [e.type for e in orchestrator.events] == ["run.started"]
    orchestrator.resume()
    waiter = asyncio.create_task(drive_existing(orchestrator, task))
    await asyncio.wait_for(waiter, 10)
    assert orchestrator.events[-1].payload["exit"] == "reviewer_pass"


async def drive_existing(orchestrator: object, task: asyncio.Task[None]) -> None:
    from app.orchestrator.orchestrator import Orchestrator

    assert isinstance(orchestrator, Orchestrator)
    while not task.done():
        waiter = asyncio.create_task(orchestrator.human_needed.wait())
        done, _ = await asyncio.wait({task, waiter}, return_when=asyncio.FIRST_COMPLETED)
        if task in done:
            waiter.cancel()
            break
        if orchestrator.pending()["kind"] == "handoff":
            orchestrator.submit_decision("approve")
        await asyncio.sleep(0)
    await task


async def test_invalid_stub_event_stops_the_run(settings: Settings) -> None:
    base = SCENARIOS["clean-run"]
    bad = Emit(
        "intake",
        "intake.readiness",
        1000,
        {"verdict": "maybe", "checklist": [], "legibility": []},
        base.intake[0].bundle,
    )
    scenario = dataclasses.replace(base, intake=[bad])
    orchestrator = make_orchestrator(scenario, settings)
    with pytest.raises(Exception):  # noqa: B017
        await drive(orchestrator, scenario.human_script)
    assert orchestrator.events[-1].type == "run.terminated"
    assert orchestrator.events[-1].payload["exit"] == "stopped"
    assert all(e.type != "intake.readiness" for e in orchestrator.events)


async def test_names_in_reasons_follow_the_roster(settings: Settings) -> None:
    events = await run_scenario(SCENARIOS["planted-inconsistency"], settings)
    route = next(e for e in of_type(events, "stage.changed") if e.payload["direction"] == "backward")
    assert "Elena confirms" in route.payload["target_reason"]
    assert "{" not in route.payload["target_reason"]
