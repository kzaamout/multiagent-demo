from __future__ import annotations

from app.schema.export import TARGET, render


def test_committed_json_schema_matches_models() -> None:
    committed = TARGET.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert committed == render(), "run: uv run python -m app.schema.export"


def test_prose_schema_document_is_committed() -> None:
    doc = TARGET.with_suffix(".md")
    text = doc.read_text(encoding="utf-8")
    assert "version 1.0.0" in text
    assert "dry_intake" in text
