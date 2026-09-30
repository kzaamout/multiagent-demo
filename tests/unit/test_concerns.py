"""A draft must carry every specialist concern that names a sheet (owner decision 23)."""

from __future__ import annotations

from app.live.concerns import assumptions_section, concern_problems, sheets_in

RATING = {
    "text": "Main breaker rating disagrees between sheets: E-001 shows 225 A, E-002 states 200 A.",
    "drawing_ref": "E-001, E-002",
}
RULE = {"text": "Branch circuit lengths use the 25 m per circuit rule.", "drawing_ref": ""}


def test_sheet_ids_are_read_from_a_drawing_reference() -> None:
    assert sheets_in("E-001, E-002") == ["E-001", "E-002"]
    assert sheets_in("E-001 single-line; E-002 panel schedule; E-000 materials") == [
        "E-001",
        "E-002",
        "E-000",
    ]
    assert sheets_in("A1.0 and E101") == ["E101"]
    assert sheets_in("") == []


def test_assumptions_section_is_cut_at_the_next_heading() -> None:
    md = "# P\n\n## Scope\nx\n\n## Assumptions\n\n- one\n- two\n\n## Exclusions\nnone\n"
    assert assumptions_section(md) == "\n\n- one\n- two\n\n"
    assert assumptions_section("# P\n\n## Scope\nx\n") is None


def test_a_carried_concern_passes_and_a_dropped_one_is_named() -> None:
    carried = "# P\n\n## Assumptions\n\n- The main breaker rating proceeds on E-001 (225 A) against E-002 (200 A) pending confirmation.\n"
    assert concern_problems(carried, [RATING, RULE]) == []
    dropped = "# P\n\n## Assumptions\n\n- Markup is 15 percent.\n\n## Exclusions\nnone\n"
    problems = concern_problems(dropped, [RATING, RULE])
    assert len(problems) == 1
    assert "E-001, E-002" in problems[0] and "Main breaker rating disagrees" in problems[0]
    assert "Assumptions section" in problems[0]


def test_a_concern_without_a_sheet_is_not_checked_and_a_missing_section_is() -> None:
    assert concern_problems("# P\n\nno sections\n", [RULE]) == []
    problems = concern_problems("# P\n\nno sections\n", [RATING])
    assert len(problems) == 1 and "no Assumptions section" in problems[0]


def test_one_sheet_named_is_not_enough() -> None:
    half = "# P\n\n## Assumptions\n\n- E-001 shows 225 A.\n"
    assert len(concern_problems(half, [RATING])) == 1


FILED_ONLY = {
    "text": "Branch circuit conduit and conductor quantities are inferred using the 25 m per circuit rule, "
    "since circuit runs are not dimensioned on the floor plans.",
    "drawing_ref": "E-101, E-102, E-002",
}


def test_a_concern_filed_against_sheets_its_sentence_never_names_is_carried_by_one_of_them() -> None:
    """Run 8b817f67: refused once for a word-for-word copy and once for naming two of three filed sheets,
    and the run stopped. One line in the concern's own words, naming one of the filed sheets, carries it."""
    copied = (
        "# P\n\n## Assumptions\n\n- Branch circuit conduit and conductor quantities are inferred using the "
        "25 m per circuit rule, since circuit runs\nare not dimensioned on the floor plans.\n"
    )
    assert concern_problems(copied, [FILED_ONLY]) == [], "a copy of the concern's own sentence carries it"
    reworded = "# P\n\n## Assumptions\n\n- Conduit and wire use a 25 m run per circuit; runs are not dimensioned on E-101/E-102.\n"
    assert concern_problems(reworded, [FILED_ONLY]) == []
    dropped = "# P\n\n## Assumptions\n\n- Markup is 15 percent.\n"
    problems = concern_problems(dropped, [FILED_ONLY])
    assert len(problems) == 1 and "at least one of E-101, E-102, E-002" in problems[0]


def test_a_line_carrying_another_concern_on_the_same_sheet_does_not_carry_this_one() -> None:
    switches = {
        "text": "Switch count taken from the plan since the schedule does not itemize switches.",
        "drawing_ref": "E-101",
    }
    only_switches = "# P\n\n## Assumptions\n\n- Switch count of 9 taken from E-101 since the schedule does not itemize switches.\n"
    problems = concern_problems(only_switches, [switches, FILED_ONLY])
    assert len(problems) == 1 and "25 m per circuit" in problems[0]


def test_a_copied_sentence_still_needs_every_sheet_it_names() -> None:
    copied = "# P\n\n## Assumptions\n\n- " + RATING["text"] + "\n"
    assert concern_problems(copied, [RATING]) == []
    assert (
        len(
            concern_problems(
                "# P\n\n## Assumptions\n\n- Main breaker rating disagrees between sheets.\n", [RATING]
            )
        )
        == 1
    )
