"""Scenario 8, Prospect B. A real bid package that is internally consistent under the rules of its
occupancy type (spec section 7). Expected: Ready with assumptions, no clarification, Review pass first
time. Exit reviewer_pass, retry count 0. Minimal fixture copy until the owner supplies redacted inputs
and the golden log is recorded from a verified live run. Nothing here names the prospect, the project,
or the site (CLAUDE.md rule 11)."""

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

D = "prospect-b"
PROJECT = "Prospect B clinic relocation [fixture]"
B = Bundles(D, PROJECT)

INTAKE = [
    Emit("intake", "intake.brief", m(0, 20), {"brief": brief(PROJECT)}, B.intake),
    intake_readiness(
        B.intake,
        m(0, 24),
        "ready_with_assumptions",
        checklist(
            ("Scope of work", "pass", ""),
            ("Drawing set, electrical", "pass", "prepared from one binder"),
            ("Specifications", "pass", "Division 26 on the electrical cover sheet"),
            ("Deadline", "pass", ""),
            ("Site conditions", "pass", ""),
            ("Contract form", "pass", ""),
            ("Prospect brand file", "pass", "template brand.yaml"),
            ("Addenda acknowledged", "pass", ""),
            (
                "Revision and issue date on each sheet",
                "assumed",
                "Issued for building permit and tender on every sheet; the occupancy rules apply as drawn.",
            ),
        ),
        meter(12000, 0.06, 24000),
    ),
]

SCENARIO = StubScenario(
    dataset_id=D,
    client_id="prospect-b",
    intake=INTAKE,
    plan=rfp_plan(
        ["brief", "prepared drawing sheets", "estimating conventions"],
        ["BOM", "supplier price fixture", "knowledge file markup rules"],
        ["brief", "specialist outputs", "template", "knowledge file"],
    ),
    tasks={
        "t1": estimator_steps(B.estimator, m(0, 40), lines=33),
        "t2": pricing_steps(B.pricing, m(1, 8), lines=33),
    },
    assemble=[writer_steps(B.writer, m(1, 36), "22 provenance tags")],
    review=[
        reviewer_steps(
            B.reviewer,
            m(1, 58),
            [],
            "Verdict on v1: pass. Figures match the takeoff and the priced BOM; the set is consistent for its occupancy.",
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
        "start": "A real package starts with a readiness grade so the issue stamp is on record before anyone works.",
    },
    dispatch_summaries={
        "t1": "Takeoff from the prepared sheets. Producing the bill of materials and a labour estimate.",
        "t2": "Price the BOM from the supplier fixture once the takeoff is complete.",
    },
    orchestrator_meters=ORCH_METERS,
)
