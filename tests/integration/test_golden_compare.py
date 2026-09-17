"""Replay-and-compare suite: each stubbed run against its committed golden log, on the ordered
stage transitions and the terminal exit (datasets/README.md)."""

from __future__ import annotations

import dataclasses

import pytest

from app.agents.stubs import SCENARIOS
from app.config import Settings, load_settings
from app.runs.golden import compare, deterministic_run, read_golden, terminal_exit, transitions
from app.runs.registry import discover_datasets
from app.schema.events import validate_run

pytestmark = pytest.mark.dataset

DATASETS = [d.id for d in discover_datasets(load_settings().datasets_dir)]


def test_all_nine_datasets_have_golden_logs() -> None:
    infos = discover_datasets(load_settings().datasets_dir)
    assert len(infos) == 9
    assert all(info.golden_path.exists() for info in infos)


@pytest.mark.parametrize("dataset_id", DATASETS)
async def test_live_stub_run_matches_golden(dataset_id: str) -> None:
    settings = load_settings()
    info = next(d for d in discover_datasets(settings.datasets_dir) if d.id == dataset_id)
    golden = read_golden(info.golden_path)
    actual = await deterministic_run(settings, dataset_id)
    result = compare(dataset_id, actual, golden)
    assert result.ok, result.message


@pytest.mark.parametrize("dataset_id", DATASETS)
def test_golden_log_is_a_valid_run(dataset_id: str) -> None:
    info = next(d for d in discover_datasets(load_settings().datasets_dir) if d.id == dataset_id)
    events = read_golden(info.golden_path)
    assert validate_run(events) == []
    assert events[-1].type == "run.terminated"


def test_planted_inconsistency_golden_shape() -> None:
    info = next(d for d in discover_datasets(load_settings().datasets_dir) if d.id == "planted-inconsistency")
    events = read_golden(info.golden_path)
    backward = [t for t in transitions(events) if t[2] == "backward"]
    assert backward == [("review", "work", "backward")]
    retries = [e for e in events if e.type == "retry.incremented"]
    assert len(retries) == 1 and retries[0].payload["count"] == 1


def test_missing_sheet_golden_records_escalate() -> None:
    info = next(d for d in discover_datasets(load_settings().datasets_dir) if d.id == "missing-sheet")
    events = read_golden(info.golden_path)
    assert terminal_exit(events) == "blocker_escalated"
    assert any(e.type == "clarification.answered" and e.payload["action"] == "escalate" for e in events)


async def test_divergence_is_named(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> None:
    """A stub that skips the review rework must fail the comparison with the first divergence."""
    settings = load_settings()
    info = next(d for d in discover_datasets(settings.datasets_dir) if d.id == "planted-inconsistency")
    golden = read_golden(info.golden_path)
    base = SCENARIOS["planted-inconsistency"]
    broken = dataclasses.replace(base, review=[base.review[1]])
    monkeypatch.setitem(SCENARIOS, "planted-inconsistency", broken)
    actual = await deterministic_run(Settings(datasets_dir=settings.datasets_dir), "planted-inconsistency")
    result = compare("planted-inconsistency", actual, golden)
    assert not result.ok
    assert "planted-inconsistency" in result.message
    assert "transition 5" in result.message
