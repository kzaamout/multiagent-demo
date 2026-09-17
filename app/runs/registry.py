"""Datasets, live runs, and replay sources."""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.agents.stubs import scenario_for
from app.config import Settings
from app.live.materials import DatasetFiles, supplier_order_from
from app.live.providers import (
    ModelConfig,
    SeatModelFactory,
    check_availability,
    live_roster,
    strands_model_for,
    unavailable_seats,
)
from app.live.source import LiveAgentSource, LiveContext
from app.orchestrator.knowledge_store import KnowledgeStore
from app.orchestrator.clock import Clock
from app.orchestrator.orchestrator import DatasetRef, Orchestrator
from app.orchestrator.roster import build_roster
from app.runs.bus import StreamBus
from app.runs.recorder import Recorder, read_events, read_meta
from app.schema.events import Event

DATASET_ORDER: list[tuple[str, str]] = [
    ("clean-run", "Clean run"),
    ("planted-inconsistency", "Planted inconsistency"),
    ("missing-sheet", "Missing sheet"),
    ("missing-price", "Missing price"),
    ("not-ready", "Not ready"),
    ("prospect-own", "Prospect own"),
    ("prospect-a", "Prospect A"),
    ("prospect-b", "Prospect B"),
    ("prospect-c", "Prospect C"),
]


@dataclass(frozen=True)
class DatasetInfo:
    id: str
    number: int
    label: str
    folder: Path
    brand: dict[str, Any]
    golden_path: Path
    knowledge_seed: Path | None

    @property
    def display(self) -> str:
        return f"{self.number:02d} · {self.label}"

    @property
    def client_id(self) -> str:
        name = str(self.brand.get("prospect_name") or "prospect")
        return name.lower().replace(" ", "-").replace(".", "").replace(",", "")


def discover_datasets(datasets_dir: Path) -> list[DatasetInfo]:
    found: list[DatasetInfo] = []
    for number, (folder_name, label) in enumerate(DATASET_ORDER, start=1):
        folder = datasets_dir / folder_name
        if not folder.is_dir():
            continue
        brand_path = folder / "brand.yaml"
        brand: dict[str, Any] = {}
        if brand_path.exists():
            loaded = yaml.safe_load(brand_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                brand = loaded
        seed = folder / "knowledge.seed.md"
        found.append(
            DatasetInfo(
                id=folder_name,
                number=number,
                label=label,
                folder=folder,
                brand=brand,
                golden_path=folder / "golden-events.jsonl",
                knowledge_seed=seed if seed.exists() else None,
            )
        )
    return found


class LiveUnavailable(RuntimeError):
    """A live run cannot start because a seat's provider is unavailable."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass
class ReplaySource:
    kind: str
    path: Path
    run_id: str


class Registry:
    def __init__(
        self,
        settings: Settings,
        bus: StreamBus | None = None,
        seat_model_factory: SeatModelFactory | None = None,
        model_config: ModelConfig | None = None,
    ) -> None:
        self.settings = settings
        self.seat_model_factory = seat_model_factory
        self._model_config = model_config
        self.bus = bus or StreamBus()
        self.datasets = {d.id: d for d in discover_datasets(settings.datasets_dir)}
        self.live: Orchestrator | None = None
        self.runs: dict[str, Orchestrator] = {}
        self._tasks: set[Any] = set()

    def dataset(self, dataset_id: str) -> DatasetInfo:
        try:
            return self.datasets[dataset_id]
        except KeyError as error:
            raise KeyError(f"unknown dataset {dataset_id}") from error

    def latest_recording(self, dataset_id: str) -> tuple[Path, dict[str, Any]] | None:
        runs_dir = self.settings.runs_dir
        if not runs_dir.exists():
            return None
        best: tuple[str, Path, dict[str, Any]] | None = None
        for folder in runs_dir.iterdir():
            if not folder.is_dir():
                continue
            meta = read_meta(folder)
            if not meta or meta.get("dataset_id") != dataset_id or not meta.get("exit"):
                continue
            started = str(meta.get("started_at", ""))
            if best is None or started > best[0]:
                best = (started, folder, meta)
        if best is None:
            return None
        return best[1], best[2]

    def replay_source(self, dataset_id: str) -> ReplaySource | None:
        recording = self.latest_recording(dataset_id)
        if recording is not None:
            folder, meta = recording
            return ReplaySource(kind="recording", path=folder / "events.jsonl", run_id=str(meta["run_id"]))
        info = self.dataset(dataset_id)
        if info.golden_path.exists():
            first = info.golden_path.read_text(encoding="utf-8").splitlines()[0]
            return ReplaySource(kind="golden", path=info.golden_path, run_id=Event.from_line(first).run_id)
        return None

    @property
    def model_config(self) -> ModelConfig:
        if self._model_config is None:
            self._model_config = ModelConfig.load()
        return self._model_config

    def mode_for(self, dataset_id: str) -> str:
        if self.settings.agent_mode == "stub":
            return "stub"
        return "live" if DatasetFiles(self.dataset(dataset_id).folder).is_curated() else "stub"

    def provider_report(self) -> dict[str, Any]:
        config = self.model_config
        availability = check_availability(config)
        return {
            "providers": {k: {"available": v.available, "reason": v.reason} for k, v in availability.items()},
            "seats": {
                seat: {"model": config.seat_spec(seat).label, "provider": config.seat_spec(seat).provider}
                for seat in config.seats
            },
            "live_blockers": unavailable_seats(config, availability),
        }

    def dataset_listing(self) -> list[dict[str, Any]]:
        listing: list[dict[str, Any]] = []
        for info in sorted(self.datasets.values(), key=lambda d: d.number):
            source = self.replay_source(info.id)
            listing.append(
                {
                    "id": info.id,
                    "number": info.number,
                    "label": info.display,
                    "has_golden": info.golden_path.exists(),
                    "has_recording": self.latest_recording(info.id) is not None,
                    "replay_source": source.kind if source else None,
                    "mode": self.mode_for(info.id),
                }
            )
        return listing

    def is_live(self) -> bool:
        return self.live is not None and not self.live.state.terminated

    def build_orchestrator(
        self,
        dataset_id: str,
        *,
        names: dict[str, str] | None = None,
        seed: int | None = None,
        start: dt.datetime | None = None,
        pace: float | None = None,
        record: bool = True,
        run_id: str | None = None,
        clock: Clock | None = None,
        id_factory: Callable[[int], str] | None = None,
    ) -> Orchestrator:
        info = self.dataset(dataset_id)
        rid = run_id or str(uuid.uuid4())
        roster = build_roster(self.settings.workflow, seed=seed, names=names)
        recorder = Recorder(self.settings.runs_dir, rid) if record else None
        knowledge_path = (
            recorder.knowledge_path if recorder else self.settings.runs_dir / "_ephemeral" / rid / "knowledge.md"
        )
        scenario: Any
        knowledge_store: KnowledgeStore | None = None
        run_folder = recorder.folder if recorder else knowledge_path.parent
        if self.mode_for(dataset_id) == "live":
            config = self.model_config
            if self.seat_model_factory is None:
                problems = unavailable_seats(config, check_availability(config))
                if problems:
                    raise LiveUnavailable(problems)
            factory = self.seat_model_factory or (lambda seat: strands_model_for(config, seat))
            roster, seat_models = live_roster(roster, factory)
            knowledge_store = KnowledgeStore(self.settings.knowledge_dir)
            knowledge_store.ensure(info.client_id, info.knowledge_seed)
            scenario = LiveAgentSource(
                dataset_id=info.id,
                client_id=info.client_id,
                context=LiveContext(
                    files=DatasetFiles(info.folder),
                    knowledge=knowledge_store,
                    prospect_name=str(info.brand.get("prospect_name") or "the prospect"),
                    project=f"Electrical bid response, {info.label}",
                    supplier_order=supplier_order_from(knowledge_store.read(info.client_id)),
                    long_lead_days=self.settings.long_lead_days,
                    review_max_cycles=self.settings.review_max_cycles,
                ),
                seat_models=seat_models,
                knowledge_seed=info.knowledge_seed,
            )
            clock = clock or Clock(start or dt.datetime.now(dt.UTC), 1.0)
        else:
            scenario = scenario_for(dataset_id)
            clock = clock or Clock(start or dt.datetime.now(dt.UTC), pace or self.settings.stub_pace)
        return Orchestrator(
            run_id=rid,
            workflow=self.settings.workflow,
            dataset=DatasetRef(
                dataset_id=info.id, label=info.display, client_id=info.client_id, knowledge_seed=info.knowledge_seed
            ),
            scenario=scenario,
            roster=roster,
            review_max_cycles=self.settings.review_max_cycles,
            cost_ceiling=self.settings.cost_ceiling,
            clock=clock,
            bus=self.bus,
            recorder=recorder,
            knowledge_path=knowledge_path,
            event_log_path=f"runs/{rid}/events.jsonl",
            id_factory=id_factory,
            knowledge_store=knowledge_store,
            run_folder=run_folder,
        )

    def start_run(
        self, dataset_id: str, names: dict[str, str] | None = None, *, dry_intake: bool = False
    ) -> Orchestrator:
        import asyncio

        if self.is_live():
            raise RuntimeError("a run is already in progress")
        orchestrator = self.build_orchestrator(dataset_id, names=names)
        if dry_intake:
            orchestrator.scenario.dry_intake = True
        self.live = orchestrator
        self.runs[orchestrator.run_id] = orchestrator
        task = asyncio.create_task(orchestrator.run())
        orchestrator.attach_task(task)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return orchestrator

    def get_run(self, run_id: str) -> Orchestrator | None:
        return self.runs.get(run_id)

    def read_recording(self, run_id: str) -> list[Event] | None:
        path = self.settings.runs_dir / run_id / "events.jsonl"
        if path.exists():
            return read_events(path)
        return None
