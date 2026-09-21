"""The Pre-flight payload and the dot on every page, read against the seats in force (spec 012 User
Story 2, SC-004, SC-008, SC-009). The export registry's seats: Estimator and Writer on
export-sonnet (Bedrock), Reviewer on export-gemini, Pricing on export-llama (local)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.integration.s12.support import MARKER, Probes, app_client, dot

pytestmark = pytest.mark.dataset

PAGES = ("/demo", "/settings", "/preflight", "/introduction")


async def test_payload_has_one_row_per_model_the_new_rows_and_the_header(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with app_client(tmp_path, Probes(), monkeypatch) as client:
        body = (await client.post("/api/preflight/run")).json()
    ids = [c["id"] for c in body["checks"]]
    assert ids == [
        "model:export-sonnet",
        "model:export-opus",
        "model:export-gemini",
        "model:export-grok",
        "model:export-anthropic",
        "ollama",
        "model:export-llama",
        "typst",
        "png",
        "tunnel",
        "disk",
        "env",
        "intro-recording",
        "replays",
        "family",
    ]
    rows = {c["id"]: c for c in body["checks"]}
    assert rows["model:export-sonnet"]["seats"] == [
        "orchestrator",
        "intake",
        "estimator",
        "writer",
        "case",
        "single",
    ]
    assert rows["model:export-grok"]["status"] == "skip"  # no xAI key
    assert set(body["header"]) == {"status", "glyph", "title"}


async def test_an_unused_model_failing_leaves_every_dot_green(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    probes = Probes(failing={"us.anthropic.claude-opus"})
    async with app_client(tmp_path, probes, monkeypatch) as client:
        body = (await client.post("/api/preflight/run")).json()
        rows = {c["id"]: c for c in body["checks"]}
        assert rows["model:export-opus"]["status"] == "fail"
        # Laptop mode with no login pair: the env row reports it, the dot does not (SC-009).
        assert (
            rows["env"]["status"] == "fail"
            and rows["env"]["detail"] == "Missing DEMO_USERNAME, DEMO_PASSWORD"
        )
        for path in PAGES:
            status, glyph, title = dot((await client.get(path)).text)
            assert (status, glyph) == ("pass", "✓"), path
            assert title.startswith("Pre-flight: checks for the current seats pass, 2 other rows failed"), (
                path
            )
        assert (await client.get("/api/meta")).json()["preflight"] == "pass"

        # Moving a seat onto the failing model turns the next page load red, with no rerun.
        swap = await client.post("/api/seats/estimator", json={"model": "export-opus"})
        assert swap.status_code == 200, swap.text
        status, _glyph, title = dot((await client.get("/demo")).text)
        assert status == "fail"
        assert title.startswith("Pre-flight: claude-opus via Bedrock failed for the Estimator seat")
        assert len(probes.calls) == 3  # the three cloud models with a key, once each


async def test_the_login_pair_counts_in_cloud_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async with app_client(tmp_path, Probes(), monkeypatch, run_mode="cloud") as client:
        await client.post("/api/preflight/run")
        status, _glyph, title = dot((await client.get("/demo")).text)
    # Pricing is on a local model in the export registry, which is red in Cloud mode before the login.
    assert status == "fail" and "Cloud mode" in title


async def test_no_marker_reaches_any_route_page_or_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    probes = Probes(failing={"gemini/gemini-2.5-pro"})
    async with app_client(tmp_path, probes, monkeypatch) as client:
        run = await client.post("/api/preflight/run")
        recheck = await client.post("/api/preflight/recheck", json={"model": "export-gemini"})
        assert run.status_code == 200 and recheck.status_code == 200
        texts = [run.text, recheck.text]
        for path in ("/api/preflight", "/api/meta", *PAGES):
            texts.append((await client.get(path)).text)
    for text in texts:
        assert MARKER not in text
    stored = (tmp_path / "runs" / "preflight.json").read_text(encoding="utf-8")
    assert MARKER not in stored and json.loads(stored)["schema"] == 2
