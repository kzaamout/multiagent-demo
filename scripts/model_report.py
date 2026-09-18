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
    ("Stopped runs", "times the seat ran out of attempts and the run ended because of it"),
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
    reasons: dict[str, int] = field(default_factory=dict)

    @property
    def first_time_rate(self) -> float:
        return self.accepted_first_time / self.replies if self.replies else 0.0

    @property
    def accuracy(self) -> float | None:
        return self.checks_met / self.checks_total if self.checks_total else None

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


def reason_table(groups: list[Group]) -> list[str]:
    """Every seat and model pair, including the ones never sent back, so absence is visible."""
    lines = ["| Seat | Model | Rejections | Reasons |", "|---|---|---|---|"]
    merged: dict[tuple[str, str], dict[str, int]] = {}
    for g in groups:
        bucket = merged.setdefault((g.agent_id, g.model), {})
        for name, count in g.reasons.items():
            bucket[name] = bucket.get(name, 0) + count
    for (agent_id, model), reasons in merged.items():
        total = sum(reasons.values())
        text = ", ".join(f"{name} {count}" for name, count in sorted(reasons.items())) if total else "none"
        lines.append(f"| {agent_id} | {model} | {total} | {text} |")
    return lines


def rank_key(g: Group) -> tuple[int, float, float, float]:
    """Owner ranking (2026-09-17): fewest stopped runs, then accuracy, then first-time rate, then speed."""
    return (
        g.stopped_run,
        -(g.accuracy if g.accuracy is not None else 0.0),
        -g.first_time_rate,
        g.seconds_per_call,
    )


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
        "| Seat | Best local model | Runs | Stopped runs | Accuracy | First time | Seconds per call | Runner-up |",
        "|---|---|---|---|---|---|---|---|",
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
                f"| | | | | | |"
            )
            continue
        best = qualified[0]
        runner = (
            f"{qualified[1].model} ({qualified[1].runs} runs)" if len(qualified) > 1 else "none qualified"
        )
        first = f"{best.first_time_rate * 100:.0f}%" if best.replies else "n/a"
        lines.append(
            f"| {seat} | {best.model}, {best.settings} | {best.runs} | {best.stopped_run} | {_accuracy(best)} | "
            f"{first} | {best.seconds_per_call:.1f} | {runner} |"
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
            "## How the best local model is chosen",
            "",
            f"Among local (Ollama) models with at least {MIN_RUNS_FOR_BEST} runs on the seat: fewest stopped runs "
            "first, then the highest accuracy, then the highest first-time rate, then the fastest call "
            "(owner decision 2026-09-17).",
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
        "accuracy, then first-time rate, then seconds per call (owner decision 2026-09-17).",
        "",
        *best_local_table(groups),
        "",
        "## Every seat and model",
        "",
        *table(groups),
        "",
        "## Why replies were sent back",
        "",
        "Every seat and model pair that ran, with none where nothing was sent back.",
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
        REPORT.write_text(text, encoding="utf-8", newline="\n")
        write_csv(raw_rows(runs))
        COLUMNS_DOC.write_text(columns_document(), encoding="utf-8", newline="\n")
        for path in (REPORT, RAW_CSV, COLUMNS_DOC):
            print(f"written: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
