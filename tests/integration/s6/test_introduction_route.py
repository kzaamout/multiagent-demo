"""The Introduction page renders the seven sections, the diagrams and the team without a login (spec FR-001 to FR-005)."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.intro.content import ORDER, sections
from app.main import create_app


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(Settings(runs_dir=tmp_path / "runs", stub_pace=1000.0, agent_mode="stub")))


def test_page_renders_sections_in_order_with_the_shared_header(tmp_path: Path) -> None:
    html = _client(tmp_path).get("/introduction").text
    ids = re.findall(r'<section id="([a-z-]+)" class="intro-section', html)
    assert ids == [section_id for _, section_id, _ in ORDER] + ["replay"]
    assert '<span class="nav-current">Introduction</span>' in html
    assert 'data-part="workflow-select"' not in html
    assert "{{BUILD_STAMP}}" not in html and 'data-part="build-stamp"' in html
    assert html.count('data-part="diagram"') == 3
    for name in ("architecture", "loop", "demo-vs-production"):
        assert f'data-diagram="{name}"' in html
    assert html.count('data-part="team-card"') == 8
    assert "swaps in for the appraisal workflow" in html


def test_rendered_text_equals_the_content_files(tmp_path: Path) -> None:
    html = _client(tmp_path).get("/introduction").text
    for section in sections():
        block = re.search(rf'<section id="{section.id}".*?</section>', html, re.S)
        assert block is not None
        body = re.sub(
            r"<figure.*?</figure>|<div class=\"team-grid\".*?</div></div></div>",
            "",
            block.group(0),
            flags=re.S,
        )
        text = re.sub(r"<[^>]+>", " ", body)
        text = re.sub(
            r"\s+",
            " ",
            text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&#x27;", "'"),
        )
        for line in section.text.splitlines():
            assert " ".join(line.split()) in text, (section.id, line[:60])
        assert chr(0x2014) not in text


def test_every_page_links_to_the_introduction(tmp_path: Path) -> None:
    client = _client(tmp_path)
    for path in ("/demo", "/settings", "/preflight"):
        assert 'href="/introduction"' in client.get(path).text, path


def test_header_dot_renders_from_the_stored_preflight_result(tmp_path: Path) -> None:
    from app.preflight.result import FAIL, PASS, CheckResult, build_result, save_result

    pending = _client(tmp_path).get("/introduction").text
    assert "{{PREFLIGHT_" not in pending
    assert (
        'data-part="preflight-indicator" data-status="pending" title="Pre-flight: not run yet">○<' in pending
    )
    checks = [
        CheckResult("login", "Login pair set", FAIL, "missing", True, 1),
        CheckResult("typst", "Typst compiles", PASS, "ok", True, 1),
    ]
    save_result(tmp_path / "runs", build_result("laptop", "2026-09-17T09:00:00", checks))
    failed = _client(tmp_path).get("/introduction").text
    assert 'data-status="fail" title="Pre-flight: Login pair set failed, 17 Sep 2026, 09:00">' in failed
