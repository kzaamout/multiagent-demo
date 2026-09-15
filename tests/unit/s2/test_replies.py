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
