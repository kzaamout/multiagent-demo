from __future__ import annotations

from pathlib import Path

import pytest

from app.live.documents import NO_TEXT_LAYER_CONFIDENCE, _confidence, page_count, parse_pdf, render_page_png

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "s2" / "inputs"


def test_request_text_and_confidence_per_page() -> None:
    pages = parse_pdf(FIXTURES / "request.pdf")
    assert [p.page for p in pages] == [1, 2]
    assert "Submission deadline" in pages[0].text
    assert "Division 26" in pages[1].text
    assert all(0.9 <= p.confidence <= 1.0 for p in pages)


def test_drawing_renders_to_png() -> None:
    assert page_count(FIXTURES / "drawings" / "E-001.pdf") == 1
    png = render_page_png(FIXTURES / "drawings" / "E-001.pdf", 1)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(png) > 10_000
    with pytest.raises(ValueError):
        render_page_png(FIXTURES / "drawings" / "E-001.pdf", 2)


def test_unreadable_file_yields_no_pages(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    assert parse_pdf(bad) == []


def test_confidence_heuristic() -> None:
    assert _confidence("short") == NO_TEXT_LAYER_CONFIDENCE
    assert _confidence("A clean sentence about panel LP-1, 225 A.") == 1.0
    assert _confidence("����� garbled text layer ������") < 0.8
