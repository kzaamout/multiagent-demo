"""Presenter controls through the Demo page on stubbed runs: Pause, Resume, Stop, Dry intake, and the
cost ceiling card (S3). Run with: uv run pytest -m visual"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import uvicorn

from app.config import Settings
from app.main import create_app

pytestmark = pytest.mark.visual


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def serve(settings: Settings) -> Iterator[str]:
    port = free_port()
    srv = uvicorn.Server(
        uvicorn.Config(create_app(settings), host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not srv.started and time.time() < deadline:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    runs: Path = tmp_path_factory.mktemp("runs")
    yield from serve(Settings(runs_dir=runs, stub_pace=12.0, agent_mode="stub"))


@pytest.fixture(scope="module")
def low_ceiling_server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    runs: Path = tmp_path_factory.mktemp("runs-ceiling")
    yield from serve(Settings(runs_dir=runs, stub_pace=60.0, agent_mode="stub", cost_ceiling=0.05))


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        try:
            chromium = p.chromium.launch()
        except Exception as error:  # noqa: BLE001
            pytest.skip(f"Chromium not installed: {error}")
        yield chromium
        chromium.close()


def open_page(browser: Any, url: str) -> Any:
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.errors = errors
    page.goto(url)
    page.wait_for_selector("#dataset-value:not(:has-text('Loading'))")
    return page


def choose_dataset(page: Any, label: str) -> None:
    page.click("#dataset-select")
    page.click(f"#dataset-menu .menu-item:has-text('{label}')")


def has_event(page: Any, type_: str) -> str:
    return f"() => window.__s1 && window.__s1.events.some(e => e.type === '{type_}')"


def test_pause_resume_and_stop_from_the_composer(browser: Any, server: str) -> None:
    page = open_page(browser, server + "/demo")
    assert page.is_disabled("#btn-pause") and page.is_disabled("#btn-stop"), "idle: controls disabled"
    choose_dataset(page, "04 · Missing price")
    page.click("#btn-run")
    page.wait_for_function(has_event(page, "task.dispatched"), timeout=30000)
    page.wait_for_selector("#btn-pause:not([disabled])")
    page.click("#btn-pause")
    page.wait_for_function(has_event(page, "run.paused"), timeout=10000)
    page.wait_for_selector("#btn-pause:has-text('Resume')")
    assert page.locator('.node[data-state="paused"]').count() == 1
    page.click("#btn-pause")
    page.wait_for_function(has_event(page, "run.resumed"), timeout=10000)
    page.wait_for_selector("#btn-pause:has-text('Pause')")
    page.click("#btn-stop")
    page.wait_for_selector("article[data-kind='termination'][data-exit='stopped']", timeout=10000)
    assert "stopped the run" in page.inner_text("article[data-kind='termination']")
    page.wait_for_selector("#btn-stop[disabled]")
    assert page.is_disabled("#btn-pause")
    assert not page.is_disabled("#dry-on"), "ended: Dry intake available again"
    assert page.errors == []
    page.context.close()


def test_dry_intake_toggle_ends_after_intake(browser: Any, server: str) -> None:
    page = open_page(browser, server + "/demo")
    choose_dataset(page, "01 · Clean run")
    page.click("#dry-on")
    page.wait_for_selector("#dry-on[aria-pressed='true']")
    page.click("#btn-run")
    page.wait_for_selector("#dry-on[disabled]")
    page.wait_for_selector("article[data-kind='termination'][data-exit='dry_intake']", timeout=60000)
    card = page.inner_text("article[data-kind='termination']")
    assert "Readiness verdict" in card
    assert page.locator("article[data-kind='specialist-thread']").count() == 0
    assert page.errors == []
    page.context.close()


def test_cost_ceiling_card_shows_the_spend(browser: Any, low_ceiling_server: str) -> None:
    page = open_page(browser, low_ceiling_server + "/demo")
    choose_dataset(page, "01 · Clean run")
    page.click("#btn-run")
    page.wait_for_selector("article[data-kind='termination'][data-exit='cost_ceiling']", timeout=60000)
    card = page.inner_text("article[data-kind='termination']")
    assert "Estimated spend:" in card and "against a ceiling of $0.05" in card
    assert page.errors == []
    page.context.close()
