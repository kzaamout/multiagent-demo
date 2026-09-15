from __future__ import annotations

import json
from typing import Any

import pytest

from app.live.replies import (
    EstimatorReply,
    IntakeReply,
    ReplyError,
    ReviewerReply,
    extract_json,
    intake_payloads,
    parse_reply,
    verdict_payload,
)

INTAKE: dict[str, Any] = {
    "brief": {"project": "Northgate Library", "deadline": "3 Nov"},
    "readiness": {
        "verdict": "ready_with_assumptions",
        "checklist": [
            {"item": "Scope of work", "status": "pass", "note": ""},
            {"item": "Bid bond", "status": "assumed", "note": "not stated"},
        ],
        "legibility": [{"page": 1, "confidence": 0.93}],
    },
    "clarifications": [
        {
            "question_id": "q_bid_bond",
            "question": "Is a bid bond required?",
            "why_it_matters": "It changes the submission package.",
            "proposed_default": "No bid bond",
            "blocking": False,
        }
    ],
}


def test_extract_json_from_prose_and_fences() -> None:
    assert extract_json('Here you go:\n```json\n{"a": 1}\n```\nThanks') == {"a": 1}
    assert extract_json('Result {"a": {"b": "}"}} trailing') == {"a": {"b": "}"}}
    with pytest.raises(ReplyError):
        extract_json("no object here")


def test_intake_reply_validates_and_converts() -> None:
    reply = parse_reply("intake", "Summary first.\n" + json.dumps(INTAKE))
    assert isinstance(reply, IntakeReply)
    brief, readiness, questions = intake_payloads(reply)
    assert brief["brief"]["project"] == "Northgate Library"
    assert readiness["legibility"][0]["page"] == "1"
    assert questions[0]["question_id"] == "q_bid_bond"


def test_intake_verdict_must_follow_grades() -> None:
    bad = json.loads(json.dumps(INTAKE))
    bad["readiness"]["verdict"] = "ready"
    with pytest.raises(ReplyError, match="contradicts"):
        parse_reply("intake", json.dumps(bad))


def test_intake_question_ids_are_stable_snake_case() -> None:
    bad = json.loads(json.dumps(INTAKE))
    bad["clarifications"][0]["question_id"] = "Bid Bond?"
    with pytest.raises(ReplyError, match="question_id"):
        parse_reply("intake", json.dumps(bad))


def test_estimator_blocker_or_complete() -> None:
    blocked = parse_reply(
        "estimator", json.dumps({"blocker": {"description": "LP-2 schedule missing", "needs_human": True}})
    )
    assert isinstance(blocked, EstimatorReply) and blocked.blocker is not None
    with pytest.raises(ReplyError, match="headline, bom, and labour"):
        parse_reply("estimator", json.dumps({"headline": "Done", "bom": []}))


def test_reviewer_rules() -> None:
    finding = {
        "id": "f1",
        "severity": "major",
        "text": "Total wrong.",
        "evidence": "Pricing summary",
        "route_to": "work",
        "agent_id": "pricing",
    }
    with pytest.raises(ReplyError, match="pass cannot"):
        parse_reply("reviewer", json.dumps({"verdict": "pass", "findings": [finding]}))
    with pytest.raises(ReplyError, match="needs at least one"):
        parse_reply("reviewer", json.dumps({"verdict": "fail", "findings": []}))
    reply = parse_reply(
        "reviewer", json.dumps({"verdict": "fail", "summary": "One major.", "findings": [finding]})
    )
    assert isinstance(reply, ReviewerReply)
    assert verdict_payload(reply)["findings"][0]["route_to"] == "work"


def test_pricing_needs_cost_summary_totals() -> None:
    reply = {
        "headline": "38 of 38 priced",
        "summary": "All priced.",
        "priced_bom": [{"line_ref": "L1", "description": "x"}],
        "cost_summary": {"material": 1},
    }
    with pytest.raises(ReplyError, match="cost_summary"):
        parse_reply("pricing", json.dumps(reply))


def test_writer_needs_markdown() -> None:
    with pytest.raises(ReplyError):
        parse_reply("writer", json.dumps({"markdown": ""}))


def test_nested_reply_object_is_accepted() -> None:
    from app.live.replies import PlanProposal, parse_as

    text = json.dumps(
        {"plan": {"subtasks": [{"task_id": "t1"}], "reason": "Pricing needs the takeoff."}, "headline": None}
    )
    assert parse_as(PlanProposal, text).reason == "Pricing needs the takeoff."
    with pytest.raises(ReplyError):
        parse_as(PlanProposal, json.dumps({"plan": {"steps": []}}))


def _intake(checklist: list[dict[str, Any]], clarifications: list[dict[str, Any]]) -> str:
    verdict = "ready_with_assumptions" if any(c["status"] == "assumed" for c in checklist) else "ready"
    return json.dumps(
        {
            "brief": {},
            "readiness": {"verdict": verdict, "checklist": checklist},
            "clarifications": clarifications,
        }
    )


def test_intake_must_grade_every_item_and_ask_about_every_gap() -> None:
    from app.config import ROOT
    from app.live.replies import checklist_items

    expected = checklist_items(ROOT / "config" / "electrical-rfp" / "readiness-checklist.md")
    assert len(expected) == 21 and expected[0] == "Scope statement describing the electrical work requested"
    passes = [{"item": f"Item {i}", "status": "pass", "note": None} for i in range(len(expected) - 2)]
    bonding = {
        "item": "Bonding or insurance requirements stated",
        "status": "assumed",
        "note": "bid security open",
    }
    rating = {"item": "Main breaker and bus ratings agree", "status": "assumed", "note": "E-001 vs E-002"}
    question = {
        "question_id": "q_bid_security",
        "question": "Is bid security required?",
        "why_it_matters": "It changes the tender forms and cost.",
        "proposed_default": "No bid security required",
        "blocking": True,
    }
    with pytest.raises(ReplyError, match="grades 9 items.*Scope statement describing"):
        parse_reply("intake", _intake(passes[:8] + [bonding], [question]), expected_items=expected)
    with pytest.raises(ReplyError, match="Bonding or insurance"):
        parse_reply("intake", _intake([*passes, bonding, rating], []), expected_items=expected)
    reply = parse_reply("intake", _intake([*passes, bonding, rating], [question]), expected_items=expected)
    assert isinstance(reply, IntakeReply), "a rating disagreement is the Estimator's concern, not a question"


def test_correction_names_every_kind_of_problem() -> None:
    grades = [{"item": f"Item {i}", "status": "pass", "note": 5} for i in range(12)]
    text = json.dumps(
        {
            "brief": {},
            "readiness": {"verdict": "ready", "checklist": grades},
            "clarifications": [
                {"question_id": "q_x", "question": "?", "why_it_matters": "cost", "blocking": True}
            ],
        }
    )
    with pytest.raises(ReplyError) as raised:
        parse_reply("intake", text)
    message = str(raised.value)
    assert "readiness.checklist.0.note" in message and "clarifications.0.proposed_default" in message
    assert "checklist.5.note" not in message, "repeats of one problem are folded together"


def test_stray_closing_brace_is_repaired_and_brief_fields_folded_back() -> None:
    from app.config import ROOT
    from app.live.replies import checklist_items

    items = checklist_items(ROOT / "config" / "electrical-rfp" / "readiness-checklist.md")
    grades = ", ".join(json.dumps({"item": item, "status": "pass", "note": ""}) for item in items)
    broken = (
        '{"brief": {"project": "Library", "drawing_set": {"sheets": ["E-001"]}}, "bonding": "open"}, '
        f'"readiness": {{"verdict": "ready", "checklist": [{grades}]}}, "clarifications": []}}'
    )
    reply = parse_reply("intake", broken, expected_items=items)
    assert isinstance(reply, IntakeReply) and reply.brief["bonding"] == "open"


def test_em_dashes_never_survive_a_reply() -> None:
    dash = chr(0x2014)
    nl, fence = chr(10), chr(96) * 3
    body = '{"note": "counted ' + dash + ' two sheets", "list": ["a' + dash + 'b"]}'
    fenced = "Here it is:" + nl + fence + "json" + nl + body + nl + fence + nl + "Thanks {ok}"
    assert extract_json(fenced) == {"note": "counted, two sheets", "list": ["a, b"]}


def test_malformed_json_is_reported_as_malformed() -> None:
    with pytest.raises(ReplyError, match="not valid JSON"):
        extract_json('{"brief": {"project": "x",, "readiness": 1}')
