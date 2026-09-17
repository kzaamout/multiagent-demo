"""Live agents behind the agent source interface (research D2, D7).

For each step the source assembles the run's materials, keeps what the seat may see, builds the
prompt bundle, runs one seat call, and yields agent emissions as they happen: progress lines and
tool calls while the seat works, then the validated reply converted to schema payloads. Usage
records ride on the next emission so every model call gets its own meter update.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel

from app.agents.base import Emit, HumanScript, Marks, MeterDelta
from app.agents.source import AgentFailure, HeadlineResult, PlanResult, Timing
from app.agents.stubs._common import rfp_plan
from app.compile import CompileError, compile_draft
from app.live.concerns import concern_problems, specialist_concerns
from app.live.context import build_context
from app.live.materials import CONFIG_DIR, DatasetFiles, build_materials
from app.live.replies import (
    REQUIRED_SECTIONS,
    EstimatorReply,
    HeadlineProposal,
    IntakeReply,
    PlanProposal,
    PricingReply,
    ReplyError,
    ReviewerReply,
    SingleReply,
    WriterReply,
    blocker_payload,
    checklist_items,
    checklist_markings,
    completed_payload,
    draft_payload,
    intake_payloads,
    parse_as,
    parse_reply,
    verdict_payload,
    without_em_dashes,
)
from app.live.seat_call import CallItem, Requirement, SeatCall, SeatModel
from app.live.strands_tools import ToolLog, build_tools
from app.orchestrator.knowledge_store import KnowledgeStore
from app.runs.metrics import SeatAttempt, append_attempt
from app.schema.bundles import PromptBundle
from app.schema.events import Event, Subtask
from app.seats.definitions import SEAT_DEFINITIONS, load_instructions
from app.tools.prepare import PREPARED_DIR, prepare_documents, read_manifest
from app.tools.template import commit_draft, find_tags, provenance_problems

if TYPE_CHECKING:
    from app.orchestrator.orchestrator import Orchestrator

SPECIALISTS = ("estimator", "pricing")
CORRECTIONS = {"single": 3}
"""Corrections a seat may receive after an invalid reply, so a seat gets this many attempts plus one. Two for
every seat (owner decision 2026-09-17: the local seats missed a two attempt bar often enough to stop most runs),
and three for the Single-model actor, which does the whole job in one call and stops to narrate more often (S5)."""
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
    review_max_cycles: int


def pricing_used_lookup(reply: BaseModel, tools_used: list[str]) -> str | None:
    """Prices and totals must come from price_list_lookup, never from the model."""
    if isinstance(reply, PricingReply) and "price_list_lookup" not in tools_used:
        return (
            "no price came from price_list_lookup. Call the price_list_lookup tool with every bill of materials "
            "line, the markup rate, the labour hours, and the labour rate, then copy its prices and totals"
        )
    return None


SPECIALIST_REQUIREMENTS: dict[str, Requirement] = {}


def estimator_used_calculator(reply: BaseModel, tools_used: list[str]) -> str | None:
    """A completed takeoff must take its totals from quantity_calculate, never from the model's own arithmetic."""
    if isinstance(reply, EstimatorReply) and reply.blocker is None and "quantity_calculate" not in tools_used:
        return (
            "the bill of materials was not totalled with quantity_calculate. Call quantity_calculate with every "
            "counted and measured line, then copy its quantities with waste and its labour hours into your reply"
        )
    return None


BLOCKED_WORDS = ("blocker", "blocked", "could not be counted", "cannot be counted", "not be counted")


def estimator_blocker_is_not_a_concern(reply: BaseModel, tools_used: list[str]) -> str | None:
    """The conventions list the conditions that stop a takeoff. A reply that describes one of them in a concern
    has carried on past a blocker, so it goes back to be raised as one."""
    if not isinstance(reply, EstimatorReply) or reply.blocker is not None:
        return None
    for concern in reply.concerns:
        if any(word in concern.text.lower() for word in BLOCKED_WORDS):
            return (
                f"a concern says the takeoff is blocked: {concern.text[:120]}. The estimating conventions make "
                "that a blocker, not a concern. Reply with the blocker shape alone, "
                '{"blocker": {"description", "needs_human", "route_back_to"}}, and leave out the takeoff'
            )
    return None


def estimator_requirements(reply: BaseModel, tools_used: list[str]) -> str | None:
    """Both Estimator rules, in the order a reader of the conventions would apply them."""
    return estimator_blocker_is_not_a_concern(reply, tools_used) or estimator_used_calculator(
        reply, tools_used
    )


SPECIALIST_REQUIREMENTS.update(estimator=estimator_requirements, pricing=pricing_used_lookup)


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
        self._sources: dict[str, str] = {}

    # Wiring

    def swap_seat_model(self, seat: str, seat_model: SeatModel) -> None:
        """A Settings swap: the seat's next call uses this model (S5). A call in flight is not touched."""
        self.seat_models[seat] = seat_model

    def bind(self, orchestrator: Orchestrator) -> None:
        self._orchestrator = orchestrator
        self.ctx.knowledge.ensure(self.client_id, self.knowledge_seed)

    @property
    def o(self) -> Orchestrator:
        if self._orchestrator is None:
            raise RuntimeError("the live source is not bound to a run")
        return self._orchestrator

    @property
    def run_folder(self) -> Path:
        return self.o.run_folder or self.o.knowledge.path.parent

    def _bundle(self, agent_id: str, task: str, findings: list[dict[str, Any]] | None = None) -> PromptBundle:
        self._counter += 1
        materials = build_materials(
            files=self.ctx.files,
            events=self.o.events,
            knowledge_text=self.ctx.knowledge.read(self.client_id),
            run_folder=self.run_folder,
            findings=findings,
            prepared=read_manifest(self.run_folder / PREPARED_DIR),
        )
        context = build_context(agent_id, materials)
        self._sources = context.source_events()
        return PromptBundle(
            prompt_ref=f"pb-{self.o.run_id[:8]}-{self._counter:02d}",
            system=load_instructions(
                agent_id,
                name=self.o.roster[agent_id].name,
                review_max_cycles=self.ctx.review_max_cycles,
                long_lead_days=self.ctx.long_lead_days,
            ),
            context_slice=context.render(),
            task=task,
            tools=list(SEAT_DEFINITIONS[agent_id].tools),
            model=self.seat_models[agent_id].model,
        )

    def _call(
        self,
        agent_id: str,
        bundle: PromptBundle,
        parse: Callable[[str], BaseModel],
        requirement: Requirement | None = None,
        images: list[bytes] | None = None,
    ) -> AsyncIterator[CallItem]:
        log = ToolLog()
        tools = build_tools(
            agent_id,
            files=self.ctx.files,
            prepared_dir=self.run_folder / PREPARED_DIR,
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
            requirement=requirement,
            on_attempt=lambda attempt, accepted, text, error: self._record_attempt(
                agent_id, bundle, attempt, accepted, text, error
            ),
            images=images,
            corrections=CORRECTIONS.get(agent_id, 2),
        )
        return call.run()

    def _record_attempt(
        self, agent_id: str, bundle: PromptBundle, attempt: int, accepted: bool, text: str, error: str
    ) -> None:
        """Record how a seat's attempt went, and keep a rejected reply beside the recording for diagnosis."""
        folder = self.o.run_folder
        if folder is None:
            return
        append_attempt(
            folder,
            SeatAttempt(
                prompt_ref=bundle.prompt_ref,
                agent_id=agent_id,
                model=bundle.model.label,
                provider=bundle.model.provider,
                attempt=attempt,
                accepted=accepted,
                error=without_em_dashes(error),
                settings=dict(self.seat_models[agent_id].settings) if agent_id in self.seat_models else {},
            ),
        )
        # Every reply is kept, so a recorded run can be read back without the provider (spec section 6).
        responses = folder / "responses"
        responses.mkdir(parents=True, exist_ok=True)
        head = "Accepted" if accepted else f"Rejected: {error}"
        (responses / f"{bundle.prompt_ref}-{attempt}.txt").write_text(
            without_em_dashes(f"{head}\n\n{text}\n"), encoding="utf-8", newline="\n"
        )
        if accepted:
            return
        target = folder / "rejected"
        target.mkdir(parents=True, exist_ok=True)
        body = f"Rejected: {error}\n\n{text}\n"
        (target / f"{bundle.prompt_ref}-{attempt}.txt").write_text(without_em_dashes(body), encoding="utf-8")

    async def _stream(
        self,
        agent_id: str,
        task_id: str,
        bundle: PromptBundle,
        parse: Callable[[str], BaseModel],
        requirement: Requirement | None = None,
        images: list[bytes] | None = None,
    ) -> AsyncIterator[tuple[Emit | None, BaseModel | None, list[MeterDelta], list[str]]]:
        """Yield progress and tool emissions as they happen; the last item carries the reply,
        the usage not yet attached to an emission, and the tools that were used."""
        pending: list[MeterDelta] = []
        tools_used: list[str] = []
        async for item in self._call(agent_id, bundle, parse, requirement, images):
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
        # prepare_documents runs before the Analyst reads anything: deterministic, no model call (spec 0.7 stage 1).
        prepared = await asyncio.to_thread(
            prepare_documents,
            self.ctx.files.request_files(),
            self.ctx.files.drawing_files(),
            self.run_folder / PREPARED_DIR,
        )
        bundle = self._bundle(
            "intake",
            "Read prepared/manifest.md, then grade the request against every item of the readiness checklist, including the drawing set and consistency checks, reading sheets with document_parse_pdf on prepared/<sheet>.pdf. Raise one clarification for each item that is not pass. Return the brief, readiness, and clarifications as the JSON your instructions describe.",
        )
        for prepared_file in prepared.files:
            yield self._tool_emit(
                bundle, prepared_file.source, prepared_file.summary(), prepared_file.duration_ms
            )
        yield self._tool_emit(
            bundle,
            "manifest.md",
            f"{len(prepared.sheets)} sheets from {len(prepared.files)} files, "
            f"{prepared.unknown_count()} title block fields unknown",
            prepared.manifest_ms,
        )
        checklist = CONFIG_DIR / "readiness-checklist.md"
        expected_items = checklist_items(checklist, REQUIRED_SECTIONS)
        markings = checklist_markings(checklist)
        async for emit, reply, pending, _ in self._stream(
            "intake",
            "intake",
            bundle,
            lambda t: parse_reply(
                "intake",
                t,
                expected_items=expected_items,
                markings=markings,
                request_files=[p.name for p in self.ctx.files.request_files()],
            ),
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

    def _tool_emit(
        self, bundle: PromptBundle, args: str, result: str, duration_ms: int, seat: str = "intake"
    ) -> Emit:
        return Emit(
            seat,
            "tool.called",
            0,
            {
                "task_id": seat,
                "agent_id": seat,
                "tool": "prepare_documents",
                "args_summary": without_em_dashes(args)[:200],
                "result_summary": without_em_dashes(result)[:200],
                "duration_ms": duration_ms,
            },
            bundle,
        )

    async def single(self, subtask: Subtask) -> AsyncIterator[Emit]:
        """A Single-model run (S5): prepare the documents, then one call that reads, takes off, prices, and
        writes. The output markdown is committed under drafts/ and named in the result."""
        prepared = await asyncio.to_thread(
            prepare_documents,
            self.ctx.files.request_files(),
            self.ctx.files.drawing_files(),
            self.run_folder / PREPARED_DIR,
        )
        bundle = self._bundle(
            "single",
            f"Sub-task {subtask.task_id}: {subtask.title}. Read prepared/manifest.md, take off the drawings with "
            "quantity_calculate, price every line with price_list_lookup, write the proposal with template_render, "
            "and reply once with headline, summary, markdown, and total.",
        )
        for prepared_file in prepared.files:
            yield self._tool_emit(
                bundle,
                prepared_file.source,
                prepared_file.summary(),
                prepared_file.duration_ms,
                seat="single",
            )
        yield self._tool_emit(
            bundle,
            "manifest.md",
            f"{len(prepared.sheets)} sheets from {len(prepared.files)} files, "
            f"{prepared.unknown_count()} title block fields unknown",
            prepared.manifest_ms,
            seat="single",
        )
        async for emit, reply, pending, tools_used in self._stream(
            "single", subtask.task_id, bundle, lambda t: parse_reply("single", t)
        ):
            if emit is not None:
                yield emit
                continue
            single = cast(SingleReply, reply)
            relative = "drafts/single-v1.md"
            target = self.run_folder / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(single.markdown, encoding="utf-8", newline="\n")
            result = {
                "headline": single.headline,
                "summary": single.summary,
                "total": single.total,
                "output_path": relative,
            }
            provenance = [
                {
                    "tool": name,
                    "source": f"{self.dataset_id} inputs",
                    "confidence": TOOL_CONFIDENCE.get(name, 0.8),
                }
                for name in dict.fromkeys(tools_used)
            ]
            yield Emit(
                "single",
                "task.completed",
                0,
                completed_payload(subtask.task_id, "single", result, provenance),
                bundle,
                meters=tuple(pending),
            )

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
        requirement = SPECIALIST_REQUIREMENTS.get(agent_id)
        async for emit, reply, pending, tools_used in self._stream(
            agent_id, subtask.task_id, bundle, lambda t: parse_reply(agent_id, t), requirement
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

        folder = self.o.run_folder or self.o.knowledge.path.parent

        def provenance_checked(reply: BaseModel, _tools: list[str]) -> str | None:
            markdown = cast(WriterReply, reply).markdown
            problems = provenance_problems(markdown, bundle.context_slice)
            if problems:
                return "; ".join(problems)
            # Every specialist concern that names a sheet must be carried in the Assumptions section
            # (decision 23): the local Writer dropped the rating concern in most runs, so the Reviewer
            # never saw the disagreement the demo turns on.
            dropped = [
                problem
                for role, concern in specialist_concerns(self.o.events)
                for problem in concern_problems(markdown, [concern], role)
            ]
            if dropped:
                return "; ".join(dropped)
            # The draft compiles before it becomes a version (spec FR-015): a compile failure is a
            # rejected reply carrying the compiler's message, and the second failure ends the run.
            try:
                compile_draft(
                    folder,
                    version,
                    markdown,
                    self.o.brand(),
                    sources=self._sources,
                    headlines=self.o.source_headlines(),
                )
            except CompileError as error:
                return f"the draft does not compile: {error}"
            return None

        async for emit, reply, pending, _ in self._stream(
            "writer", f"assemble-v{version}", bundle, lambda t: parse_reply("writer", t), provenance_checked
        ):
            if emit is not None:
                yield emit
                continue
            writer = cast(WriterReply, reply)
            path = commit_draft(folder, version, writer.markdown)
            sources = self._sources
            tags = [(t.tag_id, sources.get(t.source_id, t.source_id)) for t in find_tags(writer.markdown)]
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
        # The compiled pages go with the call as image content (spec stage 5, S4 decision 3b).
        compiled = self.o.latest_compiled
        page_paths = list(compiled.page_images) if compiled is not None else []
        bundle = bundle.model_copy(update={"images": page_paths})
        images = [(self.run_folder / path).read_bytes() for path in page_paths]
        async for emit, reply, pending, _ in self._stream(
            "reviewer",
            f"review-{review_round + 1}",
            bundle,
            lambda t: parse_reply("reviewer", t),
            images=images,
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
