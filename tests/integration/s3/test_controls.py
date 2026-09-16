"""Presenter controls on live runs with scripted models: pause, resume, and stop (S3, US5)."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from app.agents.base import HumanScript
from app.config import Settings
from app.orchestrator.driver import drive
from app.orchestrator.orchestrator import Orchestrator
from app.runs.bus import StreamBus
from app.runs.registry import Registry
from app.schema.events import Event
from tests.integration.s2 import live_harness as h
from tests.support.scripted_model import HANG, WaitFor

pytestmark = pytest.mark.dataset

SCRIPT = HumanScript(answers={"q_service_voltage": "120/208 V"}, decision="approve")


async def wait_until(
    orchestrator: Orchestrator, test: Callable[[list[Event]], bool], limit: float = 10.0
) -> None:
    deadline = time.monotonic() + limit
    while not test(orchestrator.events):
        if time.monotonic() > deadline:
            raise AssertionError(f"timed out; last events {[e.type for e in orchestrator.events[-5:]]}")
        await asyncio.sleep(0.01)


async def test_pause_holds_new_work_and_resume_continues(tmp_path: Path) -> None:
    release = asyncio.Event()
    turns = h.full_turns(blocking=False)
    vision, calculate, final = h.estimator_turns()
    assert isinstance(calculate, list)
    turns["estimator"] = [vision, WaitFor(release, calculate), final]
    orchestrator = h.build(tmp_path, turns, "30000000-0000-4000-8000-000000000101")
    runner = asyncio.create_task(drive(orchestrator, SCRIPT))
    await wait_until(
        orchestrator,
        lambda ev: any(e.type == "tool.called" and e.payload["agent_id"] == "estimator" for e in ev),
    )
    orchestrator.pause()
    await wait_until(orchestrator, lambda ev: any(e.type == "run.paused" for e in ev))
    release.set()
    await wait_until(
        orchestrator,
        lambda ev: any(e.type == "task.completed" and e.payload["agent_id"] == "estimator" for e in ev),
    )
    await asyncio.sleep(0.3)
    assert not any(
        e.payload.get("agent_id") == "pricing" and e.type != "task.dispatched" for e in orchestrator.events
    ), "Pricing does not start while paused"
    orchestrator.resume()
    await asyncio.wait_for(runner, 30)
    events = orchestrator.events
    paused = next(e for e in events if e.type == "run.paused")
    resumed = next(e for e in events if e.type == "run.resumed")
    assert (
        paused.payload == {"by": "human"}
        and paused.reason
        and resumed.payload == {"by": "human"}
        and resumed.reason
    )
    between = [e for e in events if paused.seq < e.seq < resumed.seq]
    assert not any(e.type == "task.dispatched" for e in between)
    assert not any(e.payload.get("agent_id") == "pricing" for e in between)
    assert events[-1].type == "run.terminated" and events[-1].payload["exit"] == "reviewer_pass"


async def test_stop_during_a_call_that_never_returns(tmp_path: Path) -> None:
    turns = h.full_turns(blocking=False)
    turns["estimator"] = [h.estimator_turns()[0], HANG]
    orchestrator = h.build(tmp_path, turns, "30000000-0000-4000-8000-000000000102")
    runner = asyncio.create_task(drive(orchestrator, SCRIPT))
    await wait_until(
        orchestrator,
        lambda ev: any(e.type == "tool.called" and e.payload["agent_id"] == "estimator" for e in ev),
    )
    await asyncio.sleep(0.2)
    started = time.monotonic()
    orchestrator.stop()
    await asyncio.wait_for(runner, 5)
    assert time.monotonic() - started < 5
    events = orchestrator.events
    assert events[-1].type == "run.terminated" and events[-1].payload["exit"] == "stopped"
    count = len(events)
    await asyncio.sleep(0.3)
    assert len(orchestrator.events) == count, "nothing is emitted after the termination"


async def test_stop_while_waiting_on_a_question_and_pause_is_ignored_there(tmp_path: Path) -> None:
    orchestrator = h.build(tmp_path, h.full_turns(blocking=True), "30000000-0000-4000-8000-000000000103")
    runner = asyncio.create_task(orchestrator.run())
    orchestrator.attach_task(runner)
    await wait_until(orchestrator, lambda ev: any(e.type == "clarification.asked" for e in ev))
    orchestrator.pause()
    await asyncio.sleep(0.2)
    assert not any(e.type == "run.paused" for e in orchestrator.events)
    orchestrator.stop()
    await asyncio.wait_for(runner, 5)
    types = [e.type for e in orchestrator.events]
    assert types[-1] == "run.terminated" and orchestrator.events[-1].payload["exit"] == "stopped"
    assert "clarification.answered" not in types


async def test_registry_attaches_the_run_task(tmp_path: Path) -> None:
    registry = Registry(Settings(runs_dir=tmp_path / "runs", stub_pace=50.0, agent_mode="stub"), StreamBus())
    orchestrator = registry.start_run("not-ready")
    assert orchestrator._run_task is not None and not orchestrator._run_task.done()
    orchestrator.stop()
    await asyncio.wait_for(orchestrator.finished.wait(), 5)
    assert orchestrator.events[-1].payload["exit"] in ("stopped", "not_ready")
