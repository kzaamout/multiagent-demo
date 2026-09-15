from __future__ import annotations

import pytest

from app.orchestrator.state import RunState


def state() -> RunState:
    return RunState(retry_budget=2, cost_ceiling=1.0)


def test_forward_and_backward_directions() -> None:
    s = state()
    assert s.direction_to("intake") == "forward"
    s.enter("intake")
    s.enter("review")
    assert s.direction_to("work") == "backward"
    assert s.direction_to("handoff") == "forward"


def test_retry_budget_then_exhausted() -> None:
    s = state()
    assert s.on_review_fail() == "rework"
    assert s.on_review_fail() == "rework"
    assert s.retries == 2
    assert s.on_review_fail() == "retry_exhausted"
    assert s.retries == 2


def test_work_to_intake_capped_at_one() -> None:
    s = state()
    assert s.on_route_back_to_intake() == "allowed"
    assert s.on_route_back_to_intake() == "blocker"
    assert s.retries == 0, "Work to Intake does not consume the review retry budget"


def test_cost_ceiling_detected_after_breaching_delta() -> None:
    s = state()
    assert s.on_meter("estimator", 10, 10, 0.6) == "ok"
    assert s.on_meter("estimator", 10, 10, 0.4) == "ok"
    assert s.on_meter("pricing", 10, 10, 0.01) == "cost_ceiling"
    assert s.tokens_in["estimator"] == 20


def test_pause_blocks_dispatch_predicate() -> None:
    s = state()
    assert s.can_dispatch()
    s.paused = True
    assert not s.can_dispatch()
    s.paused = False
    s.terminate("stopped")
    assert not s.can_dispatch()


def test_terminate_only_once() -> None:
    s = state()
    s.terminate("not_ready")
    with pytest.raises(RuntimeError):
        s.terminate("stopped")
