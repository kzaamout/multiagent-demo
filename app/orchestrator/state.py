"""Run state and the pure transition rules of the Orchestrator (spec section 3).

The review limit (spec 0.7 stage 5, constitution VI): after a failing verdict at cycle c,
rework continues only if every one of these holds: c is 1 or the count of blocker and major
findings is strictly lower than in the previous cycle; no finding in this cycle matches a
finding from the previous cycle on normalized evidence text and route target; c is below
`review_max_cycles`. The cost ceiling is checked where the meter is read and ends the run with
its own exit. Otherwise the run stops with exit retry_exhausted and a named stop reason.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Literal

from app.schema.events import STAGE_ORDER, Exit, Stage, StopReason

ReviewOutcome = Literal["rework", "retry_exhausted"]
RouteBackOutcome = Literal["allowed", "blocker"]
MeterOutcome = Literal["ok", "cost_ceiling"]
PendingHuman = Literal["clarifications", "blocker", "handoff"] | None

SERIOUS = ("blocker", "major")
_WORD = re.compile(r"[a-z0-9]+")


def normalize_evidence(text: str) -> str:
    """Evidence text reduced to lower-case words, so punctuation, case, and spacing do not hide a repeat."""
    return " ".join(_WORD.findall(text.lower()))


def finding_key(finding: dict[str, Any]) -> tuple[str, str, str]:
    """What makes two findings the same across cycles: evidence text plus the route target (stage and agent)."""
    return (
        normalize_evidence(str(finding.get("evidence", ""))),
        str(finding.get("route_to") or ""),
        str(finding.get("agent_id") or ""),
    )


@dataclass(frozen=True)
class ReviewCycle:
    """What the progress rule keeps from one failing verdict."""

    number: int
    serious: int
    keys: frozenset[tuple[str, str, str]]

    @classmethod
    def from_findings(cls, number: int, findings: Iterable[dict[str, Any]]) -> ReviewCycle:
        items = list(findings)
        serious = [f for f in items if f.get("severity") in SERIOUS]
        return cls(number=number, serious=len(serious), keys=frozenset(finding_key(f) for f in serious))


@dataclass
class RunState:
    review_max_cycles: int
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
    stop_reason: StopReason | None = None
    last_cycle: ReviewCycle | None = None
    exit: Exit | None = None
    entered: list[Stage] = field(default_factory=list)

    @property
    def retry_budget(self) -> int:
        """The maximum number of reworks, shown on the retry badge: one fewer than the review cycles."""
        return max(self.review_max_cycles - 1, 0)

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

    def on_review_fail(self, findings: list[dict[str, Any]]) -> ReviewOutcome:
        """Apply the review limit to a failing verdict. Either dispatches a rework (retries grows by one) or
        stops the loop with `stop_reason` set. When several conditions fail at once the reason is the first
        in the order no_progress, repeated_finding, max_cycles."""
        cycle = ReviewCycle.from_findings(self.retries + 1, findings)
        previous = self.last_cycle
        self.last_cycle = cycle
        reason: StopReason | None = None
        if previous is not None and cycle.serious >= previous.serious:
            reason = "no_progress"
        elif previous is not None and cycle.keys & previous.keys:
            reason = "repeated_finding"
        elif cycle.number >= self.review_max_cycles:
            reason = "max_cycles"
        if reason is not None:
            self.stop_reason = reason
            return "retry_exhausted"
        self.retries += 1
        return "rework"

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
