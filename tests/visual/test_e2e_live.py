"""Browser check of a live-mode run with scripted seat models (S2 Part A, T027).
Run with: uv run pytest -m visual"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from typing import Any

import pytest
import uvicorn

from app.config import Settings
from app.main import create_app
from tests.integration.s2.test_providers_and_api import curated_datasets, scripted_factory

pytestmark = [pytest.mark.visual, pytest.mark.dataset]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def live_server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    tmp = tmp_path_factory.mktemp("live")
    settings = Settings(
        runs_dir=tmp / "runs", datasets_dir=curated_datasets(tmp), knowledge_dir=tmp / "knowledge"
    )
    app = create_app(settings, seat_model_factory=scripted_factory())
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


def test_live_run_shows_tools_banner_and_draft_text(live_server: str) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as error:  # noqa: BLE001
            pytest.skip(f"Chromium not installed: {error}")
        page: Any = browser.new_page(viewport={"width": 1920, "height": 1080})
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(live_server + "/demo?dataset=clean-run")
        page.wait_for_selector("#dataset-value:has-text('01')")
        page.click("#btn-run")

        page.wait_for_selector("#banner:not([hidden])", timeout=30000)
        assert page.input_value("#banner-questions input") == "120/208 V"
        intake = page.locator("article[data-kind='agent-message']").first
        intake.locator(".card-hd").click()
        page.wait_for_selector("article[data-kind='agent-message'] .tool-chip:has-text('document_parse_pdf')")
        assert page.locator("article[data-card^='thread:intake']").count() == 0, "no stray Intake thread card"
        page.click("#banner-resume")

        page.wait_for_selector("#btn-approve:not([disabled])", timeout=30000)
        page.wait_for_selector("#pages-scroll:not([hidden])", timeout=10000)
        page.wait_for_function("() => document.querySelector('img.page-img').naturalWidth > 0")
        assert page.locator("figure.page-figure").count() >= 1
        assert page.inner_text("#artifact-version").startswith("v1 ·")
        page.wait_for_selector(".marker", timeout=10000)
        assert page.locator(".marker").count() == 2, "one marker per provenance tag in the draft"
        assert page.locator("article[data-card^='thread:assemble']").count() == 0, (
            "Writer activity folds into the draft card"
        )
        estimator = page.locator("article[data-agent='estimator']")
        assert "scripted estimator" in estimator.inner_text()
        assert "Takeoff complete, 2 BOM lines" in estimator.inner_text()

        page.click("#btn-approve")
        page.wait_for_selector("article[data-kind='termination']:has-text('Your decision')", timeout=20000)
        assert errors == []
        browser.close()
