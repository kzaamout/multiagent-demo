"""The S2 and S3 text interims are gone (spec SC-007)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_no_text_renderer_and_no_markdown_to_the_reviewer() -> None:
    assert not (ROOT / "app" / "web" / "static" / "js" / "draft.js").exists()
    render = (ROOT / "app" / "web" / "static" / "js" / "render.js").read_text(encoding="utf-8")
    assert "S1Draft" not in render and "renderMarkdown" not in render
    page = (ROOT / "app" / "web" / "pages" / "demo.html").read_text(encoding="utf-8")
    assert "draft.js" not in page and "draft-page" not in page
    materials = (ROOT / "app" / "live" / "materials.py").read_text(encoding="utf-8")
    assert 'f"Draft v{' not in materials, "the Reviewer no longer receives the markdown draft"
    reviewer = (ROOT / "config" / "electrical-bid" / "seats" / "reviewer.md").read_text(encoding="utf-8")
    assert "as markdown" not in reviewer
