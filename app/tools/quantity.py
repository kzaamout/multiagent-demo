"""quantity.calculate: totals, waste factors, and labour roll-up for the Estimator.

Rules from config/electrical-rfp/estimating-conventions.md: 5 percent waste on wire and conduit,
2 percent on devices. Counted items are rounded up to whole units after waste; lengths are
rounded to 0.1 metre. Labour hours use the installed quantity before waste.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

Category = Literal["wire", "conduit", "device", "fixture", "equipment", "other"]

WASTE: dict[str, Decimal] = {
    "wire": Decimal("0.05"),
    "conduit": Decimal("0.05"),
    "device": Decimal("0.02"),
    "fixture": Decimal("0.02"),
    "equipment": Decimal("0"),
    "other": Decimal("0"),
}
COUNT_UNITS = {"each", "ea", "unit", "units", "set", "sets", "lot"}


@dataclass(frozen=True)
class QuantityItem:
    description: str
    unit: str
    category: Category
    counts: tuple[Decimal, ...]
    group: str = "Miscellaneous"
    unit_hours: Decimal | None = None


@dataclass(frozen=True)
class QuantityLine:
    description: str
    unit: str
    group: str
    base_quantity: Decimal
    waste_rate: Decimal
    quantity_with_waste: Decimal
    hours: Decimal | None


@dataclass(frozen=True)
class QuantityResult:
    lines: tuple[QuantityLine, ...]
    hours_by_group: dict[str, Decimal]
    total_hours: Decimal


def _round_quantity(value: Decimal, unit: str) -> Decimal:
    if unit.strip().lower() in COUNT_UNITS:
        return Decimal(math.ceil(value))
    return value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def calculate(items: list[QuantityItem]) -> QuantityResult:
    lines: list[QuantityLine] = []
    hours_by_group: dict[str, Decimal] = {}
    for item in items:
        if any(c < 0 for c in item.counts):
            raise ValueError(f"{item.description}: negative count")
        base = sum(item.counts, Decimal("0"))
        rate = WASTE[item.category]
        with_waste = _round_quantity(base * (Decimal("1") + rate), item.unit)
        hours = None
        if item.unit_hours is not None:
            hours = (base * item.unit_hours).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            hours_by_group[item.group] = hours_by_group.get(item.group, Decimal("0")) + hours
        lines.append(QuantityLine(item.description, item.unit, item.group, base, rate, with_waste, hours))
    total = sum(hours_by_group.values(), Decimal("0"))
    return QuantityResult(tuple(lines), hours_by_group, total)
