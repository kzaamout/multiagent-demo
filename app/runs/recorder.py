"""Run recording under runs/<run_id>/ (spec section 6, recording paragraph)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.schema.bundles import PromptBundle
from app.schema.events import Event


class Recorder:
    def __init__(self, runs_dir: Path, run_id: str) -> None:
        self.folder = runs_dir / run_id
        self.events_path = self.folder / "events.jsonl"
        self.meta_path = self.folder / "meta.json"
        self.prompts_dir = self.folder / "prompts"
        self.knowledge_path = self.folder / "knowledge.md"
        self._meta: dict[str, Any] = {}

    def start(self, meta: dict[str, Any]) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        self.prompts_dir.mkdir(exist_ok=True)
        self._meta = dict(meta)
        self._meta.setdefault("exit", None)
        self._meta.setdefault("ended_at", None)
        self._write_meta()
        self.events_path.write_text("", encoding="utf-8")

    def append(self, event: Event) -> None:
        with self.events_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(event.to_line() + "\n")

    def save_bundle(self, bundle: PromptBundle) -> None:
        path = self.prompts_dir / f"{bundle.prompt_ref}.json"
        path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8", newline="\n")

    def finish(self, exit_value: str, ended_at: str) -> None:
        self._meta["exit"] = exit_value
        self._meta["ended_at"] = ended_at
        self._write_meta()
        self.write_metrics()

    def write_metrics(self) -> None:
        """Per-seat model performance, captured for every run (app/runs/metrics.py)."""
        from app.runs.metrics import write_metrics

        try:
            write_metrics(self.folder, read_events(self.events_path))
        except (OSError, ValueError):
            pass  # a recording detail never stops a run

    def _write_meta(self) -> None:
        self.meta_path.write_text(
            json.dumps(self._meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
        )


def read_events(path: Path) -> list[Event]:
    events: list[Event] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(Event.from_line(line))
    return events


def read_meta(folder: Path) -> dict[str, Any] | None:
    meta = folder / "meta.json"
    if not meta.exists():
        return None
    loaded: dict[str, Any] = json.loads(meta.read_text(encoding="utf-8"))
    return loaded
