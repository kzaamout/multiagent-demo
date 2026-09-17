"""Capture the flattened application pages in the same states as the export references.

Demo states are rendered from prefixes of the committed Planted inconsistency golden log,
which uses the export's names and timestamps. Used by test_screenshots.py and runnable
directly for inspection: uv run python tests/visual/capture_app.py http://127.0.0.1:8765
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Browser, sync_playwright

OUT = Path(__file__).resolve().parent / "output"
FREEZE = "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}"


@dataclass(frozen=True)
class AppState:
    name: str
    path: str
    open_cards: tuple[str, ...] = ()


def golden_seq(kind: str) -> int:
    """Seq at which each Demo state holds in the planted-inconsistency golden log."""
    import json

    from app.config import load_settings

    lines = (
        (load_settings().datasets_dir / "planted-inconsistency" / "golden-events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    events = [json.loads(line) for line in lines if line.strip()]

    def after(predicate: object) -> int:
        for index, event in enumerate(events):
            if predicate(event):  # type: ignore[operator]
                seq = int(event["seq"])
                if index + 1 < len(events) and events[index + 1]["type"] == "meter.update":
                    seq = int(events[index + 1]["seq"])
                return seq
        raise LookupError(kind)

    if kind == "paused":
        return after(lambda e: e["type"] == "clarification.asked")
    if kind == "running":
        return after(
            lambda e: (
                e["type"] == "task.progress"
                and e["payload"]["message"].startswith("Counting branch circuits")
            )
        )
    if kind == "terminated":
        return after(lambda e: e["type"] == "handoff.ready")
    raise LookupError(kind)


def states() -> list[AppState]:
    g = "/demo?golden=planted-inconsistency&upto="
    return [
        AppState("demo-idle", "/demo?dataset=planted-inconsistency"),
        AppState("demo-paused", g + str(golden_seq("paused"))),
        AppState("demo-running", g + str(golden_seq("running"))),
        AppState("demo-terminated", g + str(golden_seq("terminated"))),
        AppState("login", "/login"),
        AppState("settings", "/settings"),
        AppState("settings-dropdown", "/settings"),
        AppState("preflight-pending", "/preflight"),
    ]


def capture(browser: Browser, base_url: str, out: Path = OUT) -> dict[str, Path]:
    out.mkdir(parents=True, exist_ok=True)
    context = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    results: dict[str, Path] = {}
    for state in states():
        page = context.new_page()
        page.goto(base_url + state.path)
        page.wait_for_load_state("networkidle")
        page.wait_for_function("() => document.fonts && document.fonts.status === 'loaded'")
        page.add_style_tag(content=FREEZE)
        page.wait_for_timeout(500)
        if state.name == "demo-running":
            # Threads start collapsed (spec 0.7); the export's running state shows the Estimator
            # thread open, which the export reference itself reached by clicking it.
            page.click("article[data-kind='specialist-thread'][data-agent='estimator'] .card-hd")
            page.wait_for_timeout(200)
        if state.name.startswith("settings"):
            page.wait_for_selector('.seat-row[data-seat="estimator"] .model-select')
        if state.name == "settings-dropdown":
            # The export's reference has the Estimator dropdown open (openDropdown 2).
            page.click('.seat-row[data-seat="estimator"] .model-select')
            page.wait_for_selector('.seat-row[data-seat="estimator"] .menu')
            page.wait_for_timeout(200)
        if state.name == "demo-terminated":
            page.evaluate(
                "() => { const f = document.getElementById('feed'); f.scrollTop = f.scrollHeight; }"
            )
        path = out / f"{state.name}.png"
        page.screenshot(path=str(path))
        results[state.name] = path
        page.close()
    context.close()
    return results


def main(argv: list[str]) -> int:
    base = argv[0] if argv else "http://127.0.0.1:8765"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, path in capture(browser, base).items():
            print(name, path)
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
