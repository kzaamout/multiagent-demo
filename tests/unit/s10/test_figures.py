"""Numbers checked where they are born (spec 010, phase 1.7).

Every case here is one the recorded runs produced: a lookup that failed while the seat priced every line
itself, a price on a line the fixture does not carry, a drawing reference shared by several lines, a
material repeated across groups, a description the seat shortened, and a total copied from the worked
example in the Writer's instructions.
"""

from __future__ import annotations

from typing import Any

from app.live.figures import (
    amounts_not_in_context,
    estimator_disagreements,
    number,
    numbers_in,
    pricing_disagreements,
    quantity_handover_disagreements,
    summarise,
)

LOOKUP: dict[str, Any] = {
    "lines": [
        {
            "line_ref": "E-001 detail 3",
            "description": "Dry-type transformer, 75 kVA",
            "quantity": "1",
            "status": "priced",
            "unit_price": "6450.00",
            "extended": "6450.00",
        },
        {
            "line_ref": "E-001 detail 3",
            "description": "42-circuit panelboard, 225A, surface",
            "quantity": "1",
            "status": "priced",
            "unit_price": "1890.00",
            "extended": "1890.00",
        },
        {
            "line_ref": "E-101",
            "description": "2x4 LED troffer, reading room",
            "quantity": "12",
            "status": "unpriced",
            "unit_price": None,
            "extended": None,
        },
    ],
    "totals": {"material": "8340.00", "markup": "1251.00", "labour": "2090.00", "total": "11681.00"},
}
SUMMARY = {"material": 8340.0, "markup": "1,251.00", "labour": 2090, "total": "$11,681.00", "currency": "CAD"}


def priced(description: str, price: Any, extended: Any, ref: str = "E-001 detail 3") -> dict[str, Any]:
    return {"line_ref": ref, "description": description, "unit_price": price, "extended": extended}


GOOD: list[dict[str, Any]] = [
    priced("Dry-type transformer, 75 kVA", 6450.0, "6,450.00"),
    priced("42-circuit panelboard, 225A, surface", "1890", 1890.0),
]


def test_a_faithful_copy_passes_however_the_numbers_are_written() -> None:
    assert pricing_disagreements(GOOD, SUMMARY, [("price_list_lookup", LOOKUP)]) == []


def test_a_failed_lookup_supports_no_price() -> None:
    """The five runs: the call errored, so nothing was kept, and every price was the model's own."""
    problems = pricing_disagreements(GOOD, SUMMARY, [])
    assert len(problems) == 1 and "returned no result" in problems[0]
    assert "call it again" in problems[0], "the seat is told how to recover, not only that it failed"


def test_an_invented_price_is_named_with_the_right_value() -> None:
    lines = [priced("Dry-type transformer, 75 kVA", 4500.0, 4500.0), GOOD[1]]
    problems = pricing_disagreements(lines, SUMMARY, [("price_list_lookup", LOOKUP)])
    assert any("unit_price is 4500.0, the lookup returned 6450.00" in p for p in problems)


def test_lines_sharing_a_drawing_reference_are_not_confused() -> None:
    """Both lines carry the reference E-001 detail 3. Keyed on the reference alone, the transformer was
    held against the panelboard's price and an honest reply was refused."""
    assert pricing_disagreements(GOOD, SUMMARY, [("price_list_lookup", LOOKUP)]) == []


def test_a_price_on_a_line_the_fixture_does_not_carry() -> None:
    lines = [*GOOD, priced("2x4 LED troffer, reading room", 185.0, 2220.0, ref="E-101")]
    problems = pricing_disagreements(lines, SUMMARY, [("price_list_lookup", LOOKUP)])
    assert any("returned it unpriced" in p and "exceptions" in p for p in problems)


def test_an_unpriced_line_reported_without_a_price_is_fine() -> None:
    lines = [*GOOD, priced("2x4 LED troffer, reading room", None, None, ref="E-101")]
    assert pricing_disagreements(lines, SUMMARY, [("price_list_lookup", LOOKUP)]) == []


def test_a_field_left_out_is_not_an_invented_number() -> None:
    lines = [
        {"line_ref": "E-001 detail 3", "description": "Dry-type transformer, 75 kVA", "extended": "6450.00"}
    ]
    assert pricing_disagreements(lines, SUMMARY, [("price_list_lookup", LOOKUP)]) == []


def test_a_shortened_description_still_finds_its_line() -> None:
    lines = [priced("Dry-type transformer", 6450, 6450, ref="T1")]
    assert pricing_disagreements(lines, SUMMARY, [("price_list_lookup", LOOKUP)]) == []


def test_a_line_never_sent_to_the_tool() -> None:
    lines = [priced("Fire alarm panel", 900, 900, ref="FA-1")]
    problems = pricing_disagreements(lines, SUMMARY, [("price_list_lookup", LOOKUP)])
    assert any("never sent to price_list_lookup" in p for p in problems)


def test_totals_that_add_up_but_are_not_the_tools() -> None:
    """The owner's question: numbers that sum correctly prove nothing about where they came from."""
    summary = {"material": 8000.0, "markup": 1200.0, "labour": 2000.0, "total": 11200.0}
    problems = pricing_disagreements(GOOD, summary, [("price_list_lookup", LOOKUP)])
    assert len(problems) == 4 and all("the lookup returned" in p for p in problems)


def test_totals_must_come_from_one_call_that_priced_every_line() -> None:
    first = {"lines": [LOOKUP["lines"][0]], "totals": LOOKUP["totals"]}
    second = {"lines": [LOOKUP["lines"][1]]}
    problems = pricing_disagreements(
        GOOD, SUMMARY, [("price_list_lookup", first), ("price_list_lookup", second)]
    )
    assert any("no single price_list_lookup call" in p for p in problems)


def test_a_later_call_wins_over_an_earlier_one() -> None:
    stale = {"lines": [{**LOOKUP["lines"][0], "unit_price": "1.00", "extended": "1.00"}]}
    assert (
        pricing_disagreements(GOOD, SUMMARY, [("price_list_lookup", stale), ("price_list_lookup", LOOKUP)])
        == []
    )


ESTIMATOR_BOM: list[dict[str, Any]] = [
    {"group": "Lighting", "description": "EMT 21 mm", "quantity": 347.3, "unit": "metre"},
    {"group": "Power", "description": "EMT 21 mm", "quantity": 20.8, "unit": "metre"},
    {
        "group": "Power",
        "description": "Duplex receptacle 15A with box and device",
        "quantity": 9,
        "unit": "each",
    },
]


def test_a_material_repeated_across_groups_matches_either_line() -> None:
    lines: list[dict[str, Any]] = [
        {"description": "EMT 21 mm", "quantity": 20.8},
        {"description": "EMT 21 mm", "quantity": "347.3"},
    ]
    assert quantity_handover_disagreements(lines, ESTIMATOR_BOM) == []


def test_a_quantity_that_is_not_the_estimators() -> None:
    lines = [{"description": "Duplex receptacle", "quantity": 32.0}]
    problems = quantity_handover_disagreements(lines, ESTIMATOR_BOM)
    assert problems == ["Duplex receptacle: your quantity is 32.0, the Estimator's is 9"]


def test_a_line_the_estimator_never_produced() -> None:
    problems = quantity_handover_disagreements(
        [{"description": "Fire alarm panel", "quantity": 1}], ESTIMATOR_BOM
    )
    assert "not a line of the Estimator's bill of materials" in problems[0]


def test_handover_is_silent_without_a_quantity_or_a_takeoff() -> None:
    assert quantity_handover_disagreements([{"description": "EMT 21 mm"}], ESTIMATOR_BOM) == []
    assert quantity_handover_disagreements([{"description": "EMT 21 mm", "quantity": 1}], []) == []


CALCULATOR: dict[str, Any] = {
    "lines": [
        {"description": "2x4 LED troffer", "unit": "each", "quantity_with_waste": "25", "hours": "18.00"},
        {"description": "Duplex receptacle 15A", "unit": "each", "quantity_with_waste": "9", "hours": "4.00"},
    ],
    "hours_by_group": {"Lighting": "18.00", "Branch circuits and devices": "4.00"},
    "total_hours": "22.00",
}
BOM: list[dict[str, Any]] = [
    {"description": "2x4 LED troffer", "quantity": 25, "unit": "each"},
    {"description": "Duplex receptacle 15A", "quantity": "9", "unit": "each"},
]
LABOUR = {"total_hours": 22.0, "by_group": {"Lighting": 18.0, "Branch circuits and devices": 4}}


def test_a_takeoff_copied_from_the_calculator_passes() -> None:
    assert estimator_disagreements(BOM, LABOUR, [("quantity_calculate", CALCULATOR)]) == []


def test_a_failed_calculator_call_supports_no_quantity() -> None:
    problems = estimator_disagreements(BOM, LABOUR, [("price_list_lookup", LOOKUP)])
    assert len(problems) == 1 and "quantity_calculate returned no result" in problems[0]


def test_a_quantity_without_its_waste_is_named() -> None:
    bom = [{"description": "2x4 LED troffer", "quantity": 24, "unit": "each"}, BOM[1]]
    problems = estimator_disagreements(bom, LABOUR, [("quantity_calculate", CALCULATOR)])
    assert problems[0] == "2x4 LED troffer: your quantity is 24, quantity_calculate returned 25 with waste"
    assert len(problems) == 2 and "call quantity_calculate again with the corrected line" in problems[1], (
        "run c5a27415: the seat's 1 panelboard was right and the call was wrong, and it was never told it could fix the call"
    )


def test_a_reworded_line_stands_when_its_number_came_from_the_tool() -> None:
    bom = [{"description": "LED lay-in fixture, 600 by 1200", "quantity": 25, "unit": "each"}, BOM[1]]
    labour = {"total_hours": 22.0}
    assert estimator_disagreements(bom, labour, [("quantity_calculate", CALCULATOR)]) == []


def test_a_reworded_line_with_a_number_the_tool_never_produced() -> None:
    bom = [{"description": "LED lay-in fixture", "quantity": 31, "unit": "each"}]
    problems = estimator_disagreements(bom, {"total_hours": 22.0}, [("quantity_calculate", CALCULATOR)])
    assert any("is not a figure quantity_calculate returned" in p for p in problems)


def test_labour_hours_the_tool_never_produced() -> None:
    labour = {"total_hours": 30, "by_group": {"Lighting": 26, "Branch circuits and devices": 4}}
    problems = estimator_disagreements(BOM, labour, [("quantity_calculate", CALCULATOR)])
    assert any("total_hours is 30" in p for p in problems) and any(
        "by_group Lighting is 26" in p for p in problems
    )


def test_hours_split_over_two_calls_may_be_the_sum_of_the_matched_lines() -> None:
    first = {
        "lines": [CALCULATOR["lines"][0]],
        "hours_by_group": {"Lighting": "18.00"},
        "total_hours": "18.00",
    }
    second = {"lines": [CALCULATOR["lines"][1]], "hours_by_group": {"Devices": "4.00"}, "total_hours": "4.00"}
    results = [("quantity_calculate", first), ("quantity_calculate", second)]
    assert estimator_disagreements(BOM, {"total_hours": 22}, results) == []


CONTEXT = (
    '## Pricing output (source id: pricing)\n{"cost_summary": {"material": 18328.11, "total": 21077.33}, '
    '"rates_used": [{"name": "labour", "value": 95.5}], "lead": [120,208], "none": 0.0}\n'
    "## Brief (source id: brief)\nBid security of $5,000.00 is required."
)


def test_amounts_the_writer_was_given_pass_however_they_are_written() -> None:
    assert (
        amounts_not_in_context(["$21,077.33", "$18,328.11", "$95.50", "$0.00", "$5,000", "$95.5."], CONTEXT)
        == []
    )


def test_an_amount_copied_from_the_worked_example_is_caught() -> None:
    """Run 35f4f6ff: Pricing's total was 21,077.33 and the draft said 36,882.58, the figure in the
    Writer's own instructions. It carried a valid tag, so the old rule passed it."""
    assert amounts_not_in_context(["$36,882.58", "$21,077.33"], CONTEXT) == ["$36,882.58"]


def test_a_rounded_or_mistyped_amount_is_caught() -> None:
    assert amounts_not_in_context(["$21,077", "$21,077.331"], CONTEXT) == ["$21,077", "$21,077.331"]


def test_a_list_of_numbers_is_read_both_ways() -> None:
    """[120,208] is two numbers in JSON and would be one amount in a sentence. The text cannot say which,
    so both readings are held, and neither hides the members of the list."""
    assert {number("120"), number("208"), number("120208")} <= numbers_in(CONTEXT)
    assert amounts_not_in_context(["$120.00", "$208"], CONTEXT) == []


def test_many_disagreements_become_one_short_refusal() -> None:
    assert summarise([]) is None
    text = summarise([f"line {i}" for i in range(9)], limit=3)
    assert text == "line 0; line 1; line 2; and 6 more of the same kind"


def test_hours_written_by_the_seat_when_the_tool_rolled_up_none() -> None:
    """Run cb5027fc: no unit_hours were passed, the tool returned 0, and the seat wrote 350.64 hours of its
    own. The refusal has to say how to fix the call, because saying only that the figures differ brought
    the same reply back twice and the run stopped."""
    empty = {**CALCULATOR, "hours_by_group": {}, "total_hours": "0"}
    labour = {"total_hours": 350.64, "by_group": {"Lighting": 40.5}}
    problems = estimator_disagreements(BOM, labour, [("quantity_calculate", empty)])
    assert (
        len(problems) == 1
        and "matched the unit labour hours table" in problems[0]
        and "Call it again" in problems[0]
    )
    assert estimator_disagreements(BOM, {"total_hours": 0}, [("quantity_calculate", empty)]) == []


def test_a_trailing_zero_dropped_by_json_is_the_same_amount() -> None:
    """Run e60f2c88: a near perfect takeoff, and a correct draft refused three times because Pricing's
    labour reached the Writer as 13284.8 and the draft said $13,284.80. The run stopped."""
    from app.live.deterministic import money_disagreements, sources_of_figure

    context = (
        '## Pricing output (source id: pricing)\n{"labour": 13284.8, "total": 39110.1, "markup": 3368.52}'
    )
    assert sources_of_figure("$13,284.80", context) == ["pricing"]
    draft = "Labour {{$13,284.80|src:pricing}}, total {{$39,110.10|src:pricing}}, markup {{$3,368.52|src:pricing}}."
    assert money_disagreements(draft, context) == []
    assert amounts_not_in_context(["$13,284.80", "$39,110.10"], context) == []


def test_an_amount_written_to_the_cent_stands_when_upstream_rounds_to_it() -> None:
    context = '## Pricing output (source id: pricing)\n{"total": 19127.017, "markup": 2494.839}'
    assert amounts_not_in_context(["$19,127.02", "$2,494.84"], context) == []
    assert amounts_not_in_context(["$19,127.03", "$19,127", "$19,127.0171"], context) == [
        "$19,127.03",
        "$19,127",
        "$19,127.0171",
    ]


def test_the_reviewer_is_told_what_was_checked_and_never_what_to_find() -> None:
    """Owner decision 2026-09-19: say the engine checked, do not tell the Reviewer to hold back a finding."""
    from app.live.figures import verified_note

    note = verified_note(
        {"material": 20481.23, "markup": "3072.18", "labour": 13095.75, "total": "36,649.16"}
    )
    assert "material 20,481.23 + markup 3,072.18 + labour 13,095.75 = total 36,649.16" in note
    assert "did not check any other sum" in note, "the limits of the check are stated as plainly as the check"
    for forbidden in ("do not raise", "do not report", "ignore", "skip", "need not"):
        assert forbidden not in note.lower()
    partial = verified_note({"material": 1, "total": None})
    assert "The price tool computed" not in partial, "a sum is only stated when all four figures are there"
    assert "The price tool computed" not in verified_note(None)
