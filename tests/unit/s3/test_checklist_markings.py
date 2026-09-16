"""Only items the readiness checklist marks blocking can make a run Not ready (S3, US2 and US3)."""

from __future__ import annotations

import json
from typing import Any

from app.config import ROOT
from app.live.replies import (
    REQUIRED_SECTIONS,
    IntakeReply,
    checklist_items,
    checklist_markings,
    parse_reply,
)

CHECKLIST = ROOT / "config" / "electrical-rfp" / "readiness-checklist.md"
BRIEF = {"project": "Quillbrook Library", "scope": "Main floor fit-out"}


def graded(failing: dict[str, str], clarifications: list[dict[str, Any]], verdict: str) -> IntakeReply:
    items = checklist_items(CHECKLIST, REQUIRED_SECTIONS)
    grades = [
        {"item": item, "status": failing.get(item, "pass"), "note": failing.get(item, "")} for item in items
    ]
    text = json.dumps(
        {
            "brief": BRIEF,
            "readiness": {"verdict": verdict, "checklist": grades},
            "clarifications": clarifications,
        }
    )
    reply = parse_reply("intake", text, expected_items=items, markings=checklist_markings(CHECKLIST))
    assert isinstance(reply, IntakeReply)
    return reply


def status_of(reply: IntakeReply, prefix: str) -> str:
    return next(g.status for g in reply.readiness.checklist if g.item.startswith(prefix))


def test_an_index_that_lists_a_sheet_not_provided_is_carried_not_a_stop() -> None:
    reply = graded(
        {"Drawing index matching the sheets provided": "fail"},
        [
            {
                "question_id": "q_drawing_index",
                "question": "Is sheet E-003 missing or was it never issued?",
                "why_it_matters": "The index lists a sheet that is not in the set.",
                "proposed_default": "Infer the index from the sheet titles provided.",
                "blocking": False,
            }
        ],
        "ready_with_assumptions",
    )
    assert status_of(reply, "Drawing index") == "assumed"
    assert reply.readiness.verdict == "ready_with_assumptions"


def test_a_missing_deadline_still_stops_the_run() -> None:
    reply = graded({"Submission deadline, present and in the future": "fail"}, [], "not_ready")
    assert status_of(reply, "Submission deadline") == "fail"
    assert reply.readiness.verdict == "not_ready"


def test_the_checklist_marks_the_items_the_engine_relies_on() -> None:
    markings = checklist_markings(CHECKLIST)
    assert "blocking" in markings["submission deadline, present and in the future"]
    assert "concern" in markings["panel schedules for every panel shown on the single-line"]
    assert "blocking" not in markings["drawing index matching the sheets provided"]


def test_a_gap_the_checklist_closes_needs_no_question() -> None:
    reply = graded(
        {
            "Bid security requirement stated, such as a bid bond": "assumed",
            "Insurance requirements stated": "assumed",
            "Panel schedules for every panel shown on the single-line": "assumed",
        },
        [],
        "ready_with_assumptions",
    )
    assert [g.status for g in reply.readiness.checklist].count("assumed") == 3
    assert reply.clarifications == [], "defaults and Estimator concerns are graded, not asked"
