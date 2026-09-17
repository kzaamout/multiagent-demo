"""The run timeline PDF route (spec FR-012): after termination, for recordings, and for golden logs."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.runs.golden import golden_run_id

pytestmark = [pytest.mark.compiler, pytest.mark.dataset]


def _wait(client: TestClient, run_id: str, done: Any, timeout: float = 60.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status: dict[str, Any] = client.get(f"/api/runs/{run_id}").json()
        if done(status):
            return status
        time.sleep(0.05)
    raise AssertionError("the run did not reach the expected state")


def test_timeline_pdf_after_termination_and_409_before(tmp_path: Path) -> None:
    app = create_app(Settings(runs_dir=tmp_path / "runs", stub_pace=1000.0, agent_mode="stub"))
    with TestClient(app) as client:
        run_id = client.post("/api/runs", json={"dataset_id": "clean-run"}).json()["run_id"]
        status = _wait(client, run_id, lambda s: s["pending"]["kind"] in ("clarifications", "handoff"))
        if status["pending"]["kind"] == "clarifications":
            answers = [
                {"question_id": q, "answer": "", "action": "answer"}
                for q in status["pending"]["question_ids"]
            ]
            client.post(f"/api/runs/{run_id}/answers", json={"answers": answers})
            _wait(client, run_id, lambda s: s["pending"]["kind"] == "handoff")
        early = client.get(f"/api/runs/{run_id}/timeline.pdf")
        assert early.status_code == 409
        client.post(f"/api/runs/{run_id}/decision", json={"decision": "approve", "notes": ""})
        _wait(client, run_id, lambda s: s["status"] == "terminated")
        response = client.get(f"/api/runs/{run_id}/timeline.pdf")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/pdf")
        assert response.content[:5] == b"%PDF-"
        assert (tmp_path / "runs" / run_id / "artifacts" / "timeline.pdf").is_file()
        assert client.get("/api/runs/00000000-0000-4000-8000-00000000dead/timeline.pdf").status_code == 404


def test_timeline_pdf_for_a_golden_log(tmp_path: Path) -> None:
    app = create_app(Settings(runs_dir=tmp_path / "runs", stub_pace=1000.0, agent_mode="stub"))
    with TestClient(app) as client:
        response = client.get(f"/api/runs/{golden_run_id('clean-run')}/timeline.pdf")
        assert response.status_code == 200 and response.content[:5] == b"%PDF-"
        assert (
            tmp_path / "runs" / "_golden" / golden_run_id("clean-run") / "artifacts" / "timeline.pdf"
        ).is_file()
