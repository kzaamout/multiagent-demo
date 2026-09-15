from __future__ import annotations

import json

from app.agents.stubs import SCENARIOS
from app.config import Settings
from app.runs.recorder import read_events
from app.schema.events import validate_run
from tests.conftest import run_scenario


async def test_run_is_recorded(settings: Settings) -> None:
    run_id = "00000000-0000-4000-8000-00000000abcd"
    events = await run_scenario(SCENARIOS["planted-inconsistency"], settings, record=True, run_id=run_id)
    folder = settings.runs_dir / run_id
    recorded = read_events(folder / "events.jsonl")
    assert [e.event_id for e in recorded] == [e.event_id for e in events]
    assert validate_run(recorded) == []
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    assert meta["exit"] == "reviewer_pass" and meta["dataset_id"] == "planted-inconsistency"
    refs = {e.prompt_ref for e in events if e.prompt_ref}
    assert refs == {p.stem for p in (folder / "prompts").glob("*.json")}
    knowledge = (folder / "knowledge.md").read_text(encoding="utf-8")
    assert "q_service_voltage: 208Y/120 V" in knowledge
    assert "b_" not in knowledge


async def test_recording_is_appended_as_events_arrive(settings: Settings) -> None:
    """A partial run leaves a valid prefix: every line written so far parses and seq is contiguous."""
    run_id = "00000000-0000-4000-8000-00000000abce"
    await run_scenario(SCENARIOS["not-ready"], settings, record=True, run_id=run_id)
    lines = (settings.runs_dir / run_id / "events.jsonl").read_text(encoding="utf-8").splitlines()
    prefix = read_events(settings.runs_dir / run_id / "events.jsonl")[:3]
    assert len(lines) == 6
    assert [e.seq for e in prefix] == [1, 2, 3]
