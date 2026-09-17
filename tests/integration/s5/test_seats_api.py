"""The seat routes: live cards, greyed options with a reason, swaps applied next run or next dispatch (S5)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.config import ROOT, Settings
from app.live.providers import Availability, ModelConfig
from app.main import create_app

pytestmark = pytest.mark.dataset

FIXTURE = ROOT / "tests" / "fixtures" / "models-export.yaml"
AVAILABLE = {
    "bedrock": Availability("bedrock", True, "credentials resolved"),
    "google": Availability("google", True, "key present"),
    "ollama": Availability("ollama", True, "reachable, models present"),
    "xai": Availability("xai", False, "no credentials in .env"),
    "anthropic": Availability("anthropic", False, "no credentials in .env"),
}


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(
        Settings(runs_dir=tmp_path / "runs", stub_pace=40.0, agent_mode="stub"),
        model_config=ModelConfig.load(FIXTURE),
        availability=AVAILABLE,
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def events_of(client: httpx.AsyncClient, run_id: str) -> list[dict[str, Any]]:
    return list((await client.get(f"/api/runs/{run_id}/events")).json())


async def test_seat_table_and_swaps_when_idle(client: httpx.AsyncClient) -> None:
    table = (await client.get("/api/seats")).json()
    assert [row["seat"] for row in table["seats"]][:6] == [
        "orchestrator",
        "intake",
        "estimator",
        "pricing",
        "writer",
        "reviewer",
    ]
    greyed = [o for o in table["models"] if not o["available"]]
    assert {o["reason"] for o in greyed} == {"no credentials in .env"}
    assert "GEMINI_API_KEY" not in str(table) and "AWS_" not in str(table)

    assert (await client.post("/api/seats/estimator", json={"model": "nope"})).status_code == 400
    assert (await client.post("/api/seats/janitor", json={"model": "export-opus"})).status_code == 400
    refused = await client.post("/api/seats/estimator", json={"model": "export-grok"})
    assert refused.status_code == 409 and "no credentials in .env" in refused.json()["error"]

    applied = await client.post("/api/seats/estimator", json={"model": "export-opus"})
    assert applied.status_code == 200
    assert (
        applied.json()["applied"] == "next-run"
        and applied.json()["model"]["label"] == "claude-opus via Bedrock"
    )
    table = (await client.get("/api/seats")).json()
    estimator = next(row for row in table["seats"] if row["seat"] == "estimator")
    assert (
        estimator["card"]["model"]["label"] == "claude-opus via Bedrock"
        and estimator["model_key"] == "export-opus"
    )
    meta = (await client.get("/api/meta")).json()
    assert meta["idle_roster"]["estimator"]["model"]["label"] == "claude-opus via Bedrock"

    warned = await client.post("/api/seats/reviewer", json={"model": "export-sonnet"})
    assert warned.status_code == 200 and "Writer" in warned.json()["warning"]


async def test_swap_during_a_stub_run_emits_model_changed(client: httpx.AsyncClient) -> None:
    started = await client.post("/api/runs", json={"dataset_id": "clean-run"})
    assert started.status_code == 201
    run_id = started.json()["run_id"]
    for _ in range(500):
        if any(e["type"] == "stage.changed" for e in await events_of(client, run_id)):
            break
        await asyncio.sleep(0.02)
    swapped = await client.post("/api/seats/writer", json={"model": "export-gemini"})
    assert swapped.status_code == 200 and swapped.json()["applied"] == "next-dispatch"
    events = await events_of(client, run_id)
    changed = [e for e in events if e["type"] == "model.changed"]
    assert len(changed) == 1 and changed[0]["payload"]["to_model"]["label"] == "gemini-2.5-pro via Google"
    status = (await client.get(f"/api/runs/{run_id}")).json()
    assert (
        next(a for a in status["roster"] if a["agent_id"] == "writer")["model"]["label"]
        == "gemini-2.5-pro via Google"
    )
    await client.post(f"/api/runs/{run_id}/stop")
