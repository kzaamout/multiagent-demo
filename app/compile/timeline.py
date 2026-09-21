"""The run timeline as a PDF, rendered from the event log through the same pipeline (S4 decision 5a)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from app.compile.pipeline import ARTIFACTS, TEMPLATES, render_markdown
from app.runs.working_time import working_times
from app.schema.events import Event

TIMELINE_TEMPLATE = TEMPLATES / "run-timeline.typ"


def _cell(text: object) -> str:
    return str(text).replace("|", "/").replace("\n", " ").strip()


def _actor_id(event: Event) -> str:
    actor = event.actor
    return actor if isinstance(actor, str) else actor.agent_id


def _actor_label(event: Event) -> str:
    actor = event.actor
    if isinstance(actor, str):
        return {"human": "You", "system": "System"}.get(actor, actor)
    return f"{actor.name}, {actor.role}" if actor.role else actor.name


def _summary(event: Event) -> str:
    payload = event.payload if isinstance(event.payload, dict) else {}
    if _actor_id(event) in ("orchestrator", "system") and event.reason:
        return event.reason
    for key in ("headline", "message", "summary", "target_reason", "question", "verdict", "exit", "decision"):
        value = payload.get(key)
        if isinstance(value, dict):
            value = value.get("headline")
        if isinstance(value, str) and value.strip():
            return value
    if isinstance(payload.get("result"), dict):
        headline = payload["result"].get("headline")
        if isinstance(headline, str):
            return headline
    return event.reason or ""


def timeline_markdown(events: Sequence[Event]) -> str:
    if not events:
        return "# Run timeline\n\nNo events were recorded.\n"
    first = events[0]
    dataset = first.payload.get("dataset_id", "") if isinstance(first.payload, dict) else ""
    lines = [
        "# Run timeline",
        "",
        f"Run {first.run_id}, dataset {dataset}, {len(events)} events.",
        "",
        "| Time | Stage | Actor | Event | Summary |",
        "|---|---|---|---|---|",
    ]
    # Each event's working time, the same measure as the feed cards and the clock (spec 012 decision 12).
    for event, work in zip(events, working_times(events), strict=True):
        elapsed = work // 1000
        lines.append(
            f"| {elapsed // 60:02d}:{elapsed % 60:02d} | {_cell(event.stage or '')} | {_cell(_actor_label(event))} | "
            f"{_cell(event.type)} | {_cell(_summary(event))[:160]} |"
        )
    return "\n".join(lines) + "\n"


def compile_timeline(run_folder: Path, events: Sequence[Event]) -> Path:
    """Write `artifacts/timeline.pdf` for the run, regenerating when the event log, or the way the
    timeline is written (this module), is newer than the PDF."""
    out_dir = run_folder / ARTIFACTS
    pdf = out_dir / "timeline.pdf"
    log = run_folder / "events.jsonl"
    if pdf.is_file() and log.is_file():
        newest_source = max(log.stat().st_mtime, Path(__file__).stat().st_mtime)
        if pdf.stat().st_mtime >= newest_source:
            return pdf
    first = events[0] if events else None
    variables = {
        "run-id": first.run_id if first is not None else "",
        "dataset": str(first.payload.get("dataset_id", ""))
        if first is not None and isinstance(first.payload, dict)
        else "",
    }
    return render_markdown(timeline_markdown(events), TIMELINE_TEMPLATE, variables, out_dir, "timeline")
