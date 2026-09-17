from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.config import Settings
from app.main import create_app

pytestmark = pytest.mark.dataset


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(Settings(runs_dir=tmp_path / "runs", stub_pace=5000.0, agent_mode="stub"))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        c.app = app  # type: ignore[attr-defined]
        yield c


async def wait_for(
    client: httpx.AsyncClient, run_id: str, predicate: Any, limit_s: float = 10.0
) -> dict[str, Any]:
    deadline = asyncio.get_running_loop().time() + limit_s
    while True:
        status = (await client.get(f"/api/runs/{run_id}")).json()
        if predicate(status):
            return status  # type: ignore[no-any-return]
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError(f"timed out: {status}")
        await asyncio.sleep(0.02)


async def test_datasets_in_spec_order(client: httpx.AsyncClient) -> None:
    listing = (await client.get("/api/datasets")).json()
    assert [d["label"] for d in listing] == [
        "01 · Clean run",
        "02 · Planted inconsistency",
        "03 · Missing sheet",
        "04 · Missing price",
        "05 · Not ready",
        "06 · Prospect own",
        "07 · Prospect A",
        "08 · Prospect B",
        "09 · Prospect C",
    ]
    assert all(d["replay_source"] == "golden" for d in listing)


async def test_pages_carry_build_stamp(client: httpx.AsyncClient) -> None:
    for path in ["/demo", "/settings", "/preflight"]:
        html = (await client.get(path)).text
        assert "{{BUILD_STAMP}}" not in html
        assert "build " in html
    assert (await client.get("/login")).status_code == 200


async def test_full_run_over_the_api(client: httpx.AsyncClient) -> None:
    started = await client.post("/api/runs", json={"dataset_id": "planted-inconsistency"})
    assert started.status_code == 201
    run_id = started.json()["run_id"]
    assert (await client.post("/api/runs", json={"dataset_id": "clean-run"})).status_code == 409

    status = await wait_for(client, run_id, lambda s: s["pending"]["kind"] == "clarifications")
    assert status["status"] == "paused"
    bad = await client.post(
        f"/api/runs/{run_id}/answers", json={"answers": [{"question_id": "q_service_voltage", "answer": "x"}]}
    )
    assert bad.status_code == 400
    answers = [{"question_id": q, "answer": "208Y/120 V"} for q in status["pending"]["question_ids"]]
    assert (await client.post(f"/api/runs/{run_id}/answers", json={"answers": answers})).status_code == 202

    await wait_for(client, run_id, lambda s: s["pending"]["kind"] == "handoff")
    # From S4 every decision is real; an edit without its markdown is the one refused here.
    empty_edit = await client.post(f"/api/runs/{run_id}/decision", json={"decision": "edit"})
    assert empty_edit.status_code == 400 and "markdown" in empty_edit.json()["error"]
    assert (
        await client.post(f"/api/runs/{run_id}/decision", json={"decision": "approve"})
    ).status_code == 202

    final = await wait_for(client, run_id, lambda s: s["status"] == "terminated")
    assert final["exit"] == "reviewer_pass"
    events = (await client.get(f"/api/runs/{run_id}/events")).json()
    assert events[-1]["type"] == "run.terminated"
    ref = next(e["prompt_ref"] for e in events if e["prompt_ref"])
    bundle = (await client.get(f"/api/prompts/{ref}")).json()
    assert [s["label"] for s in bundle["sections"]] == [
        "System instructions",
        "Context provided",
        "Task",
        "Tools available",
        "Model",
        "Pages",
    ]
    listing = (await client.get("/api/datasets")).json()
    assert next(d for d in listing if d["id"] == "planted-inconsistency")["replay_source"] == "recording"


async def test_unknown_things_are_404(client: httpx.AsyncClient) -> None:
    assert (await client.post("/api/runs", json={"dataset_id": "nope"})).status_code == 404
    assert (await client.get("/api/runs/nope")).status_code == 404
    assert (await client.get("/api/prompts/nope")).status_code == 404
    assert (await client.get("/api/streams/nope/events")).status_code == 404


async def test_golden_prefix_endpoint(client: httpx.AsyncClient) -> None:
    events = (await client.get("/api/datasets/not-ready/golden?upto=3")).json()
    assert [e["seq"] for e in events] == [1, 2, 3]
