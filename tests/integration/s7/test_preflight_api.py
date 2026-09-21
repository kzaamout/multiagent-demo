"""The pre-flight routes and the header dot on every page, with scripted checks (S7 research D1;
spec 012 research D8: the dot is worked out from the stored rows against the seats in force)."""

from __future__ import annotations

import asyncio
import json
import shutil
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.config import ROOT, Settings
from app.live.providers import Availability, ModelConfig
from app.main import create_app
from app.preflight.checks import Check, CheckContext
from app.preflight.result import FAIL, PASS, CheckResult, PreflightResult, save_result

MARKER = "zq9-secret-marker-7f3a"
FIXTURES = ROOT / "tests" / "fixtures"
# Seats: Writer and most seats on export-sonnet (Bedrock), Reviewer on export-gemini, Pricing on export-llama.
EXPORT_CONFIG = FIXTURES / "models-export.yaml"
SEAT_MODELS = ("export-sonnet", "export-gemini", "export-llama")


def scripted(settings: Settings) -> CheckContext:
    """A context whose checks are monkeypatched in `app_with`; the server sets its config."""
    return CheckContext(
        settings=settings, config=ModelConfig(providers={}, models={}, seats={}), availability={}
    )


def passing(check_id: str, name: str, subject: dict[str, Any] | None = None) -> Check:
    async def run(_: CheckContext) -> CheckResult:
        return CheckResult(
            check_id, name, PASS, "fine", 1, "2026-09-14T08:12:00", subject or {"kind": "fixed"}
        )

    return Check(check_id, name, 1.0, run, subject or {"kind": "fixed"})


def seat_rows() -> list[Check]:
    return [
        passing(f"model:{key}", f"{key} answers", {"kind": "model", "model_key": key, "provider": "p"})
        for key in SEAT_MODELS
    ]


def settings_for(tmp_path: Path, **extra: Any) -> Settings:
    return Settings(runs_dir=tmp_path / "runs", agent_mode="stub", **extra)


def app_with(settings: Settings, checks: list[Check], monkeypatch: pytest.MonkeyPatch) -> httpx.AsyncClient:
    monkeypatch.setattr("app.preflight.runner.checks_for", lambda _ctx: checks)
    monkeypatch.setattr("app.preflight.runner.cloud_model_checks", lambda _ctx: [])
    monkeypatch.setattr("app.preflight.runner.sequential_checks", lambda _ctx: checks)
    availability = {
        "bedrock": Availability("bedrock", True, "credentials resolved"),
        "google": Availability("google", True, "key present"),
        "xai": Availability("xai", False, "no credentials in .env"),
        "anthropic": Availability("anthropic", False, "no credentials in .env"),
        "ollama": Availability("ollama", True, "reachable, models present"),
    }
    app = create_app(
        settings,
        model_config=ModelConfig.load(EXPORT_CONFIG),
        availability=availability,
        preflight_context=lambda: scripted(settings),
    )
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[httpx.AsyncClient]:
    checks = [*seat_rows(), passing("disk", "Disk space"), passing("tunnel", "Tunnel reachable from outside")]
    async with app_with(settings_for(tmp_path), checks, monkeypatch) as c:
        yield c


def dot(html: str) -> tuple[str, str, str]:
    start = html.index('data-part="preflight-indicator"')
    fragment = html[start : html.index("</span>", start)]
    status = fragment.split('data-status="')[1].split('"')[0]
    title = fragment.split('title="')[1].split('"')[0]
    glyph = fragment.rsplit(">", 1)[1]
    return status, glyph, title


async def test_pending_shape_before_any_run(client: httpx.AsyncClient) -> None:
    body = (await client.get("/api/preflight")).json()
    assert body["header"]["status"] == "pending" and body["ran_at"] is None and body["running"] is False
    names = [c["name"] for c in body["checks"]]
    assert names[-3:] == [
        "Disk space",
        "Tunnel reachable from outside",
        "Reviewer and Writer on different model families",
    ]
    assert {c["detail"] for c in body["checks"][:-1]} == {"Pending"}
    for path in ("/demo", "/settings", "/preflight"):
        assert dot((await client.get(path)).text) == ("pending", "○", "Pre-flight: not run yet"), path
    assert (await client.get("/api/meta")).json()["preflight"] == "pending"


async def test_run_stores_the_result_and_turns_every_dot_green(
    client: httpx.AsyncClient, tmp_path: Path
) -> None:
    body = (await client.post("/api/preflight/run")).json()
    assert body["header"]["status"] == "pass"
    assert body["passed"] == body["applicable"] == 6 and body["running"] is False
    stored = json.loads((tmp_path / "runs" / "preflight.json").read_text(encoding="utf-8"))
    assert stored["schema"] == 2 and "status" not in stored
    again = (await client.get("/api/preflight")).json()
    assert again["header"]["status"] == "pass" and again["stamp"] == body["stamp"]
    for path in ("/demo", "/settings", "/preflight"):
        status, glyph, title = dot((await client.get(path)).text)
        assert (status, glyph) == ("pass", "✓"), path
        assert title.startswith("Pre-flight: all checks pass, ")
    meta = (await client.get("/api/meta")).json()
    assert meta["preflight"] == "pass" and meta["run_mode"] == "laptop"


async def test_amber_and_red_render_from_the_stored_file(client: httpx.AsyncClient, tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / "preflight-one-fail.json", runs / "preflight.json")
    status, glyph, title = dot((await client.get("/demo")).text)
    assert (status, glyph) == ("warn", "!")
    assert title == "Pre-flight: Tunnel not connected, 14 Sep 2026, 08:12"
    body = (await client.get("/api/preflight")).json()
    assert body["header"]["status"] == "warn" and body["stamp"] == "14 Sep 2026, 08:12"
    rows = [CheckResult(c.id, c.name, PASS, "fine", 1, "2026-09-14T08:12:00", c.subject) for c in seat_rows()]
    rows.append(CheckResult("disk", "Disk space", FAIL, "Under 5 GB free (3.2 GB)", 1, "2026-09-14T08:12:00"))
    save_result(runs, PreflightResult("laptop", "2026-09-14T08:12:00", tuple(rows)))
    status, glyph, title = dot((await client.get("/settings")).text)
    assert (status, glyph, title) == ("fail", "✕", "Pre-flight: Disk space failed, 14 Sep 2026, 08:12")
    assert (await client.get("/api/meta")).json()["preflight"] == "fail"


async def test_second_run_is_refused_while_one_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gate = asyncio.Event()

    async def waits(_: CheckContext) -> CheckResult:
        await gate.wait()
        return CheckResult("slow", "Slow", PASS, "done", 1)

    checks = [Check("slow", "Slow", 30.0, waits)]
    async with app_with(settings_for(tmp_path), checks, monkeypatch) as client:
        first = asyncio.create_task(client.post("/api/preflight/run"))
        await asyncio.sleep(0.05)
        assert (await client.get("/api/preflight")).json()["running"] is True
        second = await client.post("/api/preflight/run")
        assert second.status_code == 409 and second.json() == {"error": "a pre-flight is already running"}
        gate.set()
        assert (await first).status_code == 200


async def test_no_value_from_env_reaches_any_route_or_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", MARKER)
    settings = settings_for(tmp_path, demo_username="presenter", demo_password=MARKER)

    async def leaky(_: CheckContext) -> CheckResult:
        raise RuntimeError(MARKER)

    checks = [*seat_rows(), passing("disk", "Disk space"), Check("env", ".env completeness", 1.0, leaky)]
    async with app_with(settings, checks, monkeypatch) as client:
        login = await client.post("/login", data={"username": "presenter", "password": MARKER})
        assert login.status_code == 303
        run = await client.post("/api/preflight/run")
        assert run.status_code == 200 and MARKER not in run.text
        for path in ("/api/preflight", "/api/meta", "/api/seats", "/api/providers", "/preflight", "/demo"):
            response = await client.get(path)
            assert response.status_code == 200, path
            assert MARKER not in response.text, path
    assert MARKER not in (tmp_path / "runs" / "preflight.json").read_text(encoding="utf-8")
