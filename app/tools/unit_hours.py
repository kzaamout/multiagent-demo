"""The unit labour hours table, read from the estimating conventions and applied by the calculator.

The Estimator used to pass unit hours into quantity_calculate itself. In 36 of 119 recorded takeoffs it
passed none, the tool rolled up 0 hours, and the seat wrote a labour total of its own, anywhere from 20 to
875 hours on jobs of about 120. When it did pass them they were its own reading of the table, and one
takeoff came to 2,927 hours. Labour is priced by the hour, so this was the largest silent error in the
price. The table is a lookup, so the tool does it, the same way price_list_lookup owns the prices.

The table lives in one place, the conventions file the seat also reads, and is parsed from there.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

HEADING = re.compile(r"^##\s+(Unit labour hours|Materials)", re.I)
LENGTH_UNITS = {"m", "metre", "metres", "meter", "meters"}
COUNT_UNITS = {"each", "ea", "unit", "units"}


@dataclass(frozen=True)
class UnitHourRow:
    item: str
    unit: str
    hours: Decimal
    category: str = ""
    """The waste class the conventions give this material, empty when the table does not say."""


def _key(text: str) -> str:
    return re.sub(r"[^a-z0-9#]+", " ", text.lower()).strip()


QUALIFIERS = {"run", "install", "incl", "including", "and"}
"""Words the table adds to say what the hours cover. They are not part of the material's name."""


def _words(text: str) -> frozenset[str]:
    return frozenset(_key(text).split()) - QUALIFIERS


def _unit_family(unit: str) -> str:
    name = unit.strip().lower()
    if name in LENGTH_UNITS:
        return "length"
    if name in COUNT_UNITS:
        return "count"
    return name


def table_from_conventions(path: Path) -> list[UnitHourRow]:
    """The rows of the markdown table under the "Unit labour hours" heading. No heading, no rows."""
    rows: list[UnitHourRow] = []
    inside = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            inside = bool(HEADING.match(line))
            continue
        if not inside or not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        # Item | Unit | Hours, or Item | Unit | Category | Hours. The hours are the last cell either way,
        # so a table that gains a column does not need this parser changed again.
        try:
            hours = Decimal(cells[-1])
        except InvalidOperation:
            continue  # the header row and the rule under it
        category = cells[2].lower() if len(cells) >= 4 else ""
        rows.append(UnitHourRow(cells[0], cells[1], hours, category))
    return rows


def hours_for(description: str, unit: str, table: Sequence[UnitHourRow]) -> UnitHourRow | None:
    """The table row for a bill of materials line, or None when the table does not settle it.

    The same description, or one whose words contain the other's: the table says "EMT 21 mm, run" where a
    materials schedule says "EMT 21 mm" and a seat writes "M10 EMT 21 mm (branch circuits)". Every word
    counts, so "EMT 35 mm" and a 30-circuit panelboard find nothing in a table that lists 21 mm and
    42-circuit. The units must be of one kind, so a length is never given a per-item figure.
    When several rows fit, the longest wins, and a tie is no match: a wrong hour figure stated with the
    table's authority is worse than a line flagged as having none.
    """
    wanted = _words(description)
    if not wanted:
        return None
    family = _unit_family(unit)
    same_kind = [row for row in table if _unit_family(row.unit) == family]
    exact = [row for row in same_kind if _key(row.item) == _key(description)]
    if exact:
        return exact[0]
    # One word is a category, not a material: "Panelboard" must not take the 42-circuit row's hours.
    fits = [
        row
        for row in same_kind
        if _words(row.item) <= wanted or (len(wanted) >= 2 and wanted <= _words(row.item))
    ]
    if not fits:
        return None
    fits.sort(key=lambda row: len(_words(row.item)), reverse=True)
    if len(fits) > 1 and len(_words(fits[0].item)) == len(_words(fits[1].item)):
        return None
    return fits[0]
