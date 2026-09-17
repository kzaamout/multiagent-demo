"""Edit and Reject at Handoff (spec stage 6, FR-011): one human commit and recompile, then the end."""

from __future__ import annotations

import asyncio

import pytest

from app.agents.base import HumanScript
from app.agents.stubs import clean_run
from app.agents.stubs.fixture import fixture_draft
from app.config import Settings
from app.orchestrator.orchestrator import Answer, Orchestrator
from tests.conftest import make_orchestrator, run_scenario

pytestmark = pytest.mark.compiler

RUN_ID = "00000000-0000-4000-8000-000000000001"
EDITED = fixture_draft(1).replace(
    "Fire alarm, data and security systems are excluded.",
    "Fire alarm is excluded; data and security are priced separately.",
)


async def test_edit_commits_once_as_the_human_and_ends_the_run(settings: Settings) -> None:
    script = HumanScript(decision="edit", edit_markdown=EDITED)
    events = await run_scenario(clean_run.SCENARIO, settings, script, record=True)
    commits = [e for e in events if e.type == "draft.committed"]
    compiled = [e for e in events if e.type == "artifact.compiled"]
    assert [c.payload["version"] for c in commits] == [1, 2]
    assert commits[1].actor == "human" and commits[1].payload["note"] == "edited at Handoff"
    assert commits[1].payload["provenance_tags"] and all(
        not t["source_event_id"].startswith("$") for t in commits[1].payload["provenance_tags"]
    )
    assert [c.payload["version"] for c in compiled] == [1, 2]
    assert compiled[1].payload["page_images"][0] == "artifacts/v2/page-01.png"
    tail = [e.type for e in events[-4:]]
    assert tail == ["draft.committed", "artifact.compiled", "human.approved", "run.terminated"]
    approved = events[-2].payload
    assert approved["decision"] == "edit"
    assert events[-1].payload["exit"] == "reviewer_pass"
    run_folder = settings.runs_dir / RUN_ID
    assert "priced separately" in (run_folder / "drafts" / "draft-v2.md").read_text(encoding="utf-8")
    assert (run_folder / "artifacts" / "v2" / "page-01.png").is_file()
    assert (run_folder / "artifacts" / "v1" / "page-01.png").is_file(), "the first version is kept"


async def test_reject_records_notes_and_ends_with_the_same_exit(settings: Settings) -> None:
    script = HumanScript(decision="reject")
    events = await run_scenario(clean_run.SCENARIO, settings, script, record=True)
    assert [e.type for e in events[-2:]] == ["human.approved", "run.terminated"]
    assert events[-2].payload["decision"] == "reject"
    assert events[-1].payload["exit"] == "reviewer_pass", (
        "reject keeps the Handoff exit; it never re-enters the loop"
    )
    assert len([e for e in events if e.type == "draft.committed"]) == 1


async def _run_to_handoff(orchestrator: Orchestrator) -> asyncio.Task[None]:
    task = asyncio.create_task(orchestrator.run())
    orchestrator.attach_task(task)
    while True:
        await orchestrator.human_needed.wait()
        pending = orchestrator.pending()
        if pending["kind"] == "handoff":
            return task
        if pending["kind"] == "clarifications":
            orchestrator.submit_answers([Answer(question_id=q, answer="") for q in pending["question_ids"]])
        await asyncio.sleep(0)


async def test_an_edit_that_does_not_compile_is_refused_and_the_run_waits(settings: Settings) -> None:
    orchestrator = make_orchestrator(clean_run.SCENARIO, settings, record=True)
    task = await _run_to_handoff(orchestrator)
    with pytest.raises(ValueError) as caught:
        orchestrator.submit_decision("edit", markdown="# Broken\n\n`#let (`{=typst}\n")
    assert "does not compile" in str(caught.value)
    assert orchestrator.pending()["kind"] == "handoff", "the run still waits at Handoff"
    assert not (settings.runs_dir / RUN_ID / "drafts" / "draft-v2.md").exists()
    with pytest.raises(ValueError):
        orchestrator.submit_decision("edit", markdown="   ")
    orchestrator.submit_decision("approve")
    await task
    assert orchestrator.events[-1].payload["exit"] == "reviewer_pass"
    assert (settings.runs_dir / RUN_ID / "artifacts" / "v1" / "compiled.json").is_file()
