"""A stub run compiles its fixture draft for real and names the pages in its events (spec FR-014)."""

from __future__ import annotations

import json

import pytest

from app.agents.stubs import clean_run, planted_inconsistency
from app.agents.stubs.fixture import fixture_tags
from app.config import Settings
from tests.conftest import run_scenario

pytestmark = pytest.mark.compiler

RUN_ID = "00000000-0000-4000-8000-000000000001"


async def test_stub_clean_run_leaves_a_compiled_version(settings: Settings) -> None:
    events = await run_scenario(clean_run.SCENARIO, settings, record=True)
    compiled = [e for e in events if e.type == "artifact.compiled"]
    assert len(compiled) == 1
    payload = compiled[0].payload
    run_folder = settings.runs_dir / RUN_ID
    record = json.loads((run_folder / "artifacts" / "v1" / "compiled.json").read_text(encoding="utf-8"))
    assert payload["pdf_path"] == record["pdf_path"] == "artifacts/v1/draft-v1.pdf"
    assert payload["page_images"] == record["page_images"] and len(payload["page_images"]) >= 2
    for path in [payload["pdf_path"], *payload["page_images"]]:
        assert (run_folder / path).is_file(), path
    assert (run_folder / "drafts" / "draft-v1.md").is_file(), "the fixture draft was written for the stub"


async def test_stub_provenance_tags_are_the_fixture_tags(settings: Settings) -> None:
    events = await run_scenario(clean_run.SCENARIO, settings, record=True)
    draft = next(e for e in events if e.type == "draft.committed")
    tags = draft.payload["provenance_tags"]
    assert [t["tag_id"] for t in tags] == [t.tag_id for t in fixture_tags()]
    assert all(t["source_event_id"] and not t["source_event_id"].startswith("$event") for t in tags)


async def test_rework_compiles_a_second_version_that_differs(settings: Settings) -> None:
    events = await run_scenario(planted_inconsistency.SCENARIO, settings, record=True)
    versions = [e.payload["version"] for e in events if e.type == "artifact.compiled"]
    assert versions == [1, 2]
    run_folder = settings.runs_dir / RUN_ID
    v1 = (run_folder / "drafts" / "draft-v1.md").read_text(encoding="utf-8")
    v2 = (run_folder / "drafts" / "draft-v2.md").read_text(encoding="utf-8")
    assert v1 != v2 and "Revision 2" in v2
    assert (run_folder / "artifacts" / "v2" / "page-01.png").is_file()
    assert (run_folder / "artifacts" / "v1" / "page-01.png").is_file(), "earlier versions are kept"
