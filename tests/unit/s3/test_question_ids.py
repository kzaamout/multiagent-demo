"""A gap carries the same question id on every run, so ask once finds the stored answer (decision 2a)."""

from __future__ import annotations

import json
from typing import Any

from app.config import ROOT
from app.live.replies import (
    REQUIRED_SECTIONS,
    IntakeReply,
    canonical_question_id,
    checklist_items,
    checklist_markings,
    parse_reply,
)

CHECKLIST = ROOT / "config" / "electrical-bid" / "readiness-checklist.md"
ITEMS = checklist_items(CHECKLIST, REQUIRED_SECTIONS)
BID_SECURITY = "Bid security requirement stated, such as a bid bond"


def intake_with(clarification: dict[str, Any], failing: dict[str, str]) -> IntakeReply:
    grades = [{"item": item, "status": failing.get(item, "pass"), "note": ""} for item in ITEMS]
    verdict = "ready_with_assumptions" if failing else "ready"
    text = json.dumps(
        {
            "brief": {"project": "Quillbrook Library"},
            "readiness": {"verdict": verdict, "checklist": grades},
            "clarifications": [clarification],
        }
    )
    reply = parse_reply("intake", text, expected_items=ITEMS, markings=checklist_markings(CHECKLIST))
    assert isinstance(reply, IntakeReply)
    return reply


def test_the_same_gap_keeps_its_id_whatever_the_seat_called_it() -> None:
    reply = intake_with(
        {
            "question_id": "q_bid_security_confirmation",
            "question": "Confirm whether bid security is required for this tender and in what form.",
            "why_it_matters": "A tender without confirming the bid security requirement is rejected.",
            "proposed_default": "None required.",
            "blocking": True,
        },
        {BID_SECURITY: "assumed"},
    )
    assert reply.clarifications[0].question_id == "q_bid_security", (
        "the id comes from the checklist item, not from the seat"
    )


def test_a_question_about_nothing_on_the_checklist_keeps_its_own_id() -> None:
    reply = intake_with(
        {
            "question_id": "q_parking_arrangements",
            "question": "Where may the crew park during construction?",
            "why_it_matters": "Parking affects daily mobilisation time.",
            "proposed_default": "On street.",
            "blocking": False,
        },
        {},
    )
    assert reply.clarifications[0].question_id == "q_parking_arrangements"


def test_each_checklist_item_has_a_stable_short_id() -> None:
    ids = [canonical_question_id(item) for item in ITEMS]
    assert len(set(ids)) == len(ids), "no two checklist items share an id"
    assert canonical_question_id(BID_SECURITY) == "q_bid_security"
    assert canonical_question_id("Submission deadline, present and in the future") == "q_submission_deadline"
