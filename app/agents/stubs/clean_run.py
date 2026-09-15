"""Scenario 1, Clean run. Minimal fixture copy. Expected: Intake ready with assumptions
(one non-blocking default), Plan, Work (Estimator then Pricing), Assemble, Review pass,
Handoff. Exit reviewer_pass, retry count 0."""

from __future__ import annotations

from app.agents.base import Emit, HumanScript, Marks, StubScenario
from app.agents.stubs._common import checklist, meter, rfp_plan
from app.agents.stubs._rfp_base import (
    ORCH_METERS,
    Bundles,
    brief,
    estimator_steps,
    intake_readiness,
    m,
    pricing_steps,
    reviewer_steps,
    writer_steps,
)

D = "clean-run"
PROJECT = "Northgate Library lighting upgrade [fixture]"
B = Bundles(D, PROJECT)

INTAKE = [
    Emit("intake", "intake.brief", m(0, 20), {"brief": brief(PROJECT)}, B.intake),
    intake_readiness(
        B.intake,
        m(0, 24),
        "ready_with_assumptions",
        checklist(
            ("Scope of work", "pass", ""),
            ("Drawing set E-001 to E-012", "pass", ""),
            ("Specifications", "pass", ""),
            ("Deadline, 3 Nov", "pass", ""),
            ("Site conditions", "pass", ""),
            ("Contract form", "pass", ""),
            ("Prospect brand file", "pass", ""),
            ("Addenda acknowledged", "pass", ""),
            ("Bid bond not stated", "assumed", "non-blocking, default proposed"),
        ),
        meter(12000, 0.06, 24000),
    ),
    Emit(
        "intake",
        "clarification.needed",
        m(0, 24),
        {
            "question_id": "q_bid_bond",
            "question": "Is a bid bond required?",
            "why_it_matters": "It changes the submission package, not the price.",
            "proposed_default": "No bid bond",
            "blocking": False,
        },
        B.intake,
    ),
]

SCENARIO = StubScenario(
    dataset_id=D,
    client_id="northgate-library",
    intake=INTAKE,
    plan=rfp_plan(
        ["brief", "drawings E-001 to E-012", "estimating conventions"],
        ["BOM", "supplier price fixture", "knowledge file markup rules"],
        ["brief", "specialist outputs", "template", "knowledge file"],
    ),
    tasks={"t1": estimator_steps(B.estimator, m(0, 40)), "t2": pricing_steps(B.pricing, m(1, 8))},
    assemble=[writer_steps(B.writer, m(1, 36), "24 provenance tags")],
    review=[
        reviewer_steps(
            B.reviewer, m(1, 58), [], "Verdict on v1: pass. Figures match the takeoff and the priced BOM."
        )
    ],
    human_script=HumanScript(decision="approve"),
    marks=Marks(
        {
            "intake_enter": 0,
            "assumption": m(0, 26),
            "plan_enter": m(0, 28),
            "plan": m(0, 29),
            "work_enter": m(0, 30),
            "dispatch": m(0, 31),
            "assemble_enter": m(1, 30),
            "assemble_dispatch_1": m(1, 31),
            "review_enter_1": m(1, 40),
            "handoff_enter": m(2, 0),
            "handoff": m(2, 1),
            "approve": m(2, 2),
            "end": m(2, 3),
        }
    ),
    reasons={"assumption": "A bid bond is non-blocking and the default is safe; it is flagged for Handoff."},
    dispatch_summaries={
        "t1": "Takeoff: drawing set E-001 to E-012. Producing the bill of materials and a labour estimate.",
        "t2": "Price the BOM from the supplier fixture once the takeoff is complete.",
    },
    orchestrator_meters=ORCH_METERS,
)
