"""Each registry model states whether its weights are open or proprietary (spec 014, decision 6a)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.live.providers import ModelConfig


def test_every_model_in_the_registry_states_its_kind() -> None:
    config = ModelConfig.load()
    assert {spec.key: spec.weights for spec in config.models.values() if spec.weights is None} == {}
    for spec in config.models.values():
        # True of every model registered today; the field is still set by hand, never derived from this.
        expected = "open" if spec.provider == "ollama" else "proprietary"
        assert spec.weights == expected, spec.key


def _write(tmp_path: Path, weights: object) -> Path:
    model = {"provider": "ollama", "model_id": "m:1b", "label": "m, local"}
    if weights is not None:
        model["weights"] = weights  # type: ignore[assignment]
    data = {"providers": {"ollama": {}}, "models": {"m": model}, "seats": {"writer": {"model": "m"}}}
    path = tmp_path / "models.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_an_unknown_kind_is_refused_by_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="model m: weights must be open or proprietary"):
        ModelConfig.load(_write(tmp_path, "shareware"))


def test_a_model_without_the_key_loads_unclassified(tmp_path: Path) -> None:
    assert ModelConfig.load(_write(tmp_path, None)).models["m"].weights is None
    assert ModelConfig.load(_write(tmp_path, "open")).models["m"].weights == "open"
