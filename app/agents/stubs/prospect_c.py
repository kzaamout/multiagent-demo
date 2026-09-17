"""Scenario 9, Prospect C. A real package with architectural drawings only and no electrical set
(spec section 7). Intake grades the single-line and the electrical floor plans as missing, both
blocking, and the run stops before Plan. Exit not_ready. Minimal fixture copy until the owner supplies
redacted inputs and the golden log is recorded from a verified live run. Nothing here names the
prospect, the project, or the site (CLAUDE.md rule 11)."""

from __future__ import annotations

from app.agents.base import Emit, HumanScript, Marks, StubScenario
from app.agents.stubs._common import checklist, meter, rfp_plan
from app.agents.stubs._rfp_base import Bundles, brief, intake_readiness, m

D = "prospect-c"
PROJECT = "Prospect C retail unit [fixture]"
B = Bundles(D, PROJECT)

INTAKE = [
    Emit("intake", "intake.brief", m(0, 18), {"brief": brief(PROJECT, spec=None)}, B.intake),
    intake_readiness(
        B.intake,
        m(0, 22),
        "not_ready",
        checklist(
            ("Scope of work", "pass", "electrical fit-out described in the request"),
            (
                "Single-line diagram",
                "fail",
                "The binder holds architectural sheets only; no electrical sheet was prepared.",
            ),
            (
                "Electrical floor plans, power and lighting",
                "fail",
                "No electrical plan for any level; the architectural plans carry no circuits or devices.",
            ),
            ("Specifications", "assumed", "No Division 26 section; the request does not reference one."),
            ("Deadline", "pass", ""),
            ("Site conditions", "pass", ""),
            ("Contract form", "pass", ""),
            ("Prospect brand file", "pass", "template brand.yaml"),
            ("Revision and issue date on each sheet", "assumed", "Stamp unknown on several sheets."),
        ),
        meter(11000, 0.05, 22000),
    ),
]

SCENARIO = StubScenario(
    dataset_id=D,
    client_id="prospect-c",
    intake=INTAKE,
    plan=rfp_plan(["brief"], ["BOM"], ["brief"]),
    tasks={},
    assemble=[],
    review=[],
    human_script=HumanScript(decision=None),
    marks=Marks({"intake_enter": 0, "end": m(0, 24)}),
    reasons={
        "not_ready": "The package has no electrical set, so there is nothing for a specialist to take off.",
    },
)
