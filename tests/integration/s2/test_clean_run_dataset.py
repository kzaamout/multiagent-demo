"""Integrity of the curated Clean run inputs: everything a live run needs, and no planted defect."""

from __future__ import annotations

import csv
import re
from decimal import Decimal
from pathlib import Path

from app.config import ROOT
from app.live.documents import parse_pdf
from app.live.materials import DatasetFiles
from app.runs.registry import discover_datasets
from app.tools.price_list import LookupRequest, PriceList

FOLDER = ROOT / "datasets" / "clean-run"
SCHEDULED = {
    "2x4 LED troffer": "each",
    "Exit sign, LED": "each",
    "Emergency battery unit with heads": "each",
    "Single-pole switch": "each",
    "Duplex receptacle, 15A, incl. box and device": "each",
    "20A branch circuit breaker": "each",
    "42-circuit panelboard, 225A, surface": "each",
    "Dry-type transformer, 75 kVA": "each",
    "Feeder, 3C plus ground, 100A in EMT": "metre",
    "EMT 21 mm": "metre",
    "Copper conductor #12 THHN": "metre",
}


def text_of(path: Path) -> str:
    return "\n".join(page.text for page in parse_pdf(path))


def test_clean_run_is_curated_and_legible() -> None:
    files = DatasetFiles(FOLDER)
    assert files.is_curated()
    assert [p.stem for p in files.drawing_files()] == ["E-000", "E-001", "E-002", "E-101", "E-102"]
    for path in files.request_files() + files.drawing_files():
        pages = parse_pdf(path)
        assert pages and all(page.confidence >= 0.7 for page in pages), path.name
        body = "\n".join(page.text for page in pages)
        assert chr(0x2014) not in body and chr(0x2013) not in body, path.name


def test_every_scheduled_material_prices_exactly_once_under_long_lead() -> None:
    schedule_text = " ".join(text_of(FOLDER / "inputs" / "drawings" / "E-000.pdf").split())
    prices = PriceList.from_csv(FOLDER / "fixtures" / "supplier-prices.csv")
    requests = [LookupRequest(f"L{i}", d, Decimal(1), u) for i, (d, u) in enumerate(SCHEDULED.items())]
    lines = prices.lookup(
        requests, supplier_order=["Supplier A", "Supplier B", "Supplier C"], long_lead_days=28
    )
    for (description, _), line in zip(SCHEDULED.items(), lines, strict=True):
        assert description in schedule_text, f"{description} not on the materials schedule"
        assert line.status == "priced" and not line.long_lead, description
    with (FOLDER / "fixtures" / "supplier-prices.csv").open(encoding="utf-8", newline="") as handle:
        descriptions = [row["description"] for row in csv.DictReader(handle)]
    assert all(descriptions.count(d) == 1 for d in SCHEDULED), "one listing per scheduled material"


def test_drawings_agree_on_ratings_counts_and_loads() -> None:
    single_line = text_of(FOLDER / "inputs" / "drawings" / "E-001.pdf")
    schedule = text_of(FOLDER / "inputs" / "drawings" / "E-002.pdf")
    for rating in ("225 A main breaker", "120/208 V, 3 phase, 4 wire"):
        assert rating in single_line and rating in schedule
    assert "225 A bus" in single_line and "Bus: 225 A" in schedule
    troffers = sum(int(n) for n in re.findall(r"\((\d+) troffers\)", schedule))
    assert troffers == 45
    receptacle_lines = [line for line in schedule.splitlines() if "Receptacles," in line]
    assert sum(sum(int(n) for n in re.findall(r"\((\d+)\)", line)) for line in receptacle_lines) == 30
    assert "Total connected load" in schedule and "7250" in schedule


def test_request_leaves_exactly_bid_security_open() -> None:
    request = " ".join(text_of(FOLDER / "inputs" / "invitation-to-tender.pdf").split())
    assert "29 January 2027" in request and "No alternates or unit prices" in request
    assert "has not yet confirmed the bid security requirement" in request
    assert "A schedule of values is not required" in request


def test_registry_finds_clean_run_curated() -> None:
    info = next(d for d in discover_datasets(ROOT / "datasets") if d.id == "clean-run")
    assert DatasetFiles(info.folder).is_curated()
