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

from app.compile.pipeline import ARTIFACTS
from app.config import ROOT
from app.live.context import Material
from app.live.documents import page_count
from app.schema.events import Event
from app.seats import definitions as d
from app.tools.prepare import Prepared

CONFIG_DIR = ROOT / "config" / "electrical-bid"
TEMPLATE_PATH = ROOT / "templates" / "rfp-response.md"
ROLE_LABEL = {"estimator": "Estimator", "pricing": "Pricing", "writer": "Writer", "intake": "Intake Analyst"}

SHORT_SOURCE = {"estimator": "takeoff", "pricing": "pricing"}
"""The short name a seat writes in a provenance tag for each specialist's output (roadmap decision 17)."""


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
    prepared: Prepared | None = None,
) -> list[Material]:
    """Every material the run has so far. Seats get a filtered subset via build_context."""
    materials: list[Material] = []

    request_lines = [f"- {p.name} ({_pages(p)})" for p in files.request_files()]
    drawing_lines = [f"- drawings/{p.name} ({_pages(p)})" for p in files.drawing_files()]
    if prepared is not None:
        manifest = prepared.folder / "manifest.md"
        materials.append(
            Material(
                d.REQUEST_DOCUMENTS,
                "Request documents and drawing sheets, prepared by prepare_documents",
                (manifest.read_text(encoding="utf-8") if manifest.exists() else "no manifest")
                + "\nRead the manifest first. Use document_parse_pdf with prepared/<sheet>.pdf to read any sheet or "
                "request page listed above; do not read the raw binders. A field that reads unknown could not be "
                "read: grade it as an assumption, never guess it.",
            )
        )
    elif request_lines or drawing_lines:
        materials.append(
            Material(
                d.REQUEST_DOCUMENTS,
                "Request documents and drawing sheets in the inputs folder",
                "\n".join(request_lines + drawing_lines)
                + "\nUse document_parse_pdf with each path above to read every document and every drawing sheet, "
                "so the drawing set, consistency, and legibility items are graded from what the sheets show.",
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
        materials.append(Material(d.BRIEF, "Brief", _json(body), "brief", brief.event_id))

    if prepared is not None:
        sheet_lines = [
            f"- {s.sheet_id}: {s.title} (discipline {s.discipline}, issued for {s.issued_for}, legibility {s.confidence:.2f})"
            for s in prepared.drawing_sheets()
        ]
    else:
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
                d.ESTIMATOR_OUTPUT,
                "Estimator output",
                _json(estimator.payload["result"]),
                "takeoff",
                estimator.event_id,
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
                    SHORT_SOURCE[agent_id],
                    output.event_id,
                )
            )

    materials.append(Material(d.TEMPLATE, "Response template", TEMPLATE_PATH.read_text(encoding="utf-8")))

    # The Reviewer judges the compiled pages (spec stage 5, S4 decision 3b): the text of each page rides
    # along as material, and the page images go on the bundle. The markdown is never shown to it.
    compiled = latest(events, "artifact.compiled")
    if compiled is not None:
        pages_path = run_folder / ARTIFACTS / f"v{compiled.payload['version']}" / "pages.json"
        if pages_path.exists():
            texts = json.loads(pages_path.read_text(encoding="utf-8"))
            for number, text in enumerate(texts, start=1):
                materials.append(
                    Material(
                        d.DRAFT, f"Page {number} text", text or "(no text on this page)", f"page-{number}"
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
