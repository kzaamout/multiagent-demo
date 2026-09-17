from __future__ import annotations

import datetime as dt
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agents.base import HumanScript, StubScenario  # noqa: E402
from app.config import Settings  # noqa: E402
from app.orchestrator.clock import Clock, VirtualClock  # noqa: E402
from app.orchestrator.driver import drive  # noqa: E402
from app.orchestrator.orchestrator import DatasetRef, Orchestrator  # noqa: E402
from app.orchestrator.roster import EXPORT_NAMES, build_roster  # noqa: E402
from app.runs.bus import StreamBus  # noqa: E402
from app.runs.recorder import Recorder  # noqa: E402
from app.schema.events import Event  # noqa: E402

START = dt.datetime(2026, 9, 14, 9, 12, 0, tzinfo=dt.UTC)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "dataset: needs the scenario datasets, which are local assets and not published"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Datasets are not committed (see .gitignore). Without them these tests cannot run, so they skip
    rather than fail, and a checkout with the datasets in place runs everything as before."""
    folder = ROOT / "datasets"
    if folder.is_dir() and any(p.is_dir() for p in folder.iterdir()):
        return
    skip = pytest.mark.skip(reason="no datasets in this checkout; see datasets/README.md")
    for item in items:
        if "dataset" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _never_call_real_model_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing the app loads the real .env, and a curated dataset runs live. A test that reaches the
    registry's real model factory would spend money, so it fails instead; live tests inject a scripted factory."""

    def refuse(*_: object, **__: object) -> None:
        raise AssertionError(
            "a test tried to build a real provider model; inject a scripted seat_model_factory"
        )

    monkeypatch.setattr("app.runs.registry.strands_model_for", refuse)


@pytest.fixture
def settings(tmp_path: Path) -> Iterator[Settings]:
    yield Settings(runs_dir=tmp_path / "runs", stub_pace=1000.0, agent_mode="stub")


def make_orchestrator(
    scenario: StubScenario,
    settings: Settings,
    *,
    clock: Clock | None = None,
    record: bool = False,
    bus: StreamBus | None = None,
    run_id: str = "00000000-0000-4000-8000-000000000001",
) -> Orchestrator:
    recorder = Recorder(settings.runs_dir, run_id) if record else None
    return Orchestrator(
        run_id=run_id,
        workflow="electrical_rfp",
        dataset=DatasetRef(
            dataset_id=scenario.dataset_id, label=scenario.dataset_id, client_id=scenario.client_id
        ),
        scenario=scenario,
        roster=build_roster("electrical_rfp", names=EXPORT_NAMES),
        review_max_cycles=settings.review_max_cycles,
        cost_ceiling=settings.cost_ceiling,
        clock=clock or VirtualClock(START),
        bus=bus or StreamBus(),
        recorder=recorder,
        knowledge_path=settings.runs_dir / run_id / "knowledge.md",
        event_log_path=f"runs/{run_id}/events.jsonl",
    )


async def run_scenario(
    scenario: StubScenario, settings: Settings, script: HumanScript | None = None, **kwargs: object
) -> list[Event]:
    orchestrator = make_orchestrator(scenario, settings, **kwargs)  # type: ignore[arg-type]
    await drive(orchestrator, script or scenario.human_script)
    return orchestrator.events
