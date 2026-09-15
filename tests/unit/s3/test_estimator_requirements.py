"""A blocker condition described in a concern is sent back to the Estimator as a blocker (S3, US2)."""

from __future__ import annotations

from app.live.replies import BomLine, EstimatorBlocker, EstimatorReply, Labour, Referenced
from app.live.source import estimator_requirements

TOOLS = ["vision_read_drawing", "quantity_calculate"]


def takeoff(*concerns: str) -> EstimatorReply:
    return EstimatorReply(
        headline="Takeoff complete",
        summary="A bill of materials for the sheets provided.",
        bom=[
            BomLine(
                group="Service and distribution",
                description="42-circuit panelboard, 225A, surface",
                quantity=1,
                unit="each",
                drawing_ref="E-001",
                confidence="high",
            )
        ],
        labour=Labour(total_hours=8.0),
        concerns=[Referenced(text=text, drawing_ref="E-001") for text in concerns],
    )


def test_a_concern_that_says_the_work_is_blocked_goes_back() -> None:
    reply = takeoff(
        "Panel LP-2 is on E-001 but schedule E-003 is absent, so its devices could not be counted."
    )
    message = estimator_requirements(reply, TOOLS)
    assert message and "blocker, not a concern" in message
    assert '"blocker"' in message, "the correction names the shape to reply with"


def test_an_ordinary_concern_passes() -> None:
    reply = takeoff("Branch circuit runs are not dimensioned, so the 25 m rule was used.")
    assert estimator_requirements(reply, TOOLS) is None


def test_a_raised_blocker_is_never_corrected() -> None:
    reply = EstimatorReply(
        blocker=EstimatorBlocker(
            description="Panel LP-2 on E-001 has no schedule in the set.", needs_human=True
        )
    )
    assert estimator_requirements(reply, []) is None, "a blocker needs no calculator call"
