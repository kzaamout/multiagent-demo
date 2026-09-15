"""Per-run client knowledge file: seeded from the dataset, appended by the Orchestrator only."""

from __future__ import annotations

from pathlib import Path

from app.schema.events import KnowledgeEntry


class KnowledgeFile:
    def __init__(self, path: Path, seed: Path | None, client_id: str) -> None:
        self.path = path
        self.client_id = client_id
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if seed is not None and seed.exists():
            self.path.write_text(seed.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
        else:
            self.path.write_text(f"# Knowledge file: {client_id}\n", encoding="utf-8", newline="\n")

    def append(self, entries: list[KnowledgeEntry], when: str) -> None:
        lines = [f"\n## Clarifications answered {when}\n"]
        for entry in entries:
            lines.append(f"- {entry.question_id}: {entry.answer} (source {entry.source_event_id})\n")
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.writelines(lines)

    def read(self) -> str:
        return self.path.read_text(encoding="utf-8")
