"""Builds a live-mode Orchestrator on the synthetic S2 inputs with scripted seat models."""

from __future__ import annotations

import datetime as dt
import re
import shutil
from pathlib import Path
from typing import Any

from app.live.materials import CONFIG_DIR, DatasetFiles
from app.live.providers import live_roster
from app.live.seat_call import SeatModel
from app.live.source import LiveAgentSource, LiveContext
from app.orchestrator.clock import Clock
from app.orchestrator.knowledge_store import KnowledgeStore
from app.orchestrator.orchestrator import DatasetRef, Orchestrator
from app.orchestrator.roster import EXPORT_NAMES, build_roster
from app.runs.bus import StreamBus
from app.runs.recorder import Recorder
from app.schema.events import Model
from tests.support.scripted_model import ScriptedModel, Turn, reply

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "s2"
CLIENT = "test-library"


def dataset(tmp: Path) -> Path:
    folder = tmp / "dataset"
    if not folder.exists():
        shutil.copytree(FIXTURES, folder)
    return folder


def checklist_items() -> list[str]:
    """Every gradable item in the readiness checklist, as a real Intake reply must grade them."""
    items: list[str] = []
    graded = False
    for line in (CONFIG_DIR / "readiness-checklist.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            graded = line[3:].strip().lower() in {"request document", "drawing set", "consistency checks"}
        elif graded and line.startswith("- "):
            items.append(line[2:].split(" (")[0])
    return items


def intake_turns(blocking: bool = True) -> list[Turn]:
    return [
        [{"text": "Listing the request files."}, {"tool": "document_extract_attachments", "input": {}}],
        [{"text": "Reading request.pdf."}, {"tool": "document_parse_pdf", "input": {"file": "request.pdf"}}],
        reply(
            {
                "brief": {
                    "project": "Test Library lighting upgrade",
                    "client": "Test Owner Ltd.",
                    "deadline": "3 November 2026",
                    "drawing_set": "E-001",
                    "drawing_pages": 1,
                },
                "readiness": {
                    "verdict": "ready_with_assumptions",
                    "checklist": [
                        *({"item": item, "status": "pass", "note": ""} for item in checklist_items()),
                        {"item": "Service voltage", "status": "assumed", "note": "question raised"},
                    ],
                    "legibility": [{"page": "request.pdf p1", "confidence": 1.0}],
                },
                "clarifications": [
                    {
                        "question_id": "q_service_voltage",
                        "question": "Which service voltage applies?",
                        "why_it_matters": "It sets conductor sizes.",
                        "proposed_default": "120/208 V",
                        "blocking": blocking,
                    }
                ],
            }
        ),
    ]


def plan_turn() -> Turn:
    return reply(
        {
            "subtasks": [
                {
                    "task_id": "t1",
                    "title": "Takeoff from drawings",
                    "agent_id": "estimator",
                    "depends_on": [],
                    "scope": ["brief", "drawings"],
                },
                {
                    "task_id": "t2",
                    "title": "Price the BOM",
                    "agent_id": "pricing",
                    "depends_on": ["t1"],
                    "scope": ["BOM"],
                },
                {
                    "task_id": "t3",
                    "title": "Assemble proposal",
                    "agent_id": "writer",
                    "depends_on": ["t1", "t2"],
                    "scope": ["outputs"],
                },
            ],
            "reason": "Pricing needs the takeoff, and the Writer needs both.",
        }
    )


def estimator_turns() -> list[Turn]:
    return [
        [
            {"text": "Reading single-line E-001."},
            {"tool": "vision_read_drawing", "input": {"sheet": "E-001"}},
        ],
        [
            {"text": "Totalling troffers and receptacles."},
            {
                "tool": "quantity_calculate",
                "input": {
                    "items": [
                        {
                            "description": "2x4 LED troffer",
                            "unit": "each",
                            "category": "fixture",
                            "counts": [24],
                            "group": "Lighting",
                            "unit_hours": 0.75,
                        },
                        {
                            "description": "Duplex receptacle 15A with box and device",
                            "unit": "each",
                            "category": "device",
                            "counts": [8],
                            "group": "Branch circuits and devices",
                            "unit_hours": 0.5,
                        },
                    ]
                },
            },
        ],
        reply(
            {
                "headline": "Takeoff complete, 2 BOM lines",
                "summary": "Two lines from E-001. Labour 22 hours.",
                "bom": [
                    {
                        "group": "Lighting",
                        "description": "2x4 LED troffer",
                        "quantity": 25,
                        "unit": "each",
                        "drawing_ref": "E-001",
                        "confidence": "high",
                    },
                    {
                        "group": "Branch circuits and devices",
                        "description": "Duplex receptacle 15A with box and device",
                        "quantity": 9,
                        "unit": "each",
                        "drawing_ref": "E-001",
                        "confidence": "high",
                    },
                ],
                "labour": {
                    "total_hours": 22.0,
                    "by_group": {"Lighting": 18.0, "Branch circuits and devices": 4.0},
                },
                "assumptions": [],
                "concerns": [],
            }
        ),
    ]


def pricing_turns() -> list[Turn]:
    return [
        [
            {"text": "Pricing 2 lines."},
            {
                "tool": "price_list_lookup",
                "input": {
                    "items": [
                        {"line_ref": "L1", "description": "2x4 LED troffer", "quantity": 25, "unit": "each"},
                        {
                            "line_ref": "L2",
                            "description": "Duplex receptacle 15A with box and device",
                            "quantity": 9,
                            "unit": "each",
                        },
                    ],
                    "markup_rate": 0.15,
                    "labour_hours": 22,
                    "labour_rate": 95,
                },
            },
        ],
        reply(
            {
                "headline": "2 of 2 lines priced",
                "summary": "All lines priced from the fixture.",
                "priced_bom": [
                    {"line_ref": "L1", "description": "2x4 LED troffer", "extended": "3550.00"},
                    {"line_ref": "L2", "description": "Duplex receptacle", "extended": "165.60"},
                ],
                "cost_summary": {
                    "material": "3715.60",
                    "markup_rate": "0.15",
                    "markup": "557.34",
                    "labour": "2090.00",
                    "total": "6362.94",
                    "currency": "CAD",
                },
                "exceptions": [],
                "rates_used": [{"name": "markup", "value": "0.15", "source": "knowledge file"}],
            }
        ),
    ]


def _source_ids(prompt: str) -> dict[str, str]:
    found = dict(re.findall(r"## (Estimator output|Pricing output) \(source id: ([0-9a-f-]+)\)", prompt))
    return found


def writer_turns() -> list[Turn]:
    def final(prompt: str) -> list[dict[str, Any]]:
        ids = _source_ids(prompt)
        est, price = ids["Estimator output"], ids["Pricing output"]
        markdown = (
            "# Proposal\n\nWe will install {{25 troffers|src:"
            + est
            + "}} for {{$6,362.94|src:"
            + price
            + "}}.\n"
        )
        return reply(
            {"markdown": markdown, "note": "1 page of text, 2 provenance tags", "tags": [], "gaps": []}
        )

    return [
        [
            {"text": "Writing the executive summary."},
            {
                "tool": "template_render",
                "input": {
                    "sections": {
                        "executive_summary": "x",
                        "scope": "y",
                        "pricing_summary": "z",
                        "assumptions": "a",
                        "exclusions": "b",
                    }
                },
            },
        ],
        final,
    ]


def reviewer_turns() -> list[Turn]:
    return [reply({"verdict": "pass", "summary": "Pass. Figures are tagged.", "findings": []})]


def headline_turn() -> Turn:
    return reply({"headline": "The Reviewer passed the proposal first time."})


def seat_models(turns: dict[str, list[Turn]]) -> dict[str, SeatModel]:
    return {
        seat: SeatModel(
            strands_model=ScriptedModel(seat_turns),
            model=Model(provider="test", model_id="scripted", label=f"scripted {seat}"),
            price_in=2.0,
            price_out=10.0,
        )
        for seat, seat_turns in turns.items()
    }


def full_turns(blocking: bool = True) -> dict[str, list[Turn]]:
    return {
        "orchestrator": [plan_turn(), headline_turn()],
        "intake": intake_turns(blocking),
        "estimator": estimator_turns(),
        "pricing": pricing_turns(),
        "writer": writer_turns(),
        "reviewer": reviewer_turns(),
    }


def build(tmp: Path, turns: dict[str, list[Turn]], run_id: str) -> Orchestrator:
    folder = dataset(tmp)
    models = seat_models(turns)
    roster, _ = live_roster(build_roster("electrical_rfp", names=EXPORT_NAMES), lambda seat: models[seat])
    store = KnowledgeStore(tmp / "knowledge")
    recorder = Recorder(tmp / "runs", run_id)
    source = LiveAgentSource(
        dataset_id="test-live",
        client_id=CLIENT,
        context=LiveContext(
            files=DatasetFiles(folder),
            knowledge=store,
            prospect_name="Test Owner Ltd.",
            project="Test Library lighting upgrade",
            supplier_order=["Supplier A", "Supplier B", "Supplier C"],
            long_lead_days=28,
            retry_budget=2,
        ),
        seat_models=models,
    )
    return Orchestrator(
        run_id=run_id,
        workflow="electrical_rfp",
        dataset=DatasetRef(dataset_id="test-live", label="Test live", client_id=CLIENT),
        scenario=source,
        roster=roster,
        retry_budget=2,
        cost_ceiling=5.0,
        clock=Clock(dt.datetime.now(dt.UTC), pace=1.0),
        bus=StreamBus(),
        recorder=recorder,
        knowledge_path=recorder.knowledge_path,
        event_log_path=f"runs/{run_id}/events.jsonl",
        knowledge_store=store,
        run_folder=recorder.folder,
    )
