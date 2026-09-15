"""Run state and the pure transition rules of the Orchestrator (spec section 3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.schema.events import STAGE_ORDER, Exit, Stage

ReviewOutcome = Literal["rework", "retry_exhausted"]
RouteBackOutcome = Literal["allowed", "blocker"]
MeterOutcome = Literal["ok", "cost_ceiling"]
PendingHuman = Literal["clarifications", "blocker", "handoff"] | None


@dataclass
class RunState:
    retry_budget: int
    cost_ceiling: float
    stage: Stage | None = None
    retries: int = 0
    work_to_intake_used: bool = False
    paused: bool = False
    stopped: bool = False
    pending_human: PendingHuman = None
    draft_version: int = 0
    est_cost: float = 0.0
    tokens_in: dict[str, int] = field(default_factory=dict)
    tokens_out: dict[str, int] = field(default_factory=dict)
    assumptions: list[str] = field(default_factory=list)
    clarifications: dict[str, str] = field(default_factory=dict)
    unresolved_findings: list[str] = field(default_factory=list)
    missing: list[tuple[str, str, str | None]] = field(default_factory=list)
    readiness_verdict: str | None = None
    exit: Exit | None = None
    entered: list[Stage] = field(default_factory=list)

    @property
    def terminated(self) -> bool:
        return self.exit is not None

    def can_dispatch(self) -> bool:
        return not self.paused and not self.stopped and not self.terminated

    def direction_to(self, stage: Stage) -> Literal["forward", "backward"]:
        if self.stage is None:
            return "forward"
        return "forward" if STAGE_ORDER.index(stage) > STAGE_ORDER.index(self.stage) else "backward"

    def enter(self, stage: Stage) -> None:
        self.stage = stage
        if stage not in self.entered:
            self.entered.append(stage)

    def on_review_fail(self) -> ReviewOutcome:
        """A failed verdict either consumes a retry or exhausts the budget."""
        if self.retries < self.retry_budget:
            self.retries += 1
            return "rework"
        return "retry_exhausted"

    def on_route_back_to_intake(self) -> RouteBackOutcome:
        """Work to Intake is capped at one per run; the second attempt becomes a blocker."""
        if self.work_to_intake_used:
            return "blocker"
        self.work_to_intake_used = True
        return "allowed"

    def on_meter(self, agent_id: str, tokens_in: int, tokens_out: int, est_cost: float) -> MeterOutcome:
        self.tokens_in[agent_id] = self.tokens_in.get(agent_id, 0) + tokens_in
        self.tokens_out[agent_id] = self.tokens_out.get(agent_id, 0) + tokens_out
        self.est_cost = round(self.est_cost + est_cost, 6)
        return "cost_ceiling" if self.est_cost > self.cost_ceiling else "ok"

    def terminate(self, exit_value: Exit) -> None:
        if self.exit is not None:
            raise RuntimeError("run already terminated")
        self.exit = exit_value
        self.pending_human = None
        self.paused = False
