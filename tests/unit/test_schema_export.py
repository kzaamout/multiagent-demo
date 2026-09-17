from __future__ import annotations

from app.schema.export import TARGET, render


def test_committed_json_schema_matches_models() -> None:
    committed = TARGET.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert committed == render(), "run: uv run python -m app.schema.export"


def test_prose_schema_document_is_committed() -> None:
    doc = TARGET.with_suffix(".md")
    text = doc.read_text(encoding="utf-8")
    assert "version 1.1.0" in text
    assert "dry_intake" in text
    assert "stop_reason" in text and "latency_ms" in text


def test_previous_schema_version_stays_committed() -> None:
    """Every 1.0.0 recording still validates: the amendment is additive and the old documents stay."""
    folder = TARGET.parent
    assert (folder / "events-v1.0.0.md").exists() and (folder / "events-v1.0.0.json").exists()
