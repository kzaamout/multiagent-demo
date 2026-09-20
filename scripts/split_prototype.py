"""Run the split Estimator as a chain and score it against the dataset's reference (spec 011).

    uv run python scripts/split_prototype.py <run id prefix> <dataset> <what> <times>

`what` is one of: schedule (the Schedule Reader alone), count (the Plan Counter alone), chain (all three),
or single (today's Estimator, for comparison on the same measure).

Nothing here is wired into the engine. The seats read their instructions from
specs/011-estimator-split/prototype/, and this script stands in for the Orchestrator so the question
"is the split worth building" can be answered before it is built.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.live.documents import render_page_png  # noqa: E402
from app.live.materials import DatasetFiles  # noqa: E402
from app.live.providers import ModelConfig, strands_model_for  # noqa: E402
from app.live.replies import parse_as, parse_reply  # noqa: E402
from app.live.seat_call import SeatCall  # noqa: E402
from app.live.strands_tools import ToolLog, build_tools  # noqa: E402
from app.runs.reference import reference  # noqa: E402
from app.schema.bundles import PromptBundle  # noqa: E402
from app.tools.prepare import read_manifest  # noqa: E402

PROTOTYPE = Path(__file__).resolve().parents[1] / "specs" / "011-estimator-split" / "prototype"
DATASETS = Path("datasets")

# What the drawings really say, for scoring the two seats that produce facts rather than a takeoff.
TRUTH: dict[str, Any] = {
    "circuits_in_use": 11,
    "spare_breakers": 4,
    "switches_on_plan": 9,
    "troffers_scheduled": 45,
    "receptacles_scheduled": 30,
    "exit_signs_scheduled": 4,
}
# The two ratings agree on the Clean run and disagree only where the scenario plants it, so scoring every
# dataset against 200 marked a correct reading wrong.
RATINGS = {
    "clean-run": ("225", "225"),
    "missing-price": ("225", "225"),
    "missing-sheet": ("225", "225"),
    "planted-inconsistency": ("225", "200"),
}


class ScheduleReply(BaseModel):
    materials: list[dict[str, Any]] = Field(default_factory=list)
    panels: list[dict[str, Any]] = Field(default_factory=list)
    scheduled_counts: list[dict[str, Any]] = Field(default_factory=list)
    feeders: list[dict[str, Any]] = Field(default_factory=list)
    sheets_read: list[str] = Field(default_factory=list)
    concerns: list[dict[str, Any]] = Field(default_factory=list)

    def check(self) -> None:
        if not self.materials:
            raise ValueError("no materials were read from the schedule")


class CountReply(BaseModel):
    counts: list[dict[str, Any]] = Field(default_factory=list)
    sheets_read: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    def check(self) -> None:
        if not self.counts:
            raise ValueError("no counts were reported")


def key(text: Any) -> str:
    return re.sub(
        r"[^a-z0-9]+", " ", re.sub(r"^[A-Za-z]{1,2}-?\d{1,3}[\s:.)-]+", "", str(text)).lower()
    ).strip()


def number(value: Any) -> float | None:
    try:
        return float(re.sub(r"[^0-9.\-]", "", str(value)))
    except ValueError:
        return None


def seat_call(
    agent_id: str,
    instructions: str,
    bundle: PromptBundle,
    tools: list[Any],
    log: ToolLog,
    parse: Any,
    images: list[bytes],
) -> SeatCall:
    return SeatCall(
        agent_id=agent_id,
        role=agent_id,
        instructions=instructions,
        seat_model=strands_model_for(ModelConfig.load().with_seat("estimator", "qwen3-5-9b"), "estimator"),
        tools=tools,
        log=log,
        bundle=bundle,
        parse=parse,
        images=images,
        corrections=2,
    )


def keep(agent_id: str, reply: Any) -> None:
    """Write a seat's raw reply beside the run, so a score that looks odd can be read rather than guessed."""
    dump = Path(os.environ["PROTOTYPE_DUMP"])
    dump.mkdir(parents=True, exist_ok=True)
    (dump / f"{agent_id}.json").write_text(reply.model_dump_json(indent=1), encoding="utf-8")


async def run_seat(
    agent_id: str,
    file: str,
    task: str,
    context: str,
    tool_names: tuple[str, ...],
    folder: Path,
    dataset: str,
    parse: Any,
    images: list[bytes] | None = None,
) -> Any:
    log = ToolLog()
    every = build_tools(
        "single",
        files=DatasetFiles(DATASETS / dataset),
        prepared_dir=folder / "prepared",
        log=log,
        prospect_name="Fictional Prospect Ltd.",
        project="prototype",
        supplier_order=["Supplier A", "Supplier B", "Supplier C"],
        long_lead_days=28,
    )
    tools = [t for t in every if str(getattr(t, "tool_name", "")) in tool_names]
    instructions = (PROTOTYPE / file).read_text(encoding="utf-8").replace("{name}", agent_id)
    bundle = PromptBundle(
        prompt_ref=f"proto-{agent_id}",
        system=instructions,
        context_slice=context,
        task=task,
        tools=list(tool_names),
        model=strands_model_for(ModelConfig.load().with_seat("estimator", "qwen3-5-9b"), "estimator").model,
    )
    call = seat_call(agent_id, instructions, bundle, tools, log, parse, images or [])
    reply = None
    async for item in call.run():
        if item.kind == "reply":
            reply = item.reply
    if os.environ.get("PROTOTYPE_DUMP") and reply is not None:
        keep(agent_id, reply)
    return reply, log.results


def sheet_list(folder: Path) -> str:
    prepared = read_manifest(folder / "prepared")
    rows = []
    for sheet in getattr(prepared, "sheets", []) or []:
        number_ = getattr(sheet, "sheet_number", "")
        if number_ and number_ != "n/a":
            rows.append(
                f"- prepared/{getattr(sheet, 'sheet_id', number_)}.pdf, sheet {number_}, {getattr(sheet, 'title', '')}"
            )
    return "\n".join(rows)


def named(reply: ScheduleReply) -> dict[str, float | None]:
    """The counts the schedule states, keyed by description. The schedule names a material by its mark,
    "M1", and the materials list is what resolves a mark to the words the rest of the team uses."""
    marks = marks_of(reply)
    counts: dict[str, float | None] = {}
    for row in reply.scheduled_counts:
        name = row.get("material")
        counts[marks.get(mark_token(name), marks.get(key(name), key(name)))] = number(row.get("count"))
    return counts


MARK = re.compile(r"\b([A-Z]{1,2}\d{1,2})\b")


def mark_token(text: Any) -> str:
    """The mark a material is named by, from however the reply writes it."""
    found = MARK.findall(str(text).upper())
    return found[0].lower() if found else key(text)


def marks_of(reply: ScheduleReply) -> dict[str, str]:
    """Mark to description, keyed by the mark alone so "M1 (troffers)" still resolves."""
    table: dict[str, str] = {}
    for material in reply.materials:
        description = key(material.get("description"))
        if not description:
            continue
        if material.get("mark"):
            table[mark_token(material.get("mark"))] = description
        table[description] = description
    return table


def score_schedule(reply: ScheduleReply, dataset: str) -> dict[str, Any]:
    panel = next((p for p in reply.panels), {})
    counts = named(reply)
    single_line, schedule = RATINGS.get(dataset, ("225", "225"))

    def has(word: str, want: int) -> bool:
        return any(v == want for k, v in counts.items() if word in k)

    return {
        "circuits_in_use": number(panel.get("circuits_in_use")) == TRUTH["circuits_in_use"],
        "spare_breakers": number(panel.get("spare_breakers")) == TRUTH["spare_breakers"],
        "both_ratings": single_line in str(panel.get("single_line_bus_rating"))
        and schedule in str(panel.get("main_breaker")),
        "troffers": has("troffer", TRUTH["troffers_scheduled"]),
        "receptacles": has("receptacle", TRUTH["receptacles_scheduled"]),
        "exit_signs": has("exit", TRUTH["exit_signs_scheduled"]),
        "materials": len(reply.materials),
    }


def score_counts(reply: CountReply, marks: dict[str, str] | None = None) -> dict[str, Any]:
    totals: dict[str, float] = {}
    for row in reply.counts:
        value = number(row.get("count"))
        if value is not None:
            table = marks or {}
            raw = row.get("material")
            name = table.get(mark_token(raw), table.get(key(raw), key(raw)))
            totals[name] = totals.get(name, 0) + value
    switch = next((v for k, v in totals.items() if "switch" in k), None)
    troffer = next((v for k, v in totals.items() if "troffer" in k), None)
    return {
        "switches": switch,
        "switches_right": switch == TRUTH["switches_on_plan"],
        "troffers": troffer,
        "troffers_right": troffer == TRUTH["troffers_scheduled"],
        "materials_counted": len(totals),
    }


def score_takeoff(reply: Any, dataset: str) -> dict[str, Any]:
    truth = reference(dataset, DATASETS)
    if truth is None:
        return {}
    got: dict[str, float] = {}
    for line in reply.bom:
        value = number(line.quantity)
        if value is not None:
            got[key(line.description)] = got.get(key(line.description), 0) + value
    right = [
        name
        for name, want in truth["quantities"].items()
        if key(name) in got and abs(got[key(name)] - float(want)) <= max(0.011 * float(want), 0.11)
    ]
    hours = number(reply.labour.total_hours if reply.labour else None)
    return {
        "lines_right": len(right),
        "lines": len(truth["quantities"]),
        "missed": [key(n) for n in truth["quantities"] if key(n) not in [key(r) for r in right]],
        "hours": hours,
        "hours_error_pct": None
        if hours is None
        else round(100 * (hours - float(truth["labour_hours"])) / float(truth["labour_hours"]), 1),
    }


async def estimator(bundle: PromptBundle, folder: Path, dataset: str) -> Any:
    """Today's Estimator seat, on its own instructions and its own tools."""
    from app.seats.definitions import load_instructions

    log = ToolLog()
    tools = build_tools(
        "estimator",
        files=DatasetFiles(DATASETS / dataset),
        prepared_dir=folder / "prepared",
        log=log,
        prospect_name="Fictional Prospect Ltd.",
        project="prototype",
        supplier_order=["Supplier A", "Supplier B", "Supplier C"],
        long_lead_days=28,
    )
    call = seat_call(
        "estimator",
        load_instructions("estimator", name="Elias", review_max_cycles=4, long_lead_days=28),
        bundle,
        tools,
        log,
        lambda t: parse_reply("estimator", t),
        [],
    )
    reply = None
    async for item in call.run():
        if item.kind == "reply":
            reply = item.reply
    return reply


def run_folder(prefix: str) -> Path:
    return next(Path("runs").glob(prefix + "*"))


async def once(prefix: str, dataset: str, what: str, index: int) -> str:
    folder = run_folder(prefix)
    started = time.monotonic()
    sheets = sheet_list(folder)
    brief_prompt = next(
        (
            p
            for p in sorted((folder / "prompts").glob("*.json"))
            if "the Estimator" in json.loads(p.read_text(encoding="utf-8"))["system"][:80]
        ),
        None,
    )
    if brief_prompt is None:
        return f"  {index}: that run has no recorded Estimator prompt to replay"
    brief = json.loads(brief_prompt.read_text(encoding="utf-8"))["context_slice"]
    conventions = re.search(r"## Estimating conventions.*", brief, re.S)
    conventions_text = conventions.group(0) if conventions else ""
    brief_only = brief.split("## Drawing sheets")[0]

    if what == "assisted":
        schedule, _ = await run_seat(
            "ScheduleReader",
            "schedule-reader.md",
            "Read every prepared sheet and record what the schedules state.",
            f"{brief_only}\n## Drawing sheets, prepared\n{sheets}\n",
            ("document_parse_pdf",),
            folder,
            dataset,
            lambda t: parse_as(ScheduleReply, t),
        )
        if schedule is None:
            return f"  {index}: assisted, the schedule reader gave no reply"
        quantities, concerns = resolved(schedule, CountReply())
        first_panel: dict[str, Any] = next((p for p in schedule.panels), {})
        facts = (
            "\n\n## What the schedules state, read for you\n"
            "These figures were read from the sheets' text by another seat. Where a material has a figure "
            "here, use it: it is what the schedule says, and you do not need to count it again. Where it "
            "reads not stated, count it or derive it as the conventions say.\n"
            f"{quantities}\n\n### The panel\n{json.dumps(first_panel)}\n"
        )
        bundle = PromptBundle.model_validate(json.loads(brief_prompt.read_text(encoding="utf-8")))
        bundle = bundle.model_copy(update={"context_slice": bundle.context_slice + facts})
        reply = await estimator(bundle, folder, dataset)
        took = round(time.monotonic() - started)
        if reply is None:
            return f"  {index}: assisted, no takeoff ({took}s)"
        return (
            f"  {index}: assisted {json.dumps(score_takeoff(reply, dataset))} ({took}s) "
            f"| schedule {json.dumps(score_schedule(schedule, dataset))}"
        )

    if what == "single":
        bundle = PromptBundle.model_validate(json.loads(brief_prompt.read_text(encoding="utf-8")))
        reply = await estimator(bundle, folder, dataset)
        took = round(time.monotonic() - started)
        return (
            f"  {index}: single {json.dumps(score_takeoff(reply, dataset))} ({took}s)"
            if reply
            else f"  {index}: single no reply"
        )

    schedule_context = f"{brief_only}\n## Drawing sheets, prepared\n{sheets}\n"
    schedule, _ = await run_seat(
        "ScheduleReader",
        "schedule-reader.md",
        "Read every prepared sheet and record what the schedules state.",
        schedule_context,
        ("document_parse_pdf",),
        folder,
        dataset,
        lambda t: parse_as(ScheduleReply, t),
    )
    if schedule is None:
        return f"  {index}: schedule reader gave no reply"
    if what == "schedule":
        took = round(time.monotonic() - started)
        return f"  {index}: schedule {json.dumps(score_schedule(schedule, dataset))} ({took}s)"

    materials = (
        "\n".join(
            f"- {m.get('mark')}: {m.get('description')} ({m.get('unit')})"
            if m.get("mark")
            else f"- {m.get('description')} ({m.get('unit')})"
            for m in schedule.materials
        )
        or "none"
    )
    legend = [render_page_png(folder / "prepared" / "E-000.pdf", 1)]
    count_context = f"## Materials to count\n{materials}\n\n## Plan sheets\n{sheets}\n"
    counted, _ = await run_seat(
        "PlanCounter",
        "plan-counter.md",
        "Count the marks of each material on each plan sheet. The legend is attached as an image.",
        count_context,
        ("vision_read_drawing",),
        folder,
        dataset,
        lambda t: parse_as(CountReply, t),
        legend,
    )
    if counted is None:
        return f"  {index}: plan counter gave no reply"
    if what == "count":
        took = round(time.monotonic() - started)
        return f"  {index}: count {json.dumps(score_counts(counted, marks_of(schedule)))} ({took}s)"

    quantities, concerns = resolved(schedule, counted)
    panel: dict[str, Any] = next((p for p in schedule.panels), {})
    assemble_context = (
        f"{brief_only}\n"
        "## The materials and their quantities, settled\n"
        "One line per material: description, quantity, unit, and where the figure came from. These are the "
        "quantities. Do not change them, do not add a line, and do not split one material into two.\n"
        f"{quantities}\n\n"
        "## The panel\n"
        f"{json.dumps(panel)}\n\n"
        "## Concerns to carry, already written\n"
        f"{concerns}\n\n"
        f"{conventions_text}"
    )
    takeoff, _ = await run_seat(
        "TakeoffAssembler",
        "takeoff-assembler.md",
        "Build the bill of materials and the labour from the two outputs you were given.",
        assemble_context,
        ("quantity_calculate",),
        folder,
        dataset,
        lambda t: parse_reply("estimator", t),
    )
    took = round(time.monotonic() - started)
    if takeoff is None:
        return f"  {index}: assembler gave no reply ({took}s)"
    scored = score_takeoff(takeoff, dataset)
    return f"  {index}: chain {json.dumps(scored)} ({took}s) | schedule {json.dumps(score_schedule(schedule, dataset))} | count {json.dumps(score_counts(counted, marks_of(schedule)))}"


def resolved(schedule: ScheduleReply, counted: CountReply) -> tuple[str, str]:
    """One quantity per material, and the concerns that follow, decided in code.

    The first prototype handed the Assembler both figures and asked it to choose. It emitted a bill of
    materials line for each instead, and once a quantity of minus one: two numbers for one material is a
    harder job than one, not an easier one. So the engine chooses, by the conventions' own rule that a
    schedule governs where it states a figure, and writes the concern itself. The seat receives a settled
    list and sentences to carry.
    """
    marks = marks_of(schedule)
    stated = named(schedule)
    seen: dict[str, float] = {}
    for row in counted.counts:
        value = number(row.get("count"))
        if value is not None:
            raw = row.get("material")
            name = marks.get(mark_token(raw), marks.get(key(raw), key(raw)))
            seen[name] = seen.get(name, 0) + value

    descriptions = {key(m.get("description")): str(m.get("description")) for m in schedule.materials}
    units = {key(m.get("description")): str(m.get("unit")) for m in schedule.materials}
    lines: list[str] = []
    concerns: list[str] = []
    for name, description in descriptions.items():
        said, saw = stated.get(name), seen.get(name)
        quantity = said if said is not None else saw
        if quantity is None:
            lines.append(
                f"- {description} | not stated | {units.get(name, '')} | neither source gives a figure"
            )
            continue
        source = "the schedule states it" if said is not None else "counted on the plans"
        lines.append(f"- {description} | {quantity:g} | {units.get(name, '')} | {source}")
        if said is not None and saw is not None and abs(said - saw) > 1:
            concerns.append(
                f"- The schedule states {said:g} {description} and the plans show {saw:g}. Priced to the "
                f"schedule's {said:g}; the difference is disclosed for the prospect to confirm."
            )
    for panel in schedule.panels:
        one, two = str(panel.get("single_line_bus_rating")), str(panel.get("main_breaker"))
        first, second = re.sub(r"[^0-9.]", "", one), re.sub(r"[^0-9.]", "", two)
        if first and second and Decimal(first) != Decimal(second):
            concerns.append(
                f"- {panel.get('panel')} is rated {one} on the single-line ({panel.get('single_line_sheet')}) "
                f"and {two} on its schedule ({panel.get('schedule_sheet')}). Proceeding on the single-line "
                "value; both are disclosed for the prospect to confirm before award."
            )
    return "\n".join(lines) or "none", "\n".join(concerns) or "Nothing disagreed."


async def main() -> None:
    prefix, dataset, what, times = sys.argv[1:5]
    print(f"prototype: run {prefix}, dataset {dataset}, {what}, {times} times", flush=True)
    for i in range(int(times)):
        try:
            print(await once(prefix, dataset, what, i + 1), flush=True)
        except Exception as error:  # noqa: BLE001
            print(f"  {i + 1}: failed, {type(error).__name__}: {str(error)[:200]}", flush=True)
    print("PROTOTYPE DONE", flush=True)


asyncio.run(main())
