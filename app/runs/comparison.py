"""The Team versus Single-model comparison, read from recordings only (S5, research D6).

The newest terminated recording of each mode for a dataset, with the figures the Compare strip and the
comparison line show. Nothing here touches a live run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.runs.recorder import read_events, read_meta
from app.runs.working_time import working_ms
from app.schema.events import Event


def _figures(folder: Path, meta: dict[str, Any]) -> dict[str, Any] | None:
    path = folder / "events.jsonl"
    if not path.exists():
        return None
    try:
        events: list[Event] = read_events(path)
    except ValueError:
        return None
    if not events or events[-1].type != "run.terminated":
        return None
    summary = events[-1].payload.get("summary") or {}
    started = events[0].payload if events[0].type == "run.started" else {}
    roster = started.get("roster") or []
    single = next((a for a in roster if a.get("agent_id") == "single"), None)
    output = next(
        (e for e in reversed(events) if e.type == "task.completed" and e.payload.get("agent_id") == "single"),
        None,
    )
    result = (output.payload.get("result") or {}) if output is not None else {}
    return {
        "run_id": str(meta.get("run_id") or folder.name),
        "started_at": str(meta.get("started_at", "")),
        "exit": str(events[-1].payload.get("exit", "")),
        "est_cost": float(summary.get("est_cost", 0.0)),
        "elapsed_ms": int(summary.get("elapsed_ms", 0)),
        # Compute time: the working time without human waits, as the clock shows (spec 012 decision 13).
        "working_ms": working_ms(events),
        "model_label": str((single or {}).get("model", {}).get("label", "")) if single else "",
        "output_path": result.get("output_path"),
        "summary": str(result.get("summary") or result.get("headline") or ""),
        "total": result.get("total"),
    }


COMPLETED_EXITS = ("reviewer_pass", "retry_exhausted", "single_complete")


def rank(meta: dict[str, Any]) -> tuple[int, str]:
    """A run that finished its job outranks one that stopped early (not ready, a blocker, Stop, the ceiling);
    within each group the newest wins. A comparison of a stopped Team run with a finished Single-model run
    would say nothing about the team."""
    return (1 if str(meta.get("exit", "")) in COMPLETED_EXITS else 0, str(meta.get("started_at", "")))


def comparison(runs_dir: Path, dataset_id: str) -> dict[str, Any]:
    """The recording per mode that best represents the dataset: newest completed, else newest terminated."""
    best: dict[str, tuple[tuple[int, str], Path, dict[str, Any]]] = {}
    if runs_dir.exists():
        for folder in runs_dir.iterdir():
            if not folder.is_dir():
                continue
            meta = read_meta(folder)
            if not meta or meta.get("dataset_id") != dataset_id or not meta.get("exit"):
                continue
            mode = str(meta.get("mode") or "team")
            key = rank(meta)
            if mode not in best or key > best[mode][0]:
                best[mode] = (key, folder, meta)
    return {
        "dataset_id": dataset_id,
        "team": _figures(best["team"][1], best["team"][2]) if "team" in best else None,
        "single": _figures(best["single"][1], best["single"][2]) if "single" in best else None,
    }
