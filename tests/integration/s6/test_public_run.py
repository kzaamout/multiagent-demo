"""The public routes serve exactly one pinned run and refuse everything else (spec FR-006, SC-003)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.agents.stubs import clean_run, planted_inconsistency
from app.config import Settings
from app.main import create_app
from tests.conftest import run_scenario

pytestmark = pytest.mark.compiler

PINNED = "00000000-0000-4000-8000-0000000000aa"
OTHER = "00000000-0000-4000-8000-0000000000bb"


async def _record(settings: Settings, scenario: object, run_id: str) -> None:
    await run_scenario(scenario, settings, record=True, run_id=run_id)  # type: ignore[arg-type]


@pytest.fixture
async def client(tmp_path: Path) -> TestClient:
    settings = Settings(runs_dir=tmp_path / "runs", stub_pace=1000.0, agent_mode="stub", public_run_id=PINNED)
    await _record(settings, planted_inconsistency.SCENARIO, PINNED)
    await _record(settings, clean_run.SCENARIO, OTHER)
    return TestClient(create_app(settings))


async def test_pinned_run_is_served_and_the_other_is_refused_on_every_route(
    client: TestClient, tmp_path: Path
) -> None:
    events = client.get(f"/public/run/{PINNED}/events")
    assert events.status_code == 200 and events.json()[-1]["type"] == "run.terminated"
    meta = client.get(f"/public/run/{PINNED}/meta").json()
    assert meta == {
        "run_id": PINNED,
        "dataset_id": "planted-inconsistency",
        "exit": "reviewer_pass",
        "has_pages": True,
    }
    compiled = next(e for e in events.json() if e["type"] == "artifact.compiled")
    page = client.get(f"/public/run/{PINNED}/files/{compiled['payload']['page_images'][0]}")
    assert page.status_code == 200 and page.content[:8] == b"\x89PNG\r\n\x1a\n"
    ref = next(e["prompt_ref"] for e in events.json() if e["prompt_ref"])
    prompt = client.get(f"/public/run/{PINNED}/prompts/{ref}")
    assert prompt.status_code == 200 and prompt.json()["sections"][0]["label"] == "System instructions"
    assert (tmp_path / "runs" / OTHER / "events.jsonl").is_file(), "the other run exists and is still refused"
    for path in ("events", "meta", f"files/{compiled['payload']['page_images'][0]}", f"prompts/{ref}"):
        assert client.get(f"/public/run/{OTHER}/{path}").status_code == 404, path
    assert client.get(f"/public/run/{PINNED}/files/../{OTHER}/events.jsonl").status_code == 404
    assert client.get(f"/public/run/{PINNED}/files/events.jsonl").status_code == 404, (
        "only pages, pdfs, markdown and json"
    )


async def test_introduction_frame_points_at_the_pinned_run(client: TestClient) -> None:
    html = client.get("/introduction").text
    assert f'data-run="{PINNED}"' in html
    assert f'src="/demo?public=1&amp;run={PINNED}&amp;speed=1"' in html
    assert "dataset planted-inconsistency" in html and "exit reviewer_pass" in html


def test_missing_pinned_recording_shows_a_note(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", stub_pace=1000.0, agent_mode="stub", public_run_id=PINNED)
    html = TestClient(create_app(settings)).get("/introduction").text
    assert "The pinned recording is not on this machine" in html and "replay-iframe" not in html
    assert TestClient(create_app(settings)).get(f"/public/run/{PINNED}/events").status_code == 404
