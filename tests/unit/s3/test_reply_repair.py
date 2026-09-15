"""A takeoff with a null note parses, and a reply of the right shape reports its own bad line (S3, US2)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.live.replies import EstimatorReply, ReplyError, parse_reply

LINE = {
    "group": "Lighting",
    "description": "2x4 LED troffer",
    "quantity": 46,
    "unit": "each",
    "drawing_ref": "E-101",
    "confidence": "high",
}


def takeoff(**changes: Any) -> str:
    body: dict[str, Any] = {
        "headline": "Takeoff complete",
        "summary": "One sentence. And another.",
        "bom": [{**LINE, "note": None}],
        "labour": {"total_hours": 156.45, "by_group": {"Lighting": 39.15}},
    }
    body.update(changes)
    return json.dumps(body)


def test_a_null_note_is_no_note() -> None:
    reply = parse_reply("estimator", takeoff())
    assert isinstance(reply, EstimatorReply)
    assert reply.bom[0].note == "" and reply.labour is not None


def test_a_bad_line_is_reported_not_swapped_for_an_inner_object() -> None:
    with pytest.raises(ReplyError) as raised:
        parse_reply("estimator", takeoff(bom=[{**LINE, "confidence": "certain"}]))
    assert "confidence" in str(raised.value), "the seat is told which line to fix"
