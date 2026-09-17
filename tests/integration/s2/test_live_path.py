"""Part A evidence: live agents on the unchanged event spine, with scripted models (SC-003 to SC-006)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agents.base import HumanScript
from app.config import load_settings
from app.orchestrator.driver import drive
from app.runs.golden import compare, read_golden
from app.runs.registry import discover_datasets
from app.schema.events import Event, validate_run
from tests.integration.s2 import live_harness as h
from tests.support.scripted_model import ScriptedModel, reply

pytestmark = pytest.mark.dataset

SCRIPT = HumanScript(answers={"q_service_voltage": "120/208 V"}, decision="approve")


def of_type(events: list[Event], type_: str) -> list[Event]:
    return [e for e in events if e.type == type_]


async def test_live_run_matches_clean_run_golden(tmp_path: Path) -> None:
    orchestrator = h.build(tmp_path, h.full_turns(), "10000000-0000-4000-8000-000000000001")
    await drive(orchestrator, SCRIPT)
    events = orchestrator.events
    assert validate_run(events) == []
    assert events[-1].payload["exit"] == "reviewer_pass"
    assert events[-1].payload["summary"]["headline"] == "The Reviewer passed the proposal first time."

    golden_path = next(
        d for d in discover_datasets(load_settings().datasets_dir) if d.id == "clean-run"
    ).golden_path
    result = compare("clean-run", events, read_golden(golden_path))
    assert result.ok, result.message

    plan = of_type(events, "plan.created")[0]
    assert plan.reason == "Pricing needs the takeoff, and the Writer needs both."
    assert [s["task_id"] for s in plan.payload["subtasks"]] == ["t1", "t2", "t3"]


async def test_tools_progress_meters_and_bundles(tmp_path: Path) -> None:
    orchestrator = h.build(tmp_path, h.full_turns(), "10000000-0000-4000-8000-000000000002")
    await drive(orchestrator, SCRIPT)
    events = orchestrator.events

    tools = [(e.payload["task_id"], e.payload["tool"]) for e in of_type(events, "tool.called")]
    assert tools == [
        ("intake", "prepare_documents"),  # division-26-specification.pdf
        ("intake", "prepare_documents"),  # request.pdf
        ("intake", "prepare_documents"),  # drawings/E-001.pdf
        ("intake", "prepare_documents"),  # manifest.md
        ("intake", "document_extract_attachments"),
        ("intake", "document_parse_pdf"),
        ("t1", "vision_read_drawing"),
        ("t1", "quantity_calculate"),
        ("t2", "price_list_lookup"),
        ("assemble-v1", "template_render"),
    ]
    prepared = [e for e in of_type(events, "tool.called") if e.payload["tool"] == "prepare_documents"]
    assert [e.payload["args_summary"] for e in prepared] == [
        "division-26-specification.pdf",
        "request.pdf",
        "drawings/E-001.pdf",
        "manifest.md",
    ]
    assert prepared[2].payload["result_summary"].startswith("1 page, sheets E-001")
    assert prepared[3].payload["result_summary"].startswith("5 sheets from 3 files")
    assert (tmp_path / "runs" / "10000000-0000-4000-8000-000000000002" / "prepared" / "manifest.md").exists()
    parse = next(e for e in of_type(events, "tool.called") if e.payload["tool"] == "document_parse_pdf")
    assert parse.payload["args_summary"] == "request.pdf" and parse.payload["result_summary"].startswith(
        "2 pages"
    )
    lookup = next(e for e in of_type(events, "tool.called") if e.payload["tool"] == "price_list_lookup")
    assert lookup.payload["result_summary"] == "2 priced, 0 exceptions"

    progress = [
        e.payload["message"] for e in of_type(events, "task.progress") if e.payload["task_id"] == "t1"
    ]
    assert progress == ["Reading single-line E-001.", "Totalling troffers and receptacles."]

    meters = of_type(events, "meter.update")
    assert len(meters) == 13, "one meter update per model call"
    assert {m.payload["agent_id"] for m in meters} == {
        "orchestrator",
        "intake",
        "estimator",
        "pricing",
        "writer",
        "reviewer",
    }
    assert all(m.payload["est_cost"] == 0.0054 for m in meters)

    pricing_started = next(
        i for i, e in enumerate(events) if e.type == "tool.called" and e.payload["task_id"] == "t2"
    )
    estimator_done = next(
        i for i, e in enumerate(events) if e.type == "task.completed" and e.payload["task_id"] == "t1"
    )
    assert pricing_started > estimator_done

    for event in events:
        if event.prompt_ref:
            bundle = orchestrator.bundles[event.prompt_ref]
            assert all(text for _, text in bundle.sections())
    estimator_msg = of_type(events, "task.completed")[0]
    bundle = orchestrator.bundles[estimator_msg.prompt_ref or ""]
    assert bundle.system.startswith("You are Elena, the Estimator")
    assert bundle.model.label == "scripted estimator"
    assert (tmp_path / "runs" / orchestrator.run_id / "prompts" / f"{bundle.prompt_ref}.json").exists()


async def test_writer_tags_resolve_to_specialist_events(tmp_path: Path) -> None:
    orchestrator = h.build(tmp_path, h.full_turns(), "10000000-0000-4000-8000-000000000003")
    await drive(orchestrator, SCRIPT)
    events = orchestrator.events
    draft = of_type(events, "draft.committed")[0]
    completed = {e.payload["agent_id"]: e.event_id for e in of_type(events, "task.completed")}
    assert [t["source_event_id"] for t in draft.payload["provenance_tags"]] == [
        completed["estimator"],
        completed["pricing"],
    ]
    path = tmp_path / "runs" / orchestrator.run_id / draft.payload["markdown_path"]
    assert "25 troffers" in path.read_text(encoding="utf-8")


async def test_roles_are_real_in_recorded_bundles(tmp_path: Path) -> None:
    orchestrator = h.build(tmp_path, h.full_turns(), "10000000-0000-4000-8000-000000000004")
    await drive(orchestrator, SCRIPT)
    events = orchestrator.events
    by_seat = {}
    for event in events:
        if event.prompt_ref and isinstance(event.actor, dict) is False and hasattr(event.actor, "agent_id"):
            by_seat[event.actor.agent_id] = orchestrator.bundles[event.prompt_ref]  # type: ignore[union-attr]
    reviewer = by_seat["reviewer"].context_slice
    assert "## Brief" in reviewer and "## Page 1 text" in reviewer and "## Reviewer criteria" in reviewer
    assert "## Draft v1" not in reviewer, "from S4 the Reviewer sees the compiled pages, never the markdown"
    for forbidden in [
        "Estimator output",
        "Pricing output",
        "Client knowledge file",
        "Drawing sheets",
        "Estimating conventions",
    ]:
        assert forbidden not in reviewer
    pricing = by_seat["pricing"].context_slice
    assert "## Estimator output" in pricing and "## Client knowledge file" in pricing
    assert "Drawing sheets" not in pricing and "Request documents" not in pricing
    estimator = by_seat["estimator"].context_slice
    assert "## Drawing sheets" in estimator and "Client knowledge file" not in estimator
    intake = by_seat["intake"].context_slice
    assert "## Request documents" in intake and "## Brief" not in intake
    assert by_seat["pricing"].tools == ["price_list_lookup"]
    assert by_seat["reviewer"].tools == []


async def test_ask_once_across_runs(tmp_path: Path) -> None:
    first = h.build(tmp_path, h.full_turns(), "10000000-0000-4000-8000-000000000005")
    await drive(first, SCRIPT)
    assert of_type(first.events, "clarification.asked")
    assert of_type(first.events, "knowledge.appended")[0].payload["entries"][0]["answer"] == "120/208 V"

    second = h.build(tmp_path, h.full_turns(), "10000000-0000-4000-8000-000000000006")
    await drive(second, HumanScript(decision="approve"))
    events = second.events
    assert not of_type(events, "clarification.asked"), "the answered question is not asked again"
    assumption = next(
        e for e in of_type(events, "assumption.accepted") if e.payload["question_id"] == "q_service_voltage"
    )
    assert assumption.payload["default_used"] == "120/208 V"
    assert "already answers" in (assumption.reason or "")
    intake_bundle = second.bundles[of_type(events, "intake.readiness")[0].prompt_ref or ""]
    assert "q_service_voltage: 120/208 V" in intake_bundle.context_slice
    assert events[-1].payload["exit"] == "reviewer_pass"


async def test_invalid_reply_on_every_attempt_stops_with_seat_named(tmp_path: Path) -> None:
    """A seat gets three attempts (two corrections) before it stops the run (decision 2026-09-17)."""
    turns = h.full_turns()
    turns["intake"] = [[{"text": "not json"}], [{"text": "still not json"}], [{"text": "not json again"}]]
    orchestrator = h.build(tmp_path, turns, "10000000-0000-4000-8000-000000000007")
    await drive(orchestrator, SCRIPT)
    last = orchestrator.events[-1]
    assert last.payload["exit"] == "stopped"
    assert "Intake Analyst" in (last.reason or "") and "invalid reply 3 times" in (last.reason or "")
    assert validate_run(orchestrator.events) == []
    rejected = sorted((orchestrator.run_folder or tmp_path).glob("rejected/*.txt"))
    assert [r.name.rsplit("-", 1)[1] for r in rejected] == ["1.txt", "2.txt", "3.txt"], (
        "every rejected reply is kept"
    )
    assert "not json again" in rejected[2].read_text(encoding="utf-8")


async def test_provider_error_never_leaks_its_text(tmp_path: Path) -> None:
    turns = h.full_turns()
    secret = "sk-secret-token-9f8e"
    turns["intake"] = [RuntimeError(f"401 bad key {secret}"), RuntimeError(f"401 bad key {secret}")]
    orchestrator = h.build(tmp_path, turns, "10000000-0000-4000-8000-000000000008")
    await drive(orchestrator, SCRIPT)
    last = orchestrator.events[-1]
    assert last.payload["exit"] == "stopped"
    assert "could not reach scripted intake after a retry" in (last.reason or "")
    recorded = (tmp_path / "runs" / orchestrator.run_id / "events.jsonl").read_text(encoding="utf-8")
    assert secret not in recorded


async def test_invalid_plan_falls_back_to_standard_plan(tmp_path: Path) -> None:
    turns = h.full_turns()
    bad_plan = {
        "subtasks": [
            {"task_id": "t1", "title": "Everything", "agent_id": "reviewer", "depends_on": [], "scope": []}
        ],
        "reason": "one step",
    }
    turns["orchestrator"] = [reply(bad_plan), h.headline_turn()]
    orchestrator = h.build(tmp_path, turns, "10000000-0000-4000-8000-000000000009")
    await drive(orchestrator, SCRIPT)
    plan = of_type(orchestrator.events, "plan.created")[0]
    assert "standard plan" in (plan.reason or "")
    assert [s["agent_id"] for s in plan.payload["subtasks"]] == ["estimator", "pricing", "writer"]
    assert orchestrator.events[-1].payload["exit"] == "reviewer_pass"


def test_scripted_model_is_test_only() -> None:
    import app

    assert "ScriptedModel" not in Path(app.__file__).parent.joinpath("live", "providers.py").read_text(
        encoding="utf-8"
    )
    assert ScriptedModel.__module__.startswith("tests.")


async def test_unreadable_plan_twice_falls_back_to_standard_plan(tmp_path: Path) -> None:
    turns = h.full_turns()
    turns["orchestrator"] = [
        [{"text": "I will plan the work."}],
        [{"text": "Still no JSON."}],
        h.headline_turn(),
    ]
    orchestrator = h.build(tmp_path, turns, "10000000-0000-4000-8000-000000000010")
    await drive(orchestrator, SCRIPT)
    plan = of_type(orchestrator.events, "plan.created")[0]
    assert "could not be read" in (plan.reason or "")
    assert orchestrator.events[-1].payload["exit"] == "reviewer_pass"


async def test_estimator_totals_must_come_from_the_calculator(tmp_path: Path) -> None:
    turns = h.full_turns()
    vision, calculate, final = h.estimator_turns()
    turns["estimator"] = [vision, final, calculate, final]
    orchestrator = h.build(tmp_path, turns, "10000000-0000-4000-8000-000000000011")
    await drive(orchestrator, SCRIPT)
    estimator_tools = [
        e.payload["tool"]
        for e in of_type(orchestrator.events, "tool.called")
        if e.payload["agent_id"] == "estimator"
    ]
    assert estimator_tools == ["vision_read_drawing", "quantity_calculate"]
    assert orchestrator.events[-1].payload["exit"] == "reviewer_pass"


async def test_pricing_tool_call_written_as_text_is_corrected(tmp_path: Path) -> None:
    turns = h.full_turns()
    lookup, final = h.pricing_turns()
    written = [{"text": 'Here is the call: {"name": "price_list_lookup", "parameters": {"items": []}}'}]
    turns["pricing"] = [written, lookup, final]
    orchestrator = h.build(tmp_path, turns, "10000000-0000-4000-8000-000000000012")
    await drive(orchestrator, SCRIPT)
    pricing_tools = [
        e.payload["tool"]
        for e in of_type(orchestrator.events, "tool.called")
        if e.payload["agent_id"] == "pricing"
    ]
    assert pricing_tools == ["price_list_lookup"]
    assert orchestrator.events[-1].payload["exit"] == "reviewer_pass"


async def test_output_limit_stops_without_a_costly_retry(tmp_path: Path) -> None:
    from strands.types.exceptions import MaxTokensReachedException

    turns = h.full_turns()
    vision = h.estimator_turns()[0]
    turns["estimator"] = [vision, MaxTokensReachedException("cut off"), *h.estimator_turns()]
    orchestrator = h.build(tmp_path, turns, "10000000-0000-4000-8000-000000000013")
    await drive(orchestrator, SCRIPT)
    last = orchestrator.events[-1]
    assert last.payload["exit"] == "stopped"
    assert "reached its output limit" in (last.reason or "")
    vision_reads = [
        e for e in of_type(orchestrator.events, "tool.called") if e.payload["tool"] == "vision_read_drawing"
    ]
    assert len(vision_reads) == 1, "the drawings are not read a second time"


async def test_writer_draft_without_provenance_gets_a_correction(tmp_path: Path) -> None:
    turns = h.full_turns()
    render, final = h.writer_turns()
    body = "# Proposal" + chr(10) + chr(10) + "We will install 25 troffers for $6,362.94." + chr(10)
    untagged = reply({"markdown": body, "note": "no tags"})
    turns["writer"] = [render, untagged, final]
    orchestrator = h.build(tmp_path, turns, "10000000-0000-4000-8000-000000000014")
    await drive(orchestrator, SCRIPT)
    draft = of_type(orchestrator.events, "draft.committed")[0]
    assert len(draft.payload["provenance_tags"]) == 2
    assert orchestrator.events[-1].payload["exit"] == "reviewer_pass"


async def test_progress_lines_never_carry_em_dashes(tmp_path: Path) -> None:
    dash = chr(0x2014)
    turns = h.full_turns()
    estimator = h.estimator_turns()
    estimator[0] = [
        {"text": f"Reading E-001 {dash} the single-line."},
        {"tool": "vision_read_drawing", "input": {"sheet": "E-001"}},
    ]
    turns["estimator"] = estimator
    orchestrator = h.build(tmp_path, turns, "10000000-0000-4000-8000-000000000015")
    await drive(orchestrator, SCRIPT)
    progress = [e.payload["message"] for e in of_type(orchestrator.events, "task.progress")]
    assert "Reading E-001, the single-line." in progress
    assert all(dash not in e.to_line() for e in orchestrator.events)
