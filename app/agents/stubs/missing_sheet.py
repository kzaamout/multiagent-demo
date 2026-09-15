"""Scenario 3, Missing sheet. Minimal fixture copy. The panel schedule for a panel on the
single-line is absent. Intake passes; the Estimator raises a blocker that needs a human;
the presenter escalates. Exit blocker_escalated. The golden log records the Escalate path
(datasets/missing-sheet/README.md asks that the path be documented).

The Answer path continues to a pass and is exercised by a unit test only."""

from __future__ import annotations

from app.agents.base import Emit, HumanScript, Marks, StubScenario
from app.agents.stubs._common import checklist, completed, meter, progress, rfp_plan
from app.agents.stubs._rfp_base import (
    ORCH_METERS,
    Bundles,
    brief,
    intake_readiness,
    m,
    pricing_steps,
    reviewer_steps,
    writer_steps,
)

D = "missing-sheet"
PROJECT = "Harbour Depot office electrical [fixture]"
B = Bundles(D, PROJECT)

INTAKE = [
    Emit("intake", "intake.brief", m(0, 20), {"brief": brief(PROJECT)}, B.intake),
    intake_readiness(
        B.intake,
        m(0, 24),
        "ready",
        checklist(
            ("Scope of work", "pass", ""),
            ("Drawing set E-001 to E-012", "pass", "sheet count matches the index"),
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

ESTIMATOR = [
    progress(
        "estimator", "t1", m(0, 44),
        "Reading single-line E-001. Panels MDP, LP-1 and LP-2 shown.",
        B.estimator, meter(8000, 0.05, 9000), headline="Reading drawings",
    ),
    progress(
        "estimator", "t1", m(0, 55),
        "No panel schedule for LP-2 in the set. E-101 covers MDP and LP-1 only.",
        B.estimator, meter(5000, 0.03, 7000), headline="Panel schedule for LP-2 not found",
    ),
    Emit(
        "estimator",
        "blocker.raised",
        m(1, 2),
        {
            "blocker_id": "b_lp2_schedule",
            "task_id": "t1",
            "agent_id": "estimator",
            "description": "Panel schedule for LP-2 is missing from the drawing set; the single-line E-001 shows LP-2.",
            "needs_human": True,
            "route_back_to": None,
        },
        B.estimator,
    ),
]

ANSWER_CONTINUATION = [
    progress(
        "estimator", "t1", m(1, 30),
        "Proceeding with LP-2 sized from the answer provided.",
        B.estimator, meter(6000, 0.04, 6000), headline="Resuming takeoff with the answer",
    ),
    completed(
        "estimator", "t1", m(1, 48),
        "Takeoff complete, 41 BOM lines",
        "Done. BOM 41 lines. LP-2 lines are based on the answer given at the blocker.",
        {"bom_lines": 41, "labour_hours": 256, "flags": ["LP-2 from presenter answer"]},
        [{"tool": "vision.read_drawing", "source": "E-001 single-line", "confidence": 0.9}],
        B.estimator, meter(14000, 0.1, 18000),
    ),
]

SCENARIO = StubScenario(
    dataset_id=D,
    client_id="harbour-depot",
    intake=INTAKE,
    plan=rfp_plan(
        ["brief", "drawings E-001 to E-012", "estimating conventions"],
        ["BOM", "supplier price fixture", "knowledge file markup rules"],
        ["brief", "specialist outputs", "template", "knowledge file"],
    ),
    tasks={"t1": ESTIMATOR, "t2": pricing_steps(B.pricing, m(1, 52), lines=41)},
    assemble=[writer_steps(B.writer, m(2, 20), "22 provenance tags")],
    review=[reviewer_steps(B.reviewer, m(2, 40), [], "Verdict on v1: pass.")],
    blocker_answer_continuation={"t1": ANSWER_CONTINUATION},
    human_script=HumanScript(blocker_action="escalate", blocker_answer="A missing sheet cannot be supplied live."),
    marks=Marks(
        {
            "intake_enter": 0,
            "plan_enter": m(0, 28),
            "plan": m(0, 29),
            "work_enter": m(0, 30),
            "dispatch": m(0, 31),
            "blocker": m(1, 3),
            "blocker_answer": m(1, 20),
            "assemble_enter": m(2, 14),
            "assemble_dispatch_1": m(2, 15),
            "review_enter_1": m(2, 24),
            "handoff_enter": m(2, 42),
            "handoff": m(2, 43),
            "approve": m(2, 44),
            "end": m(1, 21),
        }
    ),
    reasons={
        "blocker": "{estimator} cannot size LP-2 without its panel schedule, so the run pauses for you.",
        "escalated": "A missing sheet cannot be supplied live, so the run ends and lists what is missing.",
    },
    dispatch_summaries={
        "t1": "Takeoff: drawing set E-001 to E-012. Producing the bill of materials and a labour estimate.",
        "t2": "Price the BOM from the supplier fixture once the takeoff is complete.",
    },
    orchestrator_meters={"plan": meter(1600, 0.01, 1000)},
)

_ = ORCH_METERS
