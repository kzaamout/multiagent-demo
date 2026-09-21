"""The recheck after a seat change (spec 012 User Story 3, research D10, SC-005, SC-007)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from tests.integration.s12.support import MARKER, Probes, app_client

pytestmark = pytest.mark.dataset


def stored(tmp_path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads((tmp_path / "runs" / "preflight.json").read_text(encoding="utf-8"))
    return {c["id"]: c for c in data["checks"]}


async def swap_and_recheck(client: httpx.AsyncClient, seat: str, model: str) -> dict[str, Any]:
    assert (await client.post(f"/api/seats/{seat}", json={"model": model})).status_code == 200
    reply = await client.post("/api/preflight/recheck", json={"model": model})
    assert reply.status_code == 200, reply.text
    return dict(reply.json())


async def test_a_failing_model_is_stored_and_turns_the_dot_red_then_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    probes = Probes(failing={"us.anthropic.claude-opus"})
    async with app_client(tmp_path, probes, monkeypatch) as client:
        await client.post("/api/preflight/run")
        before = stored(tmp_path)
        await asyncio.sleep(1.1)  # checked_at has one-second resolution
        reply = await swap_and_recheck(client, "estimator", "export-opus")
        assert reply["header"]["status"] == "fail"
        row = next(c for c in reply["checks"] if c["id"] == "model:export-opus")
        assert row["status"] == "fail" and row["seats"] == ["estimator"]
        assert row["detail"] == "claude-opus did not answer (RuntimeError)"
        after = stored(tmp_path)
        assert after["model:export-opus"]["checked_at"] > before["model:export-opus"]["checked_at"]
        untouched = set(before) - {"model:export-opus", "env"}
        assert {k: after[k] for k in untouched} == {k: before[k] for k in untouched}

        back = await swap_and_recheck(client, "estimator", "export-sonnet")
        assert back["header"]["status"] == "pass"
        assert MARKER not in json.dumps(reply) + json.dumps(back)


async def test_a_local_model_rechecks_ollama_and_its_pulled_row_without_a_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    probes = Probes()
    async with app_client(tmp_path, probes, monkeypatch) as client:
        reply = await swap_and_recheck(client, "reviewer", "export-llama")
    assert {c["id"] for c in reply["checks"]} == {"ollama", "model:export-llama", "env"}
    assert probes.calls == []


async def test_a_recheck_waits_for_a_running_full_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    probes = Probes(gate=asyncio.Event())
    async with app_client(tmp_path, probes, monkeypatch) as client:
        full = asyncio.create_task(client.post("/api/preflight/run"))
        await asyncio.sleep(0.05)
        recheck = asyncio.create_task(client.post("/api/preflight/recheck", json={"model": "export-gemini"}))
        await asyncio.sleep(0.1)
        assert not recheck.done()
        assert probes.gate is not None
        probes.gate.set()
        assert (await full).status_code == 200
        assert (await recheck).status_code == 200


async def test_an_unknown_model_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async with app_client(tmp_path, Probes(), monkeypatch) as client:
        reply = await client.post("/api/preflight/recheck", json={"model": "nope"})
    assert reply.status_code == 400 and reply.json() == {"error": "unknown model nope"}


async def test_a_recheck_during_a_live_run_adds_nothing_to_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    probes = Probes()
    async with app_client(tmp_path, probes, monkeypatch, stub_pace=20.0) as client:
        start = await client.post("/api/runs", json={"dataset_id": "planted-inconsistency"})
        assert start.status_code == 201, start.text
        run_id = start.json()["run_id"]
        for _ in range(250):
            if len((await client.get(f"/api/runs/{run_id}/events")).json()) >= 2:
                break
            await asyncio.sleep(0.02)
        await client.post(f"/api/runs/{run_id}/pause")
        for _ in range(250):
            events = (await client.get(f"/api/runs/{run_id}/events")).json()
            if events and events[-1]["type"] == "run.paused":
                break
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.2)
        events = (await client.get(f"/api/runs/{run_id}/events")).json()
        assert events[-1]["type"] == "run.paused"
        folder = tmp_path / "runs" / run_id
        files_before = sorted(p.name for p in folder.rglob("*"))
        reply = await swap_and_recheck(client, "reviewer", "export-opus")
        # The Reviewer now shares the Writer's claude family: amber, never red (spec 012 decision 11).
        assert reply["header"]["status"] == "warn"
        after = (await client.get(f"/api/runs/{run_id}/events")).json()
        # The swap emits the one model.changed the S5 contract already records; the recheck adds nothing.
        added = [e["type"] for e in after[len(events) :]]
        assert added == ["model.changed"]
        assert sorted(p.name for p in folder.rglob("*")) == files_before
        assert probes.calls == ["us.anthropic.claude-opus"]
        await client.post(f"/api/runs/{run_id}/stop")
