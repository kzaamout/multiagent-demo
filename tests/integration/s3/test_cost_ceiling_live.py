"""The cost ceiling on a live run with priced scripted seats (S3, US7)."""

from __future__ import annotations

from pathlib import Path

from app.agents.base import HumanScript
from app.orchestrator.driver import drive
from tests.integration.s2 import live_harness as h


async def test_breach_ends_the_run_before_further_dispatch(tmp_path: Path) -> None:
    # Each scripted call reports 1,200 tokens in and 300 out at 2 and 10 USD per million: about 0.0054 USD.
    orchestrator = h.build(
        tmp_path, h.full_turns(blocking=False), "30000000-0000-4000-8000-000000000201", cost_ceiling=0.02
    )
    await drive(orchestrator, HumanScript(answers={}, decision="approve"))
    events = orchestrator.events
    last = events[-1]
    assert last.type == "run.terminated" and last.payload["exit"] == "cost_ceiling"
    assert last.payload["summary"]["est_cost"] > 0.02
    breach = max(i for i, e in enumerate(events) if e.type == "meter.update")
    assert not any(e.type == "task.dispatched" for e in events[breach + 1 :]), (
        "nothing is dispatched after the breach"
    )
