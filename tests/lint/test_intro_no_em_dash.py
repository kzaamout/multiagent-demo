"""No em dash on the rendered Introduction page or in its diagrams (constitution IX, spec FR-012)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.intro.diagrams import diagrams
from app.main import create_app


def test_page_and_diagrams_carry_no_em_dash(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", stub_pace=1000.0, agent_mode="stub")
    html = TestClient(create_app(settings)).get("/introduction").text
    assert chr(0x2014) not in html
    for diagram in diagrams().values():
        assert chr(0x2014) not in diagram.text
