"""Stub scenario registry and prompt bundle lookup."""

from __future__ import annotations

from app.agents.base import StubScenario
from app.agents.stubs import (
    clean_run,
    missing_price,
    missing_sheet,
    not_ready,
    planted_inconsistency,
    prospect_a,
    prospect_b,
    prospect_c,
    prospect_own,
)
from app.schema.bundles import PromptBundle

SCENARIOS: dict[str, StubScenario] = {
    s.dataset_id: s
    for s in (
        clean_run.SCENARIO,
        planted_inconsistency.SCENARIO,
        missing_sheet.SCENARIO,
        missing_price.SCENARIO,
        not_ready.SCENARIO,
        prospect_own.SCENARIO,
        prospect_a.SCENARIO,
        prospect_b.SCENARIO,
        prospect_c.SCENARIO,
    )
}


def scenario_for(dataset_id: str) -> StubScenario:
    try:
        return SCENARIOS[dataset_id]
    except KeyError as error:
        raise KeyError(f"no stub scenario for dataset {dataset_id}") from error


def bundle_for(prompt_ref: str) -> PromptBundle | None:
    for scenario in SCENARIOS.values():
        found = scenario.bundles().get(prompt_ref)
        if found is not None:
            return found
    return None
