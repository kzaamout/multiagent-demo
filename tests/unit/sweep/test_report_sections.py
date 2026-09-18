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
        stopped_run=stopped,
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
        "| writer | steady, local, temperature 0.1 | 6 | 0 (0%) | 3/6 (50%) | 50% | 40.0 | "
        "sharp, local (6 runs) |"
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


def test_a_seat_that_recovers_on_a_later_attempt_did_not_stop_the_run(tmp_path: Path) -> None:
    """Three attempts made a second refusal survivable, so only an exhausted seat stops a run."""
    from app.runs.metrics import run_metrics

    def metrics(exit_value: str, attempts: list[tuple[int, bool]]) -> dict[str, Any]:
        folder = tmp_path / exit_value
        folder.mkdir(parents=True, exist_ok=True)
        events = [started("clean-run"), terminated(2, exit_value)]
        (folder / "events.jsonl").write_text("".join(e.to_line() + "\n" for e in events), encoding="utf-8")
        for number, accepted in attempts:
            append_attempt(
                folder,
                SeatAttempt(
                    "pb-01",
                    "writer",
                    "qwen3.5 9b, local",
                    "ollama",
                    number,
                    accepted,
                    "" if accepted else "bad",
                ),
            )
        data = run_metrics(events, folder)
        return next(s for s in data["seats"] if s["agent_id"] == "writer")

    recovered = metrics("reviewer_pass", [(1, False), (2, False), (3, True)])
    assert recovered["stopped_run"] == 0, "it was refused twice, then accepted, so it stopped nothing"
    assert recovered["corrections"] == 1 and recovered["replies"] == 1

    exhausted = metrics("stopped", [(1, False), (2, False), (3, False)])
    assert exhausted["stopped_run"] == 1 and exhausted["replies"] == 1


def test_a_taught_seat_starts_a_new_row_so_runs_before_and_after_do_not_blend(tmp_path: Path) -> None:
    """The prompt version is recorded per run, so teaching a seat splits its rows (owner request)."""
    module = load_report()
    runs = tmp_path / "runs"
    for index, (version, accepted) in enumerate((("old1234", True), ("new5678", True))):
        folder = runs / f"r{index}"
        folder.mkdir(parents=True)
        events = [started("clean-run"), terminated(2, "reviewer_pass")]
        (folder / "events.jsonl").write_text("".join(e.to_line() + chr(10) for e in events), encoding="utf-8")
        append_attempt(
            folder,
            SeatAttempt(
                "pb-01",
                "writer",
                "qwen3.5 9b, local",
                "ollama",
                1,
                accepted,
                "" if accepted else "bad",
                {"temperature": 0.1},
                version,
            ),
        )
    groups, _ = module.collect(runs)
    assert sorted(g.instructions for g in groups) == ["new5678", "old1234"], (
        "the same model on two prompt versions is two rows"
    )
    merged = module.merge_by_model(groups)
    assert len(merged) == 1, "the ranking still judges the model as one"


def test_stopped_runs_rank_as_a_share_so_a_model_is_not_rewarded_for_fewer_runs() -> None:
    """A real case: 1 stop in 6 runs beat 2 stops in 42, though the second is four times steadier."""
    module = load_report()
    tried_twice = group(module, "tried, local", 6, 1, 6, 6, 6, 6, 12000)
    tried_often = group(module, "often, local", 42, 2, 42, 42, 42, 42, 17000)
    lines = module.best_local_table([tried_twice, tried_often])
    row = next(line for line in lines if line.startswith("| writer |"))
    assert "often, local" in row.split("|")[2], "the steadier model wins on the share"
    assert "| 2 (5%) |" in row, "the count is shown with the share it ranked on"
