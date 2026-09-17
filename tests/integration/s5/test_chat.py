"""Chat with an agent: from the seat's last bundle, out of band, and the run folder byte-identical (S5, US4)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.agents.base import HumanScript
from app.config import ROOT, Settings, load_settings
from app.live.chat import ChatRefused, chat, chat_allowed, find_bundle, folder_digest, system_prompt_for
from app.live.providers import Availability, ModelConfig
from app.live.seat_call import SeatModel
from app.main import create_app
from app.orchestrator.driver import drive
from app.runs.registry import Registry
from app.schema.events import Model
from tests.integration.s2 import live_harness as h
from tests.support.scripted_model import ScriptedModel

pytestmark = pytest.mark.dataset

FIXTURE = ROOT / "tests" / "fixtures" / "models-export.yaml"
AVAILABLE = {
    "bedrock": Availability("bedrock", True, "credentials resolved"),
    "google": Availability("google", True, "key present"),
    "ollama": Availability("ollama", True, "reachable, models present"),
    "xai": Availability("xai", False, "no credentials in .env"),
    "anthropic": Availability("anthropic", False, "no credentials in .env"),
}
ANSWER = "The single-line E-001 governs the service size, so 225 A."


def chat_model(seat: str) -> SeatModel:
    return SeatModel(
        strands_model=ScriptedModel([[{"text": ANSWER}]], tokens_in=900, tokens_out=40),
        model=Model(provider="test", model_id="scripted", label=f"scripted {seat}"),
        price_in=2.0,
        price_out=10.0,
    )


async def test_chat_answers_from_the_bundle_and_leaves_the_run_folder_untouched(tmp_path: Path) -> None:
    settings = Settings(
        runs_dir=tmp_path / "runs",
        datasets_dir=load_settings().datasets_dir,
        stub_pace=1000.0,
        agent_mode="stub",
    )
    registry = Registry(settings, model_config=ModelConfig.load(FIXTURE), availability=AVAILABLE)
    orchestrator = registry.build_orchestrator("planted-inconsistency", record=True)
    registry.runs[orchestrator.run_id] = orchestrator
    await drive(orchestrator, orchestrator.scenario.human_script)
    folder = settings.runs_dir / orchestrator.run_id
    before = folder_digest(folder)
    event_count = len(orchestrator.events)

    found = find_bundle(registry, orchestrator.run_id, "estimator")
    assert found is not None
    bundle, card = found
    assert card.agent_id == "estimator" and "Estimator" in bundle.system
    prompt = system_prompt_for(bundle)
    assert prompt.startswith(bundle.system) and "read-only" in prompt and bundle.context_slice in prompt
    assert chat_allowed(registry, orchestrator.run_id)

    reply = await chat(
        chat_model("estimator"), bundle, [{"role": "user", "text": "Why 225 A rather than 200 A?"}]
    )
    assert reply.text == ANSWER
    assert (reply.tokens_in, reply.tokens_out) == (900, 40)
    assert reply.est_cost == pytest.approx(900 / 1e6 * 2.0 + 40 / 1e6 * 10.0)

    assert folder_digest(folder) == before, "chat wrote nothing under the run folder"
    assert len(orchestrator.events) == event_count, "chat emitted no event"
    assert find_bundle(registry, orchestrator.run_id, "janitor") is None
    with pytest.raises(ChatRefused) as refused:
        await chat(chat_model("estimator"), bundle, [{"role": "assistant", "text": "x"}])
    assert refused.value.status == 400


async def test_chat_history_is_passed_to_the_model(tmp_path: Path) -> None:
    settings = Settings(
        runs_dir=tmp_path / "runs",
        datasets_dir=load_settings().datasets_dir,
        stub_pace=1000.0,
        agent_mode="stub",
    )
    registry = Registry(settings, model_config=ModelConfig.load(FIXTURE), availability=AVAILABLE)
    orchestrator = registry.build_orchestrator("clean-run", record=False)
    registry.runs[orchestrator.run_id] = orchestrator
    await drive(orchestrator, orchestrator.scenario.human_script)
    found = find_bundle(registry, orchestrator.run_id, "writer")
    assert found is not None
    model = chat_model("writer")
    scripted = model.strands_model
    assert isinstance(scripted, ScriptedModel)
    await chat(
        model,
        found[0],
        [
            {"role": "user", "text": "first"},
            {"role": "assistant", "text": "one"},
            {"role": "user", "text": "second"},
        ],
    )
    assert "first" in scripted.prompts[0] and "one" in scripted.prompts[0] and "second" in scripted.prompts[0]


async def test_a_recorded_run_is_chattable_from_its_folder(tmp_path: Path) -> None:
    orchestrator = h.build(tmp_path, h.full_turns(blocking=False), "50000000-0000-4000-8000-000000000541")
    await drive(orchestrator, HumanScript(answers={}, decision="approve"))
    settings = Settings(
        runs_dir=tmp_path / "runs", datasets_dir=load_settings().datasets_dir, agent_mode="stub"
    )
    registry = Registry(settings, model_config=ModelConfig.load(FIXTURE), availability=AVAILABLE)
    found = find_bundle(registry, orchestrator.run_id, "pricing")
    assert found is not None and "Pricing" in found[0].system, "read from runs/<id>/prompts on disk"
    assert chat_allowed(registry, orchestrator.run_id)


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(
        Settings(runs_dir=tmp_path / "runs", stub_pace=40.0, agent_mode="stub"),
        seat_model_factory=chat_model,
        model_config=ModelConfig.load(FIXTURE),
        availability=AVAILABLE,
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def events_of(client: httpx.AsyncClient, run_id: str) -> list[dict[str, Any]]:
    return list((await client.get(f"/api/runs/{run_id}/events")).json())


async def test_chat_route_refuses_a_live_run_and_answers_a_finished_one(client: httpx.AsyncClient) -> None:
    started = await client.post("/api/runs", json={"dataset_id": "clean-run"})
    run_id = started.json()["run_id"]
    for _ in range(500):
        if any(e["type"] == "task.completed" for e in await events_of(client, run_id)):
            break
        await asyncio.sleep(0.02)
    ask = {"run_id": run_id, "agent_id": "estimator", "messages": [{"role": "user", "text": "Why?"}]}
    live = await client.post("/api/chat", json=ask)
    assert live.status_code == 409 and "paused or finished" in live.json()["error"]
    for _ in range(1000):
        events = await events_of(client, run_id)
        if events[-1]["type"] == "run.terminated":
            break
        status = (await client.get(f"/api/runs/{run_id}")).json()
        if status["pending"]["kind"] == "handoff":
            await client.post(f"/api/runs/{run_id}/decision", json={"decision": "approve"})
        elif status["pending"]["kind"] == "clarifications":
            answers = [{"question_id": q, "answer": "No bid bond"} for q in status["pending"]["question_ids"]]
            await client.post(f"/api/runs/{run_id}/answers", json={"answers": answers})
        await asyncio.sleep(0.02)
    assert events[-1]["type"] == "run.terminated"
    metrics_before = (await client.get(f"/api/runs/{run_id}/files/metrics.json")).text
    answered = await client.post("/api/chat", json=ask)
    assert answered.status_code == 200, answered.text
    data = answered.json()
    assert (
        data["text"] == ANSWER and data["tokens_in"] == 900 and data["model"]["label"] == "scripted estimator"
    )
    assert len(await events_of(client, run_id)) == len(events), "no event was added"
    assert (await client.get(f"/api/runs/{run_id}/files/metrics.json")).text == metrics_before
    missing = await client.post("/api/chat", json={**ask, "agent_id": "janitor"})
    assert missing.status_code == 404
    unknown = await client.post("/api/chat", json={**ask, "run_id": "nope"})
    assert unknown.status_code == 404
