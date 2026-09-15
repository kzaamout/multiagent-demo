"""Capture reference screenshots from the Claude Design export at 1920 by 1080.

The export bundles in design/ are copied to a temporary folder with their design-time
switch defaults rewritten per state, rendered in Chromium, and saved to
tests/visual/reference/. Nothing under design/ is written.

Usage: uv run python scripts/capture_export.py
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DESIGN = ROOT / "design"
OUT = ROOT / "tests" / "visual" / "reference"
FREEZE = "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}"


@dataclass
class Capture:
    name: str
    bundle: str
    props: dict[str, object] = field(default_factory=dict)
    click: list[str] = field(default_factory=list)
    full_page: bool = False


CAPTURES = [
    Capture("demo-idle", "Demo", {"state": "idle"}),
    Capture("demo-paused", "Demo", {"state": "paused"}),
    Capture("demo-running", "Demo", {"state": "running"}, click=['[data-card="c7"] [data-part="card-header"]']),
    Capture("demo-terminated", "Demo", {"state": "terminated"}),
    Capture("demo-terminated-chat", "Demo", {"state": "terminated", "chatOpen": True}),
    Capture("login", "Login"),
    Capture("settings", "Settings", {"openDropdown": "-1"}),
    Capture("settings-dropdown", "Settings", {"openDropdown": "2"}),
    Capture("preflight-pending", "Preflight", {"result": "pending"}),
    Capture("preflight-all-pass", "Preflight", {"result": "all-pass"}),
    Capture("preflight-one-fail", "Preflight", {"result": "one-fail"}),
]


def rewrite_defaults(bundle_text: str, props: dict[str, object]) -> str:
    match = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', bundle_text, re.S)
    if not match:
        raise SystemExit("not a Claude Design bundle")
    template: str = json.loads(match.group(2))
    for key, value in props.items():
        encoded = json.dumps(value).replace('"', "&quot;")
        pattern = re.compile(r"(&quot;" + re.escape(key) + r"&quot;:\{&quot;editor&quot;:[^}]*?&quot;default&quot;:)([^,}]+)")
        template, count = pattern.subn(lambda m: m.group(1) + encoded, template, count=1)
        if count != 1:
            raise SystemExit(f"switch {key} not found in the bundle")
    rebuilt = json.dumps(template)
    return bundle_text[: match.start(2)] + rebuilt.replace("</", "<\\/") + bundle_text[match.end(2) :]


def settle(page: Page) -> None:
    page.wait_for_function("() => !document.getElementById('__bundler_loading')", timeout=30000)
    page.wait_for_function("() => document.fonts && document.fonts.status === 'loaded'", timeout=30000)
    page.add_style_tag(content=FREEZE)
    page.wait_for_timeout(600)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        for cap in CAPTURES:
            source = (DESIGN / f"{cap.bundle}.html").read_text(encoding="utf-8")
            staged = Path(tmp) / f"{cap.name}.html"
            staged.write_text(rewrite_defaults(source, cap.props) if cap.props else source, encoding="utf-8")
            page = context.new_page()
            page.goto(staged.as_uri())
            settle(page)
            for selector in cap.click:
                page.click(selector)
                page.wait_for_timeout(300)
            page.screenshot(path=str(OUT / f"{cap.name}.png"), full_page=cap.full_page)
            page.close()
            print(f"captured {cap.name}")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
