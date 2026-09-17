"""A run refuses to start without the compiler, naming the tool (spec FR-016)."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.runs import registry as registry_module
from app.runs.registry import LiveUnavailable, Registry

pytestmark = pytest.mark.dataset


def test_missing_typst_refuses_the_run(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(registry_module, "tools_available", lambda: {"pandoc": "3.10.2", "typst": None})
    registry = Registry(settings)
    with pytest.raises(LiveUnavailable) as caught:
        registry.build_orchestrator("clean-run")
    assert caught.value.problems == ["compiler missing (typst)"]
