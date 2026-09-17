"""The leave-behind: the three PDFs a prospect keeps after the meeting (spec 0.7 section 8, slice S7).

One command, no manual steps (acceptance criterion 10): the run's compiled proposal, the run
timeline rendered from its event log with the run's `metrics.json` beside it, and the Introduction
page as a PDF. Everything is read from a recording under the runs folder; nothing here emits an
event or touches a live run. The run is the one named, else the newest recording that finished
its job (the same ranking the Compare strip uses).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.compile import compile_timeline, tools_available
from app.compile.pipeline import read_compiled
from app.config import Settings
from app.intro.pdf import render_pdf
from app.runs.comparison import rank
from app.runs.recorder import read_events, read_meta

OUT_DIR_NAME = "leave-behind"
PROPOSAL = "proposal.pdf"
TIMELINE = "run-timeline.pdf"
INTRODUCTION = "introduction.pdf"
METRICS = "metrics.json"


class LeaveBehindError(RuntimeError):
    """One line saying why the leave-behind could not be produced."""


@dataclass(frozen=True)
class LeaveBehind:
    run_id: str
    folder: Path
    proposal: Path
    timeline: Path
    introduction: Path
    metrics: Path | None

    @property
    def pdfs(self) -> list[Path]:
        return [self.proposal, self.timeline, self.introduction]


def missing_tools() -> list[str]:
    return [name for name, version in tools_available().items() if version is None]


def candidate_runs(runs_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    """Recordings that have ended: a folder with `meta.json` carrying an exit and an event log.
    Folders whose name starts with an underscore hold generated files, not runs."""
    found: list[tuple[Path, dict[str, Any]]] = []
    if not runs_dir.is_dir():
        return found
    for folder in sorted(runs_dir.iterdir()):
        if not folder.is_dir() or folder.name.startswith("_"):
            continue
        meta = read_meta(folder)
        if not meta or not meta.get("exit") or not (folder / "events.jsonl").is_file():
            continue
        found.append((folder, meta))
    return found


def choose_run(runs_dir: Path, run_id: str | None = None) -> tuple[Path, dict[str, Any]]:
    """The named run, or the newest recording that finished its job, else the newest that ended."""
    if run_id:
        folder = runs_dir / run_id
        meta = read_meta(folder)
        if meta is None or not (folder / "events.jsonl").is_file():
            raise LeaveBehindError(f"unknown run {run_id}")
        if not meta.get("exit"):
            raise LeaveBehindError(f"run {run_id} has not ended")
        return folder, meta
    candidates = candidate_runs(runs_dir)
    if not candidates:
        raise LeaveBehindError(f"no recording under {runs_dir}")
    return max(candidates, key=lambda item: rank(item[1]))


def latest_proposal(run_folder: Path) -> Path:
    """The PDF of the highest compiled version whose file is still there."""
    versions: list[int] = []
    for record in run_folder.glob("artifacts/v*/compiled.json"):
        name = record.parent.name[1:]
        if name.isdigit():
            versions.append(int(name))
    for version in sorted(versions, reverse=True):
        compiled = read_compiled(run_folder, version)
        if compiled is not None and compiled.pdf_path:
            pdf = run_folder / compiled.pdf_path
            if pdf.is_file():
                return pdf
    raise LeaveBehindError(f"run {run_folder.name} has no compiled proposal")


def build_leave_behind(
    settings: Settings, run_id: str | None = None, out_dir: Path | None = None, force: bool = False
) -> LeaveBehind:
    """Write the three PDFs (and the run's metrics beside the timeline) and return their paths.
    The default folder is `runs/<run_id>/leave-behind/`."""
    missing = missing_tools()
    if missing:
        raise LeaveBehindError("compiler missing (" + ", ".join(missing) + ")")
    folder, meta = choose_run(settings.runs_dir, run_id)
    chosen = str(meta.get("run_id") or folder.name)
    events = read_events(folder / "events.jsonl")
    proposal = latest_proposal(folder)
    timeline = compile_timeline(folder, events)
    introduction = render_pdf(settings, force=force)

    out = out_dir or folder / OUT_DIR_NAME
    out.mkdir(parents=True, exist_ok=True)
    proposal_copy = _copy(proposal, out / PROPOSAL)
    timeline_copy = _copy(timeline, out / TIMELINE)
    introduction_copy = _copy(introduction, out / INTRODUCTION)
    metrics_source = folder / METRICS
    metrics_copy = _copy(metrics_source, out / METRICS) if metrics_source.is_file() else None
    return LeaveBehind(
        run_id=chosen,
        folder=out,
        proposal=proposal_copy,
        timeline=timeline_copy,
        introduction=introduction_copy,
        metrics=metrics_copy,
    )


def _copy(source: Path, target: Path) -> Path:
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)
    return target
