"""The Introduction page in Chromium: sections, cards, and the read-only replay frame (S6 US1 to US4)."""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import uvicorn

from app.agents.stubs import planted_inconsistency
from app.config import Settings
from app.main import create_app
from tests.conftest import run_scenario

pytestmark = [pytest.mark.visual, pytest.mark.dataset, pytest.mark.compiler]

PINNED = "00000000-0000-4000-8000-0000000000cc"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[str, Path]]:
    import asyncio

    runs = tmp_path_factory.mktemp("runs")
    settings = Settings(runs_dir=runs, stub_pace=1000.0, agent_mode="stub", public_run_id=PINNED)
    asyncio.run(run_scenario(planted_inconsistency.SCENARIO, settings, record=True, run_id=PINNED))
    port = free_port()
    app = create_app(settings)
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not srv.started and time.time() < deadline:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}", runs
    srv.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def page(server: tuple[str, Path]) -> Iterator[Any]:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as error:  # noqa: BLE001
            pytest.skip(f"Chromium not installed: {error}")
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        pg = context.new_page()
        errors: list[str] = []
        pg.on("pageerror", lambda exc: errors.append(str(exc)))
        pg.errors = errors
        requests: list[str] = []
        pg.on("request", lambda req: requests.append(req.url))
        pg.requests = requests
        yield pg
        browser.close()


def test_sections_diagrams_and_team_cards(page: Any, server: tuple[str, Path]) -> None:
    base, _ = server
    page.goto(base + "/introduction")
    ids = page.evaluate("() => Array.from(document.querySelectorAll('section.intro-section')).map(s => s.id)")
    assert ids == ["what-it-is", "architecture", "agentic-loop", "the-team", "how-agents-differ", "aws", "faq", "replay"]
    assert page.locator("figure[data-part='diagram'] svg").count() == 3
    assert page.locator("[data-part='team-card']").count() == 8
    card = page.locator("[data-part='team-card'][data-agent='reviewer']")
    assert card.locator("[data-part='team-card-detail']").is_hidden()
    card.click()
    assert card.locator("[data-part='team-card-detail']").is_visible()
    assert "none, on purpose" in card.inner_text()
    card.click()
    assert card.locator("[data-part='team-card-detail']").is_hidden()
    labels = page.evaluate(
        "() => Array.from(document.querySelectorAll('[data-part=\"team-card\"]')).slice(0, 6)"
        ".map(c => [c.getAttribute('data-agent'), c.querySelector('[data-part=\"model\"]').textContent])"
    )
    seats = page.evaluate("() => fetch('/api/seats').then(r => r.json())")
    by_seat = {row["seat"]: row["card"]["model"]["label"] for row in seats["seats"]}
    assert labels == [[seat, by_seat[seat]] for seat, _ in labels]
    assert page.errors == []


def test_replay_frame_plays_the_pinned_run_with_pages_and_no_controls(page: Any, server: tuple[str, Path]) -> None:
    base, _ = server
    page.goto(base + "/introduction")
    frame_el = page.locator("#replay-iframe")
    assert frame_el.count() == 1
    assert "dataset planted-inconsistency" in page.inner_text(".replay-caption")
    page.click(".replay-speed[data-speed='4']")
    page.wait_for_function("() => document.getElementById('replay-iframe').getAttribute('src').includes('speed=4')")
    frame = page.frame_locator("#replay-iframe")
    frame.locator("article.card").first.wait_for(timeout=60000)
    page.wait_for_function(
        "() => { const f = document.getElementById('replay-iframe').contentWindow; return f.__s1 && f.__s1.events.length && f.__s1.events[f.__s1.events.length - 1].type === 'run.terminated'; }",
        timeout=180000,
    )
    inner = frame_el.content_frame if hasattr(frame_el, "content_frame") else None
    hidden = page.evaluate(
        "() => { const d = document.getElementById('replay-iframe').contentDocument;"
        " const gone = ['.composer', '#handoff-actions', '.compare', '#chat-panel', '#banner'];"
        " return gone.map(s => { const n = d.querySelector(s); return !n || n.offsetParent === null; }); }"
    )
    assert all(hidden), hidden
    assert page.evaluate(
        "() => { const d = document.getElementById('replay-iframe').contentDocument;"
        " return Array.from(d.querySelectorAll('.hdr .nav a')).every(a => a.offsetParent === null); }"
    )
    assert page.evaluate("() => document.getElementById('replay-iframe').contentDocument.querySelectorAll('figure.page-figure').length") >= 2
    assert page.evaluate("() => document.getElementById('replay-iframe').contentDocument.querySelectorAll('.node[data-state=\"complete\"]').length") == 6
    private = [u for u in page.requests if "/api/runs/" in u or "/api/replays" in u or "/api/streams/" in u]
    assert not private, private
    run_requests = [u for u in page.requests if ("/files/" in u or u.endswith("/events")) and "/static/" not in u]
    assert run_requests and all("/public/run/" in u for u in run_requests), run_requests
    assert page.errors == []
    del inner


def test_public_routes_refuse_another_run(page: Any, server: tuple[str, Path]) -> None:
    base, _ = server
    status = page.evaluate("(u) => fetch(u).then(r => r.status)", base + "/public/run/00000000-0000-4000-8000-0000000000dd/events")
    assert status == 404
