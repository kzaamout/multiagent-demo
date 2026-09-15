"""No value from .env may appear in any event payload or prompt bundle (constitution XVII)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.agents.stubs import SCENARIOS
from app.config import load_settings
from tests.conftest import run_scenario

MARKER = "zq9-secret-marker-7f3a"


@pytest.mark.parametrize("dataset_id", sorted(SCENARIOS))
async def test_env_values_never_reach_events_or_bundles(
    dataset_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(f"LEAK_MARKER={MARKER}\nANTHROPIC_API_KEY={MARKER}-key\n", encoding="utf-8")
    monkeypatch.delenv("LEAK_MARKER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    load_settings(env_file)
    assert os.environ.get("LEAK_MARKER") == MARKER
    from app.config import Settings

    scratch = Settings(runs_dir=tmp_path / "runs")
    run_id = "00000000-0000-4000-8000-0000000000ee"
    events = await run_scenario(SCENARIOS[dataset_id], scratch, record=True, run_id=run_id)
    for event in events:
        assert MARKER not in event.to_line()
    folder = tmp_path / "runs" / run_id
    for path in folder.rglob("*"):
        if path.is_file():
            assert MARKER not in path.read_text(encoding="utf-8"), path
    for bundle in SCENARIOS[dataset_id].bundles().values():
        assert MARKER not in json.dumps(bundle.model_dump())
    monkeypatch.delenv("LEAK_MARKER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


async def test_env_values_never_reach_live_bundles_or_recordings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Live mode: provider keys in the environment never appear in bundles, events, or run files."""
    from app.agents.base import HumanScript
    from app.orchestrator.driver import drive
    from tests.integration.s2 import live_harness

    for key in ("GEMINI_API_KEY", "XAI_API_KEY", "AWS_SECRET_ACCESS_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.setenv(key, MARKER)
    orchestrator = live_harness.build(
        tmp_path, live_harness.full_turns(), "30000000-0000-4000-8000-000000000001"
    )
    await drive(orchestrator, HumanScript(answers={"q_service_voltage": "120/208 V"}, decision="approve"))
    assert orchestrator.events[-1].payload["exit"] == "reviewer_pass"
    for event in orchestrator.events:
        assert MARKER not in event.to_line()
    for bundle in orchestrator.bundles.values():
        assert MARKER not in bundle.model_dump_json()
    assert_no_marker_in_files(tmp_path)


def assert_no_marker_in_files(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".json", ".jsonl"}:
            assert MARKER not in path.read_text(encoding="utf-8"), path
