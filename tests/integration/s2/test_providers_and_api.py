from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.config import Settings
from app.live.providers import ModelConfig, check_availability, unavailable_seats
from app.live.seat_call import SeatModel
from app.main import create_app
from app.schema.events import Model
from tests.integration.s2 import live_harness as h
from tests.support.scripted_model import ScriptedModel

SECRET = "zq9-provider-secret-5b1d"


@pytest.fixture
def no_credentials(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for key in [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
        "AWS_DEFAULT_PROFILE",
        "AWS_BEARER_TOKEN_BEDROCK",
        "GEMINI_API_KEY",
        "XAI_API_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "no-credentials"))
    monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "no-config"))
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")


def test_model_config_loads_and_checks_temperature(tmp_path: Path) -> None:
    config = ModelConfig.load()
    assert config.seat_spec("reviewer").provider == "google"
    assert config.seat_spec("pricing").model_id == "llama3.1:8b"
    bad = tmp_path / "models.yaml"
    bad.write_text(
        "providers: {bedrock: {region: ca-central-1}}\n"
        "models: {m: {provider: bedrock, model_id: x, label: x, temperature: false}}\n"
        "seats: {orchestrator: {model: m, temperature: 0.1}}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="does not accept a temperature"):
        ModelConfig.load(bad)


def test_availability_is_booleans_and_reasons(no_credentials: None, monkeypatch: pytest.MonkeyPatch) -> None:
    config = ModelConfig.load()
    config.providers["ollama"]["host"] = "http://127.0.0.1:9"
    report = check_availability(config)
    assert not report["bedrock"].available and "no AWS credentials" in report["bedrock"].reason
    assert not report["google"].available and report["google"].reason == "no credentials in .env"
    assert not report["ollama"].available and "not reachable" in report["ollama"].reason
    monkeypatch.setenv("GEMINI_API_KEY", SECRET)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIATESTONLY")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", SECRET)
    report = check_availability(config)
    assert report["google"].available and report["bedrock"].available
    assert all(SECRET not in a.reason for a in report.values())
    problems = unavailable_seats(config, report)
    assert problems == ["pricing needs llama3.1 8b, local: Ollama not reachable at http://127.0.0.1:9"]


def curated_datasets(tmp_path: Path) -> Path:
    root = tmp_path / "datasets"
    target = root / "clean-run"
    shutil.copytree(h.FIXTURES, target)
    (target / "brand.yaml").write_text('prospect_name: "Test Library"\n', encoding="utf-8")
    (target / "README.md").write_text("# Clean run (test copy)\n", encoding="utf-8")
    return root


def scripted_factory() -> Any:
    runs: dict[str, dict[str, Any]] = {}

    def factory(seat: str) -> SeatModel:
        turns = runs.setdefault("current", h.full_turns())
        if seat == "reviewer":
            runs.pop("current", None)
        return SeatModel(
            ScriptedModel(turns[seat]),
            Model(provider="test", model_id="scripted", label=f"scripted {seat}"),
            2.0,
            10.0,
        )

    return factory


async def test_live_run_refused_without_providers(
    no_credentials: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", SECRET)
    config = ModelConfig.load()
    config.providers["ollama"]["host"] = "http://127.0.0.1:9"
    settings = Settings(
        runs_dir=tmp_path / "runs",
        datasets_dir=curated_datasets(tmp_path),
        knowledge_dir=tmp_path / "knowledge",
    )
    app = create_app(settings, model_config=config)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        listing = (await client.get("/api/datasets")).json()
        assert listing[0]["mode"] == "live"
        refused = await client.post("/api/runs", json={"dataset_id": "clean-run"})
        assert refused.status_code == 409
        message = refused.json()["error"]
        assert (
            "orchestrator needs claude-sonnet-5 via Bedrock" in message
            and "pricing needs llama3.1 8b, local" in message
        )
        providers = await client.get("/api/providers")
        assert SECRET not in providers.text
        assert providers.json()["providers"]["google"] == {"available": True, "reason": "key present"}


async def test_live_run_through_the_api_with_scripted_models(tmp_path: Path) -> None:
    settings = Settings(
        runs_dir=tmp_path / "runs",
        datasets_dir=curated_datasets(tmp_path),
        knowledge_dir=tmp_path / "knowledge",
    )
    app = create_app(settings, seat_model_factory=scripted_factory())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        started = await client.post("/api/runs", json={"dataset_id": "clean-run"})
        assert started.status_code == 201, started.text
        run_id = started.json()["run_id"]
        for _ in range(500):
            status = (await client.get(f"/api/runs/{run_id}")).json()
            if status["pending"]["kind"] == "clarifications":
                await client.post(
                    f"/api/runs/{run_id}/answers",
                    json={"answers": [{"question_id": "q_service_voltage", "answer": "120/208 V"}]},
                )
            elif status["pending"]["kind"] == "handoff":
                await client.post(f"/api/runs/{run_id}/decision", json={"decision": "approve"})
            elif status["status"] == "terminated":
                break
            await asyncio.sleep(0.02)
        assert status["exit"] == "reviewer_pass"
        assert {a["model"]["label"] for a in status["roster"]} >= {"scripted estimator", "scripted reviewer"}
        events = (await client.get(f"/api/runs/{run_id}/events")).json()
        draft = next(e for e in events if e["type"] == "draft.committed")
        text = (await client.get(f"/api/runs/{run_id}/files/{draft['payload']['markdown_path']}")).text
        assert "25 troffers" in text
        knowledge = (tmp_path / "knowledge" / "test-library.md").read_text(encoding="utf-8")
        assert "q_service_voltage: 120/208 V" in knowledge
