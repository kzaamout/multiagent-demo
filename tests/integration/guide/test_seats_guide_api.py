"""The seat model guide travels with GET /api/seats (spec 014, contracts/seats-guide.md section 2)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.config import Settings
from app.live.providers import Availability, ModelConfig
from app.main import create_app
from tests.unit.guide.support import seed

AVAILABLE = {
    name: Availability(name, True, "available in the test") for name in ("bedrock", "google", "xai", "ollama")
}


def build(runs_dir: Path) -> Any:
    return create_app(
        Settings(runs_dir=runs_dir, agent_mode="stub"),
        model_config=ModelConfig.load(),
        availability=AVAILABLE,
    )


@pytest.fixture
def runs_dir(tmp_path: Path) -> Path:
    runs = tmp_path / "runs"
    seed(runs, "pricing", "qwen3.5 9b, local", 6, 226, 212)
    seed(runs, "pricing", "gemma4 12b, local", 5, 5, 5)
    seed(runs, "estimator", "claude-sonnet-5 via Bedrock", 5, 31, 29, provider="bedrock")
    seed(runs, "writer", "gemma4 12b, local", 2, 12, 0)
    return runs


@pytest.fixture
async def client(runs_dir: Path) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=build(runs_dir)), base_url="http://test"
    ) as c:
        yield c


def rows(table: dict[str, Any]) -> dict[str, Any]:
    return {row["seat"]: row for row in table["seats"]}


async def test_each_seat_row_carries_its_picks_and_its_current_figure(client: httpx.AsyncClient) -> None:
    table = (await client.get("/api/seats")).json()
    assert {"seats", "models", "note", "guide"} <= set(table)
    assert table["guide"] == {"runs": 18, "min_runs": 5}
    seats = rows(table)
    assert list(seats) == [
        "orchestrator",
        "intake",
        "estimator",
        "pricing",
        "writer",
        "reviewer",
        "case",
        "market",
    ]
    assert seats["case"]["guide"] is None and seats["market"]["guide"] is None, (
        "appraisal seats: no guide yet"
    )
    assert seats["pricing"]["guide"]["open"] == {
        "status": "pick",
        "model_key": "qwen3-5-9b",
        "model": "qwen3.5 9b, local",
        "runs": 6,
        "replies": 226,
        "first_time": 212,
        "percent": 94,
    }
    assert seats["pricing"]["guide"]["current"]["percent"] == 94, "the pricing seat is on qwen3.5 9b"
    assert seats["pricing"]["guide"]["proprietary"] == {"status": "no_runs"}
    estimator = seats["estimator"]["guide"]["proprietary"]
    assert (estimator["model_key"], estimator["percent"], estimator["first_time"], estimator["replies"]) == (
        "bedrock-sonnet-5",
        94,
        29,
        31,
    )
    assert seats["writer"]["guide"]["current"] is None, "qwen3.5 9b has no writer replies here"


async def test_a_swap_moves_the_current_figure_to_the_new_model(client: httpx.AsyncClient) -> None:
    moved = await client.post("/api/seats/writer", json={"model": "gemma4-12b"})
    assert moved.status_code == 200
    writer = rows((await client.get("/api/seats")).json())["writer"]
    assert writer["card"]["model"]["label"] == "gemma4 12b, local"
    assert writer["guide"]["current"] == {
        "model": "gemma4 12b, local",
        "runs": 2,
        "replies": 12,
        "first_time": 0,
        "percent": 0,
    }
    assert writer["guide"]["open"] == {"status": "too_few_runs"}, "2 runs is fewer than 5"


async def test_an_empty_runs_folder_says_no_runs_everywhere(tmp_path: Path) -> None:
    app = build(tmp_path / "nothing-here")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        table = (await c.get("/api/seats")).json()
    assert table["guide"] == {"runs": 0, "min_runs": 5}
    for row in table["seats"]:
        if row["seat"] in ("case", "market"):
            continue
        assert row["guide"] == {
            "current": None,
            "open": {"status": "no_runs"},
            "proprietary": {"status": "no_runs"},
        }


async def test_thin_records_never_win_and_empty_slots_say_why(tmp_path: Path) -> None:
    """US2 (SC-003), with run counts scaled down from the spec's example and reply counts kept."""
    runs = tmp_path / "runs"
    seed(runs, "orchestrator", "gemma4 12b, local", 8, 13, 13)
    seed(runs, "orchestrator", "qwen3.5 9b, local", 12, 397, 390)
    seed(runs, "intake", "claude-sonnet-5 via Bedrock", 4, 10, 10, provider="bedrock")
    seed(runs, "reviewer", "llama3.1 8b, local", 6, 20, 20)  # text only: never the Reviewer
    seed(runs, "reviewer", "gemma4 12b, local", 6, 20, 18)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build(runs)), base_url="http://test") as c:
        seats = rows((await c.get("/api/seats")).json())
    orchestrator = seats["orchestrator"]["guide"]["open"]
    assert (orchestrator["model"], orchestrator["percent"]) == ("qwen3.5 9b, local", 98)
    assert seats["intake"]["guide"]["proprietary"] == {"status": "too_few_runs"}
    assert seats["pricing"]["guide"]["proprietary"] == {"status": "no_runs"}
    assert seats["reviewer"]["guide"]["open"]["model"] == "gemma4 12b, local"
    named = [
        row["guide"][kind]["model"]
        for row in seats.values()
        if row["guide"]
        for kind in ("open", "proprietary")
        if row["guide"][kind]["status"] == "pick"
    ]
    assert "llama3.1 8b, local" not in named and all(m != "claude-sonnet-5 via Bedrock" for m in named)


class _Running:
    """Stands in for the Orchestrator of a run in progress: the registry reads its run id and state."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.roster: dict[str, Any] = {}
        self.state = type("State", (), {"terminated": False})()


async def test_the_run_this_app_is_running_waits_until_it_ends(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    seed(runs, "pricing", "qwen3.5 9b, local", 5, 10, 10)
    live = seed(runs, "pricing", "qwen3.5 9b, local", 1, 50, 0, prefix="live")[0]
    app = build(runs)
    running = _Running(live.name)
    app.state.registry.live = running
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        during = (await c.get("/api/seats")).json()
        running.state.terminated = True
        after = (await c.get("/api/seats")).json()
    assert during["guide"]["runs"] == 5 and rows(during)["pricing"]["guide"]["current"]["replies"] == 10
    assert after["guide"]["runs"] == 6 and rows(after)["pricing"]["guide"]["current"]["replies"] == 60
