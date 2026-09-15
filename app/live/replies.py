"""Seat reply shapes (from config/electrical-rfp/seats/*.md) and their conversion to event payloads.

Replies are validated before anything reaches the event stream (FR-016). The shapes are lenient
where the seat files are loose (numbers may arrive as strings) and strict where the schema is
strict (verdicts, severities, routing).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.schema.events import (
    BlockerRaisedPayload,
    ClarificationNeededPayload,
    DraftCommittedPayload,
    IntakeBriefPayload,
    IntakeReadinessPayload,
    ReviewVerdictPayload,
    TaskCompletedPayload,
)


class ReplyError(ValueError):
    """A reply that cannot be parsed or does not match its seat's shape."""


class Loose(BaseModel):
    model_config = ConfigDict(extra="allow")


EM_DASH = chr(0x2014)


def without_em_dashes(value: Any) -> Any:
    """Models are told not to use em dashes; small ones still do. Replace them in every reply string."""
    if isinstance(value, str):
        return value.replace(f" {EM_DASH} ", ", ").replace(EM_DASH, ", ")
    if isinstance(value, list):
        return [without_em_dashes(item) for item in value]
    if isinstance(value, dict):
        return {key: without_em_dashes(item) for key, item in value.items()}
    return value


def _balanced_object(text: str, start: int) -> str | None:
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _load_repaired(candidate: str) -> Any:
    """json.loads, repairing a stray closing brace that ends the object before its remaining fields.
    Small models sometimes close a nested object one level too early, so later fields become extra data."""
    text = candidate
    for _ in range(6):
        try:
            return json.loads(text)
        except json.JSONDecodeError as error:
            if error.msg != "Extra data" or not text[error.pos :].lstrip().startswith(","):
                raise
            cut = len(text[: error.pos].rstrip()) - 1
            if cut < 0 or text[cut] != "}":
                raise
            text = text[:cut] + text[cut + 1 :]
    return json.loads(text)


def extract_json(text: str) -> dict[str, Any]:
    """Find the reply object in model text: the whole span from the first to the last brace (repairing
    a stray closing brace), else a fenced block, else the first balanced object."""
    candidates: list[str] = []
    start, last = text.find("{"), text.rfind("}")
    if start != -1 and last > start:
        candidates.append(text[start : last + 1])
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        candidates.append(fenced.group(1))
    if start != -1:
        balanced = _balanced_object(text, start)
        if balanced:
            candidates.append(balanced)
    first_error: json.JSONDecodeError | None = None
    for candidate in candidates:
        try:
            value = _load_repaired(candidate)
        except json.JSONDecodeError as error:
            first_error = first_error or error
            continue
        if isinstance(value, dict):
            return cast(dict[str, Any], without_em_dashes(value))
    if first_error is not None:
        near = first_error.doc[max(0, first_error.pos - 40) : first_error.pos + 40]
        raise ReplyError(f"the reply is not valid JSON ({first_error.msg} near {near!r})")
    raise ReplyError("no JSON object found in the reply")


# Intake Analyst


class ChecklistGrade(BaseModel):
    item: str
    status: Literal["pass", "fail", "assumed"]
    note: str = ""

    @field_validator("note", mode="before")
    @classmethod
    def _empty_note(cls, value: Any) -> Any:
        return "" if value is None else value


class PageLegibility(BaseModel):
    page: str
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("page", mode="before")
    @classmethod
    def _page_as_text(cls, value: Any) -> str:
        return str(value)


class Readiness(BaseModel):
    verdict: Literal["ready", "ready_with_assumptions", "not_ready"]
    checklist: list[ChecklistGrade]
    legibility: list[PageLegibility] = Field(default_factory=list)


class Clarification(BaseModel):
    question_id: str = Field(pattern=r"^q_[a-z0-9_]+$")
    question: str
    why_it_matters: str
    proposed_default: str
    blocking: bool


# Checklist items that are concerns for the Estimator rather than questions for the human
# (config/electrical-rfp/readiness-checklist.md and the intake seat instructions).
ESTIMATOR_CONCERN_WORDS = ("panel schedule", "rating")


def checklist_items(path: Path) -> list[str]:
    """The gradable items: bullets under the request, drawing set, and consistency headings, without their markings."""
    items: list[str] = []
    graded = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            heading = line[3:].strip().lower()
            graded = heading in {"request document", "drawing set", "consistency checks"}
        elif graded and line.startswith("- "):
            items.append(line[2:].split(" (")[0].strip())
    return items


def checklist_item_count(path: Path) -> int:
    return len(checklist_items(path))


BRIEF_FIELDS = (
    "project", "client", "site_address", "scope", "deliverables", "bid_format", "deadline", "drawing_set",
    "drawing_pages", "specification", "alternates", "bonding", "unreliable_pages", "knowledge_used",
)  # fmt: skip


class IntakeReply(BaseModel):
    brief: dict[str, Any]
    readiness: Readiness
    clarifications: list[Clarification] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _fold_brief_fields(cls, data: Any) -> Any:
        """Brief fields a model placed beside the brief instead of inside it belong to the brief."""
        if isinstance(data, dict) and isinstance(data.get("brief"), dict):
            data = dict(data)
            brief = dict(data["brief"])
            for name in BRIEF_FIELDS:
                if name in data and name not in brief:
                    brief[name] = data.pop(name)
            data["brief"] = brief
        return data

    def check(self, expected_items: list[str] | None = None) -> None:
        failing = [c for c in self.readiness.checklist if c.status == "fail"]
        assumed = [c for c in self.readiness.checklist if c.status == "assumed"]
        expected = "not_ready" if failing else "ready_with_assumptions" if assumed else "ready"
        if self.readiness.verdict != expected:
            raise ReplyError(
                f"verdict {self.readiness.verdict} contradicts the checklist grades ({expected})"
            )
        if expected_items is not None and len(self.readiness.checklist) < len(expected_items):
            raise ReplyError(
                f"readiness.checklist grades {len(self.readiness.checklist)} items but the readiness checklist has "
                f"{len(expected_items)}. Grade each of these, in order: " + "; ".join(expected_items)
            )
        gaps = [
            c
            for c in failing + assumed
            if not any(word in c.item.lower() for word in ESTIMATOR_CONCERN_WORDS)
        ]
        if len(self.clarifications) < len(gaps):
            names = "; ".join(c.item for c in gaps)
            raise ReplyError(
                f"{len(gaps)} checklist items are not pass but there are {len(self.clarifications)} clarifications. "
                f"Add one clarification with a proposed default for each of: {names}. Mark it blocking when the "
                "request says the item must be settled before submitting"
            )


# Estimator


class BomLine(Loose):
    group: str
    description: str
    quantity: float | str
    unit: str
    drawing_ref: str
    confidence: Literal["high", "medium", "low"]
    note: str = ""


class Labour(Loose):
    total_hours: float | str
    by_group: dict[str, Any] = Field(default_factory=dict)


class Referenced(BaseModel):
    text: str
    drawing_ref: str = ""


class EstimatorBlocker(BaseModel):
    description: str
    needs_human: bool
    route_back_to: Literal["intake"] | None = None


class EstimatorReply(BaseModel):
    headline: str = ""
    summary: str = ""
    bom: list[BomLine] = Field(default_factory=list)
    labour: Labour | None = None
    assumptions: list[Referenced] = Field(default_factory=list)
    concerns: list[Referenced] = Field(default_factory=list)
    blocker: EstimatorBlocker | None = None

    def check(self) -> None:
        if self.blocker is None and (not self.bom or self.labour is None or not self.headline):
            raise ReplyError("a completed takeoff needs headline, bom, and labour")


# Pricing


class PricedBomLine(Loose):
    line_ref: str
    description: str


class PricingException(BaseModel):
    line_ref: str
    description: str
    kind: Literal["unpriced", "long_lead", "unit_mismatch"]
    detail: str = ""


class PricingReply(BaseModel):
    headline: str
    summary: str
    priced_bom: list[PricedBomLine]
    cost_summary: dict[str, Any]
    exceptions: list[PricingException] = Field(default_factory=list)
    rates_used: list[dict[str, Any]] = Field(default_factory=list)

    def check(self) -> None:
        missing = [k for k in ("material", "markup", "labour", "total") if k not in self.cost_summary]
        if missing:
            raise ReplyError(f"cost_summary lacks {missing}")


# Writer


class WriterReply(BaseModel):
    markdown: str = Field(min_length=1)
    note: str = ""
    tags: list[dict[str, str]] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)

    def check(self) -> None:
        return None


# Reviewer


class ReviewFinding(BaseModel):
    id: str
    severity: Literal["blocker", "major", "minor"]
    text: str
    evidence: str = Field(min_length=1)
    route_to: Literal["work", "assemble"] | None = None
    agent_id: Literal["estimator", "pricing", "writer"] | None = None


class ReviewerReply(BaseModel):
    verdict: Literal["pass", "fail"]
    summary: str = ""
    findings: list[ReviewFinding] = Field(default_factory=list)

    def check(self) -> None:
        serious = [f for f in self.findings if f.severity in ("blocker", "major")]
        if self.verdict == "pass" and serious:
            raise ReplyError("a pass cannot carry blocker or major findings")
        if self.verdict == "fail" and not serious:
            raise ReplyError("a fail needs at least one blocker or major finding")
        for f in serious:
            if f.route_to is None:
                raise ReplyError(f"finding {f.id} needs a route")
        ids = [f.id for f in self.findings]
        if len(ids) != len(set(ids)):
            raise ReplyError("finding ids repeat")


# Orchestrator proposals


class PlanProposal(BaseModel):
    subtasks: list[dict[str, Any]]
    reason: str


class RoutingProposal(BaseModel):
    route_to: Literal["work", "assemble"]
    agent_id: str | None = None
    target_reason: str
    reason: str


class HeadlineProposal(BaseModel):
    headline: str = Field(max_length=120)


REPLY_MODELS: dict[str, type[BaseModel]] = {
    "intake": IntakeReply,
    "estimator": EstimatorReply,
    "pricing": PricingReply,
    "writer": WriterReply,
    "reviewer": ReviewerReply,
}


def _problems(error: ValidationError, limit: int = 8) -> str:
    """One line per distinct problem, with list positions folded together, so a correction names every kind."""
    seen: dict[str, str] = {}
    for item in error.errors():
        path = ".".join("*" if isinstance(p, int) else str(p) for p in item["loc"])
        key = f"{path}: {item['msg']}"
        if key not in seen:
            seen[key] = ".".join(str(p) for p in item["loc"]) + f": {item['msg']}"
    lines = list(seen.values())
    more = f"; and {len(lines) - limit} more" if len(lines) > limit else ""
    return "; ".join(lines[:limit]) + more


def validate_as[M: BaseModel](model: type[M], data: dict[str, Any]) -> M:
    """Validate a reply object. Small models sometimes nest the requested object one level down, for
    example {"plan": {...}}; the first nested object that validates is used. Raises ReplyError."""
    try:
        return model.model_validate(data)
    except ValidationError as error:
        for value in data.values():
            if isinstance(value, dict):
                try:
                    return model.model_validate(value)
                except ValidationError:
                    continue
        raise ReplyError(_problems(error)) from error


def parse_as[M: BaseModel](model: type[M], text: str) -> M:
    return validate_as(model, extract_json(text))


def parse_reply(agent_id: str, text: str, **check_args: Any) -> BaseModel:
    """Parse and validate a seat's reply. Raises ReplyError with a message fit to send back to the seat."""
    reply = parse_as(REPLY_MODELS[agent_id], text)
    check = getattr(reply, "check", None)
    if callable(check):
        check(**check_args)
    return reply


# Conversion to event payloads


def intake_payloads(reply: IntakeReply) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    brief = IntakeBriefPayload(brief=reply.brief).model_dump(mode="json")
    readiness = IntakeReadinessPayload.model_validate(reply.readiness.model_dump()).model_dump(mode="json")
    questions = [
        ClarificationNeededPayload.model_validate(c.model_dump()).model_dump(mode="json")
        for c in reply.clarifications
    ]
    return brief, readiness, questions


def completed_payload(
    task_id: str, agent_id: str, result: dict[str, Any], provenance: list[dict[str, Any]]
) -> dict[str, Any]:
    return TaskCompletedPayload(
        task_id=task_id, agent_id=agent_id, result=result, provenance=provenance
    ).model_dump(mode="json")


def blocker_payload(
    task_id: str, agent_id: str, blocker_id: str, blocker: EstimatorBlocker
) -> dict[str, Any]:
    return BlockerRaisedPayload(
        blocker_id=blocker_id,
        task_id=task_id,
        agent_id=agent_id,
        description=blocker.description,
        needs_human=blocker.needs_human,
        route_back_to=blocker.route_back_to,
    ).model_dump(mode="json")


def draft_payload(version: int, markdown_path: str, tags: list[tuple[str, str]], note: str) -> dict[str, Any]:
    return DraftCommittedPayload(
        version=version,
        markdown_path=markdown_path,
        provenance_tags=[{"tag_id": t, "source_event_id": s} for t, s in tags],
        note=note,
    ).model_dump(mode="json")


def verdict_payload(reply: ReviewerReply) -> dict[str, Any]:
    return ReviewVerdictPayload.model_validate(reply.model_dump()).model_dump(mode="json")
