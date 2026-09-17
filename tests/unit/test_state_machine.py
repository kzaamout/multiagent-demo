from __future__ import annotations

from typing import Any

import pytest

from app.orchestrator.state import ReviewCycle, RunState, finding_key, normalize_evidence


def state(cycles: int = 4) -> RunState:
    return RunState(review_max_cycles=cycles, cost_ceiling=1.0)


def finding(
    fid: str,
    evidence: str,
    severity: str = "major",
    route_to: str | None = "work",
    agent: str | None = "estimator",
) -> dict[str, Any]:
    return {
        "id": fid,
        "severity": severity,
        "text": "x",
        "evidence": evidence,
        "route_to": route_to,
        "agent_id": agent,
    }


def test_forward_and_backward_directions() -> None:
    s = state()
    assert s.direction_to("intake") == "forward"
    s.enter("intake")
    s.enter("review")
    assert s.direction_to("work") == "backward"
    assert s.direction_to("handoff") == "forward"


def test_retry_budget_is_one_fewer_than_the_cycles() -> None:
    assert state(4).retry_budget == 3
    assert state(1).retry_budget == 0


def test_first_fail_always_reworks() -> None:
    s = state()
    assert (
        s.on_review_fail([finding("f1", "page 3"), finding("f2", "page 4"), finding("f3", "page 5")])
        == "rework"
    )
    assert s.retries == 1 and s.stop_reason is None


def test_no_progress_stops_when_serious_count_does_not_fall() -> None:
    s = state()
    s.on_review_fail([finding("f1", "page 3"), finding("f2", "page 4")])
    assert s.on_review_fail([finding("f3", "page 6"), finding("f4", "page 7")]) == "retry_exhausted"
    assert s.stop_reason == "no_progress"
    assert s.retries == 1, "the failed cycle dispatches no rework"


def test_minor_findings_do_not_count_as_progress_or_regression() -> None:
    s = state()
    s.on_review_fail([finding("f1", "page 3"), finding("f2", "page 4")])
    second = [
        finding("f3", "page 6"),
        finding("m1", "page 9", "minor", None, None),
        finding("m2", "page 9", "minor", None, None),
    ]
    assert s.on_review_fail(second) == "rework"
    assert s.retries == 2


def test_repeated_finding_stops_on_normalized_evidence_and_route() -> None:
    s = state()
    s.on_review_fail([finding("f1", "Page 3, paragraph 2 vs BOM line 4"), finding("f2", "page 5")])
    repeat = [finding("f9", "page 3 paragraph 2 VS bom line 4.")]
    assert s.on_review_fail(repeat) == "retry_exhausted"
    assert s.stop_reason == "repeated_finding"


def test_same_evidence_routed_elsewhere_is_not_a_repeat() -> None:
    s = state()
    s.on_review_fail([finding("f1", "page 3"), finding("f2", "page 5")])
    assert s.on_review_fail([finding("f3", "page 3", route_to="assemble", agent="writer")]) == "rework"


def test_max_cycles_is_the_hard_ceiling() -> None:
    s = state(3)
    s.on_review_fail([finding("f1", "a"), finding("f2", "b"), finding("f3", "c")])
    s.on_review_fail([finding("f4", "d"), finding("f5", "e")])
    assert s.retries == 2
    assert s.on_review_fail([finding("f6", "f")]) == "retry_exhausted"
    assert s.stop_reason == "max_cycles"


def test_one_cycle_means_the_first_fail_stops() -> None:
    s = state(1)
    assert s.on_review_fail([finding("f1", "a")]) == "retry_exhausted"
    assert s.stop_reason == "max_cycles" and s.retries == 0


def test_no_progress_is_named_before_a_repeat_or_the_ceiling() -> None:
    s = state(2)
    s.on_review_fail([finding("f1", "a")])
    assert s.on_review_fail([finding("f1", "a")]) == "retry_exhausted"
    assert s.stop_reason == "no_progress"


def test_review_cycle_and_keys() -> None:
    cycle = ReviewCycle.from_findings(1, [finding("f1", "Page 3!"), finding("m", "x", "minor", None, None)])
    assert cycle.serious == 1
    assert cycle.keys == {("page 3", "work", "estimator")}
    assert normalize_evidence("  Page  3, para. 2 ") == "page 3 para 2"
    assert finding_key({"evidence": "A", "route_to": None, "agent_id": None}) == ("a", "", "")


def test_work_to_intake_capped_at_one() -> None:
    s = state()
    assert s.on_route_back_to_intake() == "allowed"
    assert s.on_route_back_to_intake() == "blocker"
    assert s.retries == 0, "Work to Intake does not consume a review cycle"


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
