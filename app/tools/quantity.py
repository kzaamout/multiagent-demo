"""quantity.calculate: totals, waste factors, and labour roll-up for the Estimator.

Rules from config/electrical-bid/estimating-conventions.md: 5 percent waste on wire and conduit,
2 percent on devices. Counted items are rounded up to whole units after waste; lengths are
rounded to 0.1 metre. Labour hours use the installed quantity before waste.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from app.tools.unit_hours import UnitHourRow, hours_for

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
    each: Decimal | None = None
    """An allowance for every counted thing: 25 metres of conduit for each of 11 circuits."""
    times: Decimal | None = None
    """How many of that allowance each one needs: 3 conductors in every metre of run."""


@dataclass(frozen=True)
class QuantityLine:
    description: str
    unit: str
    group: str
    base_quantity: Decimal
    waste_rate: Decimal
    quantity_with_waste: Decimal
    hours: Decimal | None
    counted: Decimal = Decimal("0")
    """What the counts added to, before any allowance: 11 circuits, not 275 metres."""
    waste_category: str = ""
    unit_hours: Decimal | None = None
    hours_source: str = ""
    """Where the unit hours came from: the table row's name, "seat" for a figure the seat passed because
    the table has no entry, or "none" when the line carries no hours at all."""


@dataclass(frozen=True)
class QuantityResult:
    lines: tuple[QuantityLine, ...]
    hours_by_group: dict[str, Decimal]
    total_hours: Decimal


def _round_quantity(value: Decimal, unit: str) -> Decimal:
    if unit.strip().lower() in COUNT_UNITS:
        return Decimal(math.ceil(value))
    return value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def calculate(items: list[QuantityItem], table: Sequence[UnitHourRow] = ()) -> QuantityResult:
    """Total each line, apply waste, and roll up labour hours.

    Unit hours come from the conventions' table whenever it has a row for the line, whatever the seat
    passed. A seat's own figure is used only for a line the table does not list, and the line says so,
    because the conventions make such a line low confidence.
    """
    lines: list[QuantityLine] = []
    hours_by_group: dict[str, Decimal] = {}
    for item in items:
        if any(c < 0 for c in item.counts):
            raise ValueError(f"{item.description}: negative count")
        # The conventions state lengths as a rule, "25 metres per circuit, three conductors each", and the
        # tool could only add, so the seat multiplied in its head against its own instruction never to. It
        # got conduit right in 18 of 104 recorded takeoffs and wire in 16, usually by repeating the
        # feeder's length or leaving the line out (spec 011, option B).
        counted = sum(item.counts, Decimal("0"))
        base = counted * (item.each or Decimal("1")) * (item.times or Decimal("1"))
        row = hours_for(item.description, item.unit, table)
        # Which class a material belongs to is a lookup, not a judgment. The seat sent breakers as devices,
        # which carry 2 percent waste, so 15 became 16 in 45 of 104 recorded takeoffs; the conventions put
        # them in equipment, which carries none.
        category = row.category if row is not None and row.category in WASTE else item.category
        rate = WASTE[category]
        with_waste = _round_quantity(base * (Decimal("1") + rate), item.unit)
        unit_hours = row.hours if row is not None else item.unit_hours
        source = f"table: {row.item}" if row is not None else "seat" if unit_hours is not None else "none"
        hours = None
        if unit_hours is not None:
            hours = (base * unit_hours).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            hours_by_group[item.group] = hours_by_group.get(item.group, Decimal("0")) + hours
        lines.append(
            QuantityLine(
                item.description,
                item.unit,
                item.group,
                base,
                rate,
                with_waste,
                hours,
                counted,
                category,
                unit_hours,
                source,
            )
        )
    total = sum(hours_by_group.values(), Decimal("0"))
    return QuantityResult(tuple(lines), hours_by_group, total)
