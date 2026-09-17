"""A Single-model run: one actor, four stage changes, exit single_complete, recorded, replayable, compared (S5, US2)."""

from __future__ import annotations

import asyncio
import datetime as dt
import json
from pathlib import Path
from typing import Any

import pytest

from app.agents.base import HumanScript
from app.config import Settings, load_settings
from app.live.materials import DatasetFiles
from app.live.providers import live_roster
from app.live.source import LiveAgentSource, LiveContext
from app.orchestrator.clock import Clock
from app.orchestrator.driver import drive
from app.orchestrator.knowledge_store import KnowledgeStore
from app.orchestrator.orchestrator import DatasetRef, Orchestrator
from app.orchestrator.roster import EXPORT_NAMES, build_roster, single_agent
from app.runs.bus import StreamBus
from app.runs.comparison import comparison
from app.runs.recorder import Recorder, read_events
from app.runs.registry import Registry
from app.runs.replay import ReplaySession
from app.schema.events import validate_run
from tests.integration.s2 import live_harness as h
from tests.support.scripted_model import Turn, reply

pytestmark = pytest.mark.dataset

SCRIPT = HumanScript(answers={}, decision=None)
MARKDOWN = "# Proposal\n\nOne pass. Lump sum $6,362.94.\n"


def single_turns() -> list[Turn]:
    return [
        [{"text": "Listing the package."}, {"tool": "document_extract_attachments", "input": {}}],
        [
            {"text": "Pricing the two lines."},
            {
                "tool": "price_list_lookup",
                "input": {
                    "items": [
                        {"line_ref": "L1", "description": "2x4 LED troffer", "quantity": 25, "unit": "each"}
                    ],
                    "markup_rate": 0.15,
                    "labour_hours": 22,
                    "labour_rate": 95,
                },
            },
        ],
        reply(
            {
                "headline": "Proposal written in one pass",
                "summary": "One pass over the package. Lump sum $6,362.94.",
                "markdown": MARKDOWN,
                "total": "6362.94",
            }
        ),
    ]


def build_single(tmp: Path, run_id: str, turns: list[Turn] | None = None) -> Orchestrator:
    folder = h.dataset(tmp)
    models = h.seat_models({"single": turns or single_turns()})
    roster, _ = live_roster(
        {"single": single_agent("electrical_rfp", name="Sofia")}, lambda seat: models[seat]
    )
    roster = {"orchestrator": build_roster("electrical_rfp", names=EXPORT_NAMES)["orchestrator"], **roster}
    store = KnowledgeStore(tmp / "knowledge")
    recorder = Recorder(tmp / "runs", run_id)
    source = LiveAgentSource(
        dataset_id="test-live",
        client_id=h.CLIENT,
        context=LiveContext(
            files=DatasetFiles(folder),
            knowledge=store,
            prospect_name="Test Owner Ltd.",
            project="Test Library lighting upgrade",
            supplier_order=["Supplier A", "Supplier B", "Supplier C"],
            long_lead_days=28,
            review_max_cycles=4,
        ),
        seat_models=models,
    )
    return Orchestrator(
        run_id=run_id,
        workflow="electrical_rfp",
        dataset=DatasetRef(dataset_id="test-live", label="Test live", client_id=h.CLIENT),
        scenario=source,
        roster=roster,
        review_max_cycles=4,
        cost_ceiling=5.0,
        clock=Clock(dt.datetime.now(dt.UTC), pace=1.0),
        bus=StreamBus(),
        recorder=recorder,
        knowledge_path=recorder.knowledge_path,
        event_log_path=f"runs/{run_id}/events.jsonl",
        knowledge_store=store,
        run_folder=recorder.folder,
        mode="single",
    )


def of_type(events: list[Any], type_: str) -> list[Any]:
    return [e for e in events if e.type == type_]


async def test_single_run_shape_recording_and_replay(tmp_path: Path) -> None:
    run_id = "50000000-0000-4000-8000-000000000521"
    orchestrator = build_single(tmp_path, run_id)
    await drive(orchestrator, SCRIPT)
    events = orchestrator.events
    assert validate_run(events) == []
    started = events[0]
    assert started.payload["mode"] == "single"
    assert [a["agent_id"] for a in started.payload["roster"]] == ["orchestrator", "single"]
    assert (
        started.payload["roster"][1]["role"] == "Single model"
        and started.payload["roster"][1]["name"] == "Sofia"
    )
    stages = [(e.payload["to"], e.payload["direction"], e.stage) for e in of_type(events, "stage.changed")]
    assert stages == [
        ("intake", "forward", "intake"),
        ("work", "forward", "work"),
        ("assemble", "forward", "assemble"),
        ("handoff", "forward", "handoff"),
    ]
    assert len(of_type(events, "task.dispatched")) == 1 and len(of_type(events, "task.completed")) == 1
    completed = of_type(events, "task.completed")[0]
    assert completed.payload["agent_id"] == "single" and completed.payload["task_id"] == "single"
    result = completed.payload["result"]
    assert result["output_path"] == "drafts/single-v1.md" and result["total"] == "6362.94"
    assert (tmp_path / "runs" / run_id / "drafts" / "single-v1.md").read_text(encoding="utf-8") == MARKDOWN
    prepared = [e for e in of_type(events, "tool.called") if e.payload["tool"] == "prepare_documents"]
    assert len(prepared) == 4 and all(e.payload["agent_id"] == "single" for e in prepared)
    assert [e.payload["tool"] for e in of_type(events, "tool.called")][-2:] == [
        "document_extract_attachments",
        "price_list_lookup",
    ]
    assert not of_type(events, "plan.created") and not of_type(events, "review.verdict")
    assert not of_type(events, "draft.committed") and not of_type(events, "handoff.ready")
    assert events[-1].type == "run.terminated" and events[-1].payload["exit"] == "single_complete"
    assert events[-1].payload["summary"]["stop_reason"] is None
    assert all(e.payload["agent_id"] == "single" for e in of_type(events, "meter.update"))

    folder = tmp_path / "runs" / run_id
    recorded = read_events(folder / "events.jsonl")
    assert [e.event_id for e in recorded] == [e.event_id for e in events]
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    assert meta["mode"] == "single" and meta["exit"] == "single_complete"
    metrics = json.loads((folder / "metrics.json").read_text(encoding="utf-8"))
    assert [s["agent_id"] for s in metrics["seats"]] == ["orchestrator", "single"]
    session = ReplaySession(
        dataset_id="test-live", source="recording", path=folder / "events.jsonl", speed=4.0, bus=StreamBus()
    )
    session.load()
    assert session.run_id == run_id and len(session.events) == len(events)


async def test_single_run_can_be_stopped(tmp_path: Path) -> None:
    from tests.support.scripted_model import HANG

    orchestrator = build_single(tmp_path, "50000000-0000-4000-8000-000000000522", turns=[HANG])
    task = asyncio.create_task(drive(orchestrator, SCRIPT))
    for _ in range(400):
        if any(e.type == "task.dispatched" for e in orchestrator.events):
            break
        await asyncio.sleep(0.01)
    orchestrator.stop()
    await task
    assert orchestrator.events[-1].payload["exit"] == "stopped"


async def test_stub_single_runs_feed_the_comparison(tmp_path: Path) -> None:
    settings = Settings(
        runs_dir=tmp_path / "runs",
        datasets_dir=load_settings().datasets_dir,
        stub_pace=1000.0,
        agent_mode="stub",
    )
    registry = Registry(settings)
    team = registry.build_orchestrator(
        "clean-run", record=True, start=dt.datetime(2026, 9, 16, 9, 0, tzinfo=dt.UTC)
    )
    await drive(team, team.scenario.human_script)
    first = registry.build_orchestrator(
        "clean-run", record=True, mode="single", start=dt.datetime(2026, 9, 16, 9, 10, tzinfo=dt.UTC)
    )
    await drive(first, SCRIPT)
    second = registry.build_orchestrator(
        "clean-run", record=True, mode="single", start=dt.datetime(2026, 9, 16, 9, 20, tzinfo=dt.UTC)
    )
    await drive(second, SCRIPT)
    assert first.events[-1].payload["exit"] == "single_complete"
    assert (
        first.roster["single"].model.label == registry.effective_config().seat_spec("orchestrator").label
    ), "the default Single model is the Orchestrator's"
    assert (tmp_path / "runs" / first.run_id / "drafts" / "single-v1.md").exists()
    figures = comparison(settings.runs_dir, "clean-run")
    assert figures["team"]["run_id"] == team.run_id and figures["team"]["exit"] == "reviewer_pass"
    assert figures["single"]["run_id"] == second.run_id, "the newest Single-model recording wins"
    assert figures["single"]["output_path"] == "drafts/single-v1.md" and figures["single"]["model_label"]
    assert figures["single"]["est_cost"] > 0 and figures["single"]["elapsed_ms"] > 0
    assert comparison(settings.runs_dir, "missing-sheet") == {
        "dataset_id": "missing-sheet",
        "team": None,
        "single": None,
    }
    stopped = registry.build_orchestrator(
        "clean-run", record=True, start=dt.datetime(2026, 9, 16, 9, 30, tzinfo=dt.UTC)
    )
    stopped_task = asyncio.create_task(drive(stopped, stopped.scenario.human_script))
    for _ in range(400):
        if any(e.type == "stage.changed" for e in stopped.events):
            break
        await asyncio.sleep(0.005)
    stopped.stop()
    await stopped_task
    assert stopped.events[-1].payload["exit"] == "stopped"
    assert comparison(settings.runs_dir, "clean-run")["team"]["run_id"] == team.run_id, (
        "a newer stopped run does not displace the newest completed one"
    )


async def test_single_run_with_a_chosen_model_and_an_unknown_key(tmp_path: Path) -> None:
    settings = Settings(
        runs_dir=tmp_path / "runs",
        datasets_dir=load_settings().datasets_dir,
        stub_pace=1000.0,
        agent_mode="stub",
    )
    registry = Registry(settings)
    key = next(
        k for k in registry.model_config.models if k != registry.model_config.seats["orchestrator"].model
    )
    chosen = registry.build_orchestrator("clean-run", record=False, mode="single", model_key=key)
    assert chosen.roster["single"].model.label == registry.model_config.models[key].label
    with pytest.raises(ValueError, match="unknown model"):
        registry.build_orchestrator("clean-run", record=False, mode="single", model_key="nope")
