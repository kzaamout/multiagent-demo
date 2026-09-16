"""The evidence command reports a match for a run that follows its golden log and a mismatch otherwise."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from app.config import Settings, load_settings
from app.runs.golden import deterministic_run

pytestmark = pytest.mark.dataset

ROOT = Path(__file__).resolve().parents[3]


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("compare_run", ROOT / "scripts" / "compare_run.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def test_match_and_mismatch(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    settings = load_settings()
    events = await deterministic_run(Settings(datasets_dir=settings.datasets_dir), "missing-price")
    run_id = events[0].run_id
    folder = tmp_path / "runs" / run_id
    folder.mkdir(parents=True)
    (folder / "events.jsonl").write_text("\n".join(e.to_line() for e in events) + "\n", encoding="utf-8")
    script = load_script()
    args = [run_id, "--runs", str(tmp_path / "runs"), "--datasets", str(settings.datasets_dir)]
    assert script.main(args) == 0
    assert "MATCH" in capsys.readouterr().out

    other = tmp_path / "datasets" / "missing-price"
    other.mkdir(parents=True)
    not_ready = (settings.datasets_dir / "not-ready" / "golden-events.jsonl").read_text(encoding="utf-8")
    (other / "golden-events.jsonl").write_text(not_ready, encoding="utf-8")
    assert (
        script.main([run_id, "--runs", str(tmp_path / "runs"), "--datasets", str(tmp_path / "datasets")]) == 1
    )
    assert "MISMATCH" in capsys.readouterr().out
