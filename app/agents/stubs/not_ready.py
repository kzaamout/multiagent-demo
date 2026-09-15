"""Scenario 5, Not ready. Minimal fixture copy. No submission deadline and no Division 26
specification although the scope references specifications. Intake verdict not ready; the
run terminates before Plan. Exit not_ready."""

from __future__ import annotations

from app.agents.base import Emit, HumanScript, Marks, StubScenario
from app.agents.stubs._common import checklist, meter, rfp_plan
from app.agents.stubs._rfp_base import Bundles, brief, intake_readiness, m

D = "not-ready"
PROJECT = "Riverbend community centre electrical [fixture]"
B = Bundles(D, PROJECT)

INTAKE = [
    Emit("intake", "intake.brief", m(0, 18), {"brief": brief(PROJECT, deadline=None, spec=None)}, B.intake),
    intake_readiness(
        B.intake,
        m(0, 22),
        "not_ready",
        checklist(
            ("Scope of work", "pass", "references Division 26 specifications"),
            ("Drawing set E-001 to E-012", "pass", ""),
            ("Division 26 specification", "fail", "The scope references specifications that are not attached."),
            ("Submission deadline", "fail", "No deadline appears anywhere in the request."),
            ("Site conditions", "pass", ""),
            ("Contract form", "pass", ""),
            ("Prospect brand file", "pass", ""),
            ("Addenda acknowledged", "pass", ""),
            ("Bid bond", "pass", ""),
        ),
        meter(11000, 0.05, 22000),
    ),
]

SCENARIO = StubScenario(
    dataset_id=D,
    client_id="riverbend-community-centre",
    intake=INTAKE,
    plan=rfp_plan(["brief"], ["BOM"], ["brief"]),
    tasks={},
    assemble=[],
    review=[],
    human_script=HumanScript(decision=None),
    marks=Marks({"intake_enter": 0, "end": m(0, 24)}),
    reasons={
        "not_ready": "The request has no deadline and no specification, so no specialist can work on it yet.",
    },
)
