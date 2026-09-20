"""Work the engine does exactly, so a seat is not asked to remember or judge it (spec 010).

Each check has a negative case here, because the danger in every one of them is firing when it should
not: refusing a real blocker, attributing a figure to the wrong specialist, or demanding a concern the
draft already carries.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

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
    return SimpleNamespace(
        sheets=[SimpleNamespace(sheet_number=n, sheet_id=n, title="") for n in sheet_numbers]
    )


def with_titles(*pairs: tuple[str, str]) -> SimpleNamespace:
    """The manifest as it really is: each sheet with its title, which says which panel a schedule covers."""
    return SimpleNamespace(sheets=[SimpleNamespace(sheet_number=n, sheet_id=n, title=t) for n, t in pairs])


SET_WITH_TITLES = (
    ("E-000", "Legend, Drawing Index, General Notes"),
    ("E-001", "Single-Line Diagram"),
    ("E-002", "Panel Schedule LP-1"),
    ("E-101", "Lighting Plan, Main Floor"),
    ("E-102", "Power Plan, Main Floor"),
)


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


PRICED = (
    "## Brief (source id: brief)\n"
    "Budget guidance: 40000 CAD.\n"
    "## Estimator output (source id: takeoff)\n"
    '{"lines": 47, "labour_hours": 99.25}\n'
    "## Pricing output (source id: pricing)\n"
    '{"material": 18328.11, "labour": 9428.75, "total": 36882.58}\n'
)


def test_a_mistyped_total_is_caught_though_it_carries_a_tag() -> None:
    """The real failure: a draft carrying $36,882.581 for a price of $36,882.58 (spec 010, phase 1.6).

    A tag proved the Writer named an output, never that the number came from it, so a mistyped total
    passed review as readily as a correct one and six runs exhausted their budget arguing about it.
    """
    from app.live.deterministic import money_disagreements

    problems = money_disagreements("Total {{$36,882.581|src:pricing}}.", PRICED)
    assert len(problems) == 1 and "$36,882.581" in problems[0]
    assert "Copy the number from the output" in problems[0]


def test_the_same_total_written_two_ways_cannot_both_be_right() -> None:
    """Every one of the 23 review findings was a figure disagreeing with itself across sections."""
    from app.live.deterministic import money_disagreements

    draft = "Summary {{$21,077.33|src:pricing}} and the table says {{$18,328.11|src:pricing}}."
    problems = money_disagreements(draft, PRICED)
    assert [p.split(" is tagged")[0] for p in problems] == ["$21,077.33"], "only the wrong one is named"


def test_a_figure_tagged_to_the_wrong_output_is_named_as_such() -> None:
    from app.live.deterministic import money_disagreements

    problems = money_disagreements("Total {{$36,882.58|src:takeoff}}.", PRICED)
    assert len(problems) == 1 and "that figure is in pricing" in problems[0]


def test_correct_money_and_anything_that_is_not_money_pass_untouched() -> None:
    """The check must not start refusing drafts that are right, or figures it has no business judging."""
    from app.live.deterministic import money_disagreements

    good = (
        "Total {{$36,882.58|src:pricing}}, material {{$18,328.11|src:pricing}}, budget {{$40,000|src:brief}}."
    )
    assert money_disagreements(good, PRICED) == []
    assert money_disagreements("Panel {{225 A|src:brief}} over {{99.25 hours|src:takeoff}}.", PRICED) == []
    assert money_disagreements("Nothing here.\n## Provenance\n{{$99.99|src:pricing}}", PRICED) == []


SET = ("E-000", "E-001", "E-002", "E-101", "E-102")


def test_a_concern_naming_a_sheet_that_really_is_absent_is_a_blocker() -> None:
    """The Missing sheet scenario, as the Estimator actually wrote it in six of seven runs that failed to
    escalate: it saw the problem exactly, filed it as a concern, and finished the takeoff."""
    from app.live.deterministic import concern_names_an_absent_sheet

    text = (
        "Panel schedule LP-2 (E-003) referenced on E-001 and E-102 but not in drawing set per drawing index."
    )
    refusal = concern_names_an_absent_sheet([text], prepared(*SET))
    assert refusal is not None
    assert "E-003" in refusal and "E-001" not in refusal.split('"')[0], (
        "only the absent sheet is named as missing"
    )
    assert "blocker, not a concern" in refusal and "needs_human" in refusal


def test_a_concern_about_sheets_the_run_holds_is_left_alone() -> None:
    from app.live.deterministic import concern_names_an_absent_sheet

    rating = "Main breaker rating differs: E-001 shows 225 A, schedule E-002 shows 200 A. No schedule note explains it."
    assert concern_names_an_absent_sheet([rating], prepared(*SET)) is None


def test_an_absent_sheet_is_caught_however_the_seat_words_it() -> None:
    """Run 5 of the six-run check: nothing here says missing or absent, and the sheet is not in the set.
    The manifest is the evidence, so no list of words for absence is consulted."""
    from app.live.deterministic import concern_names_an_absent_sheet

    later = "Panel LP-2 schedule E-003 will be provided later and is not required for initial tender."
    refusal = concern_names_an_absent_sheet([later], prepared(*SET))
    assert refusal is not None and "E-003" in refusal and "arrive later" in refusal
    assert "If you mistyped" in refusal, "a sheet number typed wrongly has a way out that is not a blocker"


def test_a_panel_named_as_missing_is_not_read_as_a_sheet() -> None:
    from app.live.deterministic import concern_names_an_absent_sheet

    assert (
        concern_names_an_absent_sheet(["LP-2 has no schedule note on spare breakers."], prepared(*SET))
        is None
    )


def test_the_concern_check_is_silent_when_nothing_was_prepared() -> None:
    from app.live.deterministic import concern_names_an_absent_sheet

    assert concern_names_an_absent_sheet(["E-003 is not in the set."], prepared()) is None


def test_a_dollar_sign_outside_the_tag_does_not_hide_the_amount() -> None:
    """Run 8839b28c: the Writer wrote labour as a dollar sign, then the tag holding 42,161.07, where Pricing
    said 42161.0. With the sign outside the tag no check saw an amount at all, in 30 of 137 drafts."""
    from app.live.deterministic import money_disagreements
    from app.live.figures import amounts_not_in_context
    from app.tools.template import MONEY, with_dollars_inside

    context = '## Pricing output (source id: pricing)\n{"labour": 42161.0, "total": 104282.45}'
    draft = "Labour at ${{42,161.07|src:pricing}} within a total of $ {{104,282.45|src:pricing}}."
    assert money_disagreements(draft, context) == [
        "$42,161.07 is tagged src:pricing and no output holds that figure. Copy the number from the output "
        "rather than retyping it, and use the same one in every section"
    ]
    body = with_dollars_inside(draft)
    assert amounts_not_in_context(MONEY.findall(body), context) == ["$42,161.07"]
    assert (
        with_dollars_inside("{{$5.00|src:a}} and {{25 troffers|src:b}}")
        == "{{$5.00|src:a}} and {{25 troffers|src:b}}"
    )


KNOWLEDGE = """# Fictional Prospect Ltd.

## Answers from previous runs
- q_bid_security: No bid security required (run a, 2026-09-15T20:31:52Z)
- q_panel_schedules: Assume all panels are accounted for unless advised otherwise. (run b, 2026-09-18T02:06:46Z)
"""


def graded(item: str, status: str, note: str) -> Any:
    from app.live.replies import ChecklistGrade

    return ChecklistGrade(item=item, status=status, note=note)


def test_an_item_the_knowledge_file_answers_needs_no_question() -> None:
    """9 of the refusals recorded on 2026-09-19 were the engine demanding a question for an item Intake had
    correctly closed with a knowledge file answer, which its first rule tells it to do."""
    from app.live.replies import answered_ids, closed_by_knowledge

    answered = answered_ids(KNOWLEDGE)
    assert answered == {"q_bid_security", "q_panel_schedules"}
    closed = graded(
        "consistency_panels_single_line",
        "assumed",
        "Only one panel (LP-1) shown; schedule present. Consistency assumed per knowledge file entry q_panel_schedules.",
    )
    assert closed_by_knowledge(closed, answered)


def test_a_claimed_answer_the_file_does_not_hold_closes_nothing() -> None:
    """The note has to name an entry the file really carries, or a seat could close any gap by claiming one."""
    from app.live.replies import answered_ids, closed_by_knowledge

    answered = answered_ids(KNOWLEDGE)
    invented = graded(
        "consistency_panels_single_line", "assumed", "Closed per knowledge file entry q_invented."
    )
    silent = graded(
        "consistency_panels_single_line", "assumed", "Only one panel shown, so nothing to compare."
    )
    assert not closed_by_knowledge(invented, answered)
    assert not closed_by_knowledge(silent, answered)
    assert not closed_by_knowledge(graded("x", "assumed", "per q_bid_security"), set())


def test_the_answers_read_are_the_entry_ids_not_words_from_the_answer() -> None:
    from app.live.replies import answered_ids

    text = (
        "## Answers from previous runs\n"
        "- q_site_project: ask q_something_else next time (run c, 2026-09-17T00:00:00Z)\n"
    )
    assert answered_ids(text) == {"q_site_project"}, "an id inside the answer text is not an answered id"
    assert answered_ids("no answers here") == set()


def test_a_dropped_concern_is_asked_for_in_words_the_concern_itself_uses() -> None:
    """54 of the 62 dropped-concern refusals on record told the Writer to name "the values that disagree"
    for a concern that had none, and all of them named only the sheets in drawing_ref (2026-09-19)."""
    from app.live.concerns import concern_problems

    draft = "# Draft\n\n## Assumptions\n\nNothing carried here.\n"
    rating = [{"text": "E-001 shows a 225 A bus; schedule E-002 shows a 200 A main.", "drawing_ref": "E-002"}]
    message = concern_problems(draft, rating)[0]
    assert "E-002" in message and "E-001" in message, "every sheet the concern names, not only drawing_ref"
    assert "values that disagree" not in message
    assert "keeping any figures the concern states" in message
    plain = [{"text": "Exit sign quantity includes a spare listed on schedule.", "drawing_ref": "E-002"}]
    assert "values that disagree" not in concern_problems(draft, plain)[0]
    carried = "# Draft\n\n## Assumptions\n\n- Schedule E-002 lists a spare exit sign, carried as counted.\n"
    assert concern_problems(carried, plain) == []


def test_a_concern_carried_in_its_own_words_is_carried() -> None:
    """Run cb33b02d: the concern's sentence named only E-002 while its reference field named E-001 too.
    Requiring both refused a draft that copied the concern faithfully, three times, and ended the run."""
    from app.live.concerns import concern_problems

    concern = [
        {
            "text": "Panel LP-1 bus rating of 225 A on E-002 does not match the main breaker of 200 A on E-002.",
            "drawing_ref": "E-001, E-002",
        }
    ]
    carried = (
        "# Draft\n\n## Assumptions\n\n"
        "- Panel LP-1 bus rating of 225 A on E-002 does not match the main breaker of 200 A on E-002.\n"
    )
    assert concern_problems(carried, concern) == [], "the concern's own sentence is what must be carried"
    message = concern_problems("# Draft\n\n## Assumptions\n\nNothing.\n", concern)[0]
    assert "E-002, E-001" in message or "E-001, E-002" in message, "the reference field still advises"


def test_a_panel_whose_schedule_the_set_lacks_is_a_blocker() -> None:
    """A Missing sheet run passed review with no blocker: the seat wrote "Panel LP-2 schedule is missing
    from the drawing set" and named no sheet number, so the sheet check ignored it by design."""
    from app.live.deterministic import concern_names_an_absent_panel

    held = with_titles(*SET_WITH_TITLES)
    refusal = concern_names_an_absent_panel(
        ["Panel LP-2 schedule is missing from the drawing set; quantities for LP-2 were inferred."], held
    )
    assert refusal is not None and "LP-2" in refusal
    assert "blocker, not a concern" in refusal and "needs_human" in refusal


def test_a_panel_whose_schedule_the_set_holds_is_left_alone() -> None:
    """E-002 is titled "Panel Schedule LP-1", so the run holds that schedule whatever the seat claims."""
    from app.live.deterministic import concern_names_an_absent_panel

    held = with_titles(*SET_WITH_TITLES)
    assert concern_names_an_absent_panel(["Panel LP-1 schedule is missing from the set."], held) is None
    assert concern_names_an_absent_panel(["LP-2 is fed from LP-1 by feeder F2."], held) is None
    assert concern_names_an_absent_panel(["Schedule E-003 is not in the set."], held) is None
    assert concern_names_an_absent_panel(["LP-1 bus is 225 A on E-001 but 200 A on E-002."], held) is None
    assert concern_names_an_absent_panel(["Panel LP-2 schedule is missing."], with_titles()) is None
