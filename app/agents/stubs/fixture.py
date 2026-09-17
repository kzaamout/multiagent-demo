"""The fixture draft every stub run compiles (S4 decision 6a).

Stub scenarios are canned emissions and cannot write files, so the Orchestrator writes this draft
into the run folder when it relays a stub's `draft.committed`, then compiles it for real. The
tags in the fixture are the tags the stub's `provenance_tags` name, so markers resolve in Replay.
"""

from __future__ import annotations

from pathlib import Path

from app.tools.template import Tag, find_tags

FIXTURE_DRAFT = Path(__file__).resolve().parent / "fixtures" / "draft-fixture.md"


def fixture_tags() -> list[Tag]:
    return find_tags(FIXTURE_DRAFT.read_text(encoding="utf-8"))


def fixture_draft(version: int, note: str = "") -> str:
    """The fixture markdown for a version. Later versions carry the stub's note in the executive
    summary so two versions of one run differ on the page."""
    text = FIXTURE_DRAFT.read_text(encoding="utf-8")
    if version > 1 and note:
        marker = "\n## Scope"
        sentence = f"\n\nRevision {version}: {note.rstrip('.')}.\n"
        head, sep, tail = text.partition(marker)
        text = f"{head.rstrip()}{sentence}{sep}{tail}" if sep else text + sentence
    return text
