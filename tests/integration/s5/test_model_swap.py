"""A Settings swap on a live run: model.changed at once, the seat's next call on the new model (S5, US1)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.agents.base import HumanScript
from app.live.seat_call import SeatModel
from app.orchestrator.driver import drive
from app.schema.events import Agent, Model
from tests.integration.s2 import live_harness as h
from tests.support.scripted_model import ScriptedModel

pytestmark = pytest.mark.dataset

SCRIPT = HumanScript(answers={}, decision="approve")
NEW_MODEL = Model(provider="test", model_id="scripted-b", label="scripted B for the Estimator")


def new_estimator_model() -> SeatModel:
    return SeatModel(
        strands_model=ScriptedModel(h.estimator_turns(), tokens_in=700, tokens_out=200),
        model=NEW_MODEL,
        price_in=1.0,
        price_out=1.0,
    )


async def swap_after(orchestrator, type_: str, seat: str, seat_model: SeatModel) -> None:  # type: ignore[no-untyped-def]
    """Wait until the run has emitted `type_`, then swap like the Settings route does."""
    while not any(e.type == type_ for e in orchestrator.events):
        if orchestrator.state.terminated:
            raise AssertionError(f"run ended before {type_}")
        await asyncio.sleep(0.005)
    agent = orchestrator.roster[seat].model_copy(update={"model": seat_model.model})
    await orchestrator.change_model(seat, agent, seat_model)


async def test_swap_between_intake_and_work_changes_the_next_dispatch(tmp_path: Path) -> None:
    turns = h.full_turns(blocking=False)
    turns["estimator"] = []  # the old model is never called: the swap lands during Plan, before Work
    orchestrator = h.build(tmp_path, turns, "50000000-0000-4000-8000-000000000501")
    swap = asyncio.create_task(
        swap_after(orchestrator, "intake.readiness", "estimator", new_estimator_model())
    )
    await drive(orchestrator, SCRIPT)
    await swap
    events = orchestrator.events
    changed = [e for e in events if e.type == "model.changed"]
    assert len(changed) == 1
    payload = changed[0].payload
    assert payload["agent_id"] == "estimator"
    assert payload["from_model"]["label"] == "scripted estimator"
    assert payload["to_model"]["label"] == NEW_MODEL.label
    assert changed[0].actor == "system" and changed[0].stage in ("intake", "plan")
    estimator_actors = [
        e.actor for e in events if isinstance(e.actor, Agent) and e.actor.agent_id == "estimator"
    ]
    assert estimator_actors and all(a.model.label == NEW_MODEL.label for a in estimator_actors)
    bundles = [b for b in orchestrator.bundles.values() if "Estimator on an electrical" in b.system]
    assert bundles and all(b.model.label == NEW_MODEL.label for b in bundles)
    pricing = [b for b in orchestrator.bundles.values() if "Pricing on an electrical" in b.system]
    assert pricing and all(b.model.label == "scripted pricing" for b in pricing)
    assert events[-1].payload["exit"] == "reviewer_pass"
    meters = [e for e in events if e.type == "meter.update" and e.payload["agent_id"] == "estimator"]
    assert meters and all(m.payload["tokens_in"] == 700 for m in meters), "usage came from the new model"


async def test_swap_after_termination_is_refused(tmp_path: Path) -> None:
    orchestrator = h.build(tmp_path, h.full_turns(blocking=False), "50000000-0000-4000-8000-000000000502")
    await drive(orchestrator, SCRIPT)
    with pytest.raises(RuntimeError, match="next run"):
        await orchestrator.change_model("estimator", orchestrator.roster["estimator"], new_estimator_model())
    assert orchestrator.events[-1].type == "run.terminated"


async def test_unknown_seat_is_refused(tmp_path: Path) -> None:
    orchestrator = h.build(tmp_path, h.full_turns(blocking=False), "50000000-0000-4000-8000-000000000503")
    task = asyncio.create_task(drive(orchestrator, SCRIPT))
    for _ in range(2000):
        if orchestrator.events:
            break
        await asyncio.sleep(0.005)
    with pytest.raises(ValueError):
        await orchestrator.change_model("janitor", orchestrator.roster["estimator"], None)
    await task
