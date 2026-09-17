"""The pre-flight routes and the header dot on every page, with scripted checks (S7 research D1, D2)."""

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
from app.preflight.result import FAIL, PASS, CheckResult, build_result, save_result

MARKER = "zq9-secret-marker-7f3a"
FIXTURES = ROOT / "tests" / "fixtures"


def scripted(settings: Settings) -> CheckContext:
    """A context with no providers; the checks themselves are monkeypatched in `app_with`."""
    return CheckContext(
        settings=settings, config=ModelConfig(providers={}, models={}, seats={}), availability={}
    )


def passing(check_id: str, name: str, essential: bool = True) -> Check:
    async def run(_: CheckContext) -> CheckResult:
        return CheckResult(check_id, name, PASS, "fine", essential, 1)

    return Check(check_id, name, essential, 1.0, run)


def settings_for(tmp_path: Path, **extra: Any) -> Settings:
    return Settings(runs_dir=tmp_path / "runs", agent_mode="stub", **extra)


def app_with(settings: Settings, checks: list[Check], monkeypatch: pytest.MonkeyPatch) -> httpx.AsyncClient:
    monkeypatch.setattr("app.preflight.runner.checks_for", lambda _ctx: checks)
    availability = {
        "bedrock": Availability("bedrock", True, "credentials resolved"),
        "google": Availability("google", True, "key present"),
        "xai": Availability("xai", False, "no credentials in .env"),
        "ollama": Availability("ollama", True, "reachable, models present"),
    }
    app = create_app(settings, availability=availability, preflight_context=lambda: scripted(settings))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[httpx.AsyncClient]:
    checks = [
        passing("disk", "Disk space"),
        passing("tunnel", "Tunnel reachable from outside", essential=False),
    ]
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
    assert body["status"] == "pending" and body["ran_at"] is None and body["running"] is False
    assert [c["name"] for c in body["checks"]] == ["Disk space", "Tunnel reachable from outside"]
    assert {c["detail"] for c in body["checks"]} == {"Pending"}
    for path in ("/demo", "/settings", "/preflight"):
        assert dot((await client.get(path)).text) == ("pending", "○", "Pre-flight: not run yet"), path
    assert (await client.get("/api/meta")).json()["preflight"] == "pending"


async def test_run_stores_the_result_and_turns_every_dot_green(
    client: httpx.AsyncClient, tmp_path: Path
) -> None:
    body = (await client.post("/api/preflight/run")).json()
    assert (
        body["status"] == "pass"
        and body["passed"] == 2
        and body["applicable"] == 2
        and body["running"] is False
    )
    stored = json.loads((tmp_path / "runs" / "preflight.json").read_text(encoding="utf-8"))
    assert stored["schema"] == 1 and stored["status"] == "pass"
    again = (await client.get("/api/preflight")).json()
    assert again["status"] == "pass" and again["stamp"] == body["stamp"]
    for path in ("/demo", "/settings", "/preflight"):
        status, glyph, title = dot((await client.get(path)).text)
        assert (status, glyph) == ("pass", "✓"), path
        assert title.startswith("Pre-flight: all checks pass, ")
    meta = (await client.get("/api/meta")).json()
    assert meta["preflight"] == "pass" and meta["run_mode"] == "laptop"


async def test_warn_and_fail_render_from_the_stored_file_alone(
    client: httpx.AsyncClient, tmp_path: Path
) -> None:
    runs = tmp_path / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / "preflight-one-fail.json", runs / "preflight.json")
    status, glyph, title = dot((await client.get("/demo")).text)
    assert (status, glyph) == ("warn", "!")
    assert title == "Pre-flight: Tunnel reachable from outside failed (non-essential), 14 Sep 2026, 08:12"
    body = (await client.get("/api/preflight")).json()
    assert body["status"] == "warn" and body["stamp"] == "14 Sep 2026, 08:12"
    save_result(
        runs,
        build_result(
            "laptop",
            "2026-09-14T08:12:00",
            [CheckResult("disk", "Disk space", FAIL, "Under 5 GB free (3.2 GB)", True, 1)],
        ),
    )
    status, glyph, title = dot((await client.get("/settings")).text)
    assert (status, glyph, title) == ("fail", "✕", "Pre-flight: Disk space failed, 14 Sep 2026, 08:12")
    assert (await client.get("/api/meta")).json()["preflight"] == "fail"


async def test_second_run_is_refused_while_one_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gate = asyncio.Event()

    async def waits(_: CheckContext) -> CheckResult:
        await gate.wait()
        return CheckResult("slow", "Slow", PASS, "done", True, 1)

    checks = [Check("slow", "Slow", True, 30.0, waits)]
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

    checks = [passing("disk", "Disk space"), Check("env", ".env completeness", True, 1.0, leaky)]
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
