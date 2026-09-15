"""Stub agent protocol: canned emissions the Orchestrator relays into events.

A stub scenario declares what each agent seat says and when (fixture offsets from run
start). It never emits Orchestrator or human event types; tests assert that. The
Orchestrator owns every stage change, dispatch, question, retry, and termination.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.schema.bundles import PromptBundle
from app.schema.events import AGENT_MESSAGE_TYPES, Subtask


@dataclass(frozen=True)
class MeterDelta:
    tokens_in: int
    tokens_out: int
    wall_ms: int
    est_cost: float


@dataclass(frozen=True)
class Emit:
    """One agent emission: seat, event type, fixture offset from run start, payload."""

    seat: str
    type: str
    offset_ms: int
    payload: dict[str, Any]
    bundle: PromptBundle | None = None
    meter: MeterDelta | None = None

    def __post_init__(self) -> None:
        if self.type not in AGENT_MESSAGE_TYPES:
            raise ValueError(f"stubs may only emit agent message types, not {self.type}")


@dataclass(frozen=True)
class HumanScript:
    """What the presenter is expected to do, used by tests and the golden regenerator."""

    answers: dict[str, str] = field(default_factory=dict)
    blocker_action: Literal["answer", "escalate"] | None = None
    blocker_answer: str = ""
    decision: Literal["approve", "edit", "reject"] | None = "approve"


@dataclass(frozen=True)
class Marks:
    """Fixture offsets (ms) for the moments the Orchestrator owns. Unset values default
    to the previous offset plus one second."""

    values: dict[str, int] = field(default_factory=dict)

    def get(self, key: str) -> int | None:
        return self.values.get(key)


@dataclass(frozen=True)
class StubScenario:
    dataset_id: str
    client_id: str
    intake: list[Emit]
    plan: list[Subtask]
    tasks: dict[str, list[Emit]]
    assemble: list[list[Emit]]
    review: list[list[Emit]]
    rework: dict[str, list[Emit]] = field(default_factory=dict)
    blocker_answer_continuation: dict[str, list[Emit]] = field(default_factory=dict)
    human_script: HumanScript = field(default_factory=HumanScript)
    marks: Marks = field(default_factory=Marks)
    reasons: dict[str, str] = field(default_factory=dict)
    target_reasons: dict[str, str] = field(default_factory=dict)
    dispatch_summaries: dict[str, str] = field(default_factory=dict)
    orchestrator_meters: dict[str, MeterDelta] = field(default_factory=dict)
    dry_intake: bool = False
    headline_pass_first: str = "The Reviewer passed the proposal first time."
    headline_pass_rework: str = "The Reviewer passed the proposal after one rework."

    def all_emits(self) -> list[Emit]:
        emits = list(self.intake)
        for steps in self.tasks.values():
            emits.extend(steps)
        for steps in self.assemble:
            emits.extend(steps)
        for steps in self.review:
            emits.extend(steps)
        for steps in self.rework.values():
            emits.extend(steps)
        for steps in self.blocker_answer_continuation.values():
            emits.extend(steps)
        return emits

    def bundles(self) -> dict[str, PromptBundle]:
        return {e.bundle.prompt_ref: e.bundle for e in self.all_emits() if e.bundle is not None}
