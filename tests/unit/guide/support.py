"""Synthetic run folders for the seat model guide tests (spec 014).

A folder holds an event log and a current-format `metrics.json`, which `metrics_of` takes as it is, so no
event needs to be real. `seed` spreads a record over several folders the way many runs would add up.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def seat_row(
    agent_id: str,
    model: str,
    replies: int,
    first_time: int,
    *,
    provider: str = "ollama",
    calls: int | None = None,
    stopped_run: int = 0,
) -> dict[str, Any]:
    """One seat row as `app/runs/metrics.py` writes it."""
    return {
        "agent_id": agent_id,
        "role": agent_id.title(),
        "model": model,
        "provider": provider,
        "calls": replies if calls is None else calls,
        "tokens_in": 0,
        "tokens_out": 0,
        "wall_ms": 0,
        "est_cost": 0.0,
        "tool_calls": 0,
        "replies": replies,
        "accepted_first_time": first_time,
        "corrections": max(replies - first_time - stopped_run, 0),
        "stopped_run": stopped_run,
        "reasons": {},
        "settings": {},
        "instructions": "",
        "checks": {},
    }


def write_run(runs_dir: Path, run_id: str, seats: list[dict[str, Any]], *, finished: bool = True) -> Path:
    """A run folder. Unfinished, it has an event log and no `metrics.json`, as a run cut off has."""
    folder = runs_dir / run_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "events.jsonl").write_text("{}\n", encoding="utf-8")
    if finished:
        metrics: dict[str, Any] = {
            "run_id": run_id,
            "started_at": "2026-09-21T00:00:00Z",
            "dataset_id": "clean-run",
            "exit": "reviewer_pass",
            "golden_match": None,
            "golden_note": "",
            "price_check": {},
            "events": 1,
            "seats": seats,
        }
        (folder / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    return folder


def seed(
    runs_dir: Path,
    agent_id: str,
    model: str,
    runs: int,
    replies: int,
    first_time: int,
    *,
    provider: str = "ollama",
    prefix: str | None = None,
) -> list[Path]:
    """`runs` folders whose rows for this seat and model add up to `first_time` of `replies`."""
    folders = []
    name = prefix or f"{agent_id}-{model}".replace(" ", "_").replace(",", "")
    for i in range(runs):
        r = replies // runs + (1 if i < replies % runs else 0)
        f = first_time // runs + (1 if i < first_time % runs else 0)
        row = seat_row(agent_id, model, r, f, provider=provider, calls=max(r, 1))
        folders.append(write_run(runs_dir, f"{name}-{i:03d}", [row]))
    return folders
