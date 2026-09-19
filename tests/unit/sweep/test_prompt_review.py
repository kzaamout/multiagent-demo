"""The reviewer suggests what to teach next, and never suggests what has already been taught."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from app.config import ROOT
from app.runs.metrics import SeatAttempt, append_attempt, write_metrics
from tests.unit.sweep.test_expectations import ev, started, terminated


def load_review() -> Any:
    spec = importlib.util.spec_from_file_location("prompt_review", ROOT / "scripts" / "prompt_review.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_run(
    folder: Path,
    dataset: str,
    exit_value: str,
    extra: list[Any] | None = None,
    seat: str = "estimator",
    version: str = "cur12345",
    refusals: int = 0,
    error: str = "no JSON object found in the reply",
) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    events = [started(dataset), *(extra or []), terminated(9, exit_value)]
    (folder / "events.jsonl").write_text("".join(e.to_line() + chr(10) for e in events), encoding="utf-8")
    for number in range(1, refusals + 1):
        append_attempt(
            folder,
            SeatAttempt("pb-01", seat, "qwen3.5 9b, local", "ollama", number, False, error, {}, version),
        )
    if not refusals:  # a seat that ran cleanly still records the version it ran on
        append_attempt(
            folder, SeatAttempt("pb-01", seat, "qwen3.5 9b, local", "ollama", 1, True, "", {}, version)
        )
    write_metrics(folder, events)


def test_a_refusal_on_wording_since_rewritten_is_not_suggested_again(tmp_path: Path) -> None:
    module = load_review()
    make_run(tmp_path / "old", "clean-run", "stopped", version="old00000", refusals=4)
    make_run(tmp_path / "new", "clean-run", "stopped", version="cur12345", refusals=3)
    findings = module.counted(tmp_path, current={"estimator": "cur12345"})
    assert [(f.seat, f.kind, f.count) for f in findings] == [("estimator", "no_json", 3)]
    assert "no JSON object" in findings[0].examples[0][1]


def test_a_category_under_the_threshold_is_not_worth_a_suggestion(tmp_path: Path) -> None:
    module = load_review()
    make_run(tmp_path / "a", "clean-run", "stopped", version="cur12345", refusals=2)
    assert module.counted(tmp_path, current={"estimator": "cur12345"}) == []


def blocker(seq: int) -> Any:
    return ev(
        seq,
        "blocker.raised",
        {
            "blocker_id": "b1",
            "task_id": "t1",
            "agent_id": "estimator",
            "description": "Panel schedule E-002 is missing from the drawing set.",
            "needs_human": True,
            "route_back_to": None,
        },
    )


def test_a_blocker_counts_as_invented_only_where_the_dataset_plants_none(tmp_path: Path) -> None:
    module = load_review()
    make_run(tmp_path / "clean", "clean-run", "blocker_escalated", [blocker(2)])
    make_run(tmp_path / "planted", "missing-sheet", "blocker_escalated", [blocker(2)])
    findings = module.detected(tmp_path, current={"estimator": "cur12345"})
    invented = [f for f in findings if f.kind == "invented_blocker"]
    assert len(invented) == 1 and invented[0].count == 1, "only the Clean run blocker is invented"
    assert "E-002" in invented[0].examples[0][0]


def test_a_seat_taught_since_the_failure_is_not_asked_to_learn_it_again(tmp_path: Path) -> None:
    module = load_review()
    make_run(tmp_path / "before", "clean-run", "blocker_escalated", [blocker(2)], version="old00000")
    assert module.detected(tmp_path, current={"estimator": "cur12345"}) == []


def test_a_route_difference_is_an_observation_about_the_golden_log_not_a_lesson(tmp_path: Path) -> None:
    module = load_review()
    folder = tmp_path / "drift"
    make_run(folder, "clean-run", "reviewer_pass")
    data = json.loads((folder / "metrics.json").read_text(encoding="utf-8"))
    data["golden_match"], data["golden_note"] = False, "clean-run: transition 3 differs"
    (folder / "metrics.json").write_text(json.dumps(data), encoding="utf-8")
    findings = module.detected(tmp_path, current={"estimator": "cur12345"})
    drift = next(f for f in findings if f.kind == "route_drift")
    assert module.draft(drift, 1) == [
        "No example drafted: read the golden log first. A run that passes first time legitimately misses a "
        "golden that records a rework, and re-recording the golden is the fix. Only chase the seat when the "
        "detour is real, such as a route back to Intake nothing asked for."
    ]
    text = module.render([], findings)
    assert "TO FILL" not in text, "nothing invites a lesson here"


def test_the_review_says_so_plainly_when_there_is_nothing_to_teach(tmp_path: Path) -> None:
    module = load_review()
    text = module.render([], [])
    assert "Nothing to suggest" in text and "TO FILL" not in text
