"""Persistent client knowledge files for live runs (spec 3 stage 1, FR-020 and FR-021).

One human-readable file per client under knowledge/ (git-ignored), seeded once from the
dataset's knowledge.seed.md, falling back to the workflow seed. Only the Orchestrator appends,
and only Intake clarification answers. Standing facts are never rewritten.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.config import ROOT
from app.schema.events import KnowledgeEntry

WORKFLOW_SEED = ROOT / "config" / "electrical-rfp" / "knowledge-file.seed.md"
ANSWERS_HEADING = "## Answers from previous runs"
EMPTY_MARKER = "(empty; the Orchestrator appends here)"
_CLIENT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")


@dataclass(frozen=True)
class KnowledgeStore:
    root: Path

    def path_for(self, client_id: str) -> Path:
        if not _CLIENT_ID.match(client_id):
            raise ValueError(f"invalid client id {client_id!r}")
        return self.root / f"{client_id}.md"

    def ensure(self, client_id: str, dataset_seed: Path | None) -> Path:
        path = self.path_for(client_id)
        if path.exists():
            return path
        seed = dataset_seed if dataset_seed is not None and dataset_seed.exists() else WORKFLOW_SEED
        text = seed.read_text(encoding="utf-8")
        if ANSWERS_HEADING not in text:
            text = text.rstrip() + f"\n\n{ANSWERS_HEADING}\n{EMPTY_MARKER}\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    def read(self, client_id: str) -> str:
        return self.path_for(client_id).read_text(encoding="utf-8")

    def append(self, client_id: str, entries: list[KnowledgeEntry], *, run_id: str, when: str) -> None:
        path = self.path_for(client_id)
        text = path.read_text(encoding="utf-8")
        lines = "".join(f"- {e.question_id}: {e.answer} (run {run_id}, {when})\n" for e in entries)
        if EMPTY_MARKER in text:
            text = (
                text.replace(EMPTY_MARKER + "\n", lines, 1)
                if EMPTY_MARKER + "\n" in text
                else text.replace(EMPTY_MARKER, lines.rstrip("\n"), 1)
            )
        else:
            if not text.endswith("\n"):
                text += "\n"
            text += lines
        path.write_text(text, encoding="utf-8", newline="\n")

    def answered_question_ids(self, client_id: str) -> set[str]:
        text = self.read(client_id)
        if ANSWERS_HEADING not in text:
            return set()
        section = text.split(ANSWERS_HEADING, 1)[1]
        return set(re.findall(r"^- (q_[a-z0-9_]+):", section, flags=re.M))
