"""Choosing the run and its proposal for the leave-behind (S7, spec 0.7 section 8)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.compile.pipeline import Compiled
from app.leave_behind import LeaveBehindError, candidate_runs, choose_run, latest_proposal


def recording(runs_dir: Path, run_id: str, exit_value: str | None, started_at: str, log: bool = True) -> Path:
    folder = runs_dir / run_id
    folder.mkdir(parents=True)
    meta = {
        "run_id": run_id,
        "dataset_id": "clean-run",
        "mode": "team",
        "exit": exit_value,
        "started_at": started_at,
    }
    (folder / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    if log:
        (folder / "events.jsonl").write_text("", encoding="utf-8")
    return folder


def compiled_version(folder: Path, version: int, with_pdf: bool = True) -> None:
    out = folder / "artifacts" / f"v{version}"
    out.mkdir(parents=True)
    pdf = f"artifacts/v{version}/draft-v{version}.pdf"
    record = Compiled(
        version=version,
        pdf_path=pdf,
        page_images=[f"artifacts/v{version}/page-01.png"],
        marker_count=0,
        unresolved=[],
        page_count=1,
        elapsed_ms=10,
        tool_versions={},
        markers_path=f"artifacts/v{version}/markers.json",
        pages_path=f"artifacts/v{version}/pages.json",
        typ_path=f"artifacts/v{version}/draft-v{version}.typ",
    )
    (out / "compiled.json").write_text(json.dumps(record.to_json()), encoding="utf-8")
    if with_pdf:
        (folder / pdf).write_bytes(b"%PDF-1.7\n")


def test_newest_finished_run_wins_over_a_newer_stopped_one(tmp_path: Path) -> None:
    recording(tmp_path, "aaaa", "reviewer_pass", "2026-09-17T05:00:00Z")
    recording(tmp_path, "bbbb", "stopped", "2026-09-17T09:00:00Z")
    recording(tmp_path, "cccc", "single_complete", "2026-09-17T07:00:00Z")
    recording(tmp_path, "dddd", None, "2026-09-17T10:00:00Z")
    (tmp_path / "_intro").mkdir()
    (tmp_path / "preflight").mkdir()
    assert [f.name for f, _ in candidate_runs(tmp_path)] == ["aaaa", "bbbb", "cccc"]
    folder, meta = choose_run(tmp_path)
    assert folder.name == "cccc" and meta["exit"] == "single_complete"


def test_only_ended_runs_are_chosen_without_a_completed_one(tmp_path: Path) -> None:
    recording(tmp_path, "bbbb", "stopped", "2026-09-17T09:00:00Z")
    recording(tmp_path, "eeee", "not_ready", "2026-09-17T11:00:00Z")
    assert choose_run(tmp_path)[0].name == "eeee"


def test_named_run_and_its_refusals(tmp_path: Path) -> None:
    recording(tmp_path, "aaaa", "reviewer_pass", "2026-09-17T05:00:00Z")
    recording(tmp_path, "live", None, "2026-09-17T12:00:00Z")
    recording(tmp_path, "nolog", "reviewer_pass", "2026-09-17T12:00:00Z", log=False)
    assert choose_run(tmp_path, "aaaa")[0].name == "aaaa"
    with pytest.raises(LeaveBehindError, match="unknown run zzzz"):
        choose_run(tmp_path, "zzzz")
    with pytest.raises(LeaveBehindError, match="unknown run nolog"):
        choose_run(tmp_path, "nolog")
    with pytest.raises(LeaveBehindError, match="has not ended"):
        choose_run(tmp_path, "live")
    with pytest.raises(LeaveBehindError, match="no recording under"):
        choose_run(tmp_path / "empty")


def test_latest_proposal_is_the_highest_version_with_a_file(tmp_path: Path) -> None:
    folder = recording(tmp_path, "aaaa", "reviewer_pass", "2026-09-17T05:00:00Z")
    with pytest.raises(LeaveBehindError, match="no compiled proposal"):
        latest_proposal(folder)
    compiled_version(folder, 1)
    compiled_version(folder, 2)
    compiled_version(folder, 3, with_pdf=False)
    assert latest_proposal(folder) == folder / "artifacts" / "v2" / "draft-v2.pdf"
