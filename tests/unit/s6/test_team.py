"""Eight team cards from the roster, the seat definitions and the content file (spec FR-005)."""

from __future__ import annotations

from app.intro.team import SWAP_NOTE, team_cards


def test_eight_cards_in_order_with_the_appraisal_swap_ins() -> None:
    cards = team_cards()
    assert [c.agent_id for c in cards] == [
        "orchestrator",
        "intake",
        "estimator",
        "pricing",
        "writer",
        "reviewer",
        "case",
        "market",
    ]
    assert [c.role for c in cards[:6]] == [
        "Orchestrator",
        "Intake Analyst",
        "Estimator",
        "Pricing",
        "Writer",
        "Reviewer",
    ]
    assert cards[0].names == "Oscar / Olivia" and cards[0].blurb.startswith("The project manager.")
    assert cards[6].role == "Case Manager" and cards[6].model == SWAP_NOTE and cards[6].swap_in
    assert cards[7].names == "Marcus / Maya" and cards[7].swap_in


def test_the_reviewer_has_no_tools_and_sees_only_its_scope() -> None:
    reviewer = next(c for c in team_cards() if c.agent_id == "reviewer")
    assert reviewer.tools == "none, on purpose"
    assert (
        "the brief" in reviewer.sees
        and "the compiled pages" in reviewer.sees
        and "the reviewer criteria" in reviewer.sees
    )
    assert "specialist" not in reviewer.sees
    estimator = next(c for c in team_cards() if c.agent_id == "estimator")
    assert "drawing reader" in estimator.tools and "quantity calculator" in estimator.tools


def test_model_labels_come_from_the_seat_table_when_given() -> None:
    table = {"seats": [{"seat": "pricing", "card": {"model": {"label": "qwen3.5 9b, local"}}}]}
    pricing = next(c for c in team_cards(table) if c.agent_id == "pricing")
    assert pricing.model == "qwen3.5 9b, local"
    assert all(c.model for c in team_cards()) and all(c.initials for c in team_cards())
