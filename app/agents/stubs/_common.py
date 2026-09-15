"""Helpers shared by the stub scenarios. Everything here is fixture data for S1."""

from __future__ import annotations

from typing import Any

from app.agents.base import Emit, MeterDelta
from app.orchestrator.roster import SEAT_BY_ID
from app.schema.bundles import PromptBundle
from app.schema.events import Subtask

FIXTURE = "[fixture]"


def ref(dataset: str, n: int) -> str:
    return f"pb-{dataset}-{n:02d}"


def bundle(
    dataset: str,
    n: int,
    seat: str,
    system: str,
    context: str,
    task: str,
    tools: list[str],
    temperature: str = "0.2",
) -> PromptBundle:
    model = SEAT_BY_ID[seat].default_model
    return PromptBundle(
        prompt_ref=ref(dataset, n),
        system=system,
        context_slice=context,
        task=task,
        tools=tools,
        model=model,
    )


def meter(tokens: int, cost: float, wall_ms: int, out_share: float = 0.18) -> MeterDelta:
    tokens_out = int(round(tokens * out_share))
    return MeterDelta(tokens_in=tokens - tokens_out, tokens_out=tokens_out, wall_ms=wall_ms, est_cost=cost)


def checklist(*items: tuple[str, str, str]) -> list[dict[str, str]]:
    return [{"item": item, "status": status, "note": note} for item, status, note in items]


def legibility(pages: dict[str, float]) -> list[dict[str, Any]]:
    return [{"page": page, "confidence": conf} for page, conf in pages.items()]


def rfp_plan(
    estimator_scope: list[str], pricing_scope: list[str], writer_scope: list[str]
) -> list[Subtask]:
    return [
        Subtask(task_id="t1", title="Takeoff from drawings", agent_id="estimator", depends_on=[], scope=estimator_scope),
        Subtask(task_id="t2", title="Price the BOM", agent_id="pricing", depends_on=["t1"], scope=pricing_scope),
        Subtask(
            task_id="t3", title="Assemble proposal", agent_id="writer", depends_on=["t1", "t2"], scope=writer_scope
        ),
    ]


def progress(
    seat: str,
    task_id: str,
    offset: int,
    message: str,
    b: PromptBundle,
    m: MeterDelta | None = None,
    headline: str = "",
) -> Emit:
    payload: dict[str, Any] = {"task_id": task_id, "agent_id": seat, "message": message}
    if headline:
        payload["headline"] = headline
    return Emit(seat, "task.progress", offset, payload, b, m)


def tool(
    seat: str,
    task_id: str,
    offset: int,
    name: str,
    args: str,
    result: str,
    duration_ms: int,
    b: PromptBundle,
) -> Emit:
    return Emit(
        seat,
        "tool.called",
        offset,
        {
            "task_id": task_id,
            "agent_id": seat,
            "tool": name,
            "args_summary": args,
            "result_summary": result,
            "duration_ms": duration_ms,
        },
        b,
    )


def completed(
    seat: str,
    task_id: str,
    offset: int,
    headline: str,
    summary: str,
    data: dict[str, Any],
    provenance: list[dict[str, Any]],
    b: PromptBundle,
    m: MeterDelta | None = None,
) -> Emit:
    result = {"headline": headline, "summary": summary, **data}
    return Emit(
        seat,
        "task.completed",
        offset,
        {"task_id": task_id, "agent_id": seat, "result": result, "provenance": provenance},
        b,
        m,
    )


def draft(
    offset: int, version: int, tags: int, source_task: str, note: str, b: PromptBundle, m: MeterDelta
) -> Emit:
    return Emit(
        "writer",
        "draft.committed",
        offset,
        {
            "version": version,
            "markdown_path": f"drafts/draft-v{version}.md",
            "provenance_tags": [{"tag_id": f"e{i:02d}", "source_event_id": f"$event:{source_task}"} for i in range(1, tags + 1)],
            "note": note,
        },
        b,
        m,
    )


def verdict(
    offset: int, passed: bool, findings: list[dict[str, Any]], summary: str, b: PromptBundle, m: MeterDelta
) -> Emit:
    return Emit(
        "reviewer",
        "review.verdict",
        offset,
        {"verdict": "pass" if passed else "fail", "findings": findings, "summary": summary},
        b,
        m,
    )


def finding(
    fid: str, severity: str, text: str, evidence: str, route_to: str | None, agent_id: str | None
) -> dict[str, Any]:
    return {
        "id": fid,
        "severity": severity,
        "text": text,
        "evidence": evidence,
        "route_to": route_to,
        "agent_id": agent_id,
    }


SYSTEM_INTAKE = (
    "You are the Intake Analyst on an electrical RFP team. Read the request exactly as it arrived. "
    "Grade it against the readiness checklist item by item. Produce a structured brief. For every gap, "
    "propose a default and say whether it blocks work. Do not estimate, price, or write proposal text."
)
SYSTEM_ESTIMATOR = (
    "You are the Estimator on an electrical RFP team. Read the drawings and produce a bill of materials "
    "with quantities and a drawing reference on every line, plus a labour estimate with stated assumptions. "
    "Flag any drawing ambiguity. Never price anything."
)
SYSTEM_PRICING = (
    "You are Pricing on an electrical RFP team. Cost every BOM line from the supplier price fixture, apply "
    "the markup rules from the knowledge file, and list every unpriced or long-lead item as an exception. "
    "Never read drawings and never invent a price."
)
SYSTEM_WRITER = (
    "You are the Writer on an electrical RFP team. Assemble the deliverable into the template from the brief "
    "and the specialist outputs. Tag every figure with the output it came from. Invent nothing."
)
SYSTEM_REVIEWER = (
    "You are the Reviewer. Judge the compiled document against the brief and the criteria file. Return pass "
    "or fail with findings, each with severity, evidence and a routing recommendation. You cannot edit, "
    "rerun, or request tools."
)
