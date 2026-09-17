"""The performance report's ranking, raw CSV, and settings capture (scripts/model_report.py)."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from app.config import ROOT
from app.runs.metrics import SeatAttempt, append_attempt, write_metrics
from tests.unit.sweep.test_expectations import started, terminated


def load_report() -> Any:
    spec = importlib.util.spec_from_file_location("model_report", ROOT / "scripts" / "model_report.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def group(
    module: Any, model: str, runs: int, stopped: int, met: int, total: int, first: int, replies: int, ms: int
) -> Any:
    return module.Group(
        agent_id="writer",
        role="Writer",
        model=model,
        provider="ollama",
        settings="temperature 0.1",
        runs=runs,
        calls=runs,
        wall_ms=ms * runs,
        replies=replies,
        accepted_first_time=first,
        invalid_twice=stopped,
        checks_met=met,
        checks_total=total,
    )


def test_best_local_ranks_stopped_runs_before_accuracy_and_needs_five_runs() -> None:
    module = load_report()
    steady = group(module, "steady, local", 6, 0, 3, 6, 3, 6, 40000)  # never stops a run, half right, slow
    sharp = group(module, "sharp, local", 6, 1, 6, 6, 6, 6, 5000)  # perfect when it answers, stopped one run
    young = group(module, "young, local", 2, 0, 2, 2, 2, 2, 1000)  # too few runs to qualify
    lines = module.best_local_table([sharp, steady, young])
    row = next(line for line in lines if line.startswith("| writer |"))
    assert row.startswith(
        "| writer | steady, local, temperature 0.1 | 6 | 0 | 3/6 (50%) | 50% | 40.0 | sharp, local (6 runs) |"
    )
    only_young = module.best_local_table([young])
    assert "none with 5 runs yet; leading so far young, local (2 runs)" in only_young[2]


def test_reasons_table_lists_every_pair_including_none() -> None:
    module = load_report()
    quiet = group(module, "quiet, local", 3, 0, 3, 3, 3, 3, 1000)
    noisy = group(module, "noisy, local", 3, 0, 3, 3, 1, 3, 1000)
    noisy.reasons = {"json_shape": 2}
    lines = module.reason_table([quiet, noisy])
    assert "| writer | quiet, local | 0 | none |" in lines
    assert "| writer | noisy, local | 2 | json_shape 2 |" in lines


def test_settings_from_the_attempt_log_reach_the_metrics_and_the_csv(tmp_path: Path) -> None:
    module = load_report()
    folder = tmp_path / "runs" / "r1"
    folder.mkdir(parents=True)
    events = [started("clean-run"), terminated(2, "reviewer_pass")]
    (folder / "events.jsonl").write_text("".join(e.to_line() + "\n" for e in events), encoding="utf-8")
    settings = {"temperature": 0.1, "num_ctx": 65536, "think": False, "max_tokens": "model default"}
    append_attempt(
        folder, SeatAttempt("pb-r1-01", "writer", "qwen3.5 9b, local", "ollama", 1, True, "", settings)
    )
    data = json.loads(write_metrics(folder, events).read_text(encoding="utf-8"))
    writer = next(seat for seat in data["seats"] if seat["agent_id"] == "writer")
    assert writer["settings"] == settings and data["started_at"] == "2026-09-17T12:00:00.000Z"
    (folder / "sweep.json").write_text(
        json.dumps(
            {
                "label": "stage-1",
                "config_key": "writer=qwen3-5-9b",
                "varied_seat": "writer",
                "repeat": 0,
                "worker": "laptop",
            }
        ),
        encoding="utf-8",
    )

    groups, runs = module.collect(tmp_path / "runs")
    assert [g.settings for g in groups] == [
        "temperature 0.1, num_ctx 65536, think off, max_tokens model default"
    ]
    path = module.write_csv(module.raw_rows(runs), tmp_path / "rows.csv")
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0]) == [name for name, _ in module.CSV_COLUMNS]
    assert (
        rows[0]["sweep_config"] == "writer=qwen3-5-9b"
        and rows[0]["temperature"] == "0.1"
        and rows[0]["think"] == "False"
    )
    assert set(name for name, _ in module.TABLE_COLUMNS) >= {
        "Stopped runs",
        "Accuracy",
        "First time",
        "Corrections",
    }
