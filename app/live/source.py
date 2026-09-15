"""Live agents behind the agent source interface (research D2, D7).

For each step the source assembles the run's materials, keeps what the seat may see, builds the
prompt bundle, runs one seat call, and yields agent emissions as they happen: progress lines and
tool calls while the seat works, then the validated reply converted to schema payloads. Usage
records ride on the next emission so every model call gets its own meter update.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator, Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel

from app.agents.base import Emit, HumanScript, Marks, MeterDelta
from app.agents.source import AgentFailure, HeadlineResult, PlanResult, Timing
from app.agents.stubs._common import rfp_plan
from app.live.context import build_context
from app.live.materials import CONFIG_DIR, DatasetFiles, build_materials
from app.live.replies import (
    EstimatorReply,
    HeadlineProposal,
    IntakeReply,
    PlanProposal,
    PricingReply,
    ReplyError,
    ReviewerReply,
    WriterReply,
    blocker_payload,
    checklist_items,
    completed_payload,
    draft_payload,
    intake_payloads,
    parse_as,
    parse_reply,
    verdict_payload,
)
from app.live.seat_call import CallItem, SeatCall, SeatModel
from app.live.strands_tools import ToolLog, build_tools
from app.orchestrator.knowledge_store import KnowledgeStore
from app.schema.bundles import PromptBundle
from app.schema.events import Event, Subtask
from app.seats.definitions import SEAT_DEFINITIONS, load_instructions
from app.tools.template import commit_draft, find_tags

if TYPE_CHECKING:
    from app.orchestrator.orchestrator import Orchestrator

SPECIALISTS = ("estimator", "pricing")
TOOL_CONFIDENCE = {"price_list_lookup": 1.0, "quantity_calculate": 1.0, "vision_read_drawing": 0.8}
_TASK_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")


def standard_plan() -> list[Subtask]:
    return rfp_plan(
        ["brief", "drawing set", "estimating conventions"],
        ["bill of materials", "knowledge file"],
        ["brief", "specialist outputs", "template", "knowledge file"],
    )


def validate_plan(subtasks: list[dict[str, Any]]) -> list[Subtask]:
    """The run engine's rules for a proposed plan. Raises ReplyError on the first breach."""
    try:
        parsed = [Subtask.model_validate(s) for s in subtasks]
    except Exception as error:  # noqa: BLE001
        raise ReplyError(f"a sub-task is malformed: {type(error).__name__}") from None
    ids = [s.task_id for s in parsed]
    if len(ids) != len(set(ids)) or not all(_TASK_ID.match(i) for i in ids):
        raise ReplyError("task ids must be unique short lower-case names")
    by_agent: dict[str, list[Subtask]] = {}
    for s in parsed:
        if s.agent_id not in ("estimator", "pricing", "writer"):
            raise ReplyError(f"{s.agent_id} cannot hold a sub-task")
        by_agent.setdefault(s.agent_id, []).append(s)
        for dep in s.depends_on:
            if dep not in ids or dep == s.task_id:
                raise ReplyError(f"{s.task_id} depends on an unknown task {dep}")
    if len(by_agent.get("writer", [])) != 1 or not by_agent.get("estimator") or not by_agent.get("pricing"):
        raise ReplyError(
            "the plan needs an Estimator and a Pricing sub-task and exactly one Assemble sub-task"
        )
    writer = by_agent["writer"][0]
    others = {s.task_id for s in parsed if s.agent_id != "writer"}
    if set(writer.depends_on) != others:
        raise ReplyError("the Assemble sub-task must depend on every specialist sub-task")
    estimator_ids = {s.task_id for s in by_agent["estimator"]}
    for s in by_agent["pricing"]:
        if not estimator_ids & set(s.depends_on):
            raise ReplyError("Pricing must wait for the Estimator")
    return parsed


@dataclass
class LiveContext:
    files: DatasetFiles
    knowledge: KnowledgeStore
    prospect_name: str
    project: str
    supplier_order: list[str]
    long_lead_days: int
    retry_budget: int


class LiveAgentSource:
    timing: Timing = "wall"

    def __init__(
        self,
        *,
        dataset_id: str,
        client_id: str,
        context: LiveContext,
        seat_models: dict[str, SeatModel],
        knowledge_seed: Any = None,
    ) -> None:
        self.dataset_id = dataset_id
        self.client_id = client_id
        self.ctx = context
        self.seat_models = seat_models
        self.knowledge_seed = knowledge_seed
        self.human_script = HumanScript()
        self.marks = Marks()
        self.reasons: Mapping[str, str] = {}
        self.target_reasons: Mapping[str, str] = {}
        self.dispatch_summaries: Mapping[str, str] = {}
        self.orchestrator_meters: Mapping[str, MeterDelta] = {}
        self.dry_intake = False
        self.headline_pass_first = "The Reviewer passed the proposal first time."
        self.headline_pass_rework = "The Reviewer passed the proposal after one rework."
        self._orchestrator: Orchestrator | None = None
        self._counter = 0
        self._blockers = 0

    # Wiring

    def bind(self, orchestrator: Orchestrator) -> None:
        self._orchestrator = orchestrator
        self.ctx.knowledge.ensure(self.client_id, self.knowledge_seed)

    @property
    def o(self) -> Orchestrator:
        if self._orchestrator is None:
            raise RuntimeError("the live source is not bound to a run")
        return self._orchestrator

    def _bundle(self, agent_id: str, task: str, findings: list[dict[str, Any]] | None = None) -> PromptBundle:
        self._counter += 1
        materials = build_materials(
            files=self.ctx.files,
            events=self.o.events,
            knowledge_text=self.ctx.knowledge.read(self.client_id),
            run_folder=self.o.run_folder or self.o.knowledge.path.parent,
            findings=findings,
        )
        context = build_context(agent_id, materials)
        return PromptBundle(
            prompt_ref=f"pb-{self.o.run_id[:8]}-{self._counter:02d}",
            system=load_instructions(
                agent_id,
                name=self.o.roster[agent_id].name,
                retry_budget=self.ctx.retry_budget,
                long_lead_days=self.ctx.long_lead_days,
            ),
            context_slice=context.render(),
            task=task,
            tools=list(SEAT_DEFINITIONS[agent_id].tools),
            model=self.seat_models[agent_id].model,
        )

    def _call(
        self, agent_id: str, bundle: PromptBundle, parse: Callable[[str], BaseModel]
    ) -> AsyncIterator[CallItem]:
        log = ToolLog()
        tools = build_tools(
            agent_id,
            files=self.ctx.files,
            log=log,
            prospect_name=self.ctx.prospect_name,
            project=self.ctx.project,
            supplier_order=self.ctx.supplier_order,
            long_lead_days=self.ctx.long_lead_days,
        )
        call = SeatCall(
            agent_id=agent_id,
            role=self.o.roster[agent_id].role,
            instructions=bundle.system,
            seat_model=self.seat_models[agent_id],
            tools=tools,
            log=log,
            bundle=bundle,
            parse=parse,
        )
        return call.run()

    async def _stream(
        self, agent_id: str, task_id: str, bundle: PromptBundle, parse: Callable[[str], BaseModel]
    ) -> AsyncIterator[tuple[Emit | None, BaseModel | None, list[MeterDelta], list[str]]]:
        """Yield progress and tool emissions as they happen; the last item carries the reply,
        the usage not yet attached to an emission, and the tools that were used."""
        pending: list[MeterDelta] = []
        tools_used: list[str] = []
        async for item in self._call(agent_id, bundle, parse):
            if item.kind == "usage" and item.usage is not None:
                pending.append(item.usage)
            elif item.kind == "progress":
                emit = Emit(
                    agent_id,
                    "task.progress",
                    0,
                    {
                        "task_id": task_id,
                        "agent_id": agent_id,
                        "message": item.text,
                        "headline": item.text[:80],
                    },
                    bundle,
                    meters=tuple(pending),
                )
                pending = []
                yield emit, None, [], tools_used
            elif item.kind == "tool" and item.tool is not None:
                tools_used.append(item.tool.name)
                emit = Emit(
                    agent_id,
                    "tool.called",
                    0,
                    {
                        "task_id": task_id,
                        "agent_id": agent_id,
                        "tool": item.tool.name,
                        "args_summary": item.tool.args_summary,
                        "result_summary": item.tool.result_summary,
                        "duration_ms": item.tool.duration_ms,
                    },
                    bundle,
                    meters=tuple(pending),
                )
                pending = []
                yield emit, None, [], tools_used
            elif item.kind == "reply":
                yield None, item.reply, pending, tools_used
                return

    # Steps

    async def intake(self) -> AsyncIterator[Emit]:
        bundle = self._bundle(
            "intake",
            "Grade the request in the inputs folder against every item of the readiness checklist, including the drawing set and consistency checks. Raise one clarification for each item that is not pass. Return the brief, readiness, and clarifications as the JSON your instructions describe.",
        )
        expected_items = checklist_items(CONFIG_DIR / "readiness-checklist.md")
        async for emit, reply, pending, _ in self._stream(
            "intake", "intake", bundle, lambda t: parse_reply("intake", t, expected_items=expected_items)
        ):
            if emit is not None:
                yield emit
                continue
            intake = cast(IntakeReply, reply)
            brief, readiness, questions = intake_payloads(intake)
            yield Emit("intake", "intake.brief", 0, brief, bundle)
            yield Emit("intake", "intake.readiness", 0, readiness, bundle, meters=tuple(pending))
            for question in questions:
                yield Emit("intake", "clarification.needed", 0, question, bundle)

    async def plan(self) -> PlanResult:
        bundle = self._bundle(
            "orchestrator",
            'Propose the work plan for this brief. Seats that can hold sub-tasks: estimator, pricing, writer. Return only this JSON object and nothing else: {"subtasks": [{"task_id": "...", "title": "...", "agent_id": "...", "depends_on": [], "scope": []}], "reason": "..."}',
        )
        meters: list[MeterDelta] = []
        proposal: PlanProposal | None = None

        def parse(text: str) -> BaseModel:
            return parse_as(PlanProposal, text)

        self.o.bundles[bundle.prompt_ref] = bundle
        try:
            async for item in self._call("orchestrator", bundle, parse):
                if item.kind == "usage" and item.usage is not None:
                    meters.append(item.usage)
                elif item.kind == "reply":
                    proposal = cast(PlanProposal, item.reply)
        except AgentFailure as failure:
            if not failure.invalid_reply:
                raise
            return PlanResult(
                standard_plan(),
                "The Orchestrator's plan could not be read, so the standard plan is used.",
                meters,
            )
        if proposal is not None:
            try:
                return PlanResult(validate_plan(proposal.subtasks), proposal.reason, meters)
            except ReplyError:
                pass
        return PlanResult(
            standard_plan(),
            "The proposed plan broke a dependency or scope rule, so the standard plan is used.",
            meters,
        )

    def work_subtasks(self, plan: list[Subtask]) -> list[Subtask]:
        return [s for s in plan if s.agent_id != "writer"]

    def task(self, subtask: Subtask) -> AsyncIterator[Emit]:
        return self._specialist(subtask, extra="", findings=None)

    def blocker_continuation(self, subtask: Subtask, answer: str) -> AsyncIterator[Emit]:
        extra = (
            f"The presenter answered your blocker: {answer}" if answer else "Continue with the updated brief."
        )
        return self._specialist(subtask, extra=extra, findings=None)

    def rework(self, agent_id: str, subtask: Subtask, findings: list[dict[str, Any]]) -> AsyncIterator[Emit]:
        return self._specialist(
            subtask, extra="Address only the Reviewer findings routed to you.", findings=findings
        )

    async def _specialist(
        self, subtask: Subtask, *, extra: str, findings: list[dict[str, Any]] | None
    ) -> AsyncIterator[Emit]:
        agent_id = subtask.agent_id
        task = f"Sub-task {subtask.task_id}: {subtask.title}. {extra}".strip()
        bundle = self._bundle(agent_id, task, findings)
        async for emit, reply, pending, tools_used in self._stream(
            agent_id, subtask.task_id, bundle, lambda t: parse_reply(agent_id, t)
        ):
            if emit is not None:
                yield emit
                continue
            if isinstance(reply, EstimatorReply) and reply.blocker is not None:
                self._blockers += 1
                payload = blocker_payload(
                    subtask.task_id, agent_id, f"b_{subtask.task_id}_{self._blockers}", reply.blocker
                )
                yield Emit(agent_id, "blocker.raised", 0, payload, bundle, meters=tuple(pending))
                return
            result = cast(EstimatorReply | PricingReply, reply).model_dump(mode="json", exclude_none=True)
            result.pop("blocker", None)
            provenance = [
                {
                    "tool": name,
                    "source": f"{self.dataset_id} inputs",
                    "confidence": TOOL_CONFIDENCE.get(name, 0.8),
                }
                for name in dict.fromkeys(tools_used)
            ]
            yield Emit(
                agent_id,
                "task.completed",
                0,
                completed_payload(subtask.task_id, agent_id, result, provenance),
                bundle,
                meters=tuple(pending),
            )

    async def assemble(self, version: int, findings: list[dict[str, Any]]) -> AsyncIterator[Emit]:
        task = f"Assemble draft v{version} of the proposal."
        if findings:
            task += " Fix only the Reviewer findings routed to you."
        bundle = self._bundle("writer", task, findings or None)
        async for emit, reply, pending, _ in self._stream(
            "writer", f"assemble-v{version}", bundle, lambda t: parse_reply("writer", t)
        ):
            if emit is not None:
                yield emit
                continue
            writer = cast(WriterReply, reply)
            folder = self.o.run_folder or self.o.knowledge.path.parent
            path = commit_draft(folder, version, writer.markdown)
            tags = [(t.tag_id, t.source_id) for t in find_tags(writer.markdown)]
            note = writer.note or f"{len(tags)} provenance tags"
            yield Emit(
                "writer",
                "draft.committed",
                0,
                draft_payload(version, path, tags, note),
                bundle,
                meters=tuple(pending),
            )

    async def review(self, review_round: int, draft: Event | None) -> AsyncIterator[Emit]:
        version = draft.payload["version"] if draft is not None else review_round + 1
        bundle = self._bundle(
            "reviewer", f"Review draft v{version} against the brief and the reviewer criteria."
        )
        async for emit, reply, pending, _ in self._stream(
            "reviewer", f"review-{review_round + 1}", bundle, lambda t: parse_reply("reviewer", t)
        ):
            if emit is not None:
                yield emit
                continue
            verdict = verdict_payload(cast(ReviewerReply, reply))
            yield Emit("reviewer", "review.verdict", 0, verdict, bundle, meters=tuple(pending))

    async def headline(self, exit_value: str, default: str) -> HeadlineResult:
        bundle = self._bundle(
            "orchestrator",
            f'The run ends with exit {exit_value} after {self.o.state.retries} retries. Return only this JSON object: {{"headline": "one sentence under 12 words"}}. A plain default is: {default}',
        )
        self.o.bundles[bundle.prompt_ref] = bundle
        meters: list[MeterDelta] = []
        headline: str | None = None

        def parse(text: str) -> BaseModel:
            return parse_as(HeadlineProposal, text)

        try:
            async for item in self._call("orchestrator", bundle, parse):
                if item.kind == "usage" and item.usage is not None:
                    meters.append(item.usage)
                elif item.kind == "reply":
                    headline = cast(HeadlineProposal, item.reply).headline.strip() or None
        except AgentFailure as failure:
            if not failure.invalid_reply:
                raise
        return HeadlineResult(headline, meters)
