"""In-memory seat swaps on the registry: applied to the effective configuration, never to the file (S5, US1)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.config import ROOT, Settings
from app.live.providers import MODELS_PATH, Availability, ModelConfig, family_of
from app.runs.registry import SHARED_FAMILY_WARNING, LiveUnavailable, Registry

FIXTURE = ROOT / "tests" / "fixtures" / "models-export.yaml"

AVAILABLE = {
    "bedrock": Availability("bedrock", True, "credentials resolved"),
    "google": Availability("google", True, "key present"),
    "ollama": Availability("ollama", True, "reachable, models present"),
    "xai": Availability("xai", False, "no credentials in .env"),
    "anthropic": Availability("anthropic", False, "no credentials in .env"),
}


def registry(tmp_path: Path) -> Registry:
    return Registry(
        Settings(runs_dir=tmp_path / "runs", agent_mode="stub"),
        model_config=ModelConfig.load(FIXTURE),
        availability=AVAILABLE,
    )


def test_override_changes_the_effective_configuration_only(tmp_path: Path) -> None:
    before = hashlib.sha256(MODELS_PATH.read_bytes()).hexdigest()
    r = registry(tmp_path)
    assert r.effective_config().seat_spec("estimator").label == "claude-sonnet via Bedrock (vision)"
    swap = r.set_seat_model("estimator", "export-opus")
    assert swap.applied == "next-run" and swap.model.label == "claude-opus via Bedrock"
    assert r.effective_config().seat_spec("estimator").label == "claude-opus via Bedrock"
    assert r.model_config.seat_spec("estimator").label == "claude-sonnet via Bedrock (vision)", "the file's config"
    assert hashlib.sha256(MODELS_PATH.read_bytes()).hexdigest() == before


def test_unknown_key_seat_and_unavailable_provider_are_refused(tmp_path: Path) -> None:
    r = registry(tmp_path)
    with pytest.raises(ValueError, match="unknown model"):
        r.set_seat_model("estimator", "nope")
    with pytest.raises(ValueError, match="unknown seat"):
        r.set_seat_model("janitor", "export-opus")
    with pytest.raises(LiveUnavailable) as caught:
        r.set_seat_model("estimator", "export-grok")
    assert "no credentials in .env" in str(caught.value)
    assert r.overrides == {}


def test_seat_table_shows_live_labels_and_greyed_options(tmp_path: Path) -> None:
    table = registry(tmp_path).seat_table()
    seats = {row["seat"]: row for row in table["seats"]}
    assert list(seats) == ["orchestrator", "intake", "estimator", "pricing", "writer", "reviewer", "case", "market"]
    assert seats["pricing"]["card"]["model"]["label"] == "llama3.1 8b, local"
    assert seats["estimator"]["dependency"] == "Bid response workflow. Needs vision on drawings"
    assert seats["reviewer"]["warning"] == ""
    options = {o["key"]: o for o in table["models"]}
    assert options["export-grok"] == {
        "key": "export-grok",
        "label": "grok-3 via xAI",
        "provider": "xai",
        "provider_label": "xAI",
        "available": False,
        "reason": "no credentials in .env",
    }
    assert options["export-llama"]["available"] and options["export-llama"]["reason"] == ""
    assert table["note"] == "Changes apply at the next stage."
    assert "GEMINI" not in str(table) and "AKIA" not in str(table)


def test_ollama_reason_when_not_detected(tmp_path: Path) -> None:
    r = Registry(
        Settings(runs_dir=tmp_path / "runs", agent_mode="stub"),
        model_config=ModelConfig.load(FIXTURE),
        availability={**AVAILABLE, "ollama": Availability("ollama", False, "Ollama not reachable")},
    )
    llama = next(o for o in r.model_options() if o["key"] == "export-llama")
    assert llama["reason"] == "Ollama not detected at startup"


def test_reviewer_on_the_writers_family_warns_but_applies(tmp_path: Path) -> None:
    r = registry(tmp_path)
    swap = r.set_seat_model("reviewer", "export-opus")
    assert swap.warning == SHARED_FAMILY_WARNING
    assert r.effective_config().seat_spec("reviewer").label == "claude-opus via Bedrock"
    assert r.seat_table()["seats"][5]["warning"] == SHARED_FAMILY_WARNING
    back = r.set_seat_model("reviewer", "export-gemini")
    assert back.warning == ""


def test_family_detection() -> None:
    config = ModelConfig.load(MODELS_PATH)
    families = {key: family_of(spec) for key, spec in config.models.items()}
    for key, family in families.items():
        assert family in {"claude", "gemini", "llama", "qwen", "gemma", "grok", "granite"}, (key, family)
    fixture = ModelConfig.load(FIXTURE)
    assert family_of(fixture.models["export-opus"]) == "claude"
    assert family_of(fixture.models["export-gemini"]) == "gemini"
    assert family_of(fixture.models["export-llama"]) == "llama"


def test_idle_roster_carries_the_effective_models(tmp_path: Path) -> None:
    r = registry(tmp_path)
    r.set_seat_model("writer", "export-gemini")
    roster = r.idle_roster()
    assert roster["writer"].model.label == "gemini-2.5-pro via Google"
    assert roster["writer"].name == "Willa"
    assert roster["pricing"].model.label == "llama3.1 8b, local"
