"""A draft that does not compile is a rejected reply; the second failure ends the run (spec FR-015)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.agents.base import HumanScript
from app.orchestrator.driver import drive
from tests.integration.s2 import live_harness as h
from tests.integration.s2.live_harness import _source_ids
from tests.support.scripted_model import reply

pytestmark = [pytest.mark.compiler, pytest.mark.dataset]

SCRIPT = HumanScript(answers={"q_service_voltage": "120/208 V"}, decision="approve")


def broken_then_good() -> list[Any]:
    def broken(prompt: str) -> list[dict[str, Any]]:
        ids = _source_ids(prompt)
        markdown = (
            "# Proposal\n\nTotal {{$6,362.94|src:" + ids["Pricing output"] + "}}.\n\n`#let (`{=typst}\n"
        )
        return reply({"markdown": markdown, "note": "broken markup", "tags": [], "gaps": []})

    good = h.writer_turns()
    return [good[0], broken, good[1]]


async def test_uncompilable_draft_is_rejected_then_the_corrected_one_commits(tmp_path: Path) -> None:
    turns = h.full_turns(blocking=False)
    turns["writer"] = broken_then_good()
    run_id = "50000000-0000-4000-8000-000000000511"
    orchestrator = h.build(tmp_path, turns, run_id)
    await drive(orchestrator, SCRIPT)
    events = orchestrator.events
    assert events[-1].payload["exit"] == "reviewer_pass"
    assert [e.payload["version"] for e in events if e.type == "draft.committed"] == [1]
    attempts = [
        json.loads(line)
        for line in (tmp_path / "runs" / run_id / "seat-calls.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    writer = [a for a in attempts if a["agent_id"] == "writer"]
    rejected = [a for a in writer if not a["accepted"]]
    assert len(rejected) == 1 and rejected[0]["error"].startswith("the draft does not compile: typst")
    assert any(a["accepted"] for a in writer)


async def test_two_uncompilable_drafts_end_the_run(tmp_path: Path) -> None:
    turns = h.full_turns(blocking=False)
    first, broken, _ = broken_then_good()
    turns["writer"] = [first, broken, broken]
    run_id = "50000000-0000-4000-8000-000000000512"
    orchestrator = h.build(tmp_path, turns, run_id)
    await drive(orchestrator, SCRIPT)
    events = orchestrator.events
    assert not [e for e in events if e.type == "draft.committed"]
    assert events[-1].type == "run.terminated"
    assert events[-1].payload["exit"] != "reviewer_pass"
