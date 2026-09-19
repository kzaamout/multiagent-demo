"""Model performance per seat, aggregated across every recorded run.

    uv run python scripts/model_report.py              # print the report
    uv run python scripts/model_report.py --write      # also refresh docs/model-performance.md,
                                                       # docs/model-performance-runs.csv and
                                                       # docs/model-performance-columns.md

Each run writes runs/<id>/metrics.json as it ends (app/runs/metrics.py). This reads them all, groups by
seat, model and the settings the seat ran with, and reports the numbers a model choice turns on: how often
a seat stopped a run, how much of what its dataset expected it did, how often its reply was accepted first
time, and what it cost and took. Runs whose metrics predate the attempt log or the correctness checks are
recomputed from their event log. The raw rows behind the tables go to the CSV, one per run and seat.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from app.config import ROOT, load_settings
from app.live.providers import ModelConfig, check_availability
from app.runs.metrics import METRICS_FILE, run_metrics
from app.runs.recorder import read_events
from app.seats.definitions import DRAWING_PAGES, PAGE_TEXT, SEAT_DEFINITIONS

RUNS = load_settings().runs_dir  # RUNS_DIR may point at another checkout (worktrees, rule 15)
REPORT = ROOT / "docs" / "model-performance.md"
RAW_CSV = ROOT / "docs" / "model-performance-runs.csv"
COLUMNS_DOC = ROOT / "docs" / "model-performance-columns.md"
SEAT_ORDER = ["orchestrator", "intake", "estimator", "pricing", "writer", "reviewer", "single"]
MIN_RUNS_FOR_BEST = 5

TABLE_COLUMNS: list[tuple[str, str]] = [
    ("Seat", "the seat the row is about; one seat per row, so a model that held two seats appears twice"),
    ("Model", "the model label the seat ran on, as the run's events record it"),
    (
        "Settings",
        "the hyperparameters the seat ran with, recorded per run: temperature, num_ctx, think, max_tokens; "
        "'not recorded' for runs before capture",
    ),
    (
        "Prompt",
        "the version of the seat's instructions the run used, so runs before and after a seat was taught "
        "something do not blend; 'not recorded' for runs before capture",
    ),
    ("Runs", "runs in which the seat made at least one call or reply on this model with these settings"),
    ("Calls", "model calls the seat made across those runs, from meter.update events"),
    (
        "Stopped runs",
        "times the seat ran out of attempts and the run ended because of it; the ranking uses this as a "
        "share of the model's runs, so a model is not favoured for having been tried less",
    ),
    (
        "Accuracy",
        "checks met over checks defined: the dataset's own expectations of the seat, or the golden match "
        "where the dataset defines none for it (app/runs/expectations.py)",
    ),
    ("First time", "share of accepted replies that needed no correction"),
    ("Corrections", "replies accepted on the second attempt, after one refusal"),
    ("Tokens in per call", "average prompt tokens per call"),
    ("Tokens out per call", "average completion tokens per call"),
    ("Seconds per call", "average wall time per call, measured around the call"),
    ("Cost per run", "estimated spend per run from the registry's prices; zero for local models"),
]

LOCAL_TABLE_NOTES: list[tuple[str, str]] = [
    ("Seats", "how many different seats this model held across the runs counted"),
    ("Tested models", "how many different models have held this seat"),
    (
        "Prompt versions",
        "how many versions of this seat's instructions are recorded, which is how often the wording had to "
        "change to get the seat working",
    ),
    (
        "Runs",
        "recordings the model appears in at all, counted once however many seats it filled in that run",
    ),
    (
        "Stopped runs",
        "runs this model ended by running out of attempts in any seat, with the share of its runs",
    ),
    ("Tokens in/out per call", "average prompt and completion tokens per call, across its seats"),
]

CSV_COLUMNS: list[tuple[str, str]] = [
    ("run_id", "the run folder under runs/"),
    ("started_at", "when the run started, from run.started"),
    ("dataset_id", "the scenario dataset the run used"),
    (
        "exit",
        "how the run ended: reviewer_pass, retry_exhausted, blocker_escalated, not_ready, cost_ceiling, "
        "stopped, single_complete, dry_intake",
    ),
    (
        "golden_match",
        "true when the run's stage sequence and exit match the dataset's golden log, false when not, "
        "empty when the dataset has no golden",
    ),
    (
        "sweep_label",
        "the sweep plan the run belongs to, from runs/<id>/sweep.json; empty for a hand-started run",
    ),
    ("sweep_config", "the sweep configuration: baseline, seat=model, or all=model"),
    ("sweep_varied_seat", "the seat the configuration changed from the baseline, or all"),
    ("sweep_repeat", "which repeat of the configuration on the dataset, from 0"),
    ("sweep_worker", "the machine that ran the job"),
    ("instructions", "the version of the seat's instructions the run used (app/seats/definitions.py)"),
    ("seat", "the seat the row is about"),
    ("role", "the seat's display role"),
    ("model", "the model label the seat ran on"),
    ("provider", "bedrock, google, xai or ollama"),
    ("temperature", "the sampling temperature, or 'fixed by the provider' or 'model default'"),
    ("num_ctx", "the context window requested from Ollama, or 'model default'"),
    ("think", "whether the model's thinking mode was on, or 'model default'"),
    ("max_tokens", "the output limit requested, or 'model default'"),
    ("calls", "model calls the seat made in the run"),
    ("tokens_in", "prompt tokens across the seat's calls"),
    ("tokens_out", "completion tokens across the seat's calls"),
    ("wall_ms", "wall time across the seat's calls, milliseconds"),
    ("est_cost", "estimated spend for the seat in the run, USD"),
    ("tool_calls", "tools the seat called"),
    ("replies", "structured replies the seat produced"),
    ("accepted_first_time", "replies accepted without a correction"),
    ("corrections", "replies accepted on the second attempt"),
    ("stopped_run", "1 when this seat ran out of attempts and the run ended because of it, else 0"),
    ("reasons", "refusal reasons by category, as name=count separated by semicolons"),
    ("checks_met", "correctness checks the seat met in the run"),
    ("checks_total", "correctness checks defined for the seat on the dataset"),
    ("checks", "each check as name=1 or name=0 separated by semicolons"),
]


@dataclass
class Group:
    """One seat on one model with one set of settings, across runs."""

    agent_id: str
    role: str
    model: str
    provider: str = ""
    settings: str = "not recorded"
    instructions: str = "not recorded"
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
    stopped_run: int = 0
    checks_met: int = 0
    checks_total: int = 0
    takeoff_right: int = 0
    takeoff_lines: int = 0
    reasons: dict[str, int] = field(default_factory=dict)

    @property
    def first_time_rate(self) -> float:
        return self.accepted_first_time / self.replies if self.replies else 0.0

    @property
    def accuracy(self) -> float | None:
        return self.checks_met / self.checks_total if self.checks_total else None

    @property
    def takeoff_accuracy(self) -> float | None:
        """The share of scheduled materials whose quantity matches the dataset's reference.

        Only the Estimator has this, and only on scenarios that state their own quantities. It is kept out
        of `accuracy`, which stays a measure of behaviour (owner decision 1b, 2026-09-19).
        """
        return self.takeoff_right / self.takeoff_lines if self.takeoff_lines else None

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


def settings_text(settings: dict[str, Any]) -> str:
    if not settings:
        return "not recorded"
    parts = []
    for name in ("temperature", "num_ctx", "think", "max_tokens"):
        if name in settings:
            value = settings[name]
            if isinstance(value, bool):
                value = "on" if value else "off"
            parts.append(f"{name} {value}")
    return ", ".join(parts) or "not recorded"


def metrics_of(folder: Path) -> dict[str, Any] | None:
    events_path = folder / "events.jsonl"
    if not events_path.exists():
        return None
    path = folder / METRICS_FILE
    if path.exists():
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        seats = data.get("seats") or []
        if seats and "golden_match" in data and all("stopped_run" in row for row in seats):
            return data
    try:
        return run_metrics(read_events(events_path), folder)
    except (OSError, ValueError):
        return None


def sweep_of(folder: Path) -> dict[str, Any]:
    path = folder / "sweep.json"
    if not path.exists():
        return {}
    try:
        return dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {}


def started_at(folder: Path, data: dict[str, Any]) -> str:
    manifest = folder / "run.json"
    if manifest.exists():
        try:
            return str(json.loads(manifest.read_text(encoding="utf-8")).get("started_at", ""))
        except (OSError, ValueError):
            pass
    return str(data.get("started_at", ""))


def collect(runs_dir: Path = RUNS) -> tuple[list[Group], list[dict[str, Any]]]:
    groups: dict[tuple[str, str, str, str], Group] = {}
    runs: list[dict[str, Any]] = []
    for folder in sorted(p for p in runs_dir.glob("*") if p.is_dir() and not p.name.startswith("_")):
        data = metrics_of(folder)
        if data is None:
            continue
        data["sweep"] = sweep_of(folder)
        data["started_at"] = started_at(folder, data)
        runs.append(data)
        for seat in data["seats"]:
            if not seat["calls"] and not seat["replies"]:
                continue  # a seat that never ran in this run
            settings = settings_text(seat.get("settings") or {})
            prompt = seat.get("instructions") or "not recorded"
            key = (seat["agent_id"], seat["model"] or "unknown", settings, prompt)
            group = groups.setdefault(
                key,
                Group(
                    agent_id=seat["agent_id"],
                    role=seat["role"],
                    model=key[1],
                    provider=seat.get("provider", ""),
                    settings=settings,
                    instructions=prompt,
                ),
            )
            group.runs += 1
            for name in ("calls", "tokens_in", "tokens_out", "wall_ms", "tool_calls"):
                setattr(group, name, getattr(group, name) + seat[name])
            group.est_cost += seat["est_cost"]
            group.replies += seat["replies"]
            group.accepted_first_time += seat["accepted_first_time"]
            group.corrections += seat["corrections"]
            group.stopped_run += seat["stopped_run"]
            group.role = group.role or seat["role"]
            group.provider = group.provider or seat.get("provider", "")
            checks = seat.get("checks") or {}
            group.checks_met += sum(1 for met in checks.values() if met)
            group.checks_total += len(checks)
            # The takeoff belongs to the Estimator's model, and the run's price check measured it.
            price = data.get("price_check") or {}
            if seat["agent_id"] == "estimator" and price.get("takeoff_lines"):
                group.takeoff_right += int(price.get("takeoff_lines_right") or 0)
                group.takeoff_lines += int(price["takeoff_lines"])
            for reason, count in seat["reasons"].items():
                group.reasons[reason] = group.reasons.get(reason, 0) + count
    return sorted(
        groups.values(),
        key=lambda g: (
            SEAT_ORDER.index(g.agent_id) if g.agent_id in SEAT_ORDER else 99,
            g.model,
            g.settings,
            g.instructions,
        ),
    ), runs


def _accuracy(g: Group) -> str:
    return f"{g.checks_met}/{g.checks_total} ({g.accuracy * 100:.0f}%)" if g.accuracy is not None else "n/a"


def table(groups: list[Group]) -> list[str]:
    head = "| " + " | ".join(name for name, _ in TABLE_COLUMNS) + " |"
    lines = [head, "|" + "---|" * len(TABLE_COLUMNS)]
    for g in groups:
        first = f"{g.first_time_rate * 100:.0f}%" if g.replies else "n/a"
        lines.append(
            f"| {g.agent_id} | {g.model} | {g.settings} | {g.instructions} | {g.runs} | {g.calls} | "
            f"{g.stopped_run} | "
            f"{_accuracy(g)} | {first} | {g.corrections} | {g.tokens_in_per_call} | "
            f"{g.tokens_out_per_call} | {g.seconds_per_call:.1f} | ${g.cost_per_run:.2f} |"
        )
    return lines


def current_versions() -> dict[str, str]:
    """The instruction version each seat is on now, so the table can say which rejections still apply."""
    try:
        from app.seats.definitions import instructions_version

        return {seat: instructions_version(seat) for seat in SEAT_DEFINITIONS}
    except (OSError, KeyError):  # pragma: no cover - a checkout without the seat files
        return {}


def reason_table(groups: list[Group], current: dict[str, str] | None = None) -> list[str]:
    """Every seat and model pair on the instructions that seat runs on now, including the pairs never sent
    back, so absence is visible. Rejections against wording that has since been rewritten are counted
    separately rather than mixed in: they say what an earlier prompt did, not what to fix today.
    """
    current = current_versions() if current is None else current
    lines = ["| Seat | Model | Rejections | Reasons |", "|---|---|---|---|"]
    merged: dict[tuple[str, str], dict[str, int]] = {}
    superseded: dict[str, int] = {}
    for g in groups:
        version = current.get(g.agent_id)
        if version is not None and g.instructions != version:
            superseded[g.agent_id] = superseded.get(g.agent_id, 0) + sum(g.reasons.values())
            continue
        bucket = merged.setdefault((g.agent_id, g.model), {})
        for name, count in g.reasons.items():
            bucket[name] = bucket.get(name, 0) + count
    for (agent_id, model), reasons in merged.items():
        total = sum(reasons.values())
        text = ", ".join(f"{name} {count}" for name, count in sorted(reasons.items())) if total else "none"
        lines.append(f"| {agent_id} | {model} | {total} | {text} |")
    if not merged:
        lines.append("| none on the current instructions | | 0 | |")
    dropped = sum(superseded.values())
    if dropped:
        seats = ", ".join(f"{seat} {count}" for seat, count in sorted(superseded.items()) if count)
        lines += [
            "",
            f"Not counted above: {dropped} rejections against instructions that have since been rewritten "
            f"({seats}). They are in `docs/model-performance-runs.csv` with the version that produced them.",
        ]
    return lines


def rank_key(g: Group) -> tuple[float, ...]:
    """Owner ranking (2026-09-17): fewest stopped runs, then accuracy, then first-time rate, then speed.

    Stopped runs ranks as a share of the model's runs, not as a count. Counting them made a model look
    better for having been tried less: on the Clean run, 1 stop in 6 runs beat 2 stops in 42, though the
    second is four times steadier and seven times better evidenced. The other three were already shares.

    At the Estimator, how well the takeoff matches the reference ranks second, ahead of behaviour. The
    owner kept the price out of the reported Accuracy column and left the ranking to me (2026-09-19), and
    the Estimator is the one seat where behaviour says almost nothing: its whole check on a Clean run is
    that it raised no blocker, which a model passes while reading half the drawing wrong. Reading the
    drawings is that seat's job, and it is the only seat whose output this measures. Every other seat
    ranks exactly as the owner set it.
    """
    stop_share = g.stopped_run / g.runs if g.runs else 1.0
    behaviour = -(g.accuracy if g.accuracy is not None else 0.0)
    rest = (behaviour, -g.first_time_rate, g.seconds_per_call)
    if g.agent_id == "estimator" and g.takeoff_lines:
        return (stop_share, -(g.takeoff_accuracy or 0.0), *rest)
    return (stop_share, *rest)


def merge_by_model(groups: list[Group]) -> list[Group]:
    """One row per model for the ranking. Splitting by settings is right in the detail table, but it let a
    model compete with itself when some of its runs predate settings capture."""
    merged: dict[str, Group] = {}
    for g in groups:
        into = merged.get(g.model)
        if into is None:
            merged[g.model] = Group(**{k: v for k, v in vars(g).items()})
            continue
        for name in (
            "runs",
            "calls",
            "tokens_in",
            "tokens_out",
            "wall_ms",
            "tool_calls",
            "replies",
            "accepted_first_time",
            "corrections",
            "stopped_run",
            "checks_met",
            "checks_total",
            "takeoff_right",
            "takeoff_lines",
        ):
            setattr(into, name, getattr(into, name) + getattr(g, name))
        into.est_cost += g.est_cost
        if into.settings == "not recorded" and g.settings != "not recorded":
            into.settings = g.settings
        if into.instructions == "not recorded" and g.instructions != "not recorded":
            into.instructions = g.instructions
        for reason, count in g.reasons.items():
            into.reasons[reason] = into.reasons.get(reason, 0) + count
    return list(merged.values())


def best_local_table(groups: list[Group]) -> list[str]:
    lines = [
        "| Seat | Best local model | Runs | Stopped runs | Accuracy | Takeoff lines right | First time | "
        "Seconds per call | Runner-up |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for seat in SEAT_ORDER:
        local = merge_by_model([g for g in groups if g.agent_id == seat and g.provider == "ollama"])
        if not local:
            continue
        qualified = sorted((g for g in local if g.runs >= MIN_RUNS_FOR_BEST), key=rank_key)
        if not qualified:
            leader = min(local, key=rank_key)
            lines.append(
                f"| {seat} | none with {MIN_RUNS_FOR_BEST} runs yet; leading so far {leader.model} ({leader.runs} runs) "
                f"| | | | | | | |"
            )
            continue
        best = qualified[0]
        runner = (
            f"{qualified[1].model} ({qualified[1].runs} runs)" if len(qualified) > 1 else "none qualified"
        )
        first = f"{best.first_time_rate * 100:.0f}%" if best.replies else "n/a"
        takeoff = (
            f"{best.takeoff_right}/{best.takeoff_lines} ({best.takeoff_accuracy * 100:.0f}%)"
            if best.takeoff_accuracy is not None
            else ""
        )
        lines.append(
            f"| {seat} | {best.model}, {best.settings} | {best.runs} | "
            f"{best.stopped_run} ({best.stopped_run / best.runs * 100:.0f}%) | {_accuracy(best)} | "
            f"{takeoff} | {first} | {best.seconds_per_call:.1f} | {runner} |"
        )
    return lines


def local_model_table(runs: list[dict[str, Any]]) -> list[str]:
    """One row per local model, across every seat it held.

    A model can hold several seats in one run, so runs are counted as the distinct recordings it appears
    in rather than summed per seat, which would count the baseline model five times over. Settings and the
    prompt belong to the seat rather than the model, so a model that held several seats says so.
    """
    totals: dict[str, dict[str, Any]] = {}
    for data in runs:
        for seat in data.get("seats", []):
            if seat.get("provider") != "ollama" or not (seat["calls"] or seat["replies"]):
                continue
            row = totals.setdefault(
                seat["model"] or "unknown",
                {"run_ids": set(), "seats": set(), "checks": [0, 0]},
            )
            row["run_ids"].add(data["run_id"])
            row["seats"].add(seat["agent_id"])
            for name in ("calls", "tokens_in", "tokens_out", "wall_ms", "replies", "corrections"):
                row[name] = row.get(name, 0) + seat[name]
            row["first"] = row.get("first", 0) + seat["accepted_first_time"]
            row["stopped"] = row.get("stopped", 0) + seat.get("stopped_run", 0)
            row["cost"] = row.get("cost", 0.0) + seat["est_cost"]
            checks = seat.get("checks") or {}
            row["checks"][0] += sum(1 for met in checks.values() if met)
            row["checks"][1] += len(checks)
    lines = [
        "| Model | Seats | Runs | Calls | Stopped runs | Accuracy | First time | Corrections | "
        "Tokens in/out per call | Seconds per call | Cost per run |",
        "|" + "---|" * 11,
    ]
    for model, row in sorted(totals.items(), key=lambda kv: -len(kv[1]["run_ids"])):
        runs_count, calls = len(row["run_ids"]), row.get("calls", 0)
        met, total = row["checks"]
        accuracy = f"{met}/{total} ({met / total * 100:.0f}%)" if total else "n/a"
        first = f"{row['first'] / row['replies'] * 100:.0f}%" if row.get("replies") else "n/a"
        stopped = f"{row.get('stopped', 0)} ({row.get('stopped', 0) / runs_count * 100:.0f}%)"
        per_call = f"{round(row.get('tokens_in', 0) / calls) if calls else 0}/{round(row.get('tokens_out', 0) / calls) if calls else 0}"
        seconds = f"{row.get('wall_ms', 0) / calls / 1000:.1f}" if calls else "0.0"
        lines.append(
            f"| {model} | {len(row['seats'])} | {runs_count} | {calls} | {stopped} | {accuracy} | {first} | "
            f"{row.get('corrections', 0)} | {per_call} | {seconds} | ${row.get('cost', 0.0) / runs_count:.2f} |"
        )
    if len(lines) == 2:
        lines.append("| no local model has run yet | | | | | | | | | | |")
    return lines


PRICE_NOTES: list[tuple[str, str]] = [
    ("Estimator model", "the model in the Estimator seat, whose takeoff drives the price"),
    ("Priced runs", "runs on a scenario with a reference price that reached a priced total"),
    (
        "Median price difference",
        "the middle value of the run's total minus the reference total, as a percentage of the reference, "
        "sign ignored. The reference is what the app's own calculator and price lookup give for the "
        "quantities the drawings state, 36,882.58 CAD on the Clean run",
    ),
    ("Within 5%, Within 25%", "priced runs whose total is that close to the reference, either way"),
    ("Lowest, Highest", "the most a total fell below the reference and the most it rose above it"),
    (
        "Median labour difference",
        "the same measure for the takeoff's labour hours against the reference hours, 139.85 on the Clean run",
    ),
    (
        "Takeoff lines right",
        "of the materials the drawings schedule, the share whose quantity in the takeoff is within about one "
        "percent of the reference quantity. The takeoff is the Estimator's list of materials and quantities "
        "read off the drawings; it is not a price",
    ),
]


def _median(values: list[float]) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def _pct(value: float | None) -> str:
    return "" if value is None else f"{value:.1f}%"


def _price_row(label: str, checks: list[dict[str, Any]]) -> str:
    errors = [c["total_error_pct"] for c in checks if c.get("total_error_pct") is not None]
    labour = [abs(c["labour_hours_error_pct"]) for c in checks if c.get("labour_hours_error_pct") is not None]
    right = sum(c.get("takeoff_lines_right", 0) for c in checks)
    lines = sum(c.get("takeoff_lines", 0) for c in checks)
    size = [abs(e) for e in errors]
    return (
        f"| {label} | {len(errors)} | {_pct(_median(size))} | "
        f"{sum(1 for e in size if e <= 5)} | {sum(1 for e in size if e <= 25)} | "
        f"{_pct(min(errors)) if errors else ''} | {_pct(max(errors)) if errors else ''} | "
        f"{_pct(_median(labour))} | {_pct(100 * right / lines) if lines else ''} |"
    )


PRICE_HEAD = [
    "| {first} | Priced runs | Median price difference | Within 5% | Within 25% | Lowest | Highest | "
    "Median labour difference | Takeoff lines right |",
    "|---|---|---|---|---|---|---|---|---|",
]


def price_tables(runs: list[dict[str, Any]]) -> list[str]:
    """The price against the reference: by Estimator model, by how the run ended, and by sweep."""
    checked = [r for r in runs if r.get("price_check")]
    if not checked:
        return ["No run on a scenario with a reference price has been recorded yet."]

    def estimator(run: dict[str, Any]) -> str:
        seat = next((s for s in run.get("seats", []) if s["agent_id"] == "estimator" and s["calls"]), None)
        return (seat or {}).get("model") or "no Estimator call"

    out: list[str] = []
    for first, key in (
        ("Estimator model", estimator),
        ("Run ended", lambda r: str(r.get("exit") or "unfinished")),
        ("Sweep", lambda r: str((r.get("sweep") or {}).get("label") or "not a sweep")),
    ):
        grouped: dict[str, list[dict[str, Any]]] = {}
        for run in checked:
            grouped.setdefault(key(run), []).append(run["price_check"])
        out += [PRICE_HEAD[0].format(first=first), PRICE_HEAD[1]]
        out += [_price_row(label, grouped[label]) for label in sorted(grouped)]
        out.append("")
    return out[:-1]


def seat_performance_table(runs: list[dict[str, Any]]) -> list[str]:
    """One row per seat, across every model that held it.

    This is the seat's difficulty, not a model's. A seat that stops runs whatever sits in it, needs many
    corrections, and has been rewritten repeatedly is asking to be made smaller, by splitting the job or by
    moving part of it into a tool. Prompt counts the instruction versions recorded for the seat, which is
    how many times the wording had to be changed to get it working.
    """
    totals: dict[str, dict[str, Any]] = {}
    for data in runs:
        for seat in data.get("seats", []):
            if not (seat["calls"] or seat["replies"]):
                continue
            row = totals.setdefault(
                seat["agent_id"],
                {"run_ids": set(), "models": set(), "prompts": set(), "checks": [0, 0]},
            )
            row["run_ids"].add(data["run_id"])
            if seat.get("model"):
                row["models"].add(seat["model"])
            if seat.get("instructions"):
                row["prompts"].add(seat["instructions"])
            for name in ("calls", "tokens_in", "tokens_out", "wall_ms", "replies", "corrections"):
                row[name] = row.get(name, 0) + seat[name]
            row["first"] = row.get("first", 0) + seat["accepted_first_time"]
            row["stopped"] = row.get("stopped", 0) + seat.get("stopped_run", 0)
            row["cost"] = row.get("cost", 0.0) + seat["est_cost"]
            checks = seat.get("checks") or {}
            row["checks"][0] += sum(1 for met in checks.values() if met)
            row["checks"][1] += len(checks)
    lines = [
        "| Seat | Tested models | Prompt versions | Runs | Calls | Stopped runs | Accuracy | First time | "
        "Corrections | Tokens in/out per call | Seconds per call | Cost per run |",
        "|" + "---|" * 12,
    ]
    for agent_id in SEAT_ORDER:
        if agent_id not in totals:
            continue
        row = totals[agent_id]
        runs_count, calls = len(row["run_ids"]), row.get("calls", 0)
        met, total = row["checks"]
        accuracy = f"{met}/{total} ({met / total * 100:.0f}%)" if total else "n/a"
        first = f"{row['first'] / row['replies'] * 100:.0f}%" if row.get("replies") else "n/a"
        stopped = f"{row.get('stopped', 0)} ({row.get('stopped', 0) / runs_count * 100:.0f}%)"
        per_call = (
            f"{round(row.get('tokens_in', 0) / calls) if calls else 0}/"
            f"{round(row.get('tokens_out', 0) / calls) if calls else 0}"
        )
        seconds = f"{row.get('wall_ms', 0) / calls / 1000:.1f}" if calls else "0.0"
        lines.append(
            f"| {agent_id} | {len(row['models'])} | {len(row['prompts'])} | {runs_count} | {calls} | "
            f"{stopped} | {accuracy} | {first} | {row.get('corrections', 0)} | {per_call} | {seconds} | "
            f"${row.get('cost', 0.0) / runs_count:.2f} |"
        )
    return lines


def raw_rows(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for data in runs:
        sweep = data.get("sweep") or {}
        for seat in data["seats"]:
            if not seat["calls"] and not seat["replies"]:
                continue
            settings = seat.get("settings") or {}
            checks = seat.get("checks") or {}
            match = data.get("golden_match")
            rows.append(
                {
                    "run_id": data["run_id"],
                    "started_at": data.get("started_at", ""),
                    "dataset_id": data["dataset_id"],
                    "exit": data["exit"],
                    "golden_match": "" if match is None else str(bool(match)).lower(),
                    "sweep_label": sweep.get("label", ""),
                    "sweep_config": sweep.get("config_key", ""),
                    "sweep_varied_seat": sweep.get("varied_seat", ""),
                    "sweep_repeat": sweep.get("repeat", ""),
                    "sweep_worker": sweep.get("worker", ""),
                    "seat": seat["agent_id"],
                    "role": seat["role"],
                    "model": seat["model"],
                    "provider": seat.get("provider", ""),
                    "instructions": seat.get("instructions", ""),
                    "temperature": settings.get("temperature", ""),
                    "num_ctx": settings.get("num_ctx", ""),
                    "think": settings.get("think", ""),
                    "max_tokens": settings.get("max_tokens", ""),
                    "calls": seat["calls"],
                    "tokens_in": seat["tokens_in"],
                    "tokens_out": seat["tokens_out"],
                    "wall_ms": seat["wall_ms"],
                    "est_cost": seat["est_cost"],
                    "tool_calls": seat["tool_calls"],
                    "replies": seat["replies"],
                    "accepted_first_time": seat["accepted_first_time"],
                    "corrections": seat["corrections"],
                    "stopped_run": seat["stopped_run"],
                    "reasons": ";".join(f"{k}={v}" for k, v in sorted(seat["reasons"].items())),
                    "checks_met": sum(1 for met in checks.values() if met),
                    "checks_total": len(checks),
                    "checks": ";".join(f"{k}={int(bool(v))}" for k, v in sorted(checks.items())),
                }
            )
    return rows


def write_csv(rows: list[dict[str, Any]], path: Path = RAW_CSV) -> Path:
    names = [name for name, _ in CSV_COLUMNS]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in names})
    return path


def definitions(columns: list[tuple[str, str]]) -> list[str]:
    return [f"- **{name}**: {meaning}" for name, meaning in columns]


def columns_document() -> str:
    return "\n".join(
        [
            "# Model performance columns",
            "",
            "Generated with `docs/model-performance.md` and `docs/model-performance-runs.csv` by "
            "`uv run python scripts/model_report.py --write`. The CSV holds one row per run and seat, raw; "
            "the report's tables aggregate those rows by seat, model and settings.",
            "",
            "## Columns of the report tables",
            "",
            *definitions(TABLE_COLUMNS),
            "",
            "## Extra columns of the local model table",
            "",
            "The same meanings as above, except where a per-model view changes them.",
            "",
            *definitions(LOCAL_TABLE_NOTES),
            "",
            "## Columns of model-performance-runs.csv",
            "",
            *definitions(CSV_COLUMNS),
            "",
            "## How Accuracy is scored",
            "",
            "Each dataset README states its planted defect and what each seat should do about it. "
            "`app/runs/expectations.py` turns that into checks per seat: Intake stops the not-ready request naming "
            "the deadline and the specification; the Estimator raises the LP-2 blocker on Missing sheet and names "
            "E-001 and E-002 on Planted inconsistency; Pricing reports the exit sign unpriced on Missing price; "
            "the Writer's first draft carries the disagreement or the exclusion; the Reviewer fails the flawed "
            "first draft and passes the clean one; the Orchestrator takes the golden route. A seat with no check "
            "on a dataset is scored on the run's golden match, and a dataset without a golden scores nothing.",
            "",
            "## What Accuracy does not measure, and the price tables that do",
            "",
            "Accuracy never looks at a number. Every check above is about behaviour: did the run stop, reach "
            "Work, raise the blocker, carry the concern, pass review. A Clean run whose only Estimator check is "
            "that no blocker was raised scores 100 percent with a price a fifth too high. The price tables "
            "measure the number, for scenarios whose drawings state their own quantities, and are kept out of "
            "Accuracy and out of the ranking on purpose (owner decision 2026-09-19). The reference is computed "
            "by `app/runs/reference.py` from the counted quantities with the app's own calculator and price "
            "lookup, and each run stores its comparison under `price_check` in its `metrics.json`.",
            "",
            *definitions(PRICE_NOTES),
            "",
            "## How the best local model is chosen",
            "",
            f"Among local (Ollama) models with at least {MIN_RUNS_FOR_BEST} runs on the seat: fewest stopped runs "
            "first, then the highest accuracy, then the highest first-time rate, then the fastest call "
            "(owner decision 2026-09-17). At the Estimator only, the share of takeoff lines matching the "
            "dataset's reference quantities ranks second, ahead of accuracy, because that seat's behaviour "
            "checks amount to whether it raised a blocker while its real job is reading the drawings. The "
            "reported Accuracy column is behaviour everywhere, and the price is reported separately (owner "
            "decisions 1b of 2026-09-19 and the ranking left to the author).",
            "",
        ]
    )


SEAT_WHY: dict[str, str] = {
    "orchestrator": "plans and routes from text; no tools on purpose",
    "intake": "reads prepared document text and asks for what is unknown",
    "estimator": "looks at drawing sheets as images through the drawing reader, then calls the calculator",
    "pricing": "prices every line from the fixture through the lookup tool",
    "writer": "assembles the specialists' text through the template tool",
    "reviewer": "judges the compiled page images; a model without image input is refused",
    "single": "does all of the above alone",
}


def _yes(flag: bool) -> str:
    return "yes" if flag else "no"


def _ollama_models(host: str) -> dict[str, dict[str, Any]] | None:
    """Pulled models with Ollama's own capability list, or None when Ollama is not reachable."""
    base = host.rstrip("/")
    try:
        tags = httpx.get(f"{base}/api/tags", timeout=2.0).json().get("models", [])
        pulled: dict[str, dict[str, Any]] = {}
        for entry in tags:
            name = str(entry.get("name"))
            show = httpx.post(f"{base}/api/show", json={"name": name}, timeout=5.0).json()
            pulled[name] = {
                "size": int(entry.get("size", 0)),
                "capabilities": [str(c) for c in show.get("capabilities", [])],
            }
        return pulled
    except Exception:  # noqa: BLE001
        return None


def model_table(
    config: ModelConfig, availability: dict[str, Any], pulled: dict[str, dict[str, Any]] | None
) -> list[str]:
    lines = [
        "| Model | Where | Text | Vision | Audio | Tool calls | Available |",
        "|---|---|---|---|---|---|---|",
    ]
    for spec in config.models.values():
        where = str(config.providers.get(spec.provider, {}).get("label", spec.provider))
        vision, audio, tools = _yes(spec.image_input), "no", "yes"
        if spec.provider == "ollama":
            entry = None
            if pulled is not None:
                entry = pulled.get(spec.model_id) or pulled.get(f"{spec.model_id}:latest")
            if pulled is None:
                available = "Ollama not reachable"
            elif entry is None:
                available = "not pulled"
            else:
                caps = entry["capabilities"]
                available = f"pulled, {entry['size'] / 1e9:.1f} GB"
                audio, tools = _yes("audio" in caps), _yes("tools" in caps)
                if ("vision" in caps) != spec.image_input:
                    vision = f"registry says {vision}, Ollama says {_yes('vision' in caps)}"
        else:
            state = availability.get(spec.provider)
            available = str(state.reason) if state is not None else "not probed"
        lines.append(f"| {spec.label} | {where} | yes | {vision} | {audio} | {tools} | {available} |")
    return lines


def seat_table() -> list[str]:
    lines = ["| Seat | Text | Vision | Tool calls | Why |", "|---|---|---|---|---|"]
    for agent_id, definition in SEAT_DEFINITIONS.items():
        vision = agent_id == "single" or DRAWING_PAGES in definition.sees or PAGE_TEXT in definition.sees
        tools = _yes(bool(definition.tools))
        lines.append(f"| {agent_id} | yes | {_yes(vision)} | {tools} | {SEAT_WHY.get(agent_id, '')} |")
    lines.append(
        "| case, market (S8) | yes | no | yes | fixture lookups; the two seats arrive with the appraisal workflow |"
    )
    return lines


def modality_section(probe: bool = True) -> list[str]:
    """Which model takes what, and which seat needs what, so a seat is never given a model that cannot serve it."""
    config = ModelConfig.load()
    availability = check_availability(config) if probe else {}
    host = str(config.providers.get("ollama", {}).get("host", "http://localhost:11434"))
    pulled = _ollama_models(host) if probe else None
    return [
        "## Models and what they take",
        "",
        "Text, vision and tool calling come from `config/models.yaml` and, for a pulled local model, from Ollama's "
        "own capability list; audio comes only from Ollama's list, since no seat sends audio. Available says what "
        "this machine could reach when the report was written, never a credential.",
        "",
        *model_table(config, availability, pulled),
        "",
        "## Seats and what they need",
        "",
        "From the seat definitions in `app/seats/definitions.py`: a seat needs vision when drawing sheets or "
        "compiled pages reach it as images, and tool calling when it has tools. A model is eligible for a seat "
        "only when it takes everything the seat needs.",
        "",
        *seat_table(),
    ]


def report(groups: list[Group], runs: list[dict[str, Any]], probe: bool = True) -> str:
    live = [r for r in runs if any(s["calls"] for s in r["seats"])]
    spend = sum(s["est_cost"] for r in runs for s in r["seats"])
    sweeps = sorted({str((r.get("sweep") or {}).get("label", "")) for r in runs} - {""})
    body = [
        "# Model performance by seat",
        "",
        "Generated by `uv run python scripts/model_report.py --write` from every run under `runs/`, with the raw "
        "rows in `docs/model-performance-runs.csv` and every column defined in `docs/model-performance-columns.md`. "
        "Each run writes its own `metrics.json` as it ends, so the tables grow with every run.",
        "",
        f"Runs recorded: {len(runs)}, of which {len(live)} called a model. "
        f"Estimated spend across all of them: ${spend:.2f}."
        + (f" Sweeps included: {', '.join(sweeps)}." if sweeps else ""),
        "",
        "## What the columns mean",
        "",
        *definitions(TABLE_COLUMNS),
        "",
        "## Best local model per seat",
        "",
        f"Ranked among Ollama models with at least {MIN_RUNS_FOR_BEST} runs on the seat: fewest stopped runs, then "
        "accuracy, then first-time rate, then seconds per call (owner decision 2026-09-17). At the Estimator, "
        "and only there, how well the takeoff matches the dataset's reference quantities ranks second, ahead "
        "of behaviour: that seat's behaviour checks are nearly silent, and reading the drawings is its job. "
        "Accuracy itself stays a measure of behaviour everywhere.",
        "",
        *best_local_table(groups),
        "",
        "## Local model performance",
        "",
        "Each local model across every seat it held, which answers what a model is like rather than what it "
        "is like in one chair. Runs count the recordings a model appears in, not the seats it filled, so a "
        "model holding five seats in one run counts once. Settings and the prompt belong to the seat, so a "
        "model that held several says how many it saw.",
        "",
        *local_model_table(runs),
        "",
        "## Seat performance",
        "",
        "Each seat across every model that held it, which says how hard the seat is rather than how good a "
        "model is. A seat that stops runs whatever sits in it, needs many corrections, and has had its "
        "wording rewritten repeatedly is a seat asking to be made smaller, by splitting the job or by "
        "moving part of it into a tool.",
        "",
        *seat_performance_table(runs),
        "",
        "## Price against the reference",
        "",
        "Accuracy in the tables above says whether a run behaved as its scenario expects: it reached Work, "
        "raised the blocker, carried the concern, passed review. It never looks at a number, so a run that "
        "passes review with a price a fifth too high scores as accurate. These tables look at the number, "
        "for the scenarios whose drawings state their own quantities. They are kept apart from accuracy "
        "on purpose (owner decision 2026-09-19).",
        "",
        *definitions(PRICE_NOTES),
        "",
        *price_tables(runs),
        "",
        "## Every seat and model",
        "",
        *table(groups),
        "",
        "## Why replies were sent back",
        "",
        "Only rejections against the instructions each seat runs on now, so every line is something still "
        "worth fixing. A seat taught since a rejection no longer carries it here. Pairs that ran without a "
        "rejection are listed as none, so absence is visible.",
        "",
        *reason_table(groups),
        "",
        *modality_section(probe),
        "",
    ]
    return "\n".join(body)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--write", action="store_true", help="refresh the report, the CSV and the columns document"
    )
    args = parser.parse_args()
    groups, runs = collect()
    text = report(groups, runs)
    print(text)
    if args.write:
        # The CSV is the one people open in a spreadsheet, and Windows locks an open file. Each output is
        # written on its own so a locked one cannot leave the others stale, and the exit code says so.
        writers = (
            (REPORT, lambda: REPORT.write_text(text, encoding="utf-8", newline="\n")),
            (RAW_CSV, lambda: write_csv(raw_rows(runs))),
            (COLUMNS_DOC, lambda: COLUMNS_DOC.write_text(columns_document(), encoding="utf-8", newline="\n")),
        )
        locked = []
        for path, write in writers:
            try:
                write()
            except PermissionError:
                locked.append(path)
                print(f"NOT written, the file is open in another program: {path.relative_to(ROOT)}")
            else:
                print(f"written: {path.relative_to(ROOT)}")
        if locked:
            print(f"close {', '.join(p.name for p in locked)} and run this again")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
