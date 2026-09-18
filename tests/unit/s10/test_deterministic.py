"""Work the engine does exactly, so a seat is not asked to remember or judge it (spec 010).

Each check has a negative case here, because the danger in every one of them is firing when it should
not: refusing a real blocker, attributing a figure to the wrong specialist, or demanding a concern the
draft already carries.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.live.deterministic import (
    assumptions_block,
    blocker_names_a_present_sheet,
    sources_of_figure,
    tag_advice,
)

CONTEXT = (
    "## Brief (source id: brief)\n"
    "Panel LP-1 is rated 225 A.\n"
    "## Estimator output (source id: takeoff)\n"
    "225 A panel, 47 lines, labour 96.5 hours.\n"
    "## Pricing output (source id: pricing)\n"
    "material $20,518.98, labour $3,077.85, total $36,882.58, 96.5 hours of labour\n"
)


def prepared(*sheet_numbers: str) -> SimpleNamespace:
    return SimpleNamespace(sheets=[SimpleNamespace(sheet_number=n, sheet_id=n) for n in sheet_numbers])


def test_a_blocker_for_a_sheet_the_run_holds_goes_back_with_the_evidence() -> None:
    refusal = blocker_names_a_present_sheet(
        "Panel LP-1 schedule E-002 is missing from the drawing set; single-line E-001 shows LP-1.",
        prepared("E-000", "E-001", "E-002"),
    )
    assert refusal is not None
    assert "E-002" in refusal and "in the drawing set" in refusal
    assert "vision_read_drawing" in refusal, "it is told what to do instead of blocking"


def test_a_blocker_for_a_sheet_that_really_is_absent_stands() -> None:
    """Missing sheet exists to produce this blocker, so the check must not touch it."""
    assert (
        blocker_names_a_present_sheet(
            "Panel schedule E-003 for LP-2 is missing from the drawing set.",
            prepared("E-000", "E-001", "E-002"),
        )
        is None
    )


def test_a_blocker_is_left_alone_when_nothing_has_been_prepared_yet() -> None:
    assert blocker_names_a_present_sheet("E-002 is missing", prepared()) is None
    assert blocker_names_a_present_sheet("", prepared("E-002")) is None


def test_a_figure_in_exactly_one_output_gets_the_tag_to_write() -> None:
    advice = tag_advice(["$36,882.58"], CONTEXT)
    assert advice == "write these exactly: {{$36,882.58|src:pricing}}"


def test_a_figure_in_two_outputs_is_not_attributed_for_the_writer() -> None:
    """Guessing here would put a wrong source on a number and look authoritative doing it."""
    assert sources_of_figure("96.5", CONTEXT) == ["pricing", "takeoff"]
    advice = tag_advice(["96.5"], CONTEXT)
    assert advice is not None
    assert "appears in pricing and takeoff" in advice and "choose" in advice
    assert "src:" not in advice, "no tag is offered when the source is ambiguous"


def test_a_figure_in_no_output_is_called_out_as_not_belonging() -> None:
    advice = tag_advice(["$99.00"], CONTEXT)
    assert advice is not None and "in no output you were given" in advice


def test_no_untagged_figures_means_no_advice() -> None:
    assert tag_advice([], CONTEXT) is None


def test_the_assumptions_block_hands_over_every_concern_with_its_source() -> None:
    block = assumptions_block(
        [
            ("Estimator", {"text": "E-002 says 200 A, E-001 says 225 A.", "drawing_ref": "E-001"}),
            ("Pricing", {"text": "Exit sign is unpriced.", "drawing_ref": ""}),
        ]
    )
    assert "E-002 says 200 A" in block and "(E-001)" in block and "[from the Estimator]" in block
    assert "Exit sign is unpriced." in block and "[from the Pricing]" in block
    assert "Assumptions section" in block, "it says where the lines go"


def test_no_concerns_means_no_block_rather_than_an_empty_heading() -> None:
    assert assumptions_block([]) == ""
    assert assumptions_block([("Estimator", {"text": "   "})]) == ""


def test_a_blocker_naming_a_present_sheet_as_context_still_stands() -> None:
    """The real Missing sheet blocker: E-001 is present and is only cited, E-003 is what is absent.

    Reading the whole sentence at once refused this, which would have broken the one scenario built to
    produce a blocker. Only the clause claiming absence counts.
    """
    assert (
        blocker_names_a_present_sheet(
            "Panel LP-2 appears on single-line E-001 but its schedule E-003 is not in the drawing set.",
            prepared("E-000", "E-001", "E-002", "E-101", "E-102"),
        )
        is None
    )


def test_a_panel_designation_is_not_read_as_a_sheet() -> None:
    """The real invented blocker: LP-1 is a panel, E-002 is the sheet, and E-002 is in the set."""
    refusal = blocker_names_a_present_sheet(
        "Panel LP-1 schedule E-002 is missing from the drawing set; single-line E-001 shows LP-1.",
        prepared("E-000", "E-001", "E-002"),
    )
    assert refusal is not None and "E-002" in refusal
    assert "LP-1" not in refusal, "a panel name is not a sheet this run could open"


def test_a_blocker_with_no_claim_of_absence_is_left_alone() -> None:
    assert (
        blocker_names_a_present_sheet(
            "E-002 is illegible at the rating and the value cannot be confirmed.",
            prepared("E-001", "E-002"),
        )
        is None
    )


def test_a_checklist_item_written_as_a_field_name_still_finds_its_marking() -> None:
    """Intake's largest refusal category was our matching, not the model (spec 010, phase 1.5).

    The seat writes `bid_security_requirement` where the checklist has "Bid security requirement stated,
    such as a bid bond". Matching on raw text missed that, so an item the checklist closes with a default
    was read as an open gap and the reply was refused for asking no question about it.
    """
    from app.config import ROOT
    from app.live.replies import checklist_markings, needs_a_question

    marks = checklist_markings(ROOT / "config" / "electrical-bid" / "readiness-checklist.md")
    for closed in ("bid_security_requirement", "insurance_requirements", "site_address"):
        assert not needs_a_question(closed, marks), f"{closed} is closed by a checklist default"
    for open_gap in ("submission_deadline", "scope_statement"):
        assert needs_a_question(open_gap, marks), f"{open_gap} is blocking and still needs asking"
    assert needs_a_question("something_invented_entirely", marks), "an unknown item is not quietly closed"


def test_word_matching_does_not_join_two_different_checklist_items() -> None:
    """Loose matching is only safe while it cannot mark a real gap as already covered."""
    from app.live.replies import _marking

    marks = {
        "submission deadline, present and in the future": "blocking",
        "bid security requirement stated, such as a bid bond": "default: none required",
    }
    assert _marking("submission_deadline", marks) == "blocking"
    assert _marking("bid_security", marks) == "default: none required"
    assert _marking("deadline for questions about security", marks) is None, "part words are not a match"


JSON_CONTEXT = (
    "## Brief (source id: brief)\n"
    "Default labour rate: 95 CAD per hour blended.\n"
    "## Estimator output (source id: takeoff)\n"
    '{"labour_hours": 99.25, "lines": 47}\n'
    "## Pricing output (source id: pricing)\n"
    '{"material": 19051.79, "labour_rate": 95.0, "labour": 9428.75, "total": 31338.31}\n'
)


def test_a_price_is_found_though_the_output_holds_it_as_a_bare_number() -> None:
    """A specialist output reaches the Writer as JSON: 31338.31, not $31,338.31.

    Comparing the two as written found nothing, so the advice told the Writer that a real Pricing total
    did not belong in the document. Confidently wrong guidance is worse than none.
    """
    assert sources_of_figure("$31,338.31", JSON_CONTEXT) == ["pricing"]
    assert sources_of_figure("$9,428.75", JSON_CONTEXT) == ["pricing"]
    advice = tag_advice(["$31,338.31"], JSON_CONTEXT)
    assert advice == "write these exactly: {{$31,338.31|src:pricing}}"


def test_a_whole_number_matches_its_decimal_form_but_not_a_longer_number() -> None:
    assert sources_of_figure("$95", JSON_CONTEXT) == ["brief", "pricing"], "95 and 95.0 are the same rate"
    assert sources_of_figure("$5", JSON_CONTEXT) == [], "a figure is not found inside a longer one"
    assert sources_of_figure("$1,234.00", JSON_CONTEXT) == [], "a figure in no output is still not found"
