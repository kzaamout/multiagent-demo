"""Strands tool functions for the specialist seats, bound per run (research D5).

Each tool is a thin wrapper over a tested function in app/tools or app/live/documents. Every
call records a short argument and result summary keyed by the tool use id, which the seat call
turns into one tool.called event.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from strands import ToolContext, tool

from app.live.documents import parse_pdf, render_page_png
from app.live.materials import CONFIG_DIR, DatasetFiles
from app.live.replies import without_em_dashes
from app.tools.price_list import LookupRequest, PriceList, totals
from app.tools.quantity import QuantityItem, calculate
from app.tools.template import render
from app.tools.unit_hours import table_from_conventions

MAX_PAGE_TEXT = 6000


@dataclass
class ToolLog:
    """Summaries written by tools, read by the seat call's after-tool hook."""

    summaries: dict[str, tuple[str, str]] = field(default_factory=dict)
    results: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    """What each successful call returned, in order, so a reply's figures can be held against it."""

    sink: Callable[[str, dict[str, Any]], None] | None = None

    def keep(self, tool_name: str, data: dict[str, Any]) -> None:
        self.results.append((tool_name, data))
        if self.sink is not None:
            self.sink(tool_name, data)

    def record(self, context: ToolContext, args_summary: str, result_summary: str) -> None:
        self.summaries[str(context.tool_use["toolUseId"])] = (
            without_em_dashes(args_summary)[:200],
            without_em_dashes(result_summary)[:200],
        )


def _dec(value: Any, name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"{name} must be a number, got {value!r}") from error


def _text(data: Any) -> dict[str, Any]:
    return {"status": "success", "content": [{"text": json.dumps(data, ensure_ascii=False, default=str)}]}


def _resolve_in(folder: Path, name: str) -> Path:
    candidate = (folder / name).resolve()
    if not candidate.is_relative_to(folder.resolve()) or not candidate.is_file():
        raise ValueError(f"{name} is not a file in {folder.name}")
    return candidate


def build_tools(
    agent_id: str,
    *,
    files: DatasetFiles,
    log: ToolLog,
    prospect_name: str,
    prepared_dir: Path | None = None,
    project: str,
    supplier_order: list[str],
    long_lead_days: int,
) -> list[Any]:
    """The tools this seat may use, per the roster. Unknown seats get none. `prepared_dir` is where
    prepare_documents put the per-sheet files; a path starting with prepared/ or a sheet name found there
    resolves to the prepared file first, so a multi-sheet binder is read one sheet at a time."""

    # The calculator owns the unit labour hours table, read from the conventions the Estimator also reads.
    conventions = CONFIG_DIR / "estimating-conventions.md"
    unit_hours_table = table_from_conventions(conventions) if conventions.is_file() else []

    def _prepared(name: str) -> Path | None:
        if prepared_dir is None or not prepared_dir.is_dir():
            return None
        candidate = (prepared_dir / name).resolve()
        if candidate.is_relative_to(prepared_dir.resolve()) and candidate.is_file():
            return candidate
        return None

    @tool(context=True)
    def document_parse_pdf(file: str, tool_context: ToolContext) -> dict[str, Any]:
        """Read a request document or drawing sheet: text and a legibility confidence for each page.

        Read every document and every prepared sheet before grading the checklist. A sheet you have not
        opened cannot be graded from its file name, and a document absent from the list is the one fact
        you can state without reading. The confidence is the page's legibility, not your confidence in
        what it says. This returns text only: a drawing's symbols and title block need an eye, so a grade
        that depends on what a drawing shows belongs to the Estimator as a concern, not to you.

        Args:
            file: A prepared sheet or page, for example "prepared/E-001.pdf", or a path in the inputs
                folder, for example "request.pdf" or "drawings/E-001.pdf".
        """
        prepared = _prepared(file[len("prepared/") :]) if file.startswith("prepared/") else None
        path = prepared or _resolve_in(files.inputs, file)
        pages = parse_pdf(path)
        data = [{"page": p.page, "confidence": p.confidence, "text": p.text[:MAX_PAGE_TEXT]} for p in pages]
        low = [p.page for p in pages if p.confidence < 0.7]
        log.record(tool_context, file, f"{len(pages)} pages" + (f", low confidence on {low}" if low else ""))
        return _text({"file": file, "pages": data})

    @tool(context=True)
    def document_extract_attachments(tool_context: ToolContext) -> dict[str, Any]:
        """List the request files and drawing sheets provided with the request, and the prepared sheets.

        Call this first, before reading anything: it is the record of what the request actually came with.
        A document the request names that does not appear here is genuinely missing and is graded so; a
        document that appears here has been provided, whatever the request says about it. Use it to decide
        what to read, not to decide what a document contains."""
        request = [p.name for p in files.request_files()]
        sheets = [p.stem for p in files.drawing_files()]
        prepared = (
            sorted(p.stem for p in prepared_dir.glob("*.pdf"))
            if prepared_dir and prepared_dir.is_dir()
            else []
        )
        log.record(
            tool_context,
            "inputs",
            f"{len(request)} request files, {len(sheets)} drawing files, {len(prepared)} prepared sheets",
        )
        return _text({"request_files": request, "drawing_sheets": sheets, "prepared_sheets": prepared})

    @tool(context=True)
    def vision_read_drawing(sheet: str, tool_context: ToolContext, page: int = 1) -> dict[str, Any]:
        """Look at one drawing sheet as an image, with any text the sheet's PDF carries.

        Use this for any sheet in the drawing set, including one you have not opened yet. A sheet you
        have not read is not a missing sheet: read it here before deciding anything about it, and raise a
        blocker only for a sheet the drawing index lists that the set does not contain. Use it once per
        sheet you need; it returns what the sheet shows with a confidence, not an interpretation.

        Args:
            sheet: Sheet name as listed in the drawing sheets, for example "E-001".
            page: Page within the sheet file, starting at 1.
        """
        path = _prepared(f"{sheet}.pdf") or _resolve_in(files.drawings_dir, f"{sheet}.pdf")
        png = render_page_png(path, page)
        text_layer = next((p.text for p in parse_pdf(path) if p.page == page), "")
        log.record(
            tool_context,
            f"{sheet} page {page}",
            f"page image, {len(text_layer.strip())} characters of text layer",
        )
        return {
            "status": "success",
            "content": [
                {"text": f"Sheet {sheet}, page {page}. Text layer:\n{text_layer[:MAX_PAGE_TEXT]}"},
                {"image": {"format": "png", "source": {"bytes": png}}},
            ],
        }

    @tool(context=True)
    def quantity_calculate(items: list[dict[str, Any]], tool_context: ToolContext) -> dict[str, Any]:
        """Total counts and lengths, apply the waste factors, and roll up labour hours from the unit
        labour hours table in the estimating conventions, which the tool reads itself.

        Required before a completed takeoff: a reply whose quantities or labour hours were not produced
        by this tool is refused. Call it once with every counted and measured line, after reading the
        sheets and before writing your reply, then copy its numbers. Do not add, multiply or apply a waste
        factor yourself, and do not use it to decide what to count.

        Args:
            items: Lines, each with description, unit, category (wire, conduit, device, fixture,
                equipment, other), counts (list of numbers to add), and group. Write the description
                as the materials schedule writes it, because that is how the tool finds the line's unit
                hours in the table. Each returned line says where its hours came from. Pass unit_hours
                only for a line the tool returns with hours_source "none", meaning the table has no
                entry for it, and give that line confidence low in your reply.
        """
        parsed = [
            QuantityItem(
                description=str(i["description"]),
                unit=str(i["unit"]),
                category=i.get("category", "other"),
                counts=tuple(_dec(c, "counts") for c in i.get("counts", [])),
                group=str(i.get("group", "Miscellaneous")),
                unit_hours=_dec(i["unit_hours"], "unit_hours") if i.get("unit_hours") is not None else None,
            )
            for i in items
        ]
        result = calculate(parsed, unit_hours_table)
        data = {
            "lines": [
                {
                    "description": line.description,
                    "unit": line.unit,
                    "group": line.group,
                    "base_quantity": str(line.base_quantity),
                    "waste_rate": str(line.waste_rate),
                    "quantity_with_waste": str(line.quantity_with_waste),
                    "hours": None if line.hours is None else str(line.hours),
                    "unit_hours": None if line.unit_hours is None else str(line.unit_hours),
                    "hours_source": line.hours_source,
                }
                for line in result.lines
            ],
            "hours_by_group": {k: str(v) for k, v in result.hours_by_group.items()},
            "total_hours": str(result.total_hours),
        }
        log.record(tool_context, f"{len(parsed)} items", f"{len(parsed)} lines, {result.total_hours} hours")
        log.keep("quantity_calculate", data)
        return _text(data)

    @tool(context=True)
    def price_list_lookup(
        items: list[dict[str, Any]],
        tool_context: ToolContext,
        markup_rate: float | None = None,
        labour_hours: float | None = None,
        labour_rate: float | None = None,
    ) -> dict[str, Any]:
        """Price bill of materials lines from the supplier fixture and return extended costs and totals.

        Required before a priced reply: a reply whose prices or totals did not come from this tool is
        refused. Call it once with every bill of materials line, plus the markup rate, the labour hours
        and the labour rate, then copy its prices, its extensions and its totals. A price you remember or
        work out yourself is not a price from the fixture, even when it looks right. An item the fixture
        does not carry comes back unpriced, which is an exception to report rather than a price to invent.

        Args:
            items: Lines, each with line_ref, description, quantity, unit, and optional item_code.
            markup_rate: Material markup as a fraction, for example 0.15.
            labour_hours: Total labour hours from the Estimator.
            labour_rate: Blended labour rate per hour.
        """
        prices = PriceList.from_csv(files.price_fixture)
        requests = [
            LookupRequest(
                line_ref=str(i["line_ref"]),
                description=str(i["description"]),
                quantity=_dec(i["quantity"], "quantity"),
                unit=str(i["unit"]),
                item_code=str(i["item_code"]) if i.get("item_code") else None,
            )
            for i in items
        ]
        lines = prices.lookup(requests, supplier_order=supplier_order, long_lead_days=long_lead_days)
        data: dict[str, Any] = {
            "lines": [
                {
                    "line_ref": line.line_ref,
                    "description": line.description,
                    "quantity": str(line.quantity),
                    "unit": line.unit,
                    "status": line.status,
                    "unit_price": None if line.unit_price is None else str(line.unit_price),
                    "extended": None if line.extended is None else str(line.extended),
                    "supplier": line.supplier,
                    "lead_time_days": line.lead_time_days,
                    "long_lead": line.long_lead,
                }
                for line in lines
            ]
        }
        if markup_rate is not None and labour_hours is not None and labour_rate is not None:
            t = totals(
                lines,
                markup_rate=_dec(markup_rate, "markup_rate"),
                labour_hours=_dec(labour_hours, "labour_hours"),
                labour_rate=_dec(labour_rate, "labour_rate"),
            )
            data["totals"] = {k: str(v) for k, v in t.__dict__.items()}
        priced = sum(1 for line in lines if line.status == "priced")
        log.record(tool_context, f"{len(lines)} lines", f"{priced} priced, {len(lines) - priced} exceptions")
        log.keep("price_list_lookup", data)
        return _text(data)

    @tool(context=True)
    def template_render(sections: dict[str, str], tool_context: ToolContext) -> dict[str, Any]:
        """Fill the response template. Sections: executive_summary, scope, pricing_summary,
        schedule_of_values, assumptions, exclusions. Returns the markdown, tags found, and gaps.

        It reports the provenance tags it can see and the sections it found empty, which is what the
        engine checks your draft against, so calling it before you reply shows you what will be refused
        while you can still fix it. It fills the template around your text; it does not write the text,
        and it cannot tag a figure for you.

        Args:
            sections: Section name to markdown text.
        """
        rendered = render(sections, prospect_name=prospect_name, project=project)
        log.record(
            tool_context,
            f"{len(sections)} sections",
            f"{len(rendered.tags)} tags, gaps: {', '.join(rendered.gaps) or 'none'}",
        )
        return _text({"markdown": rendered.markdown, "tags": len(rendered.tags), "gaps": list(rendered.gaps)})

    @tool(context=True)
    def compile_trigger(version: int, tool_context: ToolContext) -> dict[str, Any]:
        """Ask for the draft to be committed and compiled. The draft from your final reply is
        committed as the given version and compiled to pages for the Reviewer.

        Call this once, when the draft is finished. It is not a preview: the version it commits is what
        the Reviewer judges and what the human sees. Use template_render while you are still working.

        Args:
            version: The draft version you are committing, starting at 1.
        """
        log.record(tool_context, f"v{version}", "commit requested; the final reply is compiled")
        return _text({"version": version, "status": "commit requested"})

    by_seat: dict[str, list[Any]] = {
        "intake": [document_parse_pdf, document_extract_attachments],
        "estimator": [vision_read_drawing, quantity_calculate],
        "pricing": [price_list_lookup],
        "writer": [template_render, compile_trigger],
        "single": [
            document_parse_pdf,
            document_extract_attachments,
            vision_read_drawing,
            quantity_calculate,
            price_list_lookup,
            template_render,
        ],
    }
    return by_seat.get(agent_id, [])
