"""The agent source: what the Orchestrator asks of the agents, the same for stub and live runs.

The Orchestrator owns stages, questions, knowledge writes, retries, and termination. A source
only answers "what did this seat say" for one step, as a sequence of agent emissions. The S1
stub scenarios are one source; live Strands agents are the other (app/live/source.py).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, Protocol

from app.agents.base import Emit, HumanScript, Marks, MeterDelta, StubScenario
from app.schema.events import Event, Subtask

if TYPE_CHECKING:
    from app.orchestrator.orchestrator import Orchestrator

Timing = Literal["fixture", "wall"]


@dataclass(frozen=True)
class PlanResult:
    subtasks: list[Subtask]
    reason: str | None = None
    meters: list[MeterDelta] = field(default_factory=list)


@dataclass(frozen=True)
class HeadlineResult:
    headline: str | None
    meters: list[MeterDelta] = field(default_factory=list)


class AgentSource(Protocol):
    dataset_id: str
    client_id: str
    timing: Timing
    human_script: HumanScript
    marks: Marks
    reasons: Mapping[str, str]
    target_reasons: Mapping[str, str]
    dispatch_summaries: Mapping[str, str]
    orchestrator_meters: Mapping[str, MeterDelta]
    dry_intake: bool
    headline_pass_first: str
    headline_pass_rework: str

    def bind(self, orchestrator: Orchestrator) -> None: ...

    def intake(self) -> AsyncIterator[Emit]: ...

    async def plan(self) -> PlanResult: ...

    def work_subtasks(self, plan: list[Subtask]) -> list[Subtask]: ...

    def task(self, subtask: Subtask) -> AsyncIterator[Emit]: ...

    def blocker_continuation(self, subtask: Subtask, answer: str) -> AsyncIterator[Emit]: ...

    def rework(
        self, agent_id: str, subtask: Subtask, findings: list[dict[str, Any]]
    ) -> AsyncIterator[Emit]: ...

    def assemble(self, version: int, findings: list[dict[str, Any]]) -> AsyncIterator[Emit]: ...

    def review(self, review_round: int, draft: Event | None) -> AsyncIterator[Emit]: ...

    async def headline(self, exit_value: str, default: str) -> HeadlineResult: ...


async def _each(emits: list[Emit]) -> AsyncIterator[Emit]:
    for emit in emits:
        yield emit


class StubAgentSource:
    """S1 canned scenarios behind the agent source interface."""

    timing: Timing = "fixture"
    dataset_id: str
    client_id: str
    human_script: HumanScript
    marks: Marks
    reasons: Mapping[str, str]
    target_reasons: Mapping[str, str]
    dispatch_summaries: Mapping[str, str]
    orchestrator_meters: Mapping[str, MeterDelta]
    dry_intake: bool
    headline_pass_first: str
    headline_pass_rework: str

    def __init__(self, scenario: StubScenario) -> None:
        self.scenario = scenario
        self.dataset_id = scenario.dataset_id
        self.client_id = scenario.client_id
        self.human_script = scenario.human_script
        self.marks = scenario.marks
        self.reasons = scenario.reasons
        self.target_reasons = scenario.target_reasons
        self.dispatch_summaries = scenario.dispatch_summaries
        self.orchestrator_meters = scenario.orchestrator_meters
        self.dry_intake = scenario.dry_intake
        self.headline_pass_first = scenario.headline_pass_first
        self.headline_pass_rework = scenario.headline_pass_rework

    def bind(self, orchestrator: Orchestrator) -> None:
        return None

    def intake(self) -> AsyncIterator[Emit]:
        return _each(self.scenario.intake)

    async def plan(self) -> PlanResult:
        return PlanResult(list(self.scenario.plan))

    def work_subtasks(self, plan: list[Subtask]) -> list[Subtask]:
        return [s for s in plan if s.task_id in self.scenario.tasks]

    def task(self, subtask: Subtask) -> AsyncIterator[Emit]:
        return _each(self.scenario.tasks.get(subtask.task_id, []))

    def blocker_continuation(self, subtask: Subtask, answer: str) -> AsyncIterator[Emit]:
        return _each(self.scenario.blocker_answer_continuation.get(subtask.task_id, []))

    def rework(self, agent_id: str, subtask: Subtask, findings: list[dict[str, Any]]) -> AsyncIterator[Emit]:
        return _each(self.scenario.rework.get(agent_id, []))

    def assemble(self, version: int, findings: list[dict[str, Any]]) -> AsyncIterator[Emit]:
        steps = self.scenario.assemble[min(version, len(self.scenario.assemble)) - 1]
        return _each(steps)

    def review(self, review_round: int, draft: Event | None) -> AsyncIterator[Emit]:
        return _each(self.scenario.review[min(review_round, len(self.scenario.review) - 1)])

    async def headline(self, exit_value: str, default: str) -> HeadlineResult:
        return HeadlineResult(None)


def as_source(scenario: StubScenario | AgentSource) -> AgentSource:
    if isinstance(scenario, StubScenario):
        return StubAgentSource(scenario)
    return scenario
