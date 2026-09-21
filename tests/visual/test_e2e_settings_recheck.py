"""A seat change in Settings rechecks the chosen model and updates the header dot in place
(spec 012 User Story 3, SC-005). Probes are scripted: no model is called.
Run with: uv run pytest -m visual"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from typing import Any

import pytest
import uvicorn

from tests.integration.s12.support import Probes, make_app

pytestmark = [pytest.mark.visual, pytest.mark.dataset]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    patch = pytest.MonkeyPatch()
    app = make_app(tmp_path_factory.mktemp("recheck"), Probes(failing={"us.anthropic.claude-opus"}), patch)
    port = free_port()
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not srv.started and time.time() < deadline:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    thread.join(timeout=5)
    patch.undo()


@pytest.fixture(scope="module")
def page(server: str) -> Iterator[Any]:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as error:  # noqa: BLE001
            pytest.skip(f"Chromium not installed: {error}")
        pg = browser.new_context(viewport={"width": 1920, "height": 1080}).new_page()
        errors: list[str] = []
        pg.on("pageerror", lambda exc: errors.append(str(exc)))
        pg.errors = errors
        yield pg
        browser.close()


def choose(page: Any, seat: str, model: str) -> None:
    page.click(f'.seat-row[data-seat="{seat}"] .model-select')
    page.click(f'.seat-row[data-seat="{seat}"] .menu-item[data-model="{model}"]')


def test_settings_recheck_updates_the_dot_in_place(page: Any, server: str) -> None:
    page.goto(server + "/settings")
    page.wait_for_selector('.seat-row[data-seat="estimator"] .model-select')
    page.evaluate("() => { window.__loaded = true; }")
    dot = '[data-part="preflight-indicator"]'
    assert page.get_attribute(dot, "data-status") == "pending"

    choose(page, "estimator", "export-opus")
    page.wait_for_function(
        "() => document.getElementById('settings-status').textContent.includes('did not answer')"
    )
    status = page.inner_text("#settings-status")
    assert status.startswith("Applied: the next run uses claude-opus via Bedrock.")
    assert "claude-opus did not answer (RuntimeError). Pre-flight is red." in status
    assert page.get_attribute(dot, "data-status") == "fail"
    assert "claude-opus via Bedrock failed for the Estimator seat" in (page.get_attribute(dot, "title") or "")

    choose(page, "estimator", "export-sonnet")
    page.wait_for_function(
        "() => document.getElementById('settings-status').textContent.includes('claude-sonnet answered in')"
    )
    assert page.get_attribute(dot, "data-status") != "fail"
    # No navigation happened: the flag set on this document is still there.
    assert page.evaluate("() => window.__loaded") is True
    assert page.errors == []
