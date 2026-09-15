"""Scenario 2, Planted inconsistency. Fixture copy taken from the Claude Design export's
sample transcript (design/README.md: the scenario 2 sample copy becomes this stub).

Offsets match the times on the export's cards; meter deltas sum to the export's paused,
running, and terminated meter values. Names in reasons use {seat} placeholders because the
roster is chosen per run.
"""

from __future__ import annotations

from app.agents.base import Emit, HumanScript, Marks, StubScenario
from app.agents.stubs._common import (
    SYSTEM_ESTIMATOR,
    SYSTEM_INTAKE,
    SYSTEM_PRICING,
    SYSTEM_REVIEWER,
    SYSTEM_WRITER,
    bundle,
    checklist,
    completed,
    draft,
    finding,
    legibility,
    meter,
    progress,
    rfp_plan,
    tool,
    verdict,
)

D = "planted-inconsistency"


def m(minutes: int, seconds: int, ms: int = 0) -> int:
    return (minutes * 60 + seconds) * 1000 + ms


ANNA = bundle(
    D,
    1,
    "intake",
    SYSTEM_INTAKE,
    "request/cover-letter.pdf (2 pages)\n"
    "request/drawings E-001 to E-104 (104 pages, legibility scored)\n"
    "request/spec-division-26.pdf (48 pages)\n"
    "knowledge/riverside-clinic.md (empty, first run)\n"
    "checklists/readiness-rfp.md (9 items)",
    "Grade readiness for dataset 02 and return brief, verdict, checklist and clarification.needed events.",
    ["document.parse_pdf", "document.extract_attachments"],
)
ELENA = bundle(
    D,
    2,
    "estimator",
    SYSTEM_ESTIMATOR,
    "brief.md v1\ndrawings E-001 to E-104 (page images)\nconventions/estimating-electrical.md\n"
    "answers: service voltage 208Y/120 V",
    "Takeoff for Riverside Clinic tenant fit-out. Return BOM, labour estimate, flags.",
    ["vision.read_drawing", "quantity.calculate"],
)
PAVEL = bundle(
    D,
    3,
    "pricing",
    SYSTEM_PRICING,
    "BOM from the Estimator (47 lines)\nfixtures/supplier-prices.csv\nknowledge/riverside-clinic.md (markup rules)",
    "Price the BOM for Riverside Clinic tenant fit-out. Return priced BOM, cost summary, exceptions.",
    ["price_list.lookup"],
)
WILLA_1 = bundle(
    D,
    4,
    "writer",
    SYSTEM_WRITER,
    "brief.md v1\nBOM and labour estimate from the Estimator\npriced BOM and exceptions from Pricing\n"
    "templates/rfp-response.md\nknowledge/riverside-clinic.md",
    "Assemble proposal draft v1 with a provenance tag on every figure.",
    ["template.render", "compile.trigger"],
)
RAFAEL_1 = bundle(
    D,
    5,
    "reviewer",
    SYSTEM_REVIEWER,
    "brief.md v1\nartifact v1, 6 page images\ncriteria/reviewer-rfp.md",
    "Review artifact v1.",
    [],
)
ELENA_REWORK = bundle(
    D,
    6,
    "estimator",
    SYSTEM_ESTIMATOR,
    "brief.md v1\ndrawings E-001 and E-101 (page images)\nReviewer finding f1: section 3.2 states 200 A; BOM and E-001 show 225 A",
    "Confirm the main distribution panel rating and correct the BOM if needed.",
    ["vision.read_drawing"],
)
WILLA_2 = bundle(
    D,
    7,
    "writer",
    SYSTEM_WRITER,
    "brief.md v1\nconfirmed takeoff from the Estimator rework\npriced BOM and exceptions from Pricing\n"
    "Reviewer findings on v1\ntemplates/rfp-response.md",
    "Assemble proposal draft v2 correcting section 3.2.",
    ["template.render", "compile.trigger"],
)
RAFAEL_2 = bundle(
    D,
    8,
    "reviewer",
    SYSTEM_REVIEWER,
    "brief.md v1\nartifact v2, 6 page images\ncriteria/reviewer-rfp.md",
    "Review artifact v2.",
    [],
)

INTAKE = [
    Emit(
        "intake",
        "intake.brief",
        m(0, 38),
        {
            "brief": {
                "project": "Riverside Clinic tenant fit-out",
                "scope": "Electrical distribution and lighting for 1,850 m2",
                "drawing_set": "E-001 to E-104",
                "drawing_pages": 104,
                "specification": "Division 26, 48 pages",
                "deadline": "12 Oct",
            }
        },
        ANNA,
    ),
    Emit(
        "intake",
        "intake.readiness",
        m(0, 41),
        {
            "verdict": "ready_with_assumptions",
            "checklist": checklist(
                ("Scope of work", "pass", ""),
                ("Drawing set E-001 to E-104", "pass", ""),
                ("Specifications", "pass", ""),
                ("Deadline, 12 Oct", "pass", ""),
                ("Site conditions", "pass", ""),
                ("Contract form", "pass", ""),
                ("Prospect brand file", "pass", ""),
                ("Bid validity not stated", "assumed", "non-blocking, default proposed"),
                ("Service voltage not on cover sheet", "assumed", "blocking, question raised"),
            ),
            "legibility": legibility(
                {"E-001": 0.97, "E-101": 0.82, "E-102": 0.93, "E-103": 0.95, "E-104": 0.94}
            ),
        },
        ANNA,
        meter(18400, 0.09, 41000),
    ),
    Emit(
        "intake",
        "clarification.needed",
        m(0, 41),
        {
            "question_id": "q_bid_validity",
            "question": "How long must the bid remain valid?",
            "why_it_matters": "The request does not state a validity period.",
            "proposed_default": "60 days",
            "blocking": False,
        },
        ANNA,
    ),
    Emit(
        "intake",
        "clarification.needed",
        m(0, 41),
        {
            "question_id": "q_service_voltage",
            "question": "Which service voltage applies to the 225 A main?",
            "why_it_matters": "It sets conductor sizes and every distribution line in the bill of materials.",
            "proposed_default": "208Y/120 V",
            "blocking": True,
        },
        ANNA,
    ),
    Emit(
        "intake",
        "clarification.needed",
        m(0, 41),
        {
            "question_id": "q_led_retrofit_alternate",
            "question": "Is the LED retrofit alternate to be priced?",
            "why_it_matters": "It adds roughly 40 lines and a second pricing pass.",
            "proposed_default": "No, base bid only",
            "blocking": True,
        },
        ANNA,
    ),
]

ESTIMATOR = [
    progress(
        "estimator",
        "t1",
        m(1, 19),
        "Reading single-line E-001. Main distribution panel 225 A, 3 phase, 4 wire.",
        ELENA,
        meter(9000, 0.06, 12000),
        headline="Reading drawings, MDP 225 A on the single-line",
    ),
    progress(
        "estimator",
        "t1",
        m(1, 28),
        "Panel schedule E-101 lists the MDP at 200 A. The single-line shows 225 A. "
        "Proceeding on the single-line and flagging the inconsistency.",
        ELENA,
        meter(7000, 0.05, 9000),
        headline="Reading drawings, MDP 200 A vs 225 A flagged",
    ),
    progress(
        "estimator",
        "t1",
        m(1, 35),
        "Counting branch circuits on E-102 to E-104",
        ELENA,
        meter(6300, 0.04, 7000),
        headline="Reading drawings, MDP 200 A vs 225 A flagged",
    ),
    tool(
        "estimator",
        "t1",
        m(1, 44),
        "vision.read_drawing",
        "E-102 to E-104",
        "42 branch circuits counted",
        8400,
        ELENA,
    ),
    tool(
        "estimator",
        "t1",
        m(1, 53),
        "quantity.calculate",
        "circuits, fixtures, feeders",
        "47 BOM lines",
        310,
        ELENA,
    ),
    completed(
        "estimator",
        "t1",
        m(2, 2),
        "Takeoff complete, 47 BOM lines, 1 flag carried",
        "Done. BOM 47 lines, each with a drawing reference. Labour 312 hours. "
        "One flag carried: MDP rating 200 A vs 225 A.",
        {"bom_lines": 47, "labour_hours": 312, "flags": ["MDP rating 200 A on E-101 vs 225 A on E-001"]},
        [
            {"tool": "vision.read_drawing", "source": "E-001 single-line", "confidence": 0.96},
            {"tool": "quantity.calculate", "source": "E-102 to E-104", "confidence": 0.9},
        ],
        ELENA,
        meter(21000, 0.14, 27000),
    ),
]

PRICING = [
    progress(
        "pricing",
        "t2",
        m(2, 12),
        "Pricing 47 lines from the supplier fixture.",
        PAVEL,
        meter(4000, 0.0, 6000),
        headline="Pricing the BOM, 47 lines",
    ),
    tool(
        "pricing", "t2", m(2, 25), "price_list.lookup", "47 item codes", "46 found, 1 long-lead", 120, PAVEL
    ),
    completed(
        "pricing",
        "t2",
        m(2, 38),
        "46 of 47 lines priced, 1 long-lead exception",
        "46 of 47 lines priced · 1 exception: 225 A main breaker is long-lead, 6 weeks",
        {"lines_priced": 46, "lines_total": 47, "exceptions": ["225 A main breaker, long-lead 6 weeks"]},
        [{"tool": "price_list.lookup", "source": "fixtures/supplier-prices.csv", "confidence": 1.0}],
        PAVEL,
        meter(5100, 0.0, 8000),
    ),
]

REWORK = [
    progress(
        "estimator",
        "t1-rework1",
        m(3, 22),
        "Checking the revision block on E-001 and the date on panel schedule E-101.",
        ELENA_REWORK,
        meter(9000, 0.06, 9000),
        headline="Confirming the MDP rating on E-001 and E-101",
    ),
    completed(
        "estimator",
        "t1-rework1",
        m(3, 31),
        "Rework complete, 225 A confirmed, BOM unchanged",
        "Rework complete · 225 A confirmed from E-001 rev 2; panel schedule E-101 is superseded · BOM unchanged",
        {"confirmed_rating": "225 A", "bom_changed": False},
        [{"tool": "vision.read_drawing", "source": "E-001 rev 2 revision block", "confidence": 0.97}],
        ELENA_REWORK,
        meter(8700, 0.07, 9000),
    ),
]

ASSEMBLE_1 = [draft(m(2, 41), 1, 31, "t1", "6 pages, 31 provenance tags", WILLA_1, meter(12000, 0.08, 3000))]
ASSEMBLE_2 = [
    draft(m(3, 48), 2, 31, "t1-rework1", "section 3.2 corrected to 225 A", WILLA_2, meter(12700, 0.08, 16000))
]

REVIEW_1 = [
    verdict(
        m(3, 12),
        False,
        [
            finding(
                "f1",
                "major",
                "Section 3.2 states a 200 A service; the BOM and drawing E-001 show 225 A.",
                "page 3, paragraph 2 vs BOM line 4",
                "work",
                "estimator",
            ),
            finding(
                "f2",
                "minor",
                "Long-lead item on BOM line 31 is not called out in the schedule section.",
                "page 5, schedule table",
                "assemble",
                "writer",
            ),
        ],
        "Verdict on v1: one major finding, one minor. The service rating in the proposal does not match the drawing set.",
        RAFAEL_1,
        meter(15000, 0.05, 30000),
    )
]
REVIEW_2 = [
    verdict(
        m(4, 5),
        True,
        [
            finding(
                "f3",
                "minor",
                "Line 31 breaker priced at estimate rather than supplier quote.",
                "page 5, pricing exceptions",
                None,
                None,
            )
        ],
        "Verdict on v2: pass. Service rating consistent across section 3.2, the BOM and E-001. One minor note remains.",
        RAFAEL_2,
        meter(16500, 0.06, 16000),
    )
]

SCENARIO = StubScenario(
    dataset_id=D,
    client_id="riverside-clinic",
    intake=INTAKE,
    plan=rfp_plan(
        ["brief", "drawings E-001 to E-104", "estimating conventions"],
        ["BOM", "supplier price fixture", "knowledge file markup rules"],
        ["brief", "specialist outputs", "template", "knowledge file"],
    ),
    tasks={"t1": ESTIMATOR, "t2": PRICING},
    assemble=[ASSEMBLE_1, ASSEMBLE_2],
    review=[REVIEW_1, REVIEW_2],
    rework={"estimator": REWORK},
    human_script=HumanScript(
        answers={"q_service_voltage": "208Y/120 V", "q_led_retrofit_alternate": "base bid only"},
        decision="approve",
    ),
    marks=Marks(
        {
            "intake_enter": 0,
            "assumption": m(0, 43),
            "clarification": m(0, 52),
            "human_answer": m(1, 4),
            "knowledge": m(1, 5),
            "plan_enter": m(1, 5, 500),
            "plan": m(1, 6),
            "work_enter": m(1, 6, 500),
            "dispatch": m(1, 7),
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
        "assumption": "Bid validity is non-blocking; the client knowledge file has no prior answer.",
        "clarification": "Two blocking gaps batched into one question set.",
        "plan": "Pricing cannot cost lines that do not exist yet, so it is sequenced after the takeoff.",
        "route_back_work": "The finding concerns a source figure, so the specialist who produced it resolves it, not the Writer.",
        "handoff": "Verdict on v2 is pass with one minor finding; minor findings ride to Handoff as notes. "
        "Package ready for your approval.",
    },
    target_reasons={
        "route_back_work": "Review failed on one major finding. Routing back to Work: {estimator} confirms the service "
        "rating. Retry 1 of 2. The minor finding rides to Handoff as a note.",
    },
    dispatch_summaries={
        "t1": "Takeoff: drawing set E-001 to E-104. Producing the bill of materials with drawing references per line "
        "and a labour estimate.",
        "t2": "Price the BOM from the supplier fixture once the takeoff is complete.",
        "t1-rework1": "Reviewer finding f1: confirm the service rating in the drawing set.",
    },
    orchestrator_meters={
        "clarification": meter(1100, 0.01, 900),
        "plan": meter(1800, 0.01, 1200),
        "retry": meter(1600, 0.02, 1100),
        "handoff": meter(1700, 0.01, 1300),
    },
)
