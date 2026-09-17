"""The stub Single-model source: one actor, one call, fixture copy, for any dataset (S5, spec section 5).

Used when a dataset is not curated or AGENT_MODE is stub. It emits agent message types only; the
Orchestrator owns the four stage changes, the dispatch, and the termination.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.agents.base import Emit, HumanScript, Marks, MeterDelta
from app.agents.source import HeadlineResult, PlanResult, Timing
from app.agents.stubs._common import FIXTURE, bundle, completed, meter, progress, tool
from app.schema.bundles import PromptBundle
from app.schema.events import Event, Subtask

if TYPE_CHECKING:
    from app.orchestrator.orchestrator import Orchestrator

SYSTEM_SINGLE = (
    "You are one model doing the whole electrical bid response alone: read the package, take off the "
    "quantities, price them, and write the proposal in one pass. No review, no provenance tags."
)
OUTPUT_PATH = "drafts/single-v1.md"
FIXTURE_MARKDOWN = (
    "# Proposal [fixture]\n\n"
    "## Executive summary\n\n"
    "One model read the request and the drawing set and priced the work in a single pass. "
    "Lump sum $172,400 including markup, completion in 9 weeks.\n\n"
    "## Scope\n\n"
    "Electrical distribution and lighting as drawn: one new panel, feeders, branch circuits, LED lighting, "
    "and exit and emergency units.\n\n"
    "## Pricing summary\n\n"
    "Material $118,600, labour 380 hours at $95, markup 15 percent. Total $172,400.\n\n"
    "## Assumptions\n\n"
    "Service voltage as shown on the single-line. No bid security. Standard site access.\n\n"
    "## Exclusions\n\n"
    "Fire alarm, low voltage, and demolition of existing services.\n"
)


def m(minutes: int, seconds: int, ms: int = 0) -> int:
    return (minutes * 60 + seconds) * 1000 + ms


class StubSingleSource:
    """Fixture emissions for a Single-model run on any dataset."""

    timing: Timing = "fixture"

    def __init__(self, dataset_id: str, client_id: str) -> None:
        self.dataset_id = dataset_id
        self.client_id = client_id
        self.human_script = HumanScript(decision=None)
        self.marks = Marks(
            {
                "intake_enter": 0,
                "work_enter": m(0, 4),
                "dispatch": m(0, 5),
                "assemble_enter": m(1, 12),
                "handoff_enter": m(1, 13),
                "end": m(1, 14),
            }
        )
        self.reasons: Mapping[str, str] = {}
        self.target_reasons: Mapping[str, str] = {}
        self.dispatch_summaries: Mapping[str, str] = {
            "single": "The whole request: read, take off, price, and write in one call."
        }
        self.orchestrator_meters: Mapping[str, MeterDelta] = {}
        self.dry_intake = False
        self.headline_pass_first = "The Single-model run completed."
        self.headline_pass_rework = "The Single-model run completed."
        self._orchestrator: Orchestrator | None = None
        self.bundle: PromptBundle = bundle(
            dataset_id,
            90,
            "single",
            SYSTEM_SINGLE,
            f"{FIXTURE} request and drawing set for {dataset_id}\nknowledge file\ntemplates/rfp-response.md",
            "Produce the whole bid response in one pass and return headline, summary, markdown, and total.",
            [
                "document_parse_pdf",
                "vision_read_drawing",
                "quantity_calculate",
                "price_list_lookup",
                "template_render",
            ],
        )

    def bind(self, orchestrator: Orchestrator) -> None:
        self._orchestrator = orchestrator

    def swap_seat_model(self, seat: str, seat_model: Any) -> None:
        return None

    def intake(self) -> AsyncIterator[Emit]:
        raise RuntimeError("a Single-model run has no Intake step")

    async def plan(self) -> PlanResult:
        raise RuntimeError("a Single-model run has no Plan stage")

    def work_subtasks(self, plan: list[Subtask]) -> list[Subtask]:
        return list(plan)

    def task(self, subtask: Subtask) -> AsyncIterator[Emit]:
        return self.single(subtask)

    def blocker_continuation(self, subtask: Subtask, answer: str) -> AsyncIterator[Emit]:
        raise RuntimeError("a Single-model run has no blockers")

    def rework(self, agent_id: str, subtask: Subtask, findings: list[dict[str, Any]]) -> AsyncIterator[Emit]:
        raise RuntimeError("a Single-model run has no rework")

    def assemble(self, version: int, findings: list[dict[str, Any]]) -> AsyncIterator[Emit]:
        raise RuntimeError("a Single-model run has no Assemble step")

    def review(self, review_round: int, draft: Event | None) -> AsyncIterator[Emit]:
        raise RuntimeError("a Single-model run has no Review")

    async def headline(self, exit_value: str, default: str) -> HeadlineResult:
        return HeadlineResult(None)

    async def single(self, subtask: Subtask) -> AsyncIterator[Emit]:
        b = self.bundle
        folder = self._orchestrator.run_folder if self._orchestrator else None
        if folder is not None:
            target = Path(folder) / OUTPUT_PATH
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(FIXTURE_MARKDOWN, encoding="utf-8", newline="\n")
        steps = [
            progress(
                "single",
                "single",
                m(0, 8),
                "Reading the request and the drawing index.",
                b,
                meter(6000, 0.03, 4000),
                headline="Reading the package",
            ),
            tool(
                "single",
                "single",
                m(0, 20),
                "vision_read_drawing",
                "E-001, E-002, E-101, E-102",
                "2 panels, 30 circuits",
                5200,
                b,
            ),
            tool(
                "single",
                "single",
                m(0, 38),
                "quantity_calculate",
                "circuits, fixtures, feeders",
                "31 BOM lines",
                240,
                b,
            ),
            tool(
                "single",
                "single",
                m(0, 52),
                "price_list_lookup",
                "31 item codes",
                "31 priced, 0 exceptions",
                120,
                b,
            ),
            tool("single", "single", m(1, 4), "template_render", "6 sections", "0 tags, gaps: none", 60, b),
            completed(
                "single",
                "single",
                m(1, 10),
                "Proposal written in one pass, $172,400",
                "One pass, 31 lines priced, no review and no sources. Lump sum $172,400.",
                {"total": "172400.00", "output_path": OUTPUT_PATH},
                [
                    {"tool": "vision_read_drawing", "source": "drawing set", "confidence": 0.8},
                    {
                        "tool": "price_list_lookup",
                        "source": "fixtures/supplier-prices.csv",
                        "confidence": 1.0,
                    },
                ],
                b,
                meter(38000, 0.19, 60000),
            ),
        ]
        for step in steps:
            yield step
