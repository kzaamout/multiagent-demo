from __future__ import annotations

import pytest

from app.agents.base import Emit
from app.agents.stubs import SCENARIOS, bundle_for
from app.schema.events import AGENT_MESSAGE_TYPES, HUMAN_TYPES, ORCHESTRATOR_TYPES


def test_nine_scenarios_registered() -> None:
    assert set(SCENARIOS) == {
        "clean-run",
        "planted-inconsistency",
        "missing-sheet",
        "missing-price",
        "not-ready",
        "prospect-own",
        "prospect-a",
        "prospect-b",
        "prospect-c",
    }


@pytest.mark.parametrize("dataset_id", sorted(SCENARIOS))
def test_stub_emits_only_agent_messages(dataset_id: str) -> None:
    for emit in SCENARIOS[dataset_id].all_emits():
        assert emit.type in AGENT_MESSAGE_TYPES
        assert emit.type not in ORCHESTRATOR_TYPES
        assert emit.type not in HUMAN_TYPES
        assert emit.seat != "orchestrator"
        assert emit.bundle is not None, f"{dataset_id}: {emit.type} has no prompt bundle"


def test_emit_refuses_orchestrator_types() -> None:
    with pytest.raises(ValueError):
        Emit("estimator", "stage.changed", 0, {})


def test_every_prompt_ref_resolves() -> None:
    for scenario in SCENARIOS.values():
        for ref in scenario.bundles():
            bundle = bundle_for(ref)
            assert bundle is not None
            assert all(text for _, text in bundle.sections()[:3])
