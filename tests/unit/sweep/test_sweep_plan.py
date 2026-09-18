"""The sweep plan expands to eligible jobs in an order that keeps one local model loaded (scripts/sweep.py)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from app.config import ROOT
from app.live.providers import ModelConfig


def load_sweep() -> Any:
    spec = importlib.util.spec_from_file_location("sweep", ROOT / "scripts" / "sweep.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PLAN = {
    "label": "t",
    "datasets": ["clean-run"],
    "repeats": 2,
    "baseline": {
        "orchestrator": "qwen3-5-9b",
        "intake": "qwen3-5-9b",
        "estimator": "qwen3-5-9b",
        "pricing": "qwen3-5-9b",
        "writer": "qwen3-5-9b",
        "reviewer": "gemma4-12b",
    },
    "vary": {"models": ["qwen3-5-9b", "llama3-1-8b"], "seats": ["estimator", "pricing", "reviewer"]},
    "whole": ["qwen3-5-9b"],
}


def test_text_only_models_are_skipped_on_vision_seats_and_the_baseline_model_varies_the_rest() -> None:
    sweep = load_sweep()
    jobs, skipped = sweep.expand(PLAN, ModelConfig.load())
    keys = [job.config_key for job in jobs if job.repeat == 0]
    assert keys == ["baseline", "reviewer=qwen3-5-9b", "all=qwen3-5-9b", "pricing=llama3-1-8b"]
    assert skipped == [
        "estimator=llama3-1-8b: llama3.1 8b, local cannot read images, which the estimator needs",
        "reviewer=llama3-1-8b: llama3.1 8b, local cannot read images, which the reviewer needs",
    ]
    assert len(jobs) == 8 and jobs[0].key == "t/baseline/clean-run/0"
    whole = next(job for job in jobs if job.config_key == "all=qwen3-5-9b")
    assert set(whole.seats.values()) == {"qwen3-5-9b"} and whole.varied_seat == "all"


def test_a_job_is_claimed_once_and_its_result_is_appended(tmp_path: Path) -> None:
    sweep = load_sweep()
    jobs, _ = sweep.expand(PLAN, ModelConfig.load())
    claims = sweep.Claims(tmp_path / "runs", "t")
    assert claims.claim(jobs[0], "laptop") is True
    assert claims.claim(jobs[0], "other") is False
    claims.finish(jobs[0], "laptop", {"status": "done", "run_id": "r1", "exit": "reviewer_pass"})
    lines = claims.lines()
    assert [line["status"] for line in lines] == ["claimed", "done"]
    assert lines[1]["job"] == "t/baseline/clean-run/0" and lines[1]["run_id"] == "r1"
    assert not (tmp_path / "runs" / "_sweep" / "t.lock").exists()


def test_a_repeat_stage_runs_only_the_named_pairs_without_a_baseline_job() -> None:
    """Stage 2 repeats what stage 1 found worth measuring, so it names pairs instead of a cross product."""
    sweep = load_sweep()
    plan = {
        "label": "s2",
        "datasets": ["clean-run"],
        "repeats": 3,
        "baseline_job": False,
        "baseline": PLAN["baseline"],
        "pairs": [
            {"seat": "pricing", "model": "llama3-1-8b"},
            {"seat": "reviewer", "model": "llama3-1-8b"},
        ],
    }
    jobs, skipped = sweep.expand(plan, ModelConfig.load())
    assert [j.config_key for j in jobs] == ["pricing=llama3-1-8b"] * 3
    assert skipped == [
        "reviewer=llama3-1-8b: llama3.1 8b, local cannot read images, which the reviewer needs"
    ]
    assert [j.repeat for j in jobs] == [0, 1, 2]
    assert jobs[0].seats["pricing"] == "llama3-1-8b" and jobs[0].seats["writer"] == "qwen3-5-9b"


def test_the_blocker_policy_follows_the_dataset_not_the_whole_sweep() -> None:
    """Missing sheet is built to escalate; on a dataset that plants nothing a blocker is invented."""
    sweep = load_sweep()
    plan = {"blocker": "answer", "blocker_by_dataset": {"missing-sheet": "escalate"}}
    assert sweep.blocker_policy(plan, "missing-sheet") == "escalate"
    assert sweep.blocker_policy(plan, "clean-run") == "answer"
    assert sweep.blocker_policy({}, "clean-run") == "escalate", "the old default is unchanged"
