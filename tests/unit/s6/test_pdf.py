"""The Introduction PDF carries every section and the three drawings (spec FR-009, SC-005)."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from app.config import Settings
from app.intro.content import sections
from app.intro.pdf import render_pdf
from app.live.documents import parse_pdf

pytestmark = pytest.mark.compiler


def test_pdf_has_every_section_and_three_diagrams(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs")
    pdf = render_pdf(settings)
    assert pdf.is_file() and pdf.name == "introduction.pdf"
    text = " ".join(" ".join(p.text.split()) for p in parse_pdf(pdf))
    for section in sections():
        assert section.title in text, section.title
        first = next((b.lines[0] for b in section.blocks if b.kind == "paragraph"), None)
        if first:
            words = " ".join(first.replace("**", "").split()[:5])
            assert words in text, (section.id, words)
    typ = (tmp_path / "runs" / "_intro" / "introduction.typ").read_text(encoding="utf-8")
    assert typ.count("image(") == 3
    assert chr(0x2014) not in text


def test_pdf_is_not_regenerated_when_nothing_changed(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs")
    first = render_pdf(settings)
    stamp = first.stat().st_mtime
    time.sleep(0.05)
    again = render_pdf(settings)
    assert again == first and again.stat().st_mtime == stamp
    os.utime(first, (time.time() - 100000, time.time() - 100000))
    assert render_pdf(settings).stat().st_mtime > stamp - 100000
