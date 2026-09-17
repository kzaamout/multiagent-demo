"""The run timeline PDF lists every event (spec FR-012)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.compile import compile_timeline
from app.compile.timeline import timeline_markdown
from app.config import load_settings
from app.live.documents import parse_pdf
from app.runs.recorder import read_events

GOLDEN = load_settings().datasets_dir / "clean-run" / "golden-events.jsonl"

pytestmark = [pytest.mark.compiler, pytest.mark.dataset]


def test_timeline_markdown_has_one_row_per_event() -> None:
    events = read_events(GOLDEN)
    text = timeline_markdown(events)
    rows = [line for line in text.splitlines() if line.startswith("| ") and not line.startswith("| Time")]
    assert len(rows) == len(events)
    assert rows[0].startswith("| 00:00 |")


def test_timeline_pdf_names_every_event_type(tmp_path: Path) -> None:
    events = read_events(GOLDEN)
    pdf = compile_timeline(tmp_path, events)
    assert pdf.is_file() and pdf.name == "timeline.pdf"
    text = " ".join(p.text for p in parse_pdf(pdf))
    for event_type in {e.type for e in events}:
        assert event_type in text
