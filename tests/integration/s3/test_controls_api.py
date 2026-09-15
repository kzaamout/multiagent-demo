"""Pause, resume, stop, and Dry intake through the API on stub runs (contracts/controls.md)."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.config import Settings
from app.main import create_app


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(Settings(runs_dir=tmp_path / "runs", stub_pace=40.0, agent_mode="stub"))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def events_of(client: httpx.AsyncClient, run_id: str) -> list[dict[str, Any]]:
    response = await client.get(f"/api/runs/{run_id}/events")
    return list(response.json())


async def wait_for_type(
    client: httpx.AsyncClient, run_id: str, type_: str, limit: float = 20.0
) -> list[dict[str, Any]]:
    deadline = time.monotonic() + limit
    while True:
        events = await events_of(client, run_id)
        if any(e["type"] == type_ for e in events):
            return events
        if time.monotonic() > deadline:
            raise AssertionError(f"no {type_}; last {[e['type'] for e in events[-4:]]}")
        await asyncio.sleep(0.05)


async def test_pause_resume_stop_over_the_api(client: httpx.AsyncClient) -> None:
    started = await client.post("/api/runs", json={"dataset_id": "missing-price"})
    assert started.status_code == 201
    run_id = started.json()["run_id"]
    await wait_for_type(client, run_id, "task.dispatched")
    assert (await client.post(f"/api/runs/{run_id}/pause")).status_code == 202
    await wait_for_type(client, run_id, "run.paused")
    assert (await client.post(f"/api/runs/{run_id}/resume")).status_code == 202
    await wait_for_type(client, run_id, "run.resumed")
    assert (await client.post(f"/api/runs/{run_id}/stop")).status_code == 202
    events = await wait_for_type(client, run_id, "run.terminated", limit=5)
    assert events[-1]["type"] == "run.terminated" and events[-1]["payload"]["exit"] == "stopped"
    assert (await client.post(f"/api/runs/{run_id}/stop")).status_code == 202, (
        "stop after the end is accepted"
    )


async def test_dry_intake_on_the_run_request(client: httpx.AsyncClient) -> None:
    started = await client.post("/api/runs", json={"dataset_id": "clean-run", "dry_intake": True})
    assert started.status_code == 201
    events = await wait_for_type(client, started.json()["run_id"], "run.terminated")
    last = events[-1]
    assert last["payload"]["exit"] == "dry_intake"
    assert last["payload"]["summary"]["readiness_verdict"]
    assert not any(e["type"] == "task.dispatched" for e in events)
