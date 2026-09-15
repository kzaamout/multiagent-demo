"""Integrity of the four failure datasets derived from Clean run (S3, US8)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from app.config import ROOT
from app.live.documents import parse_pdf
from app.live.materials import DatasetFiles

DATASETS = ROOT / "datasets"
CLEAN = DATASETS / "clean-run"
FAILURES = ("planted-inconsistency", "missing-sheet", "missing-price", "not-ready")


def text_of(path: Path) -> str:
    return " ".join(" ".join(page.text for page in parse_pdf(path)).split())


def prices(folder: Path) -> list[dict[str, str]]:
    with (folder / "fixtures" / "supplier-prices.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.mark.parametrize("name", FAILURES)
def test_curated_legible_and_dash_free(name: str) -> None:
    files = DatasetFiles(DATASETS / name)
    assert files.is_curated()
    for path in files.request_files() + files.drawing_files():
        pages = parse_pdf(path)
        assert pages and all(page.confidence >= 0.7 for page in pages), path
        body = "".join(page.text for page in pages)
        assert chr(0x2014) not in body and chr(0x2013) not in body, path
    readme = (DATASETS / name / "README.md").read_text(encoding="utf-8")
    assert "Planted defect:" in readme and "Expected exit:" in readme and "[SHEET TBD]" not in readme


def test_planted_inconsistency_disagrees_on_one_rating_only() -> None:
    folder = DATASETS / "planted-inconsistency"
    schedule = text_of(folder / "inputs" / "drawings" / "E-002.pdf")
    single_line = text_of(folder / "inputs" / "drawings" / "E-001.pdf")
    assert "Main: 200 A main breaker" in schedule and "225 A main breaker" not in schedule
    assert "225 A main breaker" in single_line
    assert "agree" not in schedule.lower() and "agree with panel schedule" not in single_line
    assert "225 A main breaker" in text_of(folder / "inputs" / "division-26-specification.pdf")
    for sheet in ("E-000", "E-101", "E-102"):
        assert text_of(folder / "inputs" / "drawings" / f"{sheet}.pdf") == text_of(
            CLEAN / "inputs" / "drawings" / f"{sheet}.pdf"
        )
    assert prices(folder) == prices(CLEAN)


def test_missing_sheet_names_lp2_without_its_schedule() -> None:
    folder = DATASETS / "missing-sheet"
    files = DatasetFiles(folder)
    assert [p.stem for p in files.drawing_files()] == ["E-000", "E-001", "E-002", "E-101", "E-102"], (
        "E-003 is absent"
    )
    assert "LP-2" in text_of(folder / "inputs" / "drawings" / "E-001.pdf")
    assert "See schedule E-003" in text_of(folder / "inputs" / "drawings" / "E-001.pdf")
    assert "E-003 Panel Schedule LP-2" in text_of(folder / "inputs" / "drawings" / "E-000.pdf")
    assert "LP-2-1" in text_of(folder / "inputs" / "drawings" / "E-102.pdf")
    assert "Panel Schedule LP-2" in text_of(folder / "inputs" / "invitation-to-tender.pdf")


def test_missing_price_lacks_exactly_the_exit_sign() -> None:
    clean = {row["description"] for row in prices(CLEAN)}
    derived = {row["description"] for row in prices(DATASETS / "missing-price")}
    assert clean - derived == {"Exit sign, LED"} and derived <= clean
    assert "Exit sign, LED" in text_of(DATASETS / "missing-price" / "inputs" / "drawings" / "E-000.pdf")


def test_not_ready_has_no_deadline_and_no_specification() -> None:
    folder = DATASETS / "not-ready"
    request = text_of(folder / "inputs" / "invitation-to-tender.pdf")
    assert "2027" not in request and "Tenders close" not in request
    assert "will be issued by addendum" in request
    assert "the Division 26 specification issued with it" in request
    assert not (folder / "inputs" / "division-26-specification.pdf").exists()
    assert [p.name for p in DatasetFiles(folder).request_files()] == ["invitation-to-tender.pdf"]
