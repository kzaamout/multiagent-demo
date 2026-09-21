"""Datasets, live runs, and replay sources."""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.agents.stubs import scenario_for
from app.agents.stubs.single_run import StubSingleSource
from app.compile.pipeline import tools_available
from app.config import Settings
from app.live.materials import DatasetFiles, supplier_order_from
from app.live.providers import (
    Availability,
    LiveUnavailable,
    ModelConfig,
    SeatModelFactory,
    check_availability,
    family_of,
    live_roster,
    strands_model_for,
    unavailable_seats,
)
from app.live.source import LiveAgentSource, LiveContext
from app.orchestrator.clock import Clock
from app.orchestrator.knowledge_store import KnowledgeStore
from app.orchestrator.orchestrator import DatasetRef, Orchestrator
from app.orchestrator.roster import EXPORT_NAMES, SEATS, build_roster, single_agent
from app.runs.bus import StreamBus
from app.runs.recorder import Recorder, read_events, read_meta
from app.schema.events import Agent, Event, Model

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


__all__ = ["LiveUnavailable"]

DEPENDENCY_NOTES: dict[str, str] = {
    "orchestrator": "Runs every stage transition",
    "intake": "Stage 1, before Plan",
    "estimator": "Bid response workflow. Needs vision on drawings",
    "pricing": "Bid response workflow. Runs after Estimator",
    "writer": "Runs after all specialists",
    "reviewer": "Different model family from Writer",
    "case": "Appraisal workflow",
    "market": "Appraisal workflow. Runs after Case Manager",
    "single": "Single-model mode. Does the whole job alone, no review",
}
"""The dependency note on each Settings row (design brief 9)."""

SHARED_FAMILY_WARNING = "The Reviewer now shares the Writer's model family; the review is weaker for it."


@dataclass(frozen=True)
class SeatSwap:
    seat: str
    model: Model
    warning: str
    applied: str


@dataclass
class ReplaySource:
    kind: str
    path: Path
    run_id: str


CLOUD_MODE_REASON = "not offered in Cloud mode"
"""Why every local model is greyed and a local seat refuses a live run in Cloud mode (S7 research D7)."""


class Registry:
    def __init__(
        self,
        settings: Settings,
        bus: StreamBus | None = None,
        seat_model_factory: SeatModelFactory | None = None,
        model_config: ModelConfig | None = None,
        availability: dict[str, Availability] | None = None,
    ) -> None:
        self.settings = settings
        self.seat_model_factory = seat_model_factory
        self._model_config = model_config
        self._availability = availability
        self.overrides: dict[str, str] = {}
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

    @property
    def availability(self) -> dict[str, Availability]:
        """Provider availability, checked once and cached (S5 research D2). Tests inject it.
        In Cloud mode local models are not offered, so Ollama is unavailable by the mode, not by a probe
        (S7 research D7); every consumer of availability follows."""
        if self._availability is None:
            if self.settings.run_mode == "cloud":
                cloud_only = {k: v for k, v in self.model_config.providers.items() if k != "ollama"}
                checked = check_availability(dataclasses.replace(self.model_config, providers=cloud_only))
            else:
                checked = check_availability(self.model_config)
            self._availability = checked
        if self.settings.run_mode == "cloud":
            self._availability["ollama"] = Availability("ollama", False, CLOUD_MODE_REASON)
        return self._availability

    def effective_config(self) -> ModelConfig:
        """The models configuration with every in-memory seat swap applied. The file is never written."""
        config = self.model_config
        for seat, key in self.overrides.items():
            config = config.with_seat(seat, key)
        return config

    def seat_model_object(self, seat: str, config: ModelConfig | None = None) -> Model | None:
        """The model a seat is on right now, or None when the configuration has no entry for it."""
        config = config or self.effective_config()
        if seat in config.seats:
            return config.seat_spec(seat).model_object()
        return None

    def roster_with_config(
        self, roster: dict[str, Agent], config: ModelConfig | None = None
    ) -> dict[str, Agent]:
        """A roster whose model labels are the effective configuration's, not the code defaults (constitution V)."""
        config = config or self.effective_config()
        updated: dict[str, Agent] = {}
        for seat, agent in roster.items():
            model = self.seat_model_object(seat, config)
            updated[seat] = agent.model_copy(update={"model": model}) if model is not None else agent
        return updated

    def idle_roster(self) -> dict[str, Agent]:
        """The roster shown before a run starts, with the export's names and the live models."""
        return self.roster_with_config(build_roster(self.settings.workflow, names=EXPORT_NAMES))

    def family_warning(self, config: ModelConfig | None = None) -> str:
        config = config or self.effective_config()
        if "reviewer" not in config.seats or "writer" not in config.seats:
            return ""
        if family_of(config.seat_spec("reviewer")) == family_of(config.seat_spec("writer")):
            return SHARED_FAMILY_WARNING
        return ""

    def model_options(self) -> list[dict[str, Any]]:
        """Every model in the registry with its availability as a boolean and a reason, never a credential."""
        config = self.model_config
        options: list[dict[str, Any]] = []
        for key, spec in config.models.items():
            state = self.availability.get(spec.provider)
            available = bool(state and state.available)
            provider_label = str(config.providers.get(spec.provider, {}).get("label", spec.provider))
            if available:
                reason = ""
                note = f"{provider_label}, detected" if spec.provider == "ollama" else provider_label
            elif spec.provider == "ollama" and self.settings.run_mode == "cloud":
                reason = note = CLOUD_MODE_REASON
            elif spec.provider == "ollama":
                reason = note = "Ollama not detected at startup"
            else:
                reason = note = "no credentials in .env"
            options.append(
                {
                    "key": key,
                    "label": spec.label,
                    "provider": spec.provider,
                    "provider_label": provider_label,
                    "available": available,
                    "reason": reason,
                    "note": note,
                }
            )
        return options

    def seat_table(self) -> dict[str, Any]:
        """The Settings page: one row per seat with its live card, effective model key, note, and warning."""
        config = self.effective_config()
        names = {seat: agent.name for seat, agent in self.live.roster.items()} if self.live else EXPORT_NAMES
        warning = self.family_warning(config)
        rows: list[dict[str, Any]] = []
        for seat in SEATS:
            if seat.agent_id == "single":
                continue
            name = names.get(seat.agent_id) or EXPORT_NAMES.get(seat.agent_id) or seat.names[0]
            model = self.seat_model_object(seat.agent_id, config) or seat.default_model
            rows.append(
                {
                    "seat": seat.agent_id,
                    "card": Agent(
                        agent_id=seat.agent_id, name=name, role=seat.role, model=model
                    ).model_dump(),
                    "model_key": config.seats[seat.agent_id].model if seat.agent_id in config.seats else None,
                    "dependency": DEPENDENCY_NOTES.get(seat.agent_id, ""),
                    "warning": warning if seat.agent_id == "reviewer" else "",
                }
            )
        return {"seats": rows, "models": self.model_options(), "note": "Changes apply at the next stage."}

    def set_seat_model(self, seat: str, model_key: str) -> SeatSwap:
        """Move a seat to another model in memory. Unknown keys and seats raise ValueError; a model whose
        provider is not available raises LiveUnavailable. The caller emits model.changed into a live run."""
        if seat not in {s.agent_id for s in SEATS}:
            raise ValueError(f"unknown seat {seat}")
        config = self.model_config
        if model_key not in config.models:
            raise ValueError(f"unknown model {model_key}")
        spec = config.models[model_key]
        state = self.availability.get(spec.provider)
        if state is None or not state.available:
            reason = state.reason if state else "provider not configured"
            raise LiveUnavailable([f"{spec.label}: {reason}"])
        self.overrides[seat] = model_key
        applied = "next-dispatch" if self.is_live() else "next-run"
        return SeatSwap(seat=seat, model=spec.model_object(), warning=self.family_warning(), applied=applied)

    def mode_for(self, dataset_id: str) -> str:
        if self.settings.agent_mode == "stub":
            return "stub"
        return "live" if DatasetFiles(self.dataset(dataset_id).folder).is_curated() else "stub"

    def provider_report(self) -> dict[str, Any]:
        config = self.effective_config()
        availability = self.availability
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
        mode: str = "team",
        model_key: str | None = None,
    ) -> Orchestrator:
        if mode == "single":
            return self._build_single(
                dataset_id,
                names=names,
                seed=seed,
                start=start,
                pace=pace,
                record=record,
                run_id=run_id,
                clock=clock,
                id_factory=id_factory,
                model_key=model_key,
            )
        info = self.dataset(dataset_id)
        missing = [name for name, version in tools_available().items() if version is None]
        if missing:
            # Every run compiles its drafts (spec FR-014, FR-016), so a missing tool stops it here.
            raise LiveUnavailable([f"compiler missing ({name})" for name in missing])
        rid = run_id or str(uuid.uuid4())
        roster = self.roster_with_config(build_roster(self.settings.workflow, seed=seed, names=names))
        recorder = Recorder(self.settings.runs_dir, rid) if record else None
        knowledge_path = (
            recorder.knowledge_path
            if recorder
            else self.settings.runs_dir / "_ephemeral" / rid / "knowledge.md"
        )
        scenario: Any
        knowledge_store: KnowledgeStore | None = None
        run_folder = recorder.folder if recorder else knowledge_path.parent
        if self.mode_for(dataset_id) == "live":
            config = self.effective_config()
            if self.seat_model_factory is None:
                problems = unavailable_seats(config, self.availability)
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
                dataset_id=info.id,
                label=info.display,
                client_id=info.client_id,
                knowledge_seed=info.knowledge_seed,
                folder=info.folder,
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

    def _build_single(
        self,
        dataset_id: str,
        *,
        names: dict[str, str] | None,
        seed: int | None,
        start: dt.datetime | None,
        pace: float | None,
        record: bool,
        run_id: str | None,
        clock: Clock | None,
        id_factory: Callable[[int], str] | None,
        model_key: str | None,
    ) -> Orchestrator:
        """A Single-model run (S5): one actor on the chosen model, the Orchestrator's effective model by default."""
        info = self.dataset(dataset_id)
        rid = run_id or str(uuid.uuid4())
        base = self.effective_config()
        key = model_key or (base.seats["orchestrator"].model if "orchestrator" in base.seats else None)
        if key is None:
            raise ValueError("no model chosen for the Single-model run")
        config = base.with_seat("single", key)
        agent = single_agent(self.settings.workflow, seed=seed, name=(names or {}).get("single"))
        team_roster = self.roster_with_config(
            build_roster(self.settings.workflow, seed=seed, names=names), config
        )
        agent = agent.model_copy(update={"model": config.seat_spec("single").model_object()})
        recorder = Recorder(self.settings.runs_dir, rid) if record else None
        knowledge_path = (
            recorder.knowledge_path
            if recorder
            else self.settings.runs_dir / "_ephemeral" / rid / "knowledge.md"
        )
        run_folder = recorder.folder if recorder else knowledge_path.parent
        scenario: Any
        knowledge_store: KnowledgeStore | None = None
        if self.mode_for(dataset_id) == "live":
            if self.seat_model_factory is None:
                problems = [p for p in unavailable_seats(config, self.availability) if p.startswith("single")]
                if problems:
                    raise LiveUnavailable(problems)
            factory = self.seat_model_factory or (lambda seat: strands_model_for(config, seat))
            seat_model = factory("single")
            agent = agent.model_copy(update={"model": seat_model.model})
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
                seat_models={"single": seat_model},
                knowledge_seed=info.knowledge_seed,
            )
            clock = clock or Clock(start or dt.datetime.now(dt.UTC), 1.0)
        else:
            scenario = StubSingleSource(info.id, info.client_id)
            clock = clock or Clock(start or dt.datetime.now(dt.UTC), pace or self.settings.stub_pace)
        return Orchestrator(
            run_id=rid,
            workflow=self.settings.workflow,
            dataset=DatasetRef(
                dataset_id=info.id,
                label=info.display,
                client_id=info.client_id,
                knowledge_seed=info.knowledge_seed,
            ),
            scenario=scenario,
            # The Orchestrator seat is the run engine's voice (stage changes, dispatch, termination) in every mode.
            roster={"orchestrator": team_roster["orchestrator"], "single": agent},
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
            mode="single",
        )

    def start_run(
        self,
        dataset_id: str,
        names: dict[str, str] | None = None,
        *,
        dry_intake: bool = False,
        mode: str = "team",
        model_key: str | None = None,
    ) -> Orchestrator:
        import asyncio

        if self.is_live():
            raise RuntimeError("a run is already in progress")
        orchestrator = self.build_orchestrator(dataset_id, names=names, mode=mode, model_key=model_key)
        if dry_intake and mode == "team":
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

    def events_for(self, run_id: str) -> list[Event]:
        """Every event of a run that is not live: its recording, else the golden log with that run id."""
        recorded = self.read_recording(run_id)
        if recorded is not None:
            return recorded
        for info in self.datasets.values():
            if not info.golden_path.exists():
                continue
            first = info.golden_path.read_text(encoding="utf-8").splitlines()[0]
            if Event.from_line(first).run_id == run_id:
                return read_events(info.golden_path)
        return []

    def golden_folder(self, run_id: str) -> Path | None:
        """The folder holding a golden run's compiled artifacts (`datasets/<id>/golden-artifacts/`),
        when `run_id` is the run id a dataset's golden log carries. Golden logs name page images
        relative to a run folder that never existed under `runs/`, so Replay reads them from here."""
        for info in self.datasets.values():
            if not info.golden_path.exists():
                continue
            first = info.golden_path.read_text(encoding="utf-8").splitlines()[0]
            if Event.from_line(first).run_id == run_id:
                return info.folder / "golden-artifacts"
        return None
