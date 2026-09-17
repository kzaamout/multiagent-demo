"""One command produces the three leave-behind PDFs from a recorded run (acceptance criterion 10, S7)."""

from __future__ import annotations

import pytest

from app.agents.stubs import clean_run
from app.config import Settings
from app.leave_behind import INTRODUCTION, METRICS, PROPOSAL, TIMELINE, build_leave_behind
from tests.conftest import run_scenario

pytestmark = pytest.mark.compiler

RUN_ID = "00000000-0000-4000-8000-000000000001"


async def test_build_writes_three_pdfs_beside_the_run(settings: Settings) -> None:
    await run_scenario(clean_run.SCENARIO, settings, record=True)
    result = build_leave_behind(settings)
    assert result.run_id == RUN_ID
    assert result.folder == settings.runs_dir / RUN_ID / "leave-behind"
    assert [p.name for p in result.pdfs] == [PROPOSAL, TIMELINE, INTRODUCTION]
    for pdf in result.pdfs:
        assert pdf.is_file() and pdf.read_bytes().startswith(b"%PDF"), pdf
    source_metrics = settings.runs_dir / RUN_ID / METRICS
    if source_metrics.is_file():
        assert result.metrics == result.folder / METRICS and result.metrics.is_file()
    else:
        assert result.metrics is None


async def test_out_folder_and_named_run(settings: Settings, tmp_path_factory: pytest.TempPathFactory) -> None:
    await run_scenario(clean_run.SCENARIO, settings, record=True)
    out = tmp_path_factory.mktemp("leave") / "prospect"
    result = build_leave_behind(settings, run_id=RUN_ID, out_dir=out)
    assert result.folder == out
    assert sorted(p.name for p in out.iterdir() if p.suffix == ".pdf") == sorted(
        [INTRODUCTION, PROPOSAL, TIMELINE]
    )
