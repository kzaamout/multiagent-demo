"""Golden event logs: deterministic stub runs and the replay-and-compare rule.

Golden logs are compared on the ordered stage.changed transitions and the terminal exit only
(datasets/README.md). Model text is never compared.
"""

from __future__ import annotations

import datetime as dt
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.agents.base import HumanScript
from app.config import Settings
from app.orchestrator.clock import VirtualClock
from app.orchestrator.driver import drive
from app.orchestrator.roster import EXPORT_NAMES
from app.runs.recorder import read_events
from app.runs.registry import Registry
from app.schema.events import Event

GOLDEN_START = dt.datetime(2026, 9, 14, 9, 12, 0, tzinfo=dt.UTC)
NAMESPACE = uuid.UUID("5e7c1a2b-9d34-4b6e-8f10-2a6c3d4e5f60")

Transition = tuple[str | None, str, str]


def golden_run_id(dataset_id: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"golden:{dataset_id}"))


def golden_event_id(dataset_id: str, seq: int) -> str:
    return str(uuid.uuid5(NAMESPACE, f"golden:{dataset_id}:{seq}"))


async def deterministic_run(
    settings: Settings, dataset_id: str, script: HumanScript | None = None
) -> list[Event]:
    """Run a stub scenario with the virtual clock, fixed names, ids, and start time."""
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Settings(
            root=settings.root,
            runs_dir=Path(tmp),
            datasets_dir=settings.datasets_dir,
            retry_budget=settings.retry_budget,
            cost_ceiling=settings.cost_ceiling,
            stub_pace=settings.stub_pace,
            workflow=settings.workflow,
            agent_mode="stub",
        )
        registry = Registry(scratch)
        orchestrator = registry.build_orchestrator(
            dataset_id,
            names=EXPORT_NAMES,
            record=False,
            run_id=golden_run_id(dataset_id),
            clock=VirtualClock(GOLDEN_START),
            id_factory=lambda seq: golden_event_id(dataset_id, seq),
        )
        await drive(orchestrator, script or orchestrator.scenario.human_script)
        return list(orchestrator.events)


def transitions(events: list[Event]) -> list[Transition]:
    return [
        (e.payload.get("from"), str(e.payload["to"]), str(e.payload["direction"]))
        for e in events
        if e.type == "stage.changed"
    ]


def terminal_exit(events: list[Event]) -> str | None:
    if not events or events[-1].type != "run.terminated":
        return None
    return str(events[-1].payload["exit"])


@dataclass
class Comparison:
    dataset_id: str
    ok: bool
    message: str


def compare(dataset_id: str, actual: list[Event], golden: list[Event]) -> Comparison:
    a, g = transitions(actual), transitions(golden)
    for index, (x, y) in enumerate(zip(a, g, strict=False)):
        if x != y:
            return Comparison(dataset_id, False, f"{dataset_id}: transition {index} is {x}, golden has {y}")
    if len(a) != len(g):
        shorter = min(len(a), len(g))
        extra = a[shorter:] if len(a) > len(g) else g[shorter:]
        side = "run has extra" if len(a) > len(g) else "run is missing"
        return Comparison(dataset_id, False, f"{dataset_id}: transition {shorter}: {side} {extra[0]}")
    ea, eg = terminal_exit(actual), terminal_exit(golden)
    if ea != eg:
        return Comparison(dataset_id, False, f"{dataset_id}: exit is {ea}, golden has {eg}")
    return Comparison(dataset_id, True, f"{dataset_id}: {len(a)} transitions and exit {ea} match")


def write_golden(path: Path, events: list[Event]) -> None:
    path.write_text("".join(e.to_line() + "\n" for e in events), encoding="utf-8", newline="\n")


def read_golden(path: Path) -> list[Event]:
    return read_events(path)
