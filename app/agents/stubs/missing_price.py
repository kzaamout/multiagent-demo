"""Scenario 4, Missing price. Minimal fixture copy. Exit signs are absent from the price
fixture. Pricing lists the exception, the Writer discloses it, the Reviewer records a minor
finding, and the run passes. Exit reviewer_pass, retry count 0, one minor finding."""

from __future__ import annotations

from app.agents.base import Emit, HumanScript, Marks, StubScenario
from app.agents.stubs._common import checklist, finding, meter, rfp_plan
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

D = "missing-price"
PROJECT = "Elm Street school gymnasium electrical [fixture]"
B = Bundles(D, PROJECT)

INTAKE = [
    Emit("intake", "intake.brief", m(0, 20), {"brief": brief(PROJECT)}, B.intake),
    intake_readiness(
        B.intake,
        m(0, 24),
        "ready",
        checklist(
            ("Scope of work", "pass", ""),
            ("Drawing set E-001 to E-012", "pass", ""),
            ("Specifications", "pass", ""),
            ("Deadline, 3 Nov", "pass", ""),
            ("Site conditions", "pass", ""),
            ("Contract form", "pass", ""),
            ("Prospect brand file", "pass", ""),
            ("Addenda acknowledged", "pass", ""),
            ("Bid bond", "pass", ""),
        ),
        meter(12000, 0.06, 24000),
    ),
]

SCENARIO = StubScenario(
    dataset_id=D,
    client_id="elm-street-school",
    intake=INTAKE,
    plan=rfp_plan(
        ["brief", "drawings E-001 to E-012", "estimating conventions"],
        ["BOM", "supplier price fixture", "knowledge file markup rules"],
        ["brief", "specialist outputs", "template", "knowledge file"],
    ),
    tasks={
        "t1": estimator_steps(B.estimator, m(0, 40), lines=38),
        "t2": pricing_steps(
            B.pricing, m(1, 8), lines=38, exceptions=["exit signs not in the supplier fixture"]
        ),
    },
    assemble=[
        writer_steps(B.writer, m(1, 36), "24 provenance tags, exit signs disclosed as an unpriced exclusion")
    ],
    review=[
        reviewer_steps(
            B.reviewer,
            m(1, 58),
            [
                finding(
                    "f1",
                    "minor",
                    "Exit signs are excluded as unpriced; the exclusion is disclosed but has no allowance.",
                    "pricing exceptions, exclusions section",
                    None,
                    None,
                )
            ],
            "Verdict on v1: pass. One minor note: the unpriced exit signs are disclosed as an exclusion.",
        )
    ],
    human_script=HumanScript(decision="approve"),
    marks=Marks(
        {
            "intake_enter": 0,
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
    reasons={
        "handoff": "Verdict on v1 is pass with one minor finding; the unpriced item rides to Handoff as a note.",
    },
    dispatch_summaries={
        "t1": "Takeoff: drawing set E-001 to E-012. Producing the bill of materials and a labour estimate.",
        "t2": "Price the BOM from the supplier fixture once the takeoff is complete.",
    },
    orchestrator_meters=ORCH_METERS,
)
