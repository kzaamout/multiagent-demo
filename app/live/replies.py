"""Seat reply shapes (from config/electrical-bid/seats/*.md) and their conversion to event payloads.

Replies are validated before anything reaches the event stream (FR-016). The shapes are lenient
where the seat files are loose (numbers may arrive as strings) and strict where the schema is
strict (verdicts, severities, routing).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
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


def blank_for_none(data: Any) -> Any:
    """A seat that writes null for an optional string means it had nothing to say there."""
    if isinstance(data, dict):
        return {key: "" if value is None else value for key, value in data.items()}
    return data


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


STATUS_SYNONYMS = {
    "present": "pass",
    "ok": "pass",
    "present with concerns": "assumed",
    "present with concern": "assumed",
    "concern": "assumed",
    "assumption": "assumed",
    "missing": "fail",
    "absent": "fail",
}
"""Grades a seat writes when it follows the checklist's prose ("present", "missing") rather than its shape."""


class ChecklistGrade(BaseModel):
    item: str
    status: Literal["pass", "fail", "assumed"]
    note: str = ""

    @field_validator("status", mode="before")
    @classmethod
    def _status_synonyms(cls, value: Any) -> Any:
        if isinstance(value, str):
            key = value.strip().lower()
            return STATUS_SYNONYMS.get(key, key)
        return value

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

    @field_validator("proposed_default", mode="before")
    @classmethod
    def _no_default(cls, value: Any) -> Any:
        return "" if value is None else value


# Checklist items that are concerns for the Estimator rather than questions for the human
# (config/electrical-bid/readiness-checklist.md and the intake seat instructions).
ESTIMATOR_CONCERN_WORDS = ("panel schedule", "rating")


# Datasets name their specification file after it, for example division-26-specification.pdf.
SPECIFICATION_IN_NAME = "spec"
SPECIFICATION_ITEM = "specifications or a specification section list"

GRADED_SECTIONS = ("request document", "drawing set", "consistency checks")
REQUIRED_SECTIONS = ("request document", "drawing set")


def checklist_items(path: Path, sections: tuple[str, ...] = GRADED_SECTIONS) -> list[str]:
    """The gradable items under the given headings, without their markings. Intake must grade the request and
    drawing set items; the consistency checks only feed Estimator concerns and may be omitted."""
    items: list[str] = []
    graded = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            heading = line[3:].strip().lower()
            graded = heading in sections
        elif graded and line.startswith("- "):
            items.append(line[2:].split(" (")[0].strip())
    return items


def checklist_item_count(path: Path) -> int:
    return len(checklist_items(path))


def checklist_markings(path: Path, sections: tuple[str, ...] = GRADED_SECTIONS) -> dict[str, str]:
    """Each gradable item with the marking the checklist writes after it, such as "blocking" or "default: none"."""
    markings: dict[str, str] = {}
    graded = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            graded = line[3:].strip().lower() in sections
        elif graded and line.startswith("- "):
            item, _, marking = line[2:].partition(" (")
            markings[item.strip().lower()] = marking.strip().rstrip(")").lower()
    return markings


def _marking(item: str, markings: Mapping[str, str]) -> str | None:
    """The checklist marking for a graded item, allowing for a seat that shortened or extended its wording."""
    name = item.strip().lower()
    if name in markings:
        return markings[name]
    for known, marking in markings.items():
        if known.startswith(name) or name.startswith(known):
            return marking
    return None


def blocking_at_intake(item: str, markings: Mapping[str, str]) -> bool:
    """Only an item the checklist marks blocking can make a run Not ready. Items carrying a default or a concern
    for the Estimator are graded and carried, never a stop (readiness checklist, verdict rules)."""
    marking = _marking(item, markings)
    if marking is None:
        return not any(word in item.lower() for word in ESTIMATOR_CONCERN_WORDS)
    return "blocking" in marking


# Words that carry no meaning in a checklist item or a question, for matching one to the other.
COMMON_WORDS = frozenset(
    """a an and are as at be been before by confirm confirmed for from has have in is it its list of on or
    present provided required requirement requirements stated the this to was were whether will with""".split()
)


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in COMMON_WORDS and len(w) > 2]


def canonical_question_id(item: str) -> str:
    """The id a gap on this checklist item always carries, so a stored answer is found on the next run."""
    words = _words(item)
    picked: list[str] = []
    for word in words:
        if picked and word.startswith(picked[-1][:6]):
            continue  # specifications after specification adds nothing
        picked.append(word)
        if len(picked) == 2:
            break
    return "q_" + "_".join(picked) if picked else "q_gap"


def pin_question_ids(clarifications: list[Clarification], items: list[str]) -> None:
    """Give each clarification the id of the checklist item it is about. Models invent a new id for the same
    gap on every run, which defeats ask once: the stored answer is never found (roadmap decision 17)."""
    for clarification in clarifications:
        asked = set(_words(f"{clarification.question} {clarification.why_it_matters}"))
        best, score = "", 0
        for item in items:
            shared = len(asked & set(_words(item)))
            if shared > score:
                best, score = item, shared
        if score >= 2:
            clarification.question_id = canonical_question_id(best)


def needs_a_question(item: str, markings: Mapping[str, str]) -> bool:
    """A gap needs a clarification only when the checklist leaves it open. An item the checklist hands to the
    Estimator, or closes with a default of its own, is graded and carried instead."""
    marking = _marking(item, markings)
    if marking is None:
        return not any(word in item.lower() for word in ESTIMATOR_CONCERN_WORDS)
    return "concern" not in marking and "default" not in marking


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

    def check(
        self,
        expected_items: list[str] | None = None,
        markings: Mapping[str, str] | None = None,
        request_files: list[str] | None = None,
    ) -> None:
        # Only the items the checklist marks blocking stop a run. A fail on any other item, such as a missing
        # panel schedule or an index that lists a sheet not provided, counts as assumed and is carried forward
        # (readiness checklist verdict rules, decision 2026-09-14).
        marks = markings or {}
        for grade in self.readiness.checklist:
            if grade.status == "fail" and not blocking_at_intake(grade.item, marks):
                grade.status = "assumed"
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
        if request_files is not None and not any(SPECIFICATION_IN_NAME in f.lower() for f in request_files):
            for grade in self.readiness.checklist:
                if grade.item.lower().startswith(SPECIFICATION_ITEM) and grade.status == "pass":
                    raise ReplyError(
                        "the specification item is graded pass but no specification was provided. The request "
                        f"files are: {', '.join(request_files)}. Grade it fail when the request references a "
                        "specification, and say in the note which file the request names"
                    )
        if expected_items:
            pin_question_ids(self.clarifications, expected_items)
        gaps = [c for c in failing + assumed if needs_a_question(c.item, marks)]
        # A not_ready run ends before any question is asked, so its gaps need grades, not questions.
        if expected != "not_ready" and len(self.clarifications) < len(gaps):
            # The seat's largest failure by a distance (83 refusals): it grades the items correctly and
            # then raises no question for them. The engine cannot write these questions, because a gap
            # needs one only when the checklist leaves it open, so there is no default to propose and the
            # wording has to come from the request. What it can do is hand over the skeleton with the ids
            # already right, which turns composing into filling (spec 010, phase 1.5).
            asked = {c.question_id for c in self.clarifications}
            skeleton = ", ".join(
                f'{{"question_id": "{canonical_question_id(c.item)}", "question": ..., '
                f'"why_it_matters": ..., "proposed_default": ..., "blocking": ...}}'
                for c in gaps
                if canonical_question_id(c.item) not in asked
            )
            names = "; ".join(c.item for c in gaps)
            raise ReplyError(
                f"{len(gaps)} checklist items are not pass but there are {len(self.clarifications)} clarifications. "
                f"Add one clarification for each of: {names}. Use these ids exactly, one object each, and fill "
                f"the rest from the request: {skeleton}. The proposed default is your best reading of what the "
                "client would answer, so the human can accept it in one click. Mark it blocking when the request "
                "says the item must be settled before submitting"
            )


# Estimator


class BomLine(Loose):
    _blank = model_validator(mode="before")(blank_for_none)

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
    _blank = model_validator(mode="before")(blank_for_none)

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
    _blank = model_validator(mode="before")(blank_for_none)

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


class SingleReply(BaseModel):
    """The Single-model actor's one reply (S5): the whole proposal in one pass, no tags, no review."""

    headline: str
    summary: str
    markdown: str
    total: str | None = None

    @field_validator("total", mode="before")
    @classmethod
    def _total_as_text(cls, value: Any) -> Any:
        return None if value is None else str(value)

    def check(self) -> None:
        if not self.markdown.strip():
            raise ReplyError("markdown is empty; return the full proposal in markdown")
        if not self.headline.strip():
            raise ReplyError("headline is empty")


REPLY_MODELS: dict[str, type[BaseModel]] = {
    "intake": IntakeReply,
    "estimator": EstimatorReply,
    "pricing": PricingReply,
    "writer": WriterReply,
    "reviewer": ReviewerReply,
    "single": SingleReply,
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
        # Only look one level down when the reply carries none of the model's own fields, so that a reply that
        # is the right shape but has one bad line reports that line instead of matching an inner object.
        nested = [] if set(data) & set(model.model_fields) else list(data.values())
        for value in nested:
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
