"""Scenario 6, Prospect own. The dataset holds no inputs yet, so the S1 stub performs a dry
intake and stops after the readiness grade. Exit dry_intake. Replaced by a verified live
recording in S9."""

from __future__ import annotations

from app.agents.base import Emit, HumanScript, Marks, StubScenario
from app.agents.stubs._common import checklist, meter, rfp_plan
from app.agents.stubs._rfp_base import Bundles, brief, intake_readiness, m

D = "prospect-own"
PROJECT = "Prospect request placeholder [fixture]"
B = Bundles(D, PROJECT)

INTAKE = [
    Emit("intake", "intake.brief", m(0, 18), {"brief": brief(PROJECT)}, B.intake),
    intake_readiness(
        B.intake,
        m(0, 22),
        "ready_with_assumptions",
        checklist(
            ("Scope of work", "pass", ""),
            ("Drawing set", "pass", "placeholder set"),
            ("Specifications", "pass", ""),
            ("Deadline", "pass", ""),
            ("Site conditions", "assumed", "not described; standard access assumed"),
            ("Contract form", "pass", ""),
            ("Prospect brand file", "pass", "template brand.yaml"),
            ("Addenda acknowledged", "pass", ""),
            ("Bid bond", "pass", ""),
        ),
        meter(10000, 0.05, 22000),
    ),
]

SCENARIO = StubScenario(
    dataset_id=D,
    client_id="prospect",
    intake=INTAKE,
    plan=rfp_plan(["brief"], ["BOM"], ["brief"]),
    tasks={},
    assemble=[],
    review=[],
    human_script=HumanScript(decision=None),
    marks=Marks({"intake_enter": 0, "end": m(0, 24)}),
    reasons={
        "start": "A prospect's own file gets a dry intake first, so gaps are found before a full run.",
    },
    dry_intake=True,
)
