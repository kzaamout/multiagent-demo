"""Laptop and Cloud mode (S7 research D7): the setting, and Cloud mode greying local models in the registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings, load_settings
from app.live.providers import Availability
from app.runs.registry import CLOUD_MODE_REASON, Registry
from tests.unit.s7.test_preflight_checks import make_config


def test_run_mode_accepts_laptop_and_cloud_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")
    monkeypatch.delenv("RUN_MODE", raising=False)
    assert load_settings(env_file).run_mode == "laptop"
    monkeypatch.setenv("RUN_MODE", "cloud")
    assert load_settings(env_file).run_mode == "cloud"
    monkeypatch.setenv("RUN_MODE", "bogus")
    with pytest.raises(ValueError, match="RUN_MODE must be laptop or cloud"):
        load_settings(env_file)


def registry(tmp_path: Path, mode: str) -> Registry:
    availability = {
        "bedrock": Availability("bedrock", True, "credentials resolved"),
        "google": Availability("google", False, "no credentials in .env"),
        "xai": Availability("xai", False, "no credentials in .env"),
        "ollama": Availability("ollama", True, "reachable, models present"),
    }
    return Registry(
        Settings(runs_dir=tmp_path / "runs", agent_mode="stub", run_mode=mode),
        model_config=make_config({"estimator": "sonnet", "pricing": "qwen"}),
        availability=availability,
    )


def test_cloud_mode_greys_local_models_and_blocks_a_local_seat(tmp_path: Path) -> None:
    reg = registry(tmp_path, "cloud")
    assert reg.availability["ollama"] == Availability("ollama", False, CLOUD_MODE_REASON)
    options = {o["key"]: o for o in reg.model_options()}
    assert options["qwen"]["available"] is False
    assert options["qwen"]["reason"] == CLOUD_MODE_REASON
    assert options["qwen"]["note"] == CLOUD_MODE_REASON
    assert options["sonnet"]["available"] is True
    report = reg.provider_report()
    assert report["providers"]["ollama"] == {"available": False, "reason": CLOUD_MODE_REASON}
    assert any("pricing" in line and CLOUD_MODE_REASON in line for line in report["live_blockers"])
    assert all(m["available"] is False for m in reg.seat_table()["models"] if m["provider"] == "ollama")


def test_laptop_mode_serves_the_injected_availability_unchanged(tmp_path: Path) -> None:
    reg = registry(tmp_path, "laptop")
    assert reg.availability["ollama"].available is True
    options = {o["key"]: o for o in reg.model_options()}
    assert options["qwen"]["available"] is True and options["qwen"]["note"] == "Ollama, detected"
    assert reg.provider_report()["live_blockers"] == []
