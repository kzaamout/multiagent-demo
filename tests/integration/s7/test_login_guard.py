"""The shared login guards Demo, Settings, Pre-flight, and the API; the S6 public list stays open
(spec 2.8, roadmap S7 evidence, S7 research D5 and D6)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

from app.auth import COOKIE, ERROR_LINE
from app.config import Settings
from app.main import create_app

PINNED = "f2dda488-0a2f-457a-9ef1-33fcac05fa70"


@dataclass(frozen=True)
class Pinned(Settings):
    public_run_id: str = PINNED


def guarded(tmp_path: Path) -> Settings:
    return Pinned(
        runs_dir=tmp_path / "runs", agent_mode="stub", demo_username="presenter", demo_password="open sesame"
    )


async def make_client(settings: Settings) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=create_app(settings))
    return httpx.AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    async with await make_client(guarded(tmp_path)) as c:
        yield c


async def test_pages_redirect_to_the_login_with_their_path(client: httpx.AsyncClient) -> None:
    for path in ("/demo", "/settings", "/preflight", "/demo?dataset=clean-run"):
        response = await client.get(path)
        assert response.status_code == 303, path
        assert response.headers["location"].startswith("/login?next="), path
    response = await client.get("/")
    assert response.status_code == 303 and response.headers["location"] == "/login?next=%2F"


async def test_api_refuses_without_a_session(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/meta")
    assert response.status_code == 401 and response.json() == {"error": "sign in required"}
    response = await client.post("/api/runs", json={"dataset_id": "clean-run"})
    assert response.status_code == 401
    response = await client.get("/api/preflight")
    assert response.status_code == 401


async def test_public_routes_are_not_guarded(client: httpx.AsyncClient) -> None:
    assert (await client.get("/login")).status_code == 200
    assert (await client.get("/static/css/app.css")).status_code == 200
    # The S6 routes do not exist on this branch yet; the guard must still leave them alone.
    for path in ("/introduction", "/introduction.pdf", "/public/run/x/events"):
        response = await client.get(path)
        assert response.status_code not in (303, 401), path
    response = await client.get(f"/demo?public=1&run={PINNED}&speed=4")
    assert response.status_code == 200
    response = await client.get("/demo?public=1&run=another")
    assert response.status_code == 303


async def test_wrong_pair_shows_one_line_and_sets_nothing(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/login", data={"username": "presenter", "password": "wrong", "next": "/settings"}
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login?error=1&next=%2Fsettings"
    assert "set-cookie" not in response.headers
    page = await client.get(response.headers["location"])
    assert ERROR_LINE in page.text
    assert "wrong" not in page.text and "presenter" not in page.text
    assert 'name="next" value="/settings"' in page.text
    clean = await client.get("/login")
    assert ERROR_LINE not in clean.text


async def test_right_pair_admits_the_three_pages(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/login", data={"username": "presenter", "password": "open sesame", "next": "/settings"}
    )
    assert response.status_code == 303 and response.headers["location"] == "/settings"
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE}=") and "HttpOnly" in cookie and "SameSite=lax" in cookie
    for path in ("/demo", "/settings", "/preflight", "/api/meta"):
        assert (await client.get(path)).status_code == 200, path


async def test_next_off_site_lands_on_demo(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/login", data={"username": "presenter", "password": "open sesame", "next": "https://evil.example/"}
    )
    assert response.status_code == 303 and response.headers["location"] == "/demo"


async def test_sessions_end_with_the_process(tmp_path: Path) -> None:
    settings = guarded(tmp_path)
    async with await make_client(settings) as first:
        response = await first.post("/login", data={"username": "presenter", "password": "open sesame"})
        token = response.cookies[COOKIE]
    async with await make_client(settings) as second:
        second.cookies.set(COOKIE, token)
        assert (await second.get("/demo")).status_code == 303


async def test_without_credentials_nothing_is_guarded(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", agent_mode="stub")
    async with await make_client(settings) as client:
        assert (await client.get("/demo")).status_code == 200
        assert (await client.get("/api/meta")).status_code == 200
        response = await client.post("/login", data={"username": "x", "password": "y"})
        assert response.status_code == 303 and response.headers["location"] == "/demo"
