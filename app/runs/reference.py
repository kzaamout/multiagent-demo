"""A run's price against what the job should cost (owner decision 1b, 2026-09-19).

Accuracy, as the performance report uses the word, says whether a run behaved as its scenario expects: it
reached Work, raised the blocker, carried the concern, passed review. It never looks at a number. A run
that passes review with a price a fifth too high scores as accurate.

This measures the number. For the scenarios whose drawings state their own quantities, the reference price
is what the app's own calculator and price lookup give for those quantities, with the scenario's own
price list. Nothing here is typed in except the counted quantities from the dataset's README: for the
Clean run the computation gives 139.85 hours and 36,882.58, the figures the README states.

Two words used below. The takeoff is the Estimator's output: the list of materials read off the drawings
with a quantity for each, and the labour hours that follow from them. It is not a price. The price
difference is the run's total minus the reference total, as a percentage of the reference.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.tools.price_list import LookupRequest, PriceList, totals
from app.tools.quantity import Category, QuantityItem, calculate
from app.tools.unit_hours import table_from_conventions

ROOT = Path(__file__).resolve().parents[2]
CONVENTIONS = ROOT / "config" / "electrical-bid" / "estimating-conventions.md"
SUPPLIER_ORDER = ["Supplier A", "Supplier B", "Supplier C"]
MARKUP_RATE = Decimal("0.15")
LABOUR_RATE = Decimal("95")
LONG_LEAD_DAYS = 28

# Counted quantities before waste, from the Reference figures table in datasets/clean-run/README.md.
CLEAN_RUN_COUNTS: tuple[tuple[str, str, Category, int], ...] = (
    ("2x4 LED troffer", "each", "fixture", 45),
    ("Exit sign, LED", "each", "fixture", 4),
    ("Emergency battery unit with heads", "each", "fixture", 3),
    ("Single-pole switch", "each", "device", 9),
    ("Duplex receptacle, 15A, incl. box and device", "each", "device", 30),
    ("20A branch circuit breaker", "each", "equipment", 15),
    ("42-circuit panelboard, 225A, surface", "each", "equipment", 1),
    ("Dry-type transformer, 75 kVA", "each", "equipment", 1),
    ("Feeder, 3C plus ground, 100A in EMT", "metre", "conduit", 18),
    ("EMT 21 mm", "metre", "conduit", 275),
    ("Copper conductor #12 THHN", "metre", "wire", 825),
)
# Scenarios built on the Clean run's drawings, per their READMEs. Missing sheet adds a panel whose
# schedule is absent and ends in an escalation, so it has no price to be right about.
SAME_DRAWINGS = ("clean-run", "planted-inconsistency", "missing-price")


def _number(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value).replace("$", "").replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None


def _key(text: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


@lru_cache(maxsize=8)
def reference(dataset_id: str, datasets_dir: Path) -> dict[str, Any] | None:
    """What the job should cost, from the app's own tools, or None for a scenario with no reference."""
    fixture = datasets_dir / dataset_id / "fixtures" / "supplier-prices.csv"
    if dataset_id not in SAME_DRAWINGS or not fixture.is_file() or not CONVENTIONS.is_file():
        return None
    items = [
        QuantityItem(description, unit, category, (Decimal(count),), "reference")
        for description, unit, category, count in CLEAN_RUN_COUNTS
    ]
    taken = calculate(items, table_from_conventions(CONVENTIONS))
    requests = [
        LookupRequest(str(i), line.description, line.quantity_with_waste, line.unit)
        for i, line in enumerate(taken.lines)
    ]
    priced = PriceList.from_csv(fixture).lookup(
        requests, supplier_order=SUPPLIER_ORDER, long_lead_days=LONG_LEAD_DAYS
    )
    total = totals(priced, markup_rate=MARKUP_RATE, labour_hours=taken.total_hours, labour_rate=LABOUR_RATE)
    return {
        "total": total.total,
        "material": total.material,
        "labour_hours": taken.total_hours,
        "quantities": {_key(line.description): line.quantity_with_waste for line in taken.lines},
    }


def _percent(estimate: Decimal | None, truth: Decimal) -> float | None:
    if estimate is None or truth == 0:
        return None
    return round(float((estimate - truth) / truth * 100), 1)


def _latest(events: Iterable[Any], agent_id: str) -> Mapping[str, Any]:
    found: Mapping[str, Any] = {}
    for event in events:
        if event.type == "task.completed" and event.payload.get("agent_id") == agent_id:
            result = event.payload.get("result")
            if isinstance(result, Mapping):
                found = result
    return found


def price_check(dataset_id: str, events: Iterable[Any], datasets_dir: Path) -> dict[str, Any] | None:
    """The run's figures beside the reference, with each difference as a percentage of the reference.

    None when the scenario has no reference. A run that never priced still reports its takeoff.
    """
    truth = reference(dataset_id, datasets_dir)
    if truth is None:
        return None
    history = list(events)
    takeoff, pricing = _latest(history, "estimator"), _latest(history, "pricing")
    if not takeoff.get("bom") and not pricing:
        return None
    got: dict[str, Decimal] = {}
    for line in takeoff.get("bom") or []:
        quantity = _number(line.get("quantity"))
        if quantity is not None:
            key = _key(re.sub(r"^[A-Za-z]{1,2}-?\d{1,3}[\s:.)-]+", "", str(line.get("description", ""))))
            got[key] = got.get(key, Decimal(0)) + quantity
    wanted: Mapping[str, Decimal] = truth["quantities"]
    right = sum(
        1
        for key, quantity in wanted.items()
        if key in got and abs(got[key] - quantity) <= max(quantity * Decimal("0.011"), Decimal("0.11"))
    )
    summary = pricing.get("cost_summary") if isinstance(pricing.get("cost_summary"), Mapping) else {}
    total = _number((summary or {}).get("total"))
    hours = _number((takeoff.get("labour") or {}).get("total_hours"))
    return {
        "reference_total": float(truth["total"]),
        "total": None if total is None else float(total),
        "total_error_pct": _percent(total, truth["total"]),
        "reference_labour_hours": float(truth["labour_hours"]),
        "labour_hours": None if hours is None else float(hours),
        "labour_hours_error_pct": _percent(hours, truth["labour_hours"]),
        "takeoff_lines_right": right,
        "takeoff_lines": len(wanted),
    }
