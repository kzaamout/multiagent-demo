"""Run materials for live seat calls: dataset inputs, config files, and outputs from run events.

Dataset input convention for live runs: drawing sheets live in `inputs/drawings/` (one PDF per
sheet or a multi-page set, named by sheet number); every other file directly in `inputs/` is the
request or an attachment. The Orchestrator assembles every material here; the context builder
then keeps only what the seat may see.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import ROOT
from app.live.context import Material
from app.live.documents import page_count
from app.schema.events import Event
from app.seats import definitions as d

CONFIG_DIR = ROOT / "config" / "electrical-rfp"
TEMPLATE_PATH = ROOT / "templates" / "rfp-response.md"
ROLE_LABEL = {"estimator": "Estimator", "pricing": "Pricing", "writer": "Writer", "intake": "Intake Analyst"}


@dataclass(frozen=True)
class DatasetFiles:
    folder: Path

    @property
    def inputs(self) -> Path:
        return self.folder / "inputs"

    @property
    def drawings_dir(self) -> Path:
        return self.inputs / "drawings"

    @property
    def price_fixture(self) -> Path:
        return self.folder / "fixtures" / "supplier-prices.csv"

    def request_files(self) -> list[Path]:
        if not self.inputs.is_dir():
            return []
        return sorted(p for p in self.inputs.iterdir() if p.is_file())

    def drawing_files(self) -> list[Path]:
        if not self.drawings_dir.is_dir():
            return []
        return sorted(p for p in self.drawings_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")

    def is_curated(self) -> bool:
        return bool(self.request_files()) and bool(self.drawing_files()) and self.price_fixture.exists()


def supplier_order_from(knowledge_text: str) -> list[str]:
    """Preferred suppliers from the knowledge file's standing facts, in order."""
    for line in knowledge_text.splitlines():
        if "preferred suppliers" in line.lower() and ":" in line:
            names = line.split(":", 1)[1]
            return [part.split("(")[0].strip().rstrip(".") for part in names.split(",") if part.strip()]
    return []


def _pages(path: Path) -> str:
    if path.suffix.lower() != ".pdf":
        return "not a PDF"
    try:
        count = page_count(path)
    except Exception:  # noqa: BLE001
        return "unreadable PDF"
    return f"{count} page{'s' if count != 1 else ''}"


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def latest(events: list[Event], type_: str, **payload_match: Any) -> Event | None:
    for event in reversed(events):
        if event.type == type_ and all(event.payload.get(k) == v for k, v in payload_match.items()):
            return event
    return None


def completed_by(events: list[Event], agent_id: str) -> Event | None:
    return latest(events, "task.completed", agent_id=agent_id)


def build_materials(
    *,
    files: DatasetFiles,
    events: list[Event],
    knowledge_text: str,
    run_folder: Path,
    findings: list[dict[str, Any]] | None = None,
) -> list[Material]:
    """Every material the run has so far. Seats get a filtered subset via build_context."""
    materials: list[Material] = []

    request_lines = [f"- {p.name} ({_pages(p)})" for p in files.request_files()]
    if request_lines:
        materials.append(
            Material(
                d.REQUEST_DOCUMENTS,
                "Request documents in the inputs folder",
                "\n".join(request_lines) + "\nUse document_parse_pdf with a file name to read each one.",
            )
        )
    materials.append(Material(d.KNOWLEDGE_FILE, "Client knowledge file", knowledge_text))
    materials.append(
        Material(
            d.READINESS_CHECKLIST,
            "Readiness checklist",
            (CONFIG_DIR / "readiness-checklist.md").read_text(encoding="utf-8"),
        )
    )

    brief = latest(events, "intake.brief")
    readiness = latest(events, "intake.readiness")
    if brief is not None:
        answers = [
            e.payload
            for e in events
            if e.type == "clarification.answered" and e.payload["action"] == "answer"
        ]
        assumptions = [e.payload for e in events if e.type == "assumption.accepted"]
        body = {
            "brief": brief.payload["brief"],
            "readiness_verdict": readiness.payload["verdict"] if readiness else None,
            "answers": answers,
            "assumptions": assumptions,
        }
        materials.append(Material(d.BRIEF, "Brief", _json(body), brief.event_id))

    sheet_lines = [f"- {p.stem} ({_pages(p)})" for p in files.drawing_files()]
    if sheet_lines:
        materials.append(
            Material(
                d.DRAWING_PAGES,
                "Drawing sheets",
                "\n".join(sheet_lines) + "\nUse vision_read_drawing with a sheet name to see a sheet.",
            )
        )
    materials.append(
        Material(
            d.ESTIMATING_CONVENTIONS,
            "Estimating conventions",
            (CONFIG_DIR / "estimating-conventions.md").read_text(encoding="utf-8"),
        )
    )

    estimator = completed_by(events, "estimator")
    if estimator is not None:
        materials.append(
            Material(
                d.ESTIMATOR_OUTPUT, "Estimator output", _json(estimator.payload["result"]), estimator.event_id
            )
        )

    for agent_id in ("estimator", "pricing"):
        output = completed_by(events, agent_id)
        if output is not None:
            materials.append(
                Material(
                    d.SPECIALIST_OUTPUTS,
                    f"{ROLE_LABEL[agent_id]} output",
                    _json(output.payload["result"]),
                    output.event_id,
                )
            )

    materials.append(Material(d.TEMPLATE, "Response template", TEMPLATE_PATH.read_text(encoding="utf-8")))

    draft = latest(events, "draft.committed")
    if draft is not None:
        path = run_folder / draft.payload["markdown_path"]
        if path.exists():
            materials.append(
                Material(
                    d.DRAFT,
                    f"Draft v{draft.payload['version']}",
                    path.read_text(encoding="utf-8"),
                    draft.event_id,
                )
            )

    materials.append(
        Material(
            d.REVIEWER_CRITERIA,
            "Reviewer criteria",
            (CONFIG_DIR / "reviewer-criteria.md").read_text(encoding="utf-8"),
        )
    )
    if findings:
        materials.append(Material(d.FINDINGS, "Reviewer findings routed to you", _json(findings)))
    return materials
