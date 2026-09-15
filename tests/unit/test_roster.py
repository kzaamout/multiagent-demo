from __future__ import annotations

import pytest

from app.orchestrator.roster import SEAT_BY_ID, build_roster, seats_for


def test_rfp_workflow_has_six_seats() -> None:
    assert [s.agent_id for s in seats_for("electrical_rfp")] == [
        "orchestrator",
        "intake",
        "estimator",
        "pricing",
        "writer",
        "reviewer",
    ]


def test_same_seed_same_names() -> None:
    assert build_roster("electrical_rfp", seed=7) == build_roster("electrical_rfp", seed=7)


def test_both_names_appear_across_runs() -> None:
    seen = {build_roster("electrical_rfp", seed=s)["estimator"].name for s in range(40)}
    assert seen == set(SEAT_BY_ID["estimator"].names)


def test_names_override_and_validation() -> None:
    roster = build_roster("electrical_rfp", names={"estimator": "Elena"})
    assert roster["estimator"].name == "Elena"
    with pytest.raises(ValueError):
        build_roster("electrical_rfp", names={"estimator": "Oscar"})


def test_agents_carry_structured_models() -> None:
    for agent in build_roster("electrical_rfp", seed=1).values():
        assert agent.model.provider and agent.model.model_id and agent.model.label
    assert (
        build_roster("electrical_rfp", seed=1)["reviewer"].model.provider
        != build_roster("electrical_rfp", seed=1)["writer"].model.provider
    )
