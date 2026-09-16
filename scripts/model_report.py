"""Model performance per seat, aggregated across every recorded run.

    uv run python scripts/model_report.py              # print the tables
    uv run python scripts/model_report.py --write      # also refresh docs/model-performance.md

Each run writes runs/<id>/metrics.json as it ends (app/runs/metrics.py). This reads them all, groups by
seat and model, and reports the numbers a model choice turns on: what a seat costs per run, how long its
calls take, how much of its context it uses, and how often its reply is accepted first time. Runs whose
metrics predate the attempt log are recomputed from their event log and rejected replies.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.config import ROOT
from app.live.providers import MODELS_PATH
from app.runs.metrics import METRICS_FILE, run_metrics
from app.runs.recorder import read_events

RUNS = ROOT / "runs"
REPORT = ROOT / "docs" / "model-performance.md"


@dataclass
class Group:
    """One seat on one model, across runs."""

    agent_id: str
    role: str
    model: str
    runs: int = 0
    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    wall_ms: int = 0
    est_cost: float = 0.0
    tool_calls: int = 0
    replies: int = 0
    accepted_first_time: int = 0
    corrections: int = 0
    invalid_twice: int = 0
    reasons: dict[str, int] = field(default_factory=dict)

    @property
    def first_time_rate(self) -> float:
        return self.accepted_first_time / self.replies if self.replies else 0.0

    @property
    def seconds_per_call(self) -> float:
        return self.wall_ms / self.calls / 1000 if self.calls else 0.0

    @property
    def cost_per_run(self) -> float:
        return self.est_cost / self.runs if self.runs else 0.0

    @property
    def tokens_in_per_call(self) -> int:
        return round(self.tokens_in / self.calls) if self.calls else 0

    @property
    def tokens_out_per_call(self) -> int:
        return round(self.tokens_out / self.calls) if self.calls else 0


def metrics_of(folder: Path) -> dict[str, Any] | None:
    events_path = folder / "events.jsonl"
    if not events_path.exists():
        return None
    path = folder / METRICS_FILE
    if path.exists():
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        if data.get("seats"):
            return data
    try:
        return run_metrics(read_events(events_path), folder)
    except (OSError, ValueError):
        return None


def collect(runs_dir: Path = RUNS) -> tuple[list[Group], list[dict[str, Any]]]:
    groups: dict[tuple[str, str], Group] = {}
    runs: list[dict[str, Any]] = []
    for folder in sorted(p for p in runs_dir.glob("*") if p.is_dir()):
        data = metrics_of(folder)
        if data is None:
            continue
        runs.append(data)
        for seat in data["seats"]:
            if not seat["calls"] and not seat["replies"]:
                continue  # a seat that never ran in this run
            key = (seat["agent_id"], seat["model"] or "unknown")
            group = groups.setdefault(key, Group(agent_id=seat["agent_id"], role=seat["role"], model=key[1]))
            group.runs += 1
            for name in ("calls", "tokens_in", "tokens_out", "wall_ms", "tool_calls"):
                setattr(group, name, getattr(group, name) + seat[name])
            group.est_cost += seat["est_cost"]
            group.replies += seat["replies"]
            group.accepted_first_time += seat["accepted_first_time"]
            group.corrections += seat["corrections"]
            group.invalid_twice += seat["invalid_twice"]
            group.role = group.role or seat["role"]
            for reason, count in seat["reasons"].items():
                group.reasons[reason] = group.reasons.get(reason, 0) + count
    order = ["orchestrator", "intake", "estimator", "pricing", "writer", "reviewer"]
    return sorted(
        groups.values(),
        key=lambda g: (order.index(g.agent_id) if g.agent_id in order else 99, g.model),
    ), runs


def seat_settings() -> dict[str, str]:
    """What each seat is configured with, so a first time rate can be read against it."""
    data = yaml.safe_load(MODELS_PATH.read_text(encoding="utf-8"))
    models = data.get("models", {})
    settings: dict[str, str] = {}
    for seat, seat_config in (data.get("seats") or {}).items():
        model = models.get(seat_config.get("model"), {})
        parts = [str(model.get("label", ""))]
        if "temperature" in seat_config:
            parts.append(f"temperature {seat_config['temperature']}")
        elif model.get("temperature") is False:
            parts.append("temperature fixed by the provider")
        else:
            parts.append("model default temperature")
        context = (model.get("options") or {}).get("num_ctx")
        if context:
            parts.append(f"num_ctx {context}")
        if model.get("max_tokens"):
            parts.append(f"max_tokens {model['max_tokens']}")
        settings[seat] = ", ".join(part for part in parts if part)
    return settings


def settings_for(seat: str, model: str, settings: dict[str, str]) -> str:
    """The seat's settings, but only beside the model it runs on today."""
    current = settings.get(seat, "")
    if not current.startswith(model):
        return "not the current model"
    return current.removeprefix(model).lstrip(", ")


def table(groups: list[Group]) -> list[str]:
    settings = seat_settings()
    head = (
        "| Seat | Model | Settings today | Runs | Calls | First time | Corrections | Stopped runs | "
        "Tokens in per call | Tokens out per call | Seconds per call | Cost per run |"
    )
    lines = [head, "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for g in groups:
        first = f"{g.first_time_rate * 100:.0f}%" if g.replies else "n/a"
        lines.append(
            f"| {g.agent_id} | {g.model} | {settings_for(g.agent_id, g.model, settings)} | {g.runs} | {g.calls} | "
            f"{first} | {g.corrections} | {g.invalid_twice} | {g.tokens_in_per_call} | "
            f"{g.tokens_out_per_call} | {g.seconds_per_call:.1f} | ${g.cost_per_run:.2f} |"
        )
    return lines


def reason_table(groups: list[Group]) -> list[str]:
    lines = ["| Seat | Model | Rejections | Reasons |", "|---|---|---|---|"]
    for g in groups:
        total = sum(g.reasons.values())
        if not total:
            continue
        reasons = ", ".join(f"{name} {count}" for name, count in sorted(g.reasons.items()))
        lines.append(f"| {g.agent_id} | {g.model} | {total} | {reasons} |")
    if len(lines) == 2:
        lines.append("| none | | 0 | |")
    return lines


def report(groups: list[Group], runs: list[dict[str, Any]]) -> str:
    live = [r for r in runs if any(s["calls"] for s in r["seats"])]
    spend = sum(s["est_cost"] for r in runs for s in r["seats"])
    body = [
        "# Model performance by seat",
        "",
        "Generated by `uv run python scripts/model_report.py --write` from every run under `runs/`.",
        "Each run writes its own `metrics.json` as it ends, so this table grows with every run.",
        "",
        f"Runs recorded: {len(runs)}, of which {len(live)} called a model. "
        f"Estimated spend across all of them: ${spend:.2f}.",
        "",
        "First time is the share of accepted replies that needed no correction. Corrections are replies "
        "accepted on the second attempt. Stopped runs counts the times a seat failed twice and ended the run. "
        "Settings are the seat's current configuration in `config/models.yaml`, not necessarily what every "
        "past run used.",
        "",
        *table(groups),
        "",
        "## Why replies were sent back",
        "",
        *reason_table(groups),
        "",
    ]
    return "\n".join(body)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="refresh docs/model-performance.md")
    args = parser.parse_args()
    groups, runs = collect()
    text = report(groups, runs)
    print(text)
    if args.write:
        REPORT.write_text(text, encoding="utf-8", newline="\n")
        print(f"written: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
