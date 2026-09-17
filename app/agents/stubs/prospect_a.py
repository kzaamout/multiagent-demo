"""Scenario 7, Prospect A. A real bid package (spec section 7): an Issued for Construction
architectural set with an electrical set issued for permit, carrying a real disagreement between a
panel note on one sheet and the bus rating on the panel schedule. Expected: the issue stamp surfaces
as an assumption, one Review fail routed to the Estimator, rework, pass. Exit reviewer_pass with retry
count 1. Minimal fixture copy until the owner supplies redacted inputs and the golden log is recorded
from a verified live run. Nothing here names the prospect, the project, or the site (CLAUDE.md rule 11)."""

from __future__ import annotations

from app.agents.base import Emit, HumanScript, Marks, StubScenario
from app.agents.stubs._common import (
    checklist,
    completed,
    draft,
    finding,
    meter,
    progress,
    rfp_plan,
    verdict,
)
from app.agents.stubs._rfp_base import (
    ORCH_METERS,
    Bundles,
    brief,
    estimator_steps,
    intake_readiness,
    m,
    pricing_steps,
)

D = "prospect-a"
PROJECT = "Prospect A tenant fit-out [fixture]"
B = Bundles(D, PROJECT)

INTAKE = [
    Emit("intake", "intake.brief", m(0, 20), {"brief": brief(PROJECT)}, B.intake),
    intake_readiness(
        B.intake,
        m(0, 24),
        "ready_with_assumptions",
        checklist(
            ("Scope of work", "pass", ""),
            ("Drawing set, architectural and electrical", "pass", "prepared from two binders"),
            ("Specifications", "pass", "Division 26 on the electrical cover sheet"),
            ("Deadline", "pass", ""),
            ("Site conditions", "pass", ""),
            ("Contract form", "pass", ""),
            ("Prospect brand file", "pass", "template brand.yaml"),
            ("Addenda acknowledged", "pass", ""),
            (
                "Revision and issue date on each sheet",
                "assumed",
                "The electrical set is issued for permit, not for tender or construction; priced as issued.",
            ),
        ),
        meter(12000, 0.06, 24000),
    ),
]

REWORK = [
    progress(
        "estimator",
        "t1-rework1",
        m(3, 22),
        "Re-reading the panel note and the schedule bus rating on the prepared sheets.",
        B.estimator,
        meter(9000, 0.06, 9000),
        headline="Confirming the panel bus rating",
    ),
    completed(
        "estimator",
        "t1-rework1",
        m(3, 31),
        "Rework complete, schedule rating carried, note flagged",
        "Rework complete. The panel schedule bus rating is carried in the BOM; the conflicting panel note is listed as an assumption for the client.",
        {"bom_changed": True, "flags": ["panel note disagrees with schedule bus rating"]},
        [{"tool": "vision.read_drawing", "source": "prepared panel schedule sheet", "confidence": 0.95}],
        B.estimator,
        meter(8700, 0.07, 9000),
    ),
]

ASSEMBLE_1 = [draft(m(2, 41), 1, 28, "t1", "6 pages, 28 provenance tags", B.writer, meter(12000, 0.08, 3000))]
ASSEMBLE_2 = [
    draft(
        m(3, 48),
        2,
        28,
        "t1-rework1",
        "panel rating corrected to the schedule",
        B.writer,
        meter(12700, 0.08, 16000),
    )
]

REVIEW_1 = [
    verdict(
        m(3, 12),
        False,
        [
            finding(
                "f1",
                "major",
                "The proposal carries the panel note rating; the panel schedule shows a different bus rating.",
                "scope section, distribution paragraph vs BOM panel line",
                "work",
                "estimator",
            )
        ],
        "Verdict on v1: one major finding. The panel rating in the proposal does not match the schedule.",
        B.reviewer,
        meter(15000, 0.05, 30000),
    )
]
REVIEW_2 = [
    verdict(
        m(4, 5),
        True,
        [],
        "Verdict on v2: pass. The panel rating follows the schedule and the disagreement is disclosed.",
        B.reviewer,
        meter(16500, 0.06, 16000),
    )
]

SCENARIO = StubScenario(
    dataset_id=D,
    client_id="prospect-a",
    intake=INTAKE,
    plan=rfp_plan(
        ["brief", "prepared drawing sheets", "estimating conventions"],
        ["BOM", "supplier price fixture", "knowledge file markup rules"],
        ["brief", "specialist outputs", "template", "knowledge file"],
    ),
    tasks={
        "t1": estimator_steps(B.estimator, m(0, 40), lines=41),
        "t2": pricing_steps(B.pricing, m(1, 8), lines=41),
    },
    assemble=[ASSEMBLE_1, ASSEMBLE_2],
    review=[REVIEW_1, REVIEW_2],
    rework={"estimator": REWORK},
    human_script=HumanScript(decision="approve"),
    marks=Marks(
        {
            "intake_enter": 0,
            "plan_enter": m(0, 28),
            "plan": m(0, 29),
            "work_enter": m(0, 30),
            "dispatch": m(0, 31),
            "assemble_enter": m(2, 39),
            "assemble_dispatch_1": m(2, 39, 500),
            "review_enter_1": m(2, 42),
            "retry": m(3, 13),
            "route_back": m(3, 13),
            "rework_dispatch": m(3, 14),
            "assemble_enter_rework": m(3, 32),
            "assemble_dispatch_2": m(3, 33),
            "review_enter_2": m(3, 49),
            "handoff_enter": m(4, 11),
            "handoff": m(4, 12),
            "approve": m(4, 13),
            "end": m(4, 14),
        }
    ),
    reasons={
        "start": "A real package starts with a readiness grade so the issue stamp is on record before anyone works.",
        "route_back_work": "The Reviewer found a rating disagreement in the data, so the Estimator reworks it.",
    },
    dispatch_summaries={
        "t1": "Takeoff from the prepared sheets. Producing the bill of materials and a labour estimate.",
        "t2": "Price the BOM from the supplier fixture once the takeoff is complete.",
    },
    orchestrator_meters=ORCH_METERS,
)
