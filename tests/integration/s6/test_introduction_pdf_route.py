"""The Introduction PDF route (spec FR-009): a PDF on request, cached until a source changes."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

pytestmark = pytest.mark.compiler


def test_pdf_route_serves_and_caches(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", stub_pace=1000.0, agent_mode="stub")
    with TestClient(create_app(settings)) as client:
        first = client.get("/introduction.pdf")
        assert first.status_code == 200
        assert first.headers["content-type"].startswith("application/pdf") and first.content[:5] == b"%PDF-"
        pdf = tmp_path / "runs" / "_intro" / "introduction.pdf"
        stamp = pdf.stat().st_mtime
        again = client.get("/introduction.pdf")
        assert again.status_code == 200 and pdf.stat().st_mtime == stamp, "nothing changed, no recompile"


def test_pdf_route_names_a_missing_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.intro import pdf as pdf_module

    monkeypatch.setattr(pdf_module, "tools_available", lambda: {"pandoc": None, "typst": "0.15.1"})
    settings = Settings(runs_dir=tmp_path / "runs", stub_pace=1000.0, agent_mode="stub")
    with TestClient(create_app(settings)) as client:
        response = client.get("/introduction.pdf")
        assert response.status_code == 503 and "pandoc" in response.json()["error"]
