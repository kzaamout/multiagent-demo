from __future__ import annotations

import asyncio
import time
from pathlib import Path

from app.agents.stubs import SCENARIOS
from app.config import Settings
from app.runs.bus import StreamBus
from app.runs.golden import write_golden
from app.runs.registry import Registry
from app.runs.replay import ReplaySession
from app.schema.events import Event
from tests.conftest import run_scenario


async def collect(bus: StreamBus, stream_id: str) -> list[dict[str, object]]:
    return [event async for event in bus.subscribe(stream_id)]


async def test_replay_is_verbatim_and_writes_nothing(settings: Settings, tmp_path: Path) -> None:
    events = await run_scenario(SCENARIOS["not-ready"], settings)
    path = tmp_path / "log.jsonl"
    write_golden(path, events)
    bus = StreamBus()
    before = sorted(p.name for p in settings.runs_dir.glob("*")) if settings.runs_dir.exists() else []
    session = ReplaySession(dataset_id="not-ready", source="golden", path=path, speed=4000.0, bus=bus)
    session.load()
    session.start()
    replayed = await asyncio.wait_for(collect(bus, session.session_id), 10)
    assert [Event.model_validate(e) for e in replayed] == events
    after = sorted(p.name for p in settings.runs_dir.glob("*")) if settings.runs_dir.exists() else []
    assert before == after


async def test_replay_gaps_scale_with_speed(tmp_path: Path, settings: Settings) -> None:
    events = await run_scenario(SCENARIOS["not-ready"], settings)
    path = tmp_path / "log.jsonl"
    write_golden(path, events)
    one = ReplaySession(dataset_id="not-ready", source="golden", path=path, speed=1.0, bus=StreamBus())
    four = ReplaySession(dataset_id="not-ready", source="golden", path=path, speed=4.0, bus=StreamBus())
    one.load()
    four.load()
    assert sum(one.gaps()) == 24.0
    assert all(abs(a / 4 - b) < 1e-9 for a, b in zip(one.gaps(), four.gaps(), strict=True))


async def test_replay_timing_is_honoured(tmp_path: Path, settings: Settings) -> None:
    events = await run_scenario(SCENARIOS["not-ready"], settings)
    path = tmp_path / "log.jsonl"
    write_golden(path, events)
    bus = StreamBus()
    session = ReplaySession(dataset_id="not-ready", source="golden", path=path, speed=48.0, bus=bus)
    session.load()
    started = time.monotonic()
    session.start()
    await asyncio.wait_for(collect(bus, session.session_id), 10)
    elapsed = time.monotonic() - started
    assert 0.35 <= elapsed <= 1.5, elapsed


async def test_replay_source_prefers_latest_recording(settings: Settings) -> None:
    registry = Registry(settings)
    golden = registry.replay_source("clean-run")
    assert golden is not None and golden.kind == "golden"
    await run_scenario(
        SCENARIOS["clean-run"], settings, record=True, run_id="00000000-0000-4000-8000-0000000000aa"
    )
    recorded = registry.replay_source("clean-run")
    assert recorded is not None and recorded.kind == "recording"
    assert recorded.run_id == "00000000-0000-4000-8000-0000000000aa"


async def test_human_events_replay_without_waiting(tmp_path: Path, settings: Settings) -> None:
    events = await run_scenario(SCENARIOS["planted-inconsistency"], settings)
    path = tmp_path / "log.jsonl"
    write_golden(path, events)
    bus = StreamBus()
    session = ReplaySession(
        dataset_id="planted-inconsistency", source="golden", path=path, speed=100000.0, bus=bus
    )
    session.load()
    session.start()
    replayed = await asyncio.wait_for(collect(bus, session.session_id), 10)
    types = [e["type"] for e in replayed]
    assert "clarification.answered" in types and "human.approved" in types
    assert types[-1] == "run.terminated"
