"""price_list.lookup: the supplier price fixture for Pricing.

Matching is strict on purpose (the Pricing seat must never substitute a similar item): an exact
item code, or an exact description after normalising case and whitespace. The tool computes
extended costs and totals so the local model copies numbers rather than calculating them
(owner decision, 2026-09-14). Money uses Decimal and rounds half up to cents.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

CENT = Decimal("0.01")
REQUIRED_COLUMNS = ("item_code", "description", "unit", "price", "supplier", "lead_time_days")


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class FixtureRow:
    item_code: str
    description: str
    unit: str
    price: Decimal
    supplier: str
    lead_time_days: int


@dataclass(frozen=True)
class LookupRequest:
    line_ref: str
    description: str
    quantity: Decimal
    unit: str
    item_code: str | None = None


@dataclass(frozen=True)
class PricedLine:
    line_ref: str
    description: str
    quantity: Decimal
    unit: str
    status: str  # priced, unpriced, unit_mismatch
    unit_price: Decimal | None
    extended: Decimal | None
    supplier: str | None
    lead_time_days: int | None
    long_lead: bool


@dataclass(frozen=True)
class Totals:
    material: Decimal
    markup_rate: Decimal
    markup: Decimal
    labour_hours: Decimal
    labour_rate: Decimal
    labour: Decimal
    total: Decimal


class PriceList:
    def __init__(self, rows: list[FixtureRow]) -> None:
        self.rows = rows
        self._by_code: dict[str, list[FixtureRow]] = {}
        self._by_description: dict[str, list[FixtureRow]] = {}
        for row in rows:
            self._by_code.setdefault(_norm(row.item_code), []).append(row)
            self._by_description.setdefault(_norm(row.description), []).append(row)

    @classmethod
    def from_csv(cls, path: Path) -> PriceList:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(f"{path.name}: missing columns {missing}")
            rows = [
                FixtureRow(
                    item_code=r["item_code"].strip(),
                    description=r["description"].strip(),
                    unit=r["unit"].strip(),
                    price=Decimal(r["price"].strip()),
                    supplier=r["supplier"].strip(),
                    lead_time_days=int(r["lead_time_days"].strip()),
                )
                for r in reader
            ]
        return cls(rows)

    def _candidates(self, request: LookupRequest) -> list[FixtureRow]:
        if request.item_code:
            found = self._by_code.get(_norm(request.item_code), [])
            if found:
                return found
        return self._by_description.get(_norm(request.description), [])

    def lookup(
        self,
        requests: list[LookupRequest],
        *,
        supplier_order: list[str],
        long_lead_days: int,
    ) -> list[PricedLine]:
        rank = {_norm(name): i for i, name in enumerate(supplier_order)}
        results: list[PricedLine] = []
        for request in requests:
            candidates = sorted(
                self._candidates(request), key=lambda r: rank.get(_norm(r.supplier), len(rank))
            )
            if not candidates:
                results.append(
                    PricedLine(
                        request.line_ref,
                        request.description,
                        request.quantity,
                        request.unit,
                        "unpriced",
                        None,
                        None,
                        None,
                        None,
                        False,
                    )
                )
                continue
            row = candidates[0]
            if _norm(row.unit) != _norm(request.unit):
                results.append(
                    PricedLine(
                        request.line_ref,
                        request.description,
                        request.quantity,
                        request.unit,
                        "unit_mismatch",
                        row.price,
                        None,
                        row.supplier,
                        row.lead_time_days,
                        row.lead_time_days > long_lead_days,
                    )
                )
                continue
            results.append(
                PricedLine(
                    request.line_ref,
                    request.description,
                    request.quantity,
                    request.unit,
                    "priced",
                    row.price,
                    _money(request.quantity * row.price),
                    row.supplier,
                    row.lead_time_days,
                    row.lead_time_days > long_lead_days,
                )
            )
        return results


def totals(
    lines: list[PricedLine], *, markup_rate: Decimal, labour_hours: Decimal, labour_rate: Decimal
) -> Totals:
    material = _money(sum((line.extended for line in lines if line.extended is not None), Decimal("0")))
    markup = _money(material * markup_rate)
    labour = _money(labour_hours * labour_rate)
    return Totals(
        material, markup_rate, markup, labour_hours, labour_rate, labour, _money(material + markup + labour)
    )
