"""The run's own clock on the wire (spec 012, research D4): the anchor the Demo page's Elapsed
clock takes when it starts a run or loads while one is live."""

from __future__ import annotations

import asyncio
import datetime as dt
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.main import create_app
from app.orchestrator.clock import Clock, VirtualClock
from app.schema.events import parse_ts

pytestmark = pytest.mark.dataset

START = dt.datetime(2026, 9, 21, 9, 0, tzinfo=dt.UTC)


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    # A slow pace keeps the stubbed run live long enough to read /api/meta while it runs.
    app = create_app(Settings(runs_dir=tmp_path / "runs", stub_pace=1.0, agent_mode="stub"))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_start_reply_and_meta_carry_the_run_clock(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/meta")).json()["live_run_clock"] is None
    reply = await client.post("/api/runs", json={"dataset_id": "planted-inconsistency"})
    assert reply.status_code == 201
    body = reply.json()
    reading = body["clock"]
    assert reading["pace"] == 1.0
    parse_ts(reading["now"])
    meta = (await client.get("/api/meta")).json()
    assert meta["live_run_id"] == body["run_id"]
    later = meta["live_run_clock"]
    assert later["pace"] == 1.0
    assert parse_ts(later["now"]) >= parse_ts(reading["now"])
    await client.post(f"/api/runs/{body['run_id']}/stop")
    for _ in range(200):
        if (await client.get("/api/meta")).json()["live_run_clock"] is None:
            break
        await asyncio.sleep(0.02)
    assert (await client.get("/api/meta")).json()["live_run_clock"] is None


async def test_now_ts_advances_at_the_pace() -> None:
    clock = Clock(START, pace=1000.0)
    first = parse_ts(clock.now_ts())
    await asyncio.sleep(0.01)
    second = parse_ts(clock.now_ts())
    # 10 ms of wall time at pace 1000 is about 10 s on the run's clock.
    assert (second - first).total_seconds() >= 5.0


def test_virtual_clock_now_is_the_start() -> None:
    assert parse_ts(VirtualClock(START).now_ts()) == START
