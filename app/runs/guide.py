"""The seat model guide: which open and which proprietary model has followed a seat's instructions best.

Spec 014. The Settings page and the performance report take their figures from here, so the two never
disagree (rule 15). A seat's instruction accuracy on a model is the share of its replies the
Orchestrator accepted on the first attempt, summed over every recorded run whatever the seat's
instructions or settings were (owner decisions 2b and 3a, 2026-09-21). Nothing is stored: the figures
are worked out from the metrics each run writes as it ends, or from the event log of a run that has none.
"""

from __future__ import annotations

import json
import math
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.live.providers import ModelConfig
from app.runs.metrics import METRICS_FILE, run_metrics
from app.runs.recorder import read_events
from app.seats.definitions import needs_image_input

EVENTS_FILE = "events.jsonl"
MIN_RUNS_FOR_BEST = 5
"""A model needs this many runs on a seat to be named for it (owner decision 4a)."""
Z95 = 1.959963984540054
"""The normal quantile for a two-sided 95% range, for the Wilson lower bound (owner decision 5c)."""
SEAT_ORDER = ("orchestrator", "intake", "estimator", "pricing", "writer", "reviewer")
"""The seats Settings shows, in its order. The Single-model seat has no row there and no picks."""
KINDS = ("open", "proprietary")
INSTRUCTION_ACCURACY = (
    "the share of a seat's replies the Orchestrator accepted the first time it checked them against the "
    "seat's instructions"
)
"""The definition in the words the Settings page uses, so the report and the page say the same (FR-013)."""


def metrics_of(folder: Path) -> dict[str, Any] | None:
    """A run's metrics: its metrics.json when it has the current fields, otherwise worked out from its
    event log, which is how a run cut off before it ended is still counted. None without an event log
    or when neither can be read."""
    events_path = folder / EVENTS_FILE
    if not events_path.exists():
        return None
    path = folder / METRICS_FILE
    if path.exists():
        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        seats = data.get("seats") or []
        if seats and "golden_match" in data and all("stopped_run" in row for row in seats):
            return data
    try:
        return run_metrics(read_events(events_path), folder)
    except (OSError, ValueError):
        return None


def instruction_accuracy(first_time: int, replies: int) -> float | None:
    """Replies accepted on the first attempt over replies; a reply the run stopped on is a reply."""
    return first_time / replies if replies else None


def whole_percent(first_time: int, replies: int) -> int | None:
    """Instruction accuracy as a whole percentage, rounded as the report has always printed it."""
    share = instruction_accuracy(first_time, replies)
    return None if share is None else int(f"{share * 100:.0f}")


def wilson_lower(first_time: int, replies: int, z: float = Z95) -> float | None:
    """The low end of the Wilson score range around the share, so a long record outranks a short
    perfect one: 390 of 397 gives 0.964, 13 of 13 gives 0.772."""
    if not replies:
        return None
    p = first_time / replies
    z2 = z * z
    centre = p + z2 / (2 * replies)
    margin = z * math.sqrt(p * (1 - p) / replies + z2 / (4 * replies * replies))
    return (centre - margin) / (1 + z2 / replies)


@dataclass(frozen=True)
class SeatRecord:
    """One seat on one model label across every counted run."""

    agent_id: str
    model: str
    runs: int = 0
    replies: int = 0
    first_time: int = 0

    @property
    def share(self) -> float | None:
        return instruction_accuracy(self.first_time, self.replies)

    @property
    def percent(self) -> int | None:
        return whole_percent(self.first_time, self.replies)

    @property
    def bound(self) -> float | None:
        return wilson_lower(self.first_time, self.replies)

    def as_json(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "runs": self.runs,
            "replies": self.replies,
            "first_time": self.first_time,
            "percent": self.percent,
        }


def _ran(seat: dict[str, Any]) -> bool:
    """A seat row counts when the seat made a call or produced a reply, as the report has always ruled."""
    return bool(seat.get("calls") or seat.get("replies"))


def records(runs: Iterable[dict[str, Any]]) -> dict[tuple[str, str], SeatRecord]:
    """Seat rows summed by seat and model label, whatever the settings or instruction version."""
    sums: dict[tuple[str, str], list[int]] = {}
    for run in runs:
        for seat in run.get("seats") or []:
            if not _ran(seat):
                continue
            key = (str(seat["agent_id"]), str(seat.get("model") or "unknown"))
            total = sums.setdefault(key, [0, 0, 0])
            total[0] += 1
            total[1] += int(seat.get("replies", 0))
            total[2] += int(seat.get("accepted_first_time", 0))
    return {key: SeatRecord(key[0], key[1], *total) for key, total in sums.items()}


def runs_called(runs: Iterable[dict[str, Any]]) -> int:
    """Runs in which some seat made a model call or a reply; a stub run adds nothing."""
    return sum(1 for run in runs if any(_ran(seat) for seat in run.get("seats") or []))


@dataclass(frozen=True)
class SeatPick:
    """The top model of one kind for one seat, or why there is none."""

    status: str
    """"pick", "no_runs" (no model of the kind has held the seat) or "too_few_runs" (none has 5)."""
    record: SeatRecord | None = None
    model_key: str | None = None

    def as_json(self) -> dict[str, Any]:
        if self.record is None:
            return {"status": self.status}
        return {"status": self.status, "model_key": self.model_key, **self.record.as_json()}


def pick(seat: str, kind: str, recs: dict[tuple[str, str], SeatRecord], config: ModelConfig) -> SeatPick:
    """The model of this kind the seat's record favours. A candidate is in the registry, states this kind,
    and takes what the seat needs; it qualifies with 5 runs. Highest Wilson bound wins, then more
    replies, then the model listed first in the registry (FR-004, FR-006)."""
    by_label = {spec.label: (index, spec) for index, spec in enumerate(config.models.values())}
    images = needs_image_input(seat)
    candidates = []
    for (agent_id, label), record in recs.items():
        entry = by_label.get(label)
        if agent_id != seat or entry is None:
            continue
        index, spec = entry
        if spec.weights != kind or (images and not spec.image_input):
            continue
        candidates.append((index, spec.key, record))
    if not candidates:
        return SeatPick("no_runs")
    qualifying = [c for c in candidates if c[2].runs >= MIN_RUNS_FOR_BEST and c[2].replies > 0]
    if not qualifying:
        return SeatPick("too_few_runs")
    _, key, record = max(qualifying, key=lambda c: (c[2].bound or 0.0, c[2].replies, -c[0]))
    return SeatPick("pick", record, key)


def current(seat: str, recs: dict[tuple[str, str], SeatRecord], config: ModelConfig) -> SeatRecord | None:
    """The record of the model the seat is on now, whatever its runs; None when it has no replies there."""
    if seat not in config.seats:
        return None
    record = recs.get((seat, config.seat_spec(seat).label))
    return record if record is not None and record.replies else None


def unclassified(config: ModelConfig) -> list[str]:
    """Registry models that do not say whether their weights are open or proprietary."""
    return [spec.label for spec in config.models.values() if spec.weights is None]


def guide_table(recs: dict[tuple[str, str], SeatRecord], runs: int, config: ModelConfig) -> dict[str, Any]:
    """What the Settings page and the report show, per contracts/seats-guide.md section 2."""
    seats: dict[str, Any] = {}
    for seat in SEAT_ORDER:
        now = current(seat, recs, config)
        seats[seat] = {
            "current": now.as_json() if now is not None else None,
            **{kind: pick(seat, kind, recs, config).as_json() for kind in KINDS},
        }
    return {"runs": runs, "min_runs": MIN_RUNS_FOR_BEST, "seats": seats}


Signature = tuple[str, int, int]
"""A run folder's state: which file stands for it, its modification time and its size."""


def _signature(folder: Path) -> Signature | None:
    """`metrics.json` once the run has ended; the event log of a run that has not, which grows as it goes."""
    for name in (METRICS_FILE, EVENTS_FILE):
        try:
            stat = (folder / name).stat()
        except OSError:
            continue
        return (name, stat.st_mtime_ns, stat.st_size)
    return None


class SeatGuide:
    """The guide for one runs folder, as the Settings page asks for it.

    Each request lists the run folders and compares each one's signature with the last request's; only a new
    or changed folder is read again, and when nothing changed the summed records are reused as they are
    (FR-012, research D7). There is no timer and no watcher: the check runs when the page asks, so a run
    finished by a sweep in another process is counted on the next load.
    """

    def __init__(self, runs_dir: Path) -> None:
        self.runs_dir = runs_dir
        self._folders: dict[str, tuple[Signature, dict[str, Any] | None]] = {}
        self._counted: frozenset[tuple[str, Signature]] | None = None
        self._records: dict[tuple[str, str], SeatRecord] = {}
        self._runs = 0

    def _scan(self) -> dict[str, Signature]:
        if not self.runs_dir.is_dir():
            return {}
        seen: dict[str, Signature] = {}
        for entry in os.scandir(self.runs_dir):
            if entry.is_dir() and not entry.name.startswith("_"):
                signature = _signature(Path(entry.path))
                if signature is not None:
                    seen[entry.name] = signature
        return seen

    def refresh(self, exclude_run: str | None = None) -> tuple[dict[tuple[str, str], SeatRecord], int]:
        """The summed records and the number of runs that called a model, leaving out `exclude_run`."""
        seen = {name: sig for name, sig in self._scan().items() if name != exclude_run}
        for name in [name for name in self._folders if name not in seen]:
            del self._folders[name]
        for name, signature in seen.items():
            cached = self._folders.get(name)
            if cached is None or cached[0] != signature:
                self._folders[name] = (signature, metrics_of(self.runs_dir / name))
        counted = frozenset(seen.items())
        if counted != self._counted:
            runs = [data for _, data in self._folders.values() if data is not None]
            self._records, self._runs = records(runs), runs_called(runs)
            self._counted = counted
        return self._records, self._runs

    def table(self, config: ModelConfig, exclude_run: str | None = None) -> dict[str, Any]:
        """Every counted run but `exclude_run`, the run this app is running now (FR-012). The picks are
        worked out on every call, since a seat swap changes the current model."""
        recs, runs = self.refresh(exclude_run)
        return guide_table(recs, runs, config)
