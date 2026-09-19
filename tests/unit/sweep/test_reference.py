"""A run's price against what the job should cost (owner decision 1b, 2026-09-19)."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.runs.reference import CLEAN_RUN_COUNTS, price_check, reference

ROOT = Path(__file__).resolve().parents[3]
PRICES = {
    "2x4 LED troffer": "142.00",
    "Exit sign, LED": "96.00",
    "Emergency battery unit with heads": "238.00",
    "Single-pole switch": "12.90",
    "Duplex receptacle, 15A, incl. box and device": "18.40",
    "20A branch circuit breaker": "26.75",
    "42-circuit panelboard, 225A, surface": "1890.00",
    "Dry-type transformer, 75 kVA": "6450.00",
    "Feeder, 3C plus ground, 100A in EMT": "48.50",
    "EMT 21 mm": "4.85",
    "Copper conductor #12 THHN": "0.92",
}


@pytest.fixture
def datasets(tmp_path: Path) -> Path:
    """The Clean run's price list as its README gives it, so the test needs no ignored dataset folder."""
    units = {description: unit for description, unit, _, _ in CLEAN_RUN_COUNTS}
    rows = ["item_code,description,unit,price,supplier,lead_time_days"]
    rows += [f'C{i},"{d}",{units[d]},{p},Supplier A,5' for i, (d, p) in enumerate(PRICES.items())]
    for name, body in (("clean-run", rows), ("missing-price", [r for r in rows if "Exit sign" not in r])):
        folder = tmp_path / name / "fixtures"
        folder.mkdir(parents=True)
        (folder / "supplier-prices.csv").write_text("\n".join(body) + "\n", encoding="utf-8")
    reference.cache_clear()
    return tmp_path


def completed(agent_id: str, result: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(type="task.completed", payload={"agent_id": agent_id, "result": result})


def test_the_reference_is_what_the_readme_states(datasets: Path) -> None:
    """Computed by the app's own tools from the counted quantities, never typed in."""
    truth = reference("clean-run", datasets)
    assert truth is not None
    assert truth["total"] == Decimal("36882.58") and truth["labour_hours"] == Decimal("139.85")
    assert truth["material"] == Decimal("20518.98")


def test_a_scenario_with_an_item_the_price_list_lacks_has_its_own_reference(datasets: Path) -> None:
    truth = reference("missing-price", datasets)
    assert truth is not None and truth["total"] == Decimal("36330.58")


def test_a_scenario_with_no_reference_is_not_scored(datasets: Path) -> None:
    assert reference("missing-sheet", datasets) is None
    assert price_check("missing-sheet", [], datasets) is None
    assert price_check("clean-run", [], datasets) is None, (
        "a run that never reached a takeoff has nothing to score"
    )


def test_the_difference_is_a_percentage_of_the_reference(datasets: Path) -> None:
    bom = [
        {"description": "M1 2x4 LED troffer", "quantity": 46},
        {"description": "Exit sign, LED", "quantity": "5"},
        {"description": "EMT 21 mm", "quantity": 200.0},
        {"description": "EMT 21 mm", "quantity": 88.8},
        {"description": "Single-pole switch", "quantity": 26},
    ]
    events = [
        completed("estimator", {"bom": bom, "labour": {"total_hours": 167.82}}),
        completed("pricing", {"cost_summary": {"total": "44,259.10"}}),
    ]
    check = price_check("clean-run", events, datasets)
    assert check is not None
    assert check["total_error_pct"] == 20.0 and check["labour_hours_error_pct"] == 20.0
    assert check["takeoff_lines_right"] == 3, (
        "a schedule mark is ignored and a material split over two lines is summed"
    )
    assert check["takeoff_lines"] == 11


def test_a_run_that_never_priced_still_reports_its_takeoff(datasets: Path) -> None:
    check = price_check(
        "clean-run", [completed("estimator", {"bom": [{"description": "x", "quantity": 1}]})], datasets
    )
    assert check is not None and check["total"] is None and check["total_error_pct"] is None


def test_the_report_keeps_price_apart_from_accuracy() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import model_report

    seat = {"agent_id": "estimator", "calls": 3, "model": "qwen3.5 9b, local"}

    def run(error: float, exit_value: str) -> dict[str, Any]:
        check = {
            "total_error_pct": error,
            "labour_hours_error_pct": error,
            "takeoff_lines_right": 6,
            "takeoff_lines": 11,
        }
        return {"price_check": check, "seats": [seat], "exit": exit_value, "sweep": {}}

    lines = model_report.price_tables([run(-4.0, "reviewer_pass"), run(30.0, "reviewer_pass"), {"seats": []}])
    header = lines[0].split("|")
    row = dict(zip((h.strip() for h in header), (c.strip() for c in lines[2].split("|")), strict=True))
    assert row["Estimator model"] == "qwen3.5 9b, local" and row["Priced runs"] == "2"
    assert row["Median price difference"] == "17.0%", "the sign is ignored for the middle value"
    assert row["Within 5%"] == "1" and row["Lowest"] == "-4.0%" and row["Highest"] == "30.0%"
    assert model_report.price_tables([{"seats": []}]) == [
        "No run on a scenario with a reference price has been recorded yet."
    ]
