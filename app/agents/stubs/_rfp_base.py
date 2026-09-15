"""A minimal electrical RFP run used by the fixture scenarios other than scenario 2.

All text here is minimal plausible fixture copy, marked [fixture] in the prompt bundles.
Each scenario module adjusts the pieces it needs.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import Emit, MeterDelta
from app.agents.stubs._common import (
    FIXTURE,
    SYSTEM_ESTIMATOR,
    SYSTEM_INTAKE,
    SYSTEM_PRICING,
    SYSTEM_REVIEWER,
    SYSTEM_WRITER,
    bundle,
    completed,
    draft,
    legibility,
    meter,
    progress,
    tool,
    verdict,
)
from app.schema.bundles import PromptBundle


def m(minutes: int, seconds: int, ms: int = 0) -> int:
    return (minutes * 60 + seconds) * 1000 + ms


class Bundles:
    def __init__(self, dataset: str, project: str) -> None:
        ctx = f"{FIXTURE} request for {project}"
        self.intake = bundle(
            dataset, 1, "intake", SYSTEM_INTAKE,
            f"{ctx}\nrequest/drawings (fixture set)\nknowledge file\nchecklists/readiness-rfp.md (9 items)",
            f"Grade readiness for {dataset} and return brief, verdict, checklist and clarification events.",
            ["document.parse_pdf", "document.extract_attachments"],
        )
        self.estimator = bundle(
            dataset, 2, "estimator", SYSTEM_ESTIMATOR,
            f"{ctx}\nbrief.md v1\ndrawings (fixture page images)\nconventions/estimating-electrical.md",
            f"Takeoff for {project}. Return BOM, labour estimate, flags.",
            ["vision.read_drawing", "quantity.calculate"],
        )
        self.pricing = bundle(
            dataset, 3, "pricing", SYSTEM_PRICING,
            f"{ctx}\nBOM from the Estimator\nfixtures/supplier-prices.csv\nknowledge file markup rules",
            f"Price the BOM for {project}. Return priced BOM, cost summary, exceptions.",
            ["price_list.lookup"],
        )
        self.writer = bundle(
            dataset, 4, "writer", SYSTEM_WRITER,
            f"{ctx}\nbrief.md v1\nspecialist outputs\ntemplates/rfp-response.md\nknowledge file",
            "Assemble proposal draft v1 with a provenance tag on every figure.",
            ["template.render", "compile.trigger"],
        )
        self.reviewer = bundle(
            dataset, 5, "reviewer", SYSTEM_REVIEWER,
            f"{ctx}\nbrief.md v1\nartifact v1\ncriteria/reviewer-rfp.md",
            "Review artifact v1.",
            [],
        )


def brief(project: str, deadline: str | None = "3 Nov", spec: str | None = "Division 26, 36 pages") -> dict[str, Any]:
    data: dict[str, Any] = {
        "project": project,
        "scope": "Electrical distribution and lighting [fixture]",
        "drawing_set": "E-001 to E-012",
        "drawing_pages": 12,
    }
    if spec:
        data["specification"] = spec
    if deadline:
        data["deadline"] = deadline
    return data


def intake_readiness(
    b: PromptBundle, offset: int, verdict_value: str, items: list[dict[str, str]], cost: MeterDelta
) -> Emit:
    return Emit(
        "intake",
        "intake.readiness",
        offset,
        {
            "verdict": verdict_value,
            "checklist": items,
            "legibility": legibility({"E-001": 0.96, "E-002": 0.94, "E-101": 0.92}),
        },
        b,
        cost,
    )


def estimator_steps(b: PromptBundle, start: int, lines: int = 38) -> list[Emit]:
    return [
        progress("estimator", "t1", start, "Reading single-line E-001 and panel schedules E-101 to E-102.", b,
                 meter(8000, 0.05, 9000), headline="Reading drawings"),
        tool("estimator", "t1", start + 8000, "vision.read_drawing", "E-001, E-101, E-102", "2 panels, 30 circuits", 6100, b),
        tool("estimator", "t1", start + 14000, "quantity.calculate", "circuits, fixtures, feeders", f"{lines} BOM lines", 280, b),
        completed(
            "estimator", "t1", start + 22000,
            f"Takeoff complete, {lines} BOM lines",
            f"Done. BOM {lines} lines, each with a drawing reference. Labour 240 hours. No flags.",
            {"bom_lines": lines, "labour_hours": 240, "flags": []},
            [{"tool": "vision.read_drawing", "source": "E-001 single-line", "confidence": 0.95}],
            b, meter(16000, 0.11, 20000),
        ),
    ]


def pricing_steps(
    b: PromptBundle, start: int, lines: int = 38, exceptions: list[str] | None = None
) -> list[Emit]:
    exc = exceptions or []
    priced = lines - len(exc)
    headline = f"{priced} of {lines} lines priced" + (f", {len(exc)} exception" if exc else "")
    summary = f"{priced} of {lines} lines priced" + (f" · {len(exc)} exception: {exc[0]}" if exc else " · no exceptions")
    return [
        progress("pricing", "t2", start, f"Pricing {lines} lines from the supplier fixture.", b,
                 meter(3500, 0.0, 5000), headline=f"Pricing the BOM, {lines} lines"),
        tool("pricing", "t2", start + 9000, "price_list.lookup", f"{lines} item codes",
             f"{priced} found" + (f", {len(exc)} missing" if exc else ""), 110, b),
        completed(
            "pricing", "t2", start + 18000, headline, summary,
            {"lines_priced": priced, "lines_total": lines, "exceptions": exc},
            [{"tool": "price_list.lookup", "source": "fixtures/supplier-prices.csv", "confidence": 1.0}],
            b, meter(4200, 0.0, 7000),
        ),
    ]


def writer_steps(b: PromptBundle, offset: int, note: str) -> list[Emit]:
    return [draft(offset, 1, 24, "t1", note, b, meter(11000, 0.07, 14000))]


def reviewer_steps(
    b: PromptBundle, offset: int, findings: list[dict[str, Any]], summary: str
) -> list[Emit]:
    return [verdict(offset, True, findings, summary, b, meter(14000, 0.05, 18000))]


ORCH_METERS = {
    "plan": meter(1600, 0.01, 1000),
    "handoff": meter(1500, 0.01, 1000),
}
