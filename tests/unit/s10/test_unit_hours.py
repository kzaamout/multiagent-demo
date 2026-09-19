"""The calculator owns the unit labour hours table (spec 010, plan item 1.9).

In 36 of 119 recorded takeoffs the seat passed no unit hours, the tool rolled up 0, and the seat wrote a
labour total of its own, from 20 to 875 hours on jobs of about 120. The table is a lookup, so the tool
does it.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.tools.quantity import QuantityItem, calculate
from app.tools.unit_hours import UnitHourRow, hours_for, table_from_conventions

CONVENTIONS = Path(__file__).resolve().parents[3] / "config" / "electrical-bid" / "estimating-conventions.md"
TABLE = table_from_conventions(CONVENTIONS)


def found(description: str, unit: str = "each") -> str | None:
    row = hours_for(description, unit, TABLE)
    return None if row is None else row.item


def test_the_table_is_read_from_the_conventions_the_seat_also_reads() -> None:
    assert UnitHourRow("2x4 LED troffer", "each", Decimal("0.75")) in TABLE
    assert len(TABLE) >= 10 and all(row.hours > 0 for row in TABLE)


def test_a_file_with_no_table_gives_no_rows(tmp_path: Path) -> None:
    plain = tmp_path / "conventions.md"
    plain.write_text("## Waste\n| Item | Rate |\n|---|---|\n| wire | 0.05 |\n", encoding="utf-8")
    assert table_from_conventions(plain) == []


def test_descriptions_as_seats_really_wrote_them_find_their_row() -> None:
    assert (
        found("Duplex receptacle, 15A, incl. box and device")
        == "Duplex receptacle, 15A, incl. box and device"
    )
    assert found("Duplex receptacle") == "Duplex receptacle, 15A, incl. box and device"
    assert found("2x4 LED troffer, reading room") == "2x4 LED troffer"
    assert found("M10 EMT 21 mm", "metre") == "EMT 21 mm, run"
    assert found("EMT 21 mm (branch circuits)", "m") == "EMT 21 mm, run"
    assert found("M6 20A branch circuit breaker") == "20A branch circuit breaker, install"
    assert found("Feeder F1, 3C plus ground, 100A in EMT", "metre") == "Feeder, 3C plus ground, 100A in EMT"


def test_a_near_miss_gets_no_hours_rather_than_the_wrong_ones() -> None:
    """A wrong figure stated with the table's authority is worse than a line flagged as having none."""
    assert found("EMT 35 mm", "metre") is None
    assert found("30-circuit panelboard, 100A, surface") is None
    assert found("Feeder, 4C plus ground, 100A in EMT", "metre") is None
    assert found("Panelboard") is None, "one word is a category, not a material"
    assert found("") is None


def test_a_length_is_never_given_a_per_item_figure() -> None:
    assert found("Copper conductor #12 THHN", "each") is None
    assert found("Copper conductor #12 THHN", "metre") == "Copper conductor #12 THHN"


def item(description: str, count: int, unit: str = "each", unit_hours: str | None = None) -> QuantityItem:
    hours = None if unit_hours is None else Decimal(unit_hours)
    return QuantityItem(description, unit, "fixture", (Decimal(count),), "Lighting", hours)


def test_hours_come_from_the_table_when_the_seat_passes_none() -> None:
    """The failure itself: no unit hours in the call used to mean 0 hours out."""
    result = calculate([item("2x4 LED troffer", 24)], TABLE)
    assert result.total_hours == Decimal("18.00")
    assert result.lines[0].hours_source == "table: 2x4 LED troffer"


def test_the_table_wins_over_a_figure_the_seat_passed() -> None:
    """One recorded takeoff came to 2,927 hours on unit hours the seat supplied."""
    result = calculate([item("2x4 LED troffer", 24, unit_hours="9.5")], TABLE)
    assert result.total_hours == Decimal("18.00") and result.lines[0].unit_hours == Decimal("0.75")


def test_a_line_the_table_does_not_list_says_so() -> None:
    result = calculate(
        [item("EMT 35 mm", 40, unit="metre"), item("Occupancy sensor", 6, unit_hours="0.5")], TABLE
    )
    assert [line.hours_source for line in result.lines] == ["none", "seat"]
    assert result.lines[0].hours is None and result.total_hours == Decimal("3.00")


def test_without_a_table_the_calculator_behaves_as_it_always_did() -> None:
    assert calculate([item("2x4 LED troffer", 24)]).total_hours == Decimal("0")
    assert calculate([item("2x4 LED troffer", 24, unit_hours="0.75")]).total_hours == Decimal("18.00")
