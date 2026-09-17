"""prepare_documents: deterministic splitting and a manifest that says what it could not read (S3b, US2)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from app.tools.prepare import (
    MANIFEST_JSON,
    MANIFEST_MD,
    UNKNOWN,
    prepare_documents,
    read_manifest,
    read_title_block,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "s2" / "inputs"

SYNTHETIC_TAIL = (
    "REVISIONS\r\nRev Description Date\r\n0 Issued for tender 2026-09-08\r\nSCALE\r\nNot to scale\r\n"
    "SHEET TITLE\r\nSingle-Line Diagram\r\nSHEET\r\nE-001"
)
BINDER_TAIL = (
    "Contractors shall verify all dimensions. PROJECT No: DRAWN BY: SCALE: DATE: ISSUED FOR: "
    "ISSUED FOR BUILDING PERMIT / TENDER 2026-08-17 ELECTRICAL " + "x " * 300 + "E000 ELECTRICAL COVER PAGE"
)


def test_labelled_title_block_is_read_as_written() -> None:
    block = read_title_block("Some body text about panel LP-1.\r\n" + SYNTHETIC_TAIL)
    assert (block.sheet_number, block.title, block.discipline) == ("E-001", "Single-Line Diagram", "E")
    assert (block.issued_for, block.revision_date) == ("Tender", "2026-09-08")
    assert block.unknown_fields() == ()


def test_binder_title_block_without_labels() -> None:
    block = read_title_block(BINDER_TAIL)
    assert block.sheet_number == "E000" and block.discipline == "E"
    assert block.title == "ELECTRICAL COVER PAGE"
    assert block.issued_for == "Building permit / tender" and block.revision_date == "2026-08-17"


def test_ambiguity_is_unknown_not_a_guess() -> None:
    several_sheets = "see A1.0 and A2.0 for layout. E101 FLOOR PLAN"
    block = read_title_block(several_sheets)
    assert block.sheet_number == UNKNOWN and block.title == UNKNOWN and block.discipline == UNKNOWN
    revision_table = "1 ISSUED FOR COORDINATION 24-JUL-26 2 ISSUED FOR CODE REVIEW 30-JUL-26 3 ISSUED FOR CONSTRUCTION 17-AUG-26"
    assert read_title_block(revision_table).issued_for == UNKNOWN
    assert read_title_block(revision_table).revision_date == UNKNOWN
    assert read_title_block("").unknown_fields() == (
        "sheet_number",
        "title",
        "discipline",
        "issued_for",
        "revision_date",
    )


def test_a_row_of_labels_is_not_a_title() -> None:
    text = "DRAWING TITLE: PROJECT No: DRAWN BY: SCALE: DATE:\r\n" + "y " * 200 + "M301 MECHANICAL SCHEDULES"
    block = read_title_block(text)
    assert block.title == "MECHANICAL SCHEDULES" and block.discipline == "M"
    far_from_block = "T100 SITE PLAN " + "z " * 300
    assert read_title_block(far_from_block).title == UNKNOWN


def test_other_disciplines_and_dates() -> None:
    assert read_title_block("x " * 10 + "SHEET\nC-101\nSHEET TITLE\nGrading Plan").discipline == "other"
    block = read_title_block("ISSUED FOR CONSTRUCTION 17-Aug-26\n" + "q " * 200 + "S201 FRAMING PLAN")
    assert block.revision_date == "2026-08-17" and block.issued_for == "Construction"


def test_dataset_inputs_are_split_with_a_manifest(tmp_path: Path) -> None:
    out = tmp_path / "prepared"
    request = [FIXTURES / "request.pdf", FIXTURES / "division-26-specification.pdf"]
    drawings = [FIXTURES / "drawings" / "E-001.pdf"]
    prepared = prepare_documents(request, drawings, out)
    ids = [s.sheet_id for s in prepared.sheets]
    assert ids[:2] == ["request-p01", "request-p02"] and ids[-1] == "E-001"
    for sheet in prepared.sheets:
        assert (out / sheet.pdf).exists() and (out / sheet.png).read_bytes()[:4] == b"\x89PNG"
        assert (out / sheet.text).exists()
    drawing = prepared.sheet("E-001")
    assert drawing is not None and drawing.kind == "drawing" and drawing.page_count == 1
    assert drawing.sheet_number == "E-001" and drawing.confidence >= 0.9
    page = prepared.sheet("request-p01")
    assert page is not None and page.unknown_fields == () and page.discipline == "n/a"
    manifest = (out / MANIFEST_MD).read_text(encoding="utf-8")
    assert "| E-001 |" in manifest and "Title block fields unknown:" in manifest
    assert chr(0x2014) not in manifest
    data = json.loads((out / MANIFEST_JSON).read_text(encoding="utf-8"))
    assert [f["source"] for f in data["files"]] == [
        "request.pdf",
        "division-26-specification.pdf",
        "drawings/E-001.pdf",
    ]
    again = read_manifest(out)
    assert again is not None and [s.sheet_id for s in again.sheets] == ids
    assert [f.summary() for f in again.files] == [f.summary() for f in prepared.files]


def test_a_binder_becomes_one_sheet_per_page_and_records_unknowns(tmp_path: Path) -> None:
    binder = tmp_path / "binder.pdf"
    shutil.copy(FIXTURES / "request.pdf", binder)
    prepared = prepare_documents([], [binder], tmp_path / "prepared")
    sheets = prepared.drawing_sheets()
    assert [s.page for s in sheets] == [1, 2] and all(s.page_count == 2 for s in sheets)
    assert [s.sheet_id for s in sheets] == ["binder-p01", "binder-p02"]
    assert all(s.sheet_number == UNKNOWN and s.discipline == UNKNOWN for s in sheets)
    assert prepared.unknown_count() >= 8
    assert "unknown" in prepared.files[0].summary()


def test_unreadable_and_non_pdf_files_are_recorded_not_skipped(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    note = tmp_path / "note.eml"
    note.write_text("hello", encoding="utf-8")
    prepared = prepare_documents([note], [bad], tmp_path / "prepared")
    assert [f.problem for f in prepared.files] == [
        "not a PDF; passed through unread",
        "unreadable PDF; every field unknown",
    ]
    assert prepared.sheets == []
    assert "Files with problems" in (tmp_path / "prepared" / MANIFEST_MD).read_text(encoding="utf-8")


def test_same_inputs_same_manifest(tmp_path: Path) -> None:
    first = prepare_documents(
        [FIXTURES / "request.pdf"], [FIXTURES / "drawings" / "E-001.pdf"], tmp_path / "a"
    )
    second = prepare_documents(
        [FIXTURES / "request.pdf"], [FIXTURES / "drawings" / "E-001.pdf"], tmp_path / "b"
    )
    assert (tmp_path / "a" / MANIFEST_MD).read_text(encoding="utf-8") == (
        tmp_path / "b" / MANIFEST_MD
    ).read_text(encoding="utf-8")
    assert [s.sheet_id for s in first.sheets] == [s.sheet_id for s in second.sheets]
