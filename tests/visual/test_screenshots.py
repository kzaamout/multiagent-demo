"""Screenshot comparison against the Claude Design export at 1920 by 1080 (acceptance criterion 3,
except Introduction which is S6). Run with: uv run pytest -m visual"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import uvicorn

from app.config import Settings
from app.main import create_app
from tests.visual.compare import compare

HERE = Path(__file__).resolve().parent
REFERENCE = HERE / "reference"
OUTPUT = HERE / "output"

pytestmark = pytest.mark.visual


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def base_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    port = free_port()
    app = create_app(Settings(runs_dir=tmp_path_factory.mktemp("runs")))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def captures(base_url: str) -> dict[str, Path]:
    playwright = pytest.importorskip("playwright.sync_api")
    from tests.visual.capture_app import capture

    with playwright.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as error:  # noqa: BLE001
            pytest.skip(f"Chromium not installed: {error}")
        result = capture(browser, base_url, OUTPUT)
        browser.close()
    return result


@pytest.mark.parametrize(
    "name",
    ["demo-idle", "demo-paused", "demo-running", "demo-terminated", "login", "settings", "preflight-pending"],
)
def test_page_matches_export(name: str, captures: dict[str, Path]) -> None:
    result = compare(name, REFERENCE / f"{name}.png", captures[name], OUTPUT)
    assert result.passed, f"{name}: {result.ratio:.3%} of unmasked pixels differ; see {result.diff_path}"
