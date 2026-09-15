"""Event schema, version 1.0.0. Frozen (constitution II and XII).

Normative text: docs/schema/events-v1.0.0.md. This module is the typed form of that
document. Any change is an amendment and a new version.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "1.0.0"

Stage = Literal["intake", "plan", "work", "assemble", "review", "handoff"]
STAGE_ORDER: tuple[Stage, ...] = ("intake", "plan", "work", "assemble", "review", "handoff")

Exit = Literal[
    "reviewer_pass",
    "retry_exhausted",
    "blocker_escalated",
    "not_ready",
    "cost_ceiling",
    "stopped",
    "single_complete",
    "dry_intake",
]
NARRATIVE_EXITS: tuple[Exit, ...] = ("reviewer_pass", "retry_exhausted", "blocker_escalated", "not_ready")
CONTROL_EXITS: tuple[Exit, ...] = ("cost_ceiling", "stopped", "single_complete", "dry_intake")
HANDOFF_EXITS: tuple[Exit, ...] = ("reviewer_pass", "retry_exhausted")

Direction = Literal["forward", "backward"]
ReadinessVerdict = Literal["ready", "ready_with_assumptions", "not_ready"]
Verdict = Literal["pass", "fail"]
Severity = Literal["blocker", "major", "minor"]
Decision = Literal["approve", "edit", "reject"]
RunMode = Literal["team", "single"]
AnswerAction = Literal["answer", "escalate"]
RouteTo = Literal["work", "assemble"]

EventType = Literal[
    "run.started",
    "stage.changed",
    "intake.brief",
    "intake.readiness",
    "clarification.needed",
    "clarification.asked",
    "clarification.answered",
    "assumption.accepted",
    "plan.created",
    "task.dispatched",
    "task.progress",
    "tool.called",
    "task.completed",
    "blocker.raised",
    "draft.committed",
    "artifact.compiled",
    "review.verdict",
    "retry.incremented",
    "handoff.ready",
    "human.approved",
    "knowledge.appended",
    "run.paused",
    "run.resumed",
    "model.changed",
    "meter.update",
    "run.terminated",
]

ORCHESTRATOR_TYPES: frozenset[str] = frozenset(
    {
        "run.started",
        "stage.changed",
        "clarification.asked",
        "assumption.accepted",
        "plan.created",
        "task.dispatched",
        "retry.incremented",
        "handoff.ready",
        "knowledge.appended",
        "run.paused",
        "run.resumed",
        "run.terminated",
    }
)
AGENT_MESSAGE_TYPES: frozenset[str] = frozenset(
    {
        "intake.brief",
        "intake.readiness",
        "clarification.needed",
        "task.progress",
        "tool.called",
        "task.completed",
        "blocker.raised",
        "draft.committed",
        "review.verdict",
    }
)
HUMAN_TYPES: frozenset[str] = frozenset({"clarification.answered", "human.approved"})
STAGELESS_TYPES: frozenset[str] = frozenset({"run.started", "run.terminated"})


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Model(Strict):
    provider: str
    model_id: str
    label: str


class Agent(Strict):
    agent_id: str
    name: str
    role: str
    model: Model


Actor = Agent | Literal["human", "system"]


# Payloads


class RunStartedPayload(Strict):
    workflow: str
    dataset_id: str
    mode: RunMode
    roster: list[Agent]


class StageChangedPayload(Strict):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    from_stage: Stage | None = Field(alias="from")
    to: Stage
    direction: Direction
    target_reason: str


class IntakeBriefPayload(Strict):
    brief: dict[str, Any]


class ChecklistItem(Strict):
    item: str
    status: Literal["pass", "fail", "assumed"]
    note: str = ""


class LegibilityScore(Strict):
    page: str
    confidence: float = Field(ge=0.0, le=1.0)


class IntakeReadinessPayload(Strict):
    verdict: ReadinessVerdict
    checklist: list[ChecklistItem]
    legibility: list[LegibilityScore]


class ClarificationNeededPayload(Strict):
    question_id: str
    question: str
    why_it_matters: str
    proposed_default: str
    blocking: bool


class Blocker(Strict):
    blocker_id: str
    task_id: str
    agent_id: str
    description: str


class ClarificationAskedPayload(Strict):
    question_ids: list[str]
    blocker: Blocker | None = None


class ClarificationAnsweredPayload(Strict):
    question_id: str
    answer: str
    action: AnswerAction


class AssumptionAcceptedPayload(Strict):
    question_id: str
    default_used: str


class Subtask(Strict):
    task_id: str
    title: str
    agent_id: str
    depends_on: list[str]
    scope: list[str]


class PlanCreatedPayload(Strict):
    subtasks: list[Subtask]


class TaskDispatchedPayload(Strict):
    task_id: str
    agent_id: str
    inputs_summary: str


class TaskProgressPayload(Strict):
    task_id: str
    agent_id: str
    message: str
    headline: str = ""


class ToolCalledPayload(Strict):
    task_id: str
    agent_id: str
    tool: str
    args_summary: str
    result_summary: str
    duration_ms: int = Field(ge=0)


class Provenance(Strict):
    tool: str
    source: str
    confidence: float = Field(ge=0.0, le=1.0)


class TaskCompletedPayload(Strict):
    task_id: str
    agent_id: str
    result: dict[str, Any]
    provenance: list[Provenance]


class BlockerRaisedPayload(Strict):
    blocker_id: str
    task_id: str
    agent_id: str
    description: str
    needs_human: bool
    route_back_to: Literal["intake"] | None = None


class ProvenanceTag(Strict):
    tag_id: str
    source_event_id: str


class DraftCommittedPayload(Strict):
    version: int = Field(ge=1)
    markdown_path: str
    provenance_tags: list[ProvenanceTag]
    note: str = ""


class ArtifactCompiledPayload(Strict):
    version: int = Field(ge=1)
    pdf_path: str | None = None
    page_images: list[str]


class Finding(Strict):
    id: str
    severity: Severity
    text: str
    evidence: str
    route_to: RouteTo | None = None
    agent_id: str | None = None


class ReviewVerdictPayload(Strict):
    verdict: Verdict
    findings: list[Finding]
    summary: str = ""


class RetryIncrementedPayload(Strict):
    count: int = Field(ge=0)
    budget: int = Field(ge=0)


class ClarificationRecord(Strict):
    question_id: str
    answer: str


class HandoffPackage(Strict):
    pdf_path: str | None = None
    page_images: list[str]
    verdict_event_id: str
    unresolved_findings: list[str]
    assumptions: list[str]
    clarifications: list[ClarificationRecord]
    event_log_path: str


class HandoffReadyPayload(Strict):
    exit_determination: Literal["reviewer_pass", "retry_exhausted"]
    package: HandoffPackage


class HumanApprovedPayload(Strict):
    decision: Decision
    notes: str = ""


class KnowledgeEntry(Strict):
    question_id: str
    answer: str
    source_event_id: str


class KnowledgeAppendedPayload(Strict):
    client_id: str
    entries: list[KnowledgeEntry]


class RunPausedPayload(Strict):
    by: Literal["human"]


class RunResumedPayload(Strict):
    by: Literal["human"]


class ModelChangedPayload(Strict):
    agent_id: str
    from_model: Model
    to_model: Model


class MeterUpdatePayload(Strict):
    agent_id: str
    call_id: str
    tokens_in: int = Field(ge=0)
    tokens_out: int = Field(ge=0)
    wall_ms: int = Field(ge=0)
    est_cost: float = Field(ge=0.0)


class MissingItem(Strict):
    item: str
    note: str = ""
    source_event_id: str | None = None


class Retries(Strict):
    count: int = Field(ge=0)
    budget: int = Field(ge=0)


class Summary(Strict):
    headline: str
    missing: list[MissingItem]
    unresolved_findings: list[str]
    retries: Retries
    readiness_verdict: ReadinessVerdict | None = None
    event_count: int = Field(ge=1)
    elapsed_ms: int = Field(ge=0)
    est_cost: float = Field(ge=0.0)
    human_decision: Decision | None = None


class RunTerminatedPayload(Strict):
    exit: Exit
    summary: Summary


PAYLOAD_MODELS: dict[str, type[BaseModel]] = {
    "run.started": RunStartedPayload,
    "stage.changed": StageChangedPayload,
    "intake.brief": IntakeBriefPayload,
    "intake.readiness": IntakeReadinessPayload,
    "clarification.needed": ClarificationNeededPayload,
    "clarification.asked": ClarificationAskedPayload,
    "clarification.answered": ClarificationAnsweredPayload,
    "assumption.accepted": AssumptionAcceptedPayload,
    "plan.created": PlanCreatedPayload,
    "task.dispatched": TaskDispatchedPayload,
    "task.progress": TaskProgressPayload,
    "tool.called": ToolCalledPayload,
    "task.completed": TaskCompletedPayload,
    "blocker.raised": BlockerRaisedPayload,
    "draft.committed": DraftCommittedPayload,
    "artifact.compiled": ArtifactCompiledPayload,
    "review.verdict": ReviewVerdictPayload,
    "retry.incremented": RetryIncrementedPayload,
    "handoff.ready": HandoffReadyPayload,
    "human.approved": HumanApprovedPayload,
    "knowledge.appended": KnowledgeAppendedPayload,
    "run.paused": RunPausedPayload,
    "run.resumed": RunResumedPayload,
    "model.changed": ModelChangedPayload,
    "meter.update": MeterUpdatePayload,
    "run.terminated": RunTerminatedPayload,
}


def parse_ts(value: str) -> dt.datetime:
    """Parse an ISO 8601 timestamp and require a timezone."""
    text = value.replace("Z", "+00:00") if value.endswith("Z") else value
    parsed = dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("ts must carry a timezone")
    return parsed


def format_ts(value: dt.datetime) -> str:
    """Format a timestamp as ISO 8601 with millisecond precision and a Z suffix."""
    if value.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    utc = value.astimezone(dt.UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


class Event(BaseModel):
    """The envelope. Field order is the line format order."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    run_id: str
    seq: int = Field(ge=1)
    ts: str
    type: EventType
    stage: Stage | None = None
    actor: Actor
    reason: str | None = None
    prompt_ref: str | None = None
    payload: dict[str, Any]

    @field_validator("ts")
    @classmethod
    def _ts_is_iso_with_tz(cls, value: str) -> str:
        parse_ts(value)
        return value

    @model_validator(mode="after")
    def _rules(self) -> Event:
        model = PAYLOAD_MODELS[self.type]
        validated = model.model_validate(self.payload)
        object.__setattr__(self, "payload", validated.model_dump(mode="json", by_alias=True))

        is_orchestrator = isinstance(self.actor, Agent) and self.actor.agent_id == "orchestrator"
        if self.type in ORCHESTRATOR_TYPES:
            if not is_orchestrator:
                raise ValueError(f"{self.type} must be emitted by the Orchestrator")
            if not self.reason or not self.reason.strip():
                raise ValueError(f"{self.type} requires a one-sentence reason")
        elif self.reason is not None and not is_orchestrator:
            raise ValueError("reason is only present on Orchestrator events")

        if self.type in AGENT_MESSAGE_TYPES:
            if self.actor == "human" and self.type == "draft.committed":
                pass
            elif not self.prompt_ref:
                raise ValueError(f"{self.type} requires a prompt_ref")
            if self.actor == "system":
                raise ValueError(f"{self.type} cannot come from the system")
        elif self.prompt_ref is not None:
            raise ValueError("prompt_ref is only present on agent messages")

        if self.type in HUMAN_TYPES and self.actor != "human":
            raise ValueError(f"{self.type} must come from the human")

        if self.type in STAGELESS_TYPES and self.stage is not None:
            raise ValueError(f"{self.type} has no stage")
        if self.type == "meter.update" and self.actor != "system":
            raise ValueError("meter.update is a system event")
        if self.type == "model.changed" and self.actor != "system":
            raise ValueError("model.changed is a system event")
        return self

    def typed_payload(self) -> BaseModel:
        return PAYLOAD_MODELS[self.type].model_validate(self.payload)

    def to_line(self) -> str:
        import json

        return json.dumps(self.model_dump(mode="json", by_alias=True), ensure_ascii=False)

    @classmethod
    def from_line(cls, line: str) -> Event:
        return cls.model_validate_json(line)


def validate_run(events: list[Event]) -> list[str]:
    """Run-level rules. Returns a list of problems (empty when valid)."""
    problems: list[str] = []
    if not events:
        return ["run has no events"]
    if events[0].type != "run.started":
        problems.append("first event is not run.started")
    if events[-1].type != "run.terminated":
        problems.append("last event is not run.terminated")
    run_id = events[0].run_id
    last_ts = parse_ts(events[0].ts)
    for index, event in enumerate(events, start=1):
        if event.seq != index:
            problems.append(f"seq {event.seq} at position {index}")
        if event.run_id != run_id:
            problems.append(f"event {event.seq} belongs to another run")
        ts = parse_ts(event.ts)
        if ts < last_ts:
            problems.append(f"event {event.seq} timestamp goes backwards")
        last_ts = ts
        if event.type == "run.terminated" and index != len(events):
            problems.append(f"run.terminated at position {index} is not last")
    return problems
