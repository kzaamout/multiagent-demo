"""A draft that drops a specialist concern naming a sheet goes back to the Writer once (decision 23)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, cast

import pytest

from app.agents.base import HumanScript
from app.orchestrator.driver import drive
from tests.integration.s2 import live_harness as h
from tests.integration.s2.live_harness import _source_ids
from tests.support.scripted_model import Turn, reply

pytestmark = [pytest.mark.compiler, pytest.mark.dataset]

SCRIPT = HumanScript(answers={"q_service_voltage": "120/208 V"}, decision="approve")
CONCERN = {
    "text": "Main breaker rating disagrees between sheets: E-001 shows 225 A, the schedule on E-002 states 200 A.",
    "drawing_ref": "E-001, E-002",
}


def with_the_schedule_sheet(tmp_path: Path) -> None:
    """The concern compares E-001 with the schedule on E-002, so the set has to hold E-002. A concern naming a
    sheet the run does not hold is a blocker, not a concern (spec 010, plan item 1.8)."""
    drawings = h.dataset(tmp_path) / "inputs" / "drawings"
    shutil.copyfile(drawings / "E-001.pdf", drawings / "E-002.pdf")


def estimator_with_concern() -> list[Turn]:
    turns = h.estimator_turns()
    last = cast(list[dict[str, Any]], turns[-1])
    final = json.loads(last[0]["text"])
    final["concerns"] = [CONCERN]
    return [*turns[:-1], reply(final)]


def writer_turns(carry: bool) -> list[Turn]:
    def final(prompt: str) -> list[dict[str, Any]]:
        ids = _source_ids(prompt)
        est, price = ids["Estimator output"], ids["Pricing output"]
        body = (
            "# Proposal\n\nWe will install {{25 troffers|src:"
            + est
            + "}} for {{$6,362.94|src:"
            + price
            + "}}.\n\n"
        )
        assumptions = "## Assumptions\n\n- Markup is 15 percent.\n"
        if carry:
            assumptions += (
                "- The LP-1 main breaker is priced at {{225 A|src:"
                + est
                + "}} from E-001; E-002 shows 200 A, to be confirmed.\n"
            )
        return reply({"markdown": body + assumptions, "note": "draft", "tags": [], "gaps": []})

    return [h.writer_turns()[0], final]


async def test_dropped_concern_is_sent_back_once_then_the_carried_draft_commits(tmp_path: Path) -> None:
    turns = h.full_turns(blocking=False)
    turns["estimator"] = estimator_with_concern()
    with_the_schedule_sheet(tmp_path)
    turns["writer"] = [writer_turns(False)[0], writer_turns(False)[1], writer_turns(True)[1]]
    run_id = "60000000-0000-4000-8000-000000000601"
    orchestrator = h.build(tmp_path, turns, run_id)
    await drive(orchestrator, SCRIPT)
    events = orchestrator.events
    assert events[-1].payload["exit"] == "reviewer_pass"
    attempts = [
        json.loads(line)
        for line in (tmp_path / "runs" / run_id / "seat-calls.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    writer = [a for a in attempts if a["agent_id"] == "writer"]
    rejected = [a for a in writer if not a["accepted"]]
    assert len(rejected) == 1
    assert "Estimator's concern is not carried in the Assumptions section" in rejected[0]["error"]
    assert "E-001, E-002" in rejected[0]["error"]
    draft = next(e for e in events if e.type == "draft.committed")
    text = (tmp_path / "runs" / run_id / draft.payload["markdown_path"]).read_text(encoding="utf-8")
    assert "E-002 shows 200 A" in text


async def test_a_concern_carried_first_time_is_not_sent_back(tmp_path: Path) -> None:
    turns = h.full_turns(blocking=False)
    turns["estimator"] = estimator_with_concern()
    with_the_schedule_sheet(tmp_path)
    turns["writer"] = writer_turns(True)
    run_id = "60000000-0000-4000-8000-000000000602"
    orchestrator = h.build(tmp_path, turns, run_id)
    await drive(orchestrator, SCRIPT)
    attempts = [
        json.loads(line)
        for line in (tmp_path / "runs" / run_id / "seat-calls.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert all(a["accepted"] for a in attempts if a["agent_id"] == "writer")
