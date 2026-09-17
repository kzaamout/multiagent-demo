"""A seat that grades with the checklist's prose words is understood; the shape stays pass, assumed, fail (S5)."""

from __future__ import annotations

import inspect

import pytest

from app.live.replies import ChecklistGrade
from app.live.seat_call import SeatCall


@pytest.mark.parametrize(
    ("written", "status"),
    [
        ("present", "pass"),
        ("Present", "pass"),
        ("present with concerns", "assumed"),
        ("missing", "fail"),
        ("fail", "fail"),
    ],
)
def test_grade_synonyms(written: str, status: str) -> None:
    assert ChecklistGrade.model_validate({"item": "Scope", "status": written}).status == status


def test_unknown_grade_is_still_refused() -> None:
    with pytest.raises(ValueError):
        ChecklistGrade.model_validate({"item": "Scope", "status": "maybe"})


def test_corrections_default_to_one() -> None:
    assert inspect.signature(SeatCall.__init__).parameters["corrections"].default == 1
