"""The Orchestrator: the only component that changes stage, talks to the human, writes the
knowledge file, and ends a run (constitution III). An agent source (stub or live) supplies
what each seat said; the Orchestrator relays it as validated events and owns everything else.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from app.agents.base import Emit, MeterDelta, StubScenario
from app.agents.source import AgentFailure, AgentSource, as_source
from app.orchestrator.clock import Clock
from app.orchestrator.knowledge import KnowledgeFile
from app.orchestrator.knowledge_store import KnowledgeStore
from app.orchestrator.state import RunState
from app.runs.bus import StreamBus
from app.runs.recorder import Recorder
from app.schema.bundles import PromptBundle
from app.schema.events import (
    Agent,
    Event,
    Exit,
    KnowledgeEntry,
    Stage,
    Subtask,
)


class RunStopped(Exception):
    pass


class CostCeilingBreached(Exception):
    pass


@dataclass
class Answer:
    question_id: str
    answer: str
    action: Literal["answer", "escalate"] = "answer"


@dataclass
class DatasetRef:
    dataset_id: str
    label: str
    client_id: str
    knowledge_seed: Path | None = None


@dataclass
class _TaskRun:
    subtask: Subtask
    done: asyncio.Event = field(default_factory=asyncio.Event)
    completed_event_id: str | None = None


DEFAULT_REASONS: dict[str, str] = {
    "start": "Every run begins with a readiness grade before any specialist is paid to work.",
    "assumption": "The gap is non-blocking and the default is safe to proceed on; it is flagged for Handoff.",
    "clarification": "Blocking gaps are batched into one question set so you are asked once.",
    "knowledge": "Answers about the client are facts worth keeping for the next run.",
    "known_answer": "The client knowledge file already answers this, so the stored answer is used and nobody is asked again.",
    "not_ready": "The request is missing items no specialist can work without, so the run stops here.",
    "dry_intake": "Dry intake stops after the readiness grade so the request can be fixed before a full run.",
    "plan_enter": "The brief is ready, so the work can be decomposed and assigned.",
    "plan": "Each sub-task goes to the seat whose tools and scope fit it; dependent tasks wait.",
    "work_enter": "The plan is fixed; specialists can start.",
    "dispatch": "Each specialist receives only its sub-task, the brief, and the context in its scope.",
    "assemble_enter": "All specialist outputs are in, so the Writer can assemble the deliverable.",
    "assemble_dispatch": "The Writer assembles from the specialist outputs and tags every figure with its source.",
    "review_enter": "A draft exists, so the Reviewer judges it against the brief and the criteria.",
    "handoff_enter": "The Reviewer passed the draft, so it goes to you for approval.",
    "handoff_exhausted": "The retry budget is spent, so the draft goes to you with findings unresolved.",
    "handoff": "The package is complete: deliverable, verdict, assumptions, clarifications, and the event log.",
    "route_back_work": "The finding concerns a source figure, so the specialist who produced it resolves it.",
    "route_back_assemble": "The finding concerns the writing, so the Writer resolves it without new specialist work.",
    "retry": "A failed review consumes one retry from the budget.",
    "rework_dispatch": "The specialist receives the finding and reworks only what it concerns.",
    "blocker": "A specialist cannot continue without you, so the run pauses on the blocker.",
    "escalated": "You escalated the blocker, so the run ends with what is missing listed.",
    "route_back_intake": "A specialist found the brief incomplete, so Intake runs again once.",
    "terminated_pass": "The verdict is pass; the package is approved and the run closes.",
    "terminated_exhausted": "The retry budget is spent; your decision on the draft is recorded and the run closes with findings unresolved.",
    "terminated_rejected": "You rejected the package; the rejection is recorded and the run closes without re-entering the loop.",
    "terminated": "The run has reached its exit and nothing further can be dispatched.",
    "cost_ceiling": "The estimated cost passed the per-run ceiling, so nothing further is dispatched.",
    "stopped": "The presenter stopped the run.",
    "paused": "The presenter paused the run; in-flight work completes and nothing new is dispatched.",
    "resumed": "The presenter resumed the run.",
}


class Orchestrator:
    def __init__(
        self,
        *,
        run_id: str,
        workflow: str,
        dataset: DatasetRef,
        scenario: StubScenario | AgentSource,
        roster: dict[str, Agent],
        retry_budget: int,
        cost_ceiling: float,
        clock: Clock,
        bus: StreamBus,
        recorder: Recorder | None,
        knowledge_path: Path,
        event_log_path: str,
        id_factory: Callable[[int], str] | None = None,
        knowledge_store: KnowledgeStore | None = None,
        run_folder: Path | None = None,
    ) -> None:
        self._id_factory = id_factory or (lambda _seq: str(uuid.uuid4()))
        self.run_id = run_id
        self.workflow = workflow
        self.dataset = dataset
        self.scenario = as_source(scenario)
        self.roster = roster
        self.knowledge_store = knowledge_store
        self.run_folder = run_folder
        self.clock = clock
        self.bus = bus
        self.recorder = recorder
        self.state = RunState(retry_budget=retry_budget, cost_ceiling=cost_ceiling)
        self.events: list[Event] = []
        self.bundles: dict[str, PromptBundle] = {}
        self.knowledge = KnowledgeFile(knowledge_path, dataset.knowledge_seed, dataset.client_id)
        self.event_log_path = event_log_path
        self._lock = asyncio.Lock()
        self._last_offset = 0
        self._shift_ms = 0
        self._pause_gate = asyncio.Event()
        self._pause_gate.set()
        self._human_gate = asyncio.Event()
        self.human_needed = asyncio.Event()
        self._answers: list[Answer] = []
        self._decision: tuple[str, str] | None = None
        self._pending_question_ids: list[str] = []
        self._pending_blocker: dict[str, Any] | None = None
        self._terminating = False
        self._run_task: asyncio.Task[Any] | None = None
        self._started = False
        self._pause_announced = False
        self._control_tasks: set[asyncio.Task[Any]] = set()
        self.finished = asyncio.Event()
        self._call_counter = 0
        self._task_event_ids: dict[str, str] = {}
        self.plan: list[Subtask] = []
        self.latest_draft: Event | None = None
        self.scenario.bind(self)

    # Public control surface (used by the API and the test driver)

    @property
    def orchestrator(self) -> Agent:
        return self.roster["orchestrator"]

    @property
    def status(self) -> str:
        if self.state.terminated:
            return "terminated"
        if self.state.pending_human is not None or self.state.paused:
            return "paused"
        return "running"

    def pending(self) -> dict[str, Any]:
        return {
            "kind": self.state.pending_human,
            "question_ids": list(self._pending_question_ids),
            "blocker": self._pending_blocker,
        }

    def submit_answers(self, answers: list[Answer]) -> None:
        if self.state.pending_human not in ("clarifications", "blocker"):
            raise ValueError("the run is not waiting for answers")
        expected = set(self._pending_question_ids)
        if self._pending_blocker is not None:
            expected.add(self._pending_blocker["blocker_id"])
        given = {a.question_id for a in answers}
        if given != expected:
            raise ValueError(f"answers must cover exactly {sorted(expected)}")
        if any(a.action == "escalate" for a in answers) and self._pending_blocker is None:
            raise ValueError("escalate is only valid for a blocker")
        self._answers = list(answers)
        self._human_gate.set()

    def submit_decision(self, decision: str, notes: str = "") -> None:
        if self.state.pending_human != "handoff":
            raise ValueError("the run is not at Handoff")
        if decision != "approve":
            raise ValueError(f"{decision} arrives in S4; only approve is available in this slice")
        self._decision = (decision, notes)
        self._human_gate.set()

    def attach_task(self, task: asyncio.Task[Any]) -> None:
        """The task running this Orchestrator, so Stop can cancel work in flight."""
        self._run_task = task

    def pause(self) -> None:
        """Freeze dispatch. Calls in flight complete. Ignored while waiting on a human or after the end.
        A pause before the run starts holds dispatch without an event, since run.started comes first."""
        if (
            self.state.terminated
            or self._terminating
            or self.state.paused
            or self.state.pending_human is not None
        ):
            return
        self.state.paused = True
        self._pause_gate.clear()
        if self._started and self.events:
            self._pause_announced = True
            self._control_event("run.paused", "paused")

    def resume(self) -> None:
        if not self.state.paused or self.state.terminated or self._terminating:
            return
        self.state.paused = False
        self._pause_gate.set()
        if self._pause_announced:
            self._pause_announced = False
            self._control_event("run.resumed", "resumed")

    def _control_event(self, type_: str, reason_key: str) -> None:
        async def emit() -> None:
            if self.state.terminated or self._terminating:
                return
            try:
                await self._emit_orchestrator(
                    type_,
                    stage=self.state.stage,
                    offset=self._after(0),
                    reason=self._reason(reason_key),
                    payload={"by": "human"},
                )
            except RuntimeError:
                pass  # the run ended between the request and the emission

        task = asyncio.get_running_loop().create_task(emit())
        self._control_tasks.add(task)
        task.add_done_callback(self._control_tasks.discard)

    def stop(self) -> None:
        """End the run with exit stopped from any state, cancelling work in flight."""
        if self.state.terminated:
            return
        self.state.stopped = True
        self._terminating = True
        self._pause_gate.set()
        self._human_gate.set()
        task = self._run_task
        # A run that has not started yet stops at its first gate; cancelling it would skip run() entirely.
        if self._started and task is not None and not task.done() and task is not asyncio.current_task():
            task.cancel()

    # Run loop

    async def run(self) -> None:
        self._started = True
        try:
            await self._start()
            await self._intake_stage()
            if self.state.terminated:
                return
            await self._plan_stage()
            await self._work_stage()
            if self.state.terminated:
                return
            await self._assemble_review_loop()
        except RunStopped:
            if not self.state.terminated:
                await self._terminate("stopped", self._reason("stopped"))
        except asyncio.CancelledError:
            if not self.state.stopped:
                raise
            current = asyncio.current_task()
            if current is not None:
                current.uncancel()
            if not self.state.terminated:
                await asyncio.shield(self._terminate("stopped", self._reason("stopped")))
        except CostCeilingBreached:
            if not self.state.terminated:
                await self._terminate("cost_ceiling", self._reason("cost_ceiling"))
        except AgentFailure as failure:
            if not self.state.terminated:
                await self._terminate("stopped", failure.reason)
        except Exception as error:  # noqa: BLE001
            if not self.state.terminated:
                await self._terminate(
                    "stopped", f"The run stopped on an internal error: {type(error).__name__}."
                )
            raise
        finally:
            self.bus.close(self.run_id)
            self.finished.set()

    # Stages

    async def _start(self) -> None:
        if self.recorder is not None:
            self.recorder.start(
                {
                    "run_id": self.run_id,
                    "dataset_id": self.dataset.dataset_id,
                    "workflow": self.workflow,
                    "mode": "team",
                    "started_at": self.clock.ts(0),
                    "roster": {k: v.model_dump() for k, v in self.roster.items()},
                }
            )
        self.bus.open(self.run_id)
        await self._emit_orchestrator(
            "run.started",
            stage=None,
            offset=0,
            reason=self._reason("start"),
            payload={
                "workflow": self.workflow,
                "dataset_id": self.dataset.dataset_id,
                "mode": "team",
                "roster": [a.model_dump() for a in self.roster.values()],
            },
        )

    async def _change_stage(
        self, to: Stage, reason: str, mark: str | None = None, target_reason: str | None = None
    ) -> None:
        await self._gate()
        direction = self.state.direction_to(to)
        payload = {
            "from": self.state.stage,
            "to": to,
            "direction": direction,
            "target_reason": target_reason or reason,
        }
        self.state.enter(to)
        await self._emit_orchestrator(
            "stage.changed", stage=to, offset=self._mark(mark), reason=reason, payload=payload
        )

    async def _intake_stage(self) -> None:
        await self._change_stage("intake", self._reason("start"), mark="intake_enter")
        readiness_event, questions = await self._run_intake_steps()
        verdict = readiness_event.payload["verdict"] if readiness_event else "ready"
        self.state.readiness_verdict = verdict
        if readiness_event and (verdict == "not_ready" or self.scenario.dry_intake):
            for item in readiness_event.payload["checklist"]:
                if item["status"] == "fail":
                    self.state.missing.append((item["item"], item.get("note", ""), readiness_event.event_id))
        if self.scenario.dry_intake:
            await self._terminate("dry_intake", self._reason("dry_intake"))
            return
        if verdict == "not_ready":
            await self._terminate("not_ready", self._reason("not_ready"))
            return
        blocking: list[Event] = []
        known = self._known_answers()
        for question in questions:
            qid = question.payload["question_id"]
            if qid in known:
                self.state.assumptions.append(qid)
                await self._emit_orchestrator(
                    "assumption.accepted",
                    stage="intake",
                    offset=self._mark("assumption"),
                    reason=self._reason("known_answer"),
                    payload={"question_id": qid, "default_used": known[qid]},
                )
                continue
            if question.payload["blocking"]:
                blocking.append(question)
            else:
                self.state.assumptions.append(question.payload["question_id"])
                await self._emit_orchestrator(
                    "assumption.accepted",
                    stage="intake",
                    offset=self._mark("assumption"),
                    reason=self._reason("assumption"),
                    payload={
                        "question_id": question.payload["question_id"],
                        "default_used": question.payload["proposed_default"],
                    },
                )
        if blocking:
            await self._ask_clarifications([q.payload["question_id"] for q in blocking])

    async def _run_intake_steps(self) -> tuple[Event | None, list[Event]]:
        readiness: Event | None = None
        questions: list[Event] = []
        async for emit in self.scenario.intake():
            event = await self._relay(emit, stage="intake")
            if event.type == "intake.readiness":
                readiness = event
            elif event.type == "clarification.needed":
                questions.append(event)
        return readiness, questions

    async def _ask_clarifications(self, question_ids: list[str]) -> None:
        self._pending_question_ids = list(question_ids)
        self._pending_blocker = None
        await self._emit_orchestrator(
            "clarification.asked",
            stage="intake",
            offset=self._mark("clarification"),
            reason=self._reason("clarification"),
            payload={"question_ids": question_ids, "blocker": None},
            meter_key="clarification",
        )
        answers = await self._wait_for_human("clarifications", mark="human_answer")
        entries: list[KnowledgeEntry] = []
        for answer in answers:
            event = await self._emit_human(
                "clarification.answered",
                stage="intake",
                payload={"question_id": answer.question_id, "answer": answer.answer, "action": "answer"},
                mark="human_answer",
            )
            self.state.clarifications[answer.question_id] = answer.answer
            entries.append(
                KnowledgeEntry(
                    question_id=answer.question_id, answer=answer.answer, source_event_id=event.event_id
                )
            )
        for entry in entries:
            self.knowledge.append([entry], self.clock.ts(self._last_offset))
            if self.knowledge_store is not None:
                self.knowledge_store.append(
                    self.dataset.client_id, [entry], run_id=self.run_id, when=self.clock.ts(self._last_offset)
                )
            await self._emit_orchestrator(
                "knowledge.appended",
                stage="intake",
                offset=self._mark("knowledge"),
                reason=self._reason("knowledge"),
                payload={"client_id": self.dataset.client_id, "entries": [entry.model_dump()]},
            )

    async def _plan_stage(self) -> None:
        await self._change_stage("plan", self._reason("plan_enter"), mark="plan_enter")
        result = await self.scenario.plan()
        self.plan = list(result.subtasks)
        await self._emit_orchestrator(
            "plan.created",
            stage="plan",
            offset=self._mark("plan"),
            reason=result.reason or self._reason("plan"),
            payload={"subtasks": [s.model_dump() for s in self.plan]},
            meter_key="plan",
        )
        for delta in result.meters:
            await self._meter("orchestrator", delta, "plan", self._after(0))

    def _work_subtasks(self) -> list[Subtask]:
        return self.scenario.work_subtasks(self.plan)

    async def _work_stage(self) -> None:
        await self._change_stage("work", self._reason("work_enter"), mark="work_enter")
        runs: dict[str, _TaskRun] = {s.task_id: _TaskRun(subtask=s) for s in self._work_subtasks()}
        for task_run in runs.values():
            await self._dispatch(task_run.subtask, mark="dispatch")
        await self._run_tasks(runs)
        if self.state.terminated:
            return
        await self._change_stage("assemble", self._reason("assemble_enter"), mark="assemble_enter")

    async def _dispatch(self, subtask: Subtask, mark: str | None, inputs: str | None = None) -> None:
        await self._gate()
        summary = (
            inputs
            or self.scenario.dispatch_summaries.get(subtask.task_id)
            or f"{subtask.title}; scope: {', '.join(subtask.scope) or 'brief'}"
        )
        await self._emit_orchestrator(
            "task.dispatched",
            stage="work",
            offset=self._mark(mark),
            reason=self._reason("dispatch"),
            payload={"task_id": subtask.task_id, "agent_id": subtask.agent_id, "inputs_summary": summary},
            meter_key=mark,
        )

    async def _run_tasks(self, runs: dict[str, _TaskRun]) -> None:
        async def one(task_run: _TaskRun) -> None:
            for dep in task_run.subtask.depends_on:
                if dep in runs:
                    await runs[dep].done.wait()
            if self.state.terminated or self._terminating:
                return
            await self._gate()
            await self._run_task_steps(task_run, self.scenario.task(task_run.subtask))
            task_run.done.set()

        tasks = [asyncio.create_task(one(r)) for r in runs.values()]
        try:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
            for task in pending:
                task.cancel()
            for task in done:
                exc = task.exception()
                if exc is not None:
                    raise exc
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()

    async def _run_task_steps(self, task_run: _TaskRun, steps: AsyncIterator[Emit]) -> None:
        async for emit in steps:
            event = await self._relay(emit, stage="work")
            if event.type == "task.completed":
                task_run.completed_event_id = event.event_id
            elif event.type == "blocker.raised":
                await self._handle_blocker(task_run, event)
                if self.state.terminated:
                    return

    async def _handle_blocker(self, task_run: _TaskRun, event: Event) -> None:
        payload = event.payload
        route_back = payload.get("route_back_to")
        needs_human = bool(payload["needs_human"])
        if route_back == "intake":
            if self.state.on_route_back_to_intake() == "allowed":
                await self._route_back_to_intake(task_run)
                return
            needs_human = True
        if not needs_human:
            await self._run_task_steps(task_run, self.scenario.blocker_continuation(task_run.subtask, ""))
            return
        blocker = {
            "blocker_id": payload["blocker_id"],
            "task_id": payload["task_id"],
            "agent_id": payload["agent_id"],
            "description": payload["description"],
        }
        self._pending_question_ids = []
        self._pending_blocker = blocker
        await self._emit_orchestrator(
            "clarification.asked",
            stage="work",
            offset=self._mark("blocker"),
            reason=self._reason("blocker"),
            payload={"question_ids": [], "blocker": blocker},
        )
        answers = await self._wait_for_human("blocker", mark="blocker_answer")
        answer = answers[0]
        answered = await self._emit_human(
            "clarification.answered",
            stage="work",
            payload={"question_id": blocker["blocker_id"], "answer": answer.answer, "action": answer.action},
            mark="blocker_answer",
        )
        if answer.action == "escalate":
            self.state.missing.append((blocker["description"], "escalated by the presenter", event.event_id))
            await self._terminate("blocker_escalated", self._reason("escalated"))
            return
        _ = answered
        await self._run_task_steps(
            task_run, self.scenario.blocker_continuation(task_run.subtask, answer.answer)
        )

    async def _route_back_to_intake(self, task_run: _TaskRun) -> None:
        await self._change_stage("intake", self._reason("route_back_intake"), mark="route_back_intake")
        await self._run_intake_steps()
        await self._change_stage("plan", self._reason("plan_enter"))
        await self._emit_orchestrator(
            "plan.created",
            stage="plan",
            offset=self._mark(None),
            reason=self._reason("plan"),
            payload={"subtasks": [s.model_dump() for s in self.plan]},
        )
        await self._change_stage("work", self._reason("work_enter"))
        await self._dispatch(
            task_run.subtask, mark=None, inputs="Re-dispatched after Intake completed the brief"
        )
        await self._run_task_steps(task_run, self.scenario.blocker_continuation(task_run.subtask, ""))

    async def _assemble_review_loop(self) -> None:
        version = 0
        review_round = 0
        findings_for_rework: list[dict[str, Any]] = []
        while True:
            version += 1
            await self._assemble(version, findings_for_rework)
            if self.state.terminated:
                return
            await self._change_stage("review", self._reason("review_enter"), mark=f"review_enter_{version}")
            verdict_event = await self._review(review_round)
            review_round += 1
            findings = verdict_event.payload["findings"]
            if verdict_event.payload["verdict"] == "pass":
                self.state.unresolved_findings = [f["id"] for f in findings if f["severity"] == "minor"]
                await self._handoff("reviewer_pass", verdict_event)
                return
            outcome = self.state.on_review_fail()
            if outcome == "retry_exhausted":
                self.state.unresolved_findings = [f["id"] for f in findings]
                await self._handoff("retry_exhausted", verdict_event)
                return
            await self._emit_orchestrator(
                "retry.incremented",
                stage="review",
                offset=self._mark("retry"),
                reason=self._reason("retry"),
                payload={"count": self.state.retries, "budget": self.state.retry_budget},
                meter_key="retry",
            )
            routed = [f for f in findings if f["severity"] != "minor" and f.get("route_to")]
            findings_for_rework = routed
            route_to = routed[0]["route_to"] if routed else "assemble"
            if route_to == "work":
                agent_id = routed[0].get("agent_id") or "estimator"
                await self._change_stage(
                    "work",
                    self._reason("route_back_work"),
                    mark="route_back",
                    target_reason=self._target_reason("route_back_work", self._reason("route_back_work")),
                )
                await self._rework(agent_id, self.state.retries, routed)
                if self.state.terminated:
                    return
                await self._change_stage(
                    "assemble", self._reason("assemble_enter"), mark="assemble_enter_rework"
                )
            else:
                await self._change_stage(
                    "assemble",
                    self._reason("route_back_assemble"),
                    mark="route_back",
                    target_reason=self._target_reason(
                        "route_back_assemble", self._reason("route_back_assemble")
                    ),
                )

    async def _rework(self, agent_id: str, count: int, findings: list[dict[str, Any]]) -> None:
        original = next((s for s in self.plan if s.agent_id == agent_id), None)
        if original is None:
            raise RuntimeError(f"no sub-task for {agent_id} to rework")
        subtask = Subtask(
            task_id=f"{original.task_id}-rework{count}",
            title=f"Rework: {original.title}",
            agent_id=agent_id,
            depends_on=[],
            scope=original.scope,
        )
        await self._dispatch(
            subtask,
            mark="rework_dispatch",
            inputs=self.scenario.dispatch_summaries.get(subtask.task_id)
            or "Reviewer finding and the original sub-task",
        )
        task_run = _TaskRun(subtask=subtask)
        await self._run_task_steps(task_run, self.scenario.rework(agent_id, subtask, findings))

    async def _assemble(self, version: int, findings: list[dict[str, Any]]) -> None:
        await self._gate()
        assemble_task = next((s for s in self.plan if s.agent_id == "writer"), None)
        if assemble_task is None:
            raise RuntimeError("the plan has no Assemble sub-task")
        await self._emit_orchestrator(
            "task.dispatched",
            stage="assemble",
            offset=self._mark(f"assemble_dispatch_{version}"),
            reason=self._reason("assemble_dispatch"),
            payload={
                "task_id": assemble_task.task_id if version == 1 else f"{assemble_task.task_id}-v{version}",
                "agent_id": "writer",
                "inputs_summary": f"Brief, specialist outputs, template, knowledge file; draft v{version}",
            },
        )
        async for emit in self.scenario.assemble(version, findings):
            event = await self._relay(emit, stage="assemble")
            if event.type == "draft.committed":
                self.state.draft_version = event.payload["version"]
                self.latest_draft = event
                await self._emit_system(
                    "artifact.compiled",
                    stage="assemble",
                    offset=self._after(500),
                    payload={"version": event.payload["version"], "pdf_path": None, "page_images": []},
                )

    async def _review(self, review_round: int) -> Event:
        verdict: Event | None = None
        async for emit in self.scenario.review(review_round, self.latest_draft):
            event = await self._relay(emit, stage="review")
            if event.type == "review.verdict":
                verdict = event
        if verdict is None:
            raise RuntimeError("the Reviewer produced no verdict")
        return verdict

    async def _handoff(
        self, exit_value: Literal["reviewer_pass", "retry_exhausted"], verdict_event: Event
    ) -> None:
        reason = self._reason("handoff_enter" if exit_value == "reviewer_pass" else "handoff_exhausted")
        await self._change_stage("handoff", reason, mark="handoff_enter")
        package = {
            "pdf_path": None,
            "page_images": [],
            "verdict_event_id": verdict_event.event_id,
            "unresolved_findings": list(self.state.unresolved_findings),
            "assumptions": list(self.state.assumptions),
            "clarifications": [{"question_id": k, "answer": v} for k, v in self.state.clarifications.items()],
            "event_log_path": self.event_log_path,
        }
        await self._emit_orchestrator(
            "handoff.ready",
            stage="handoff",
            offset=self._mark("handoff"),
            reason=self._reason("handoff"),
            payload={"exit_determination": exit_value, "package": package},
            meter_key="handoff",
        )
        self.state.pending_human = "handoff"
        self.human_needed.set()
        await self._human_gate.wait()
        self._human_gate.clear()
        self.human_needed.clear()
        self.state.pending_human = None
        if self._terminating or self.state.stopped:
            raise RunStopped()
        decision, notes = self._decision or ("approve", "")
        await self._emit_human(
            "human.approved", stage="handoff", payload={"decision": decision, "notes": notes}, mark="approve"
        )
        if decision == "reject":
            closing = "terminated_rejected"
        elif exit_value == "reviewer_pass":
            closing = "terminated_pass"
        else:
            closing = "terminated_exhausted"
        await self._terminate(exit_value, self._reason(closing), human_decision=decision)

    # Human gate

    async def _wait_for_human(self, kind: Literal["clarifications", "blocker"], mark: str) -> list[Answer]:
        self.state.pending_human = kind
        self.human_needed.set()
        await self._human_gate.wait()
        self._human_gate.clear()
        self.human_needed.clear()
        self.state.pending_human = None
        if self._terminating or self.state.stopped:
            raise RunStopped()
        answers = list(self._answers)
        self._answers = []
        if self.scenario.timing == "wall":
            return answers
        # If the human took longer than the fixture allowed, shift every later offset.
        expected = self._mark(mark)
        actual = max(expected, self.clock.elapsed_offset_ms())
        if actual > expected:
            self._shift_ms += actual - expected
        return answers

    # Emission

    async def _gate(self) -> None:
        if self._terminating or self.state.stopped:
            raise RunStopped()
        await self._pause_gate.wait()
        if self._terminating or self.state.stopped:
            raise RunStopped()

    def _names(self) -> dict[str, str]:
        return {seat: agent.name for seat, agent in self.roster.items()}

    def _reason(self, key: str) -> str:
        text = self.scenario.reasons.get(key) or DEFAULT_REASONS[key]
        return text.format_map(self._names())

    def _target_reason(self, key: str, fallback: str) -> str:
        text = self.scenario.target_reasons.get(key)
        return text.format_map(self._names()) if text else fallback

    def _after(self, fixture_ms: int) -> int:
        """Offset shortly after the last event: fixture spacing for stubs, the wall clock for live runs."""
        if self.scenario.timing == "wall":
            return max(self._last_offset, self.clock.elapsed_offset_ms())
        return self._last_offset + fixture_ms

    def _known_answers(self) -> dict[str, str]:
        """Answers already in the client knowledge file (ask once). Live runs only."""
        if self.knowledge_store is None:
            return {}
        return self.knowledge_store.answers(self.dataset.client_id)

    def _mark(self, key: str | None) -> int:
        """Offset for an Orchestrator-owned moment: the scenario mark if given, else one second on."""
        if self.scenario.timing == "wall":
            return max(self._last_offset, self.clock.elapsed_offset_ms())
        if key is not None:
            value = self.scenario.marks.get(key)
            if value is not None:
                return value + self._shift_ms
        return self._last_offset + 1000

    async def _relay(self, emit: Emit, stage: Stage) -> Event:
        """Relay one stub emission as a validated agent event, then its meter delta."""
        if self._terminating or self.state.stopped:
            raise RunStopped()
        actor = self.roster[emit.seat]
        offset = emit.offset_ms + self._shift_ms if self.scenario.timing == "fixture" else self._mark(None)
        await self.clock.wait_for(offset)
        prompt_ref = emit.bundle.prompt_ref if emit.bundle else None
        if emit.bundle is not None:
            self.bundles[emit.bundle.prompt_ref] = emit.bundle
            if self.recorder is not None:
                self.recorder.save_bundle(emit.bundle)
        payload = self._resolve(emit.payload)
        event = await self._emit(
            type=emit.type, stage=stage, offset=offset, actor=actor, payload=payload, prompt_ref=prompt_ref
        )
        if emit.type == "task.completed":
            self._task_event_ids[str(payload.get("task_id"))] = event.event_id
        for delta in emit.all_meters():
            await self._meter(emit.seat, delta, stage, offset)
        return event

    def _resolve(self, value: Any) -> Any:
        """Replace "$event:<task_id>" placeholders with the task's completed event id."""
        if isinstance(value, str) and value.startswith("$event:"):
            return self._task_event_ids.get(value[7:], value)
        if isinstance(value, dict):
            return {k: self._resolve(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._resolve(v) for v in value]
        return value

    async def _meter(
        self, seat: str, delta: MeterDelta, stage: Stage | None, offset: int, check_ceiling: bool = True
    ) -> None:
        self._call_counter += 1
        outcome = self.state.on_meter(seat, delta.tokens_in, delta.tokens_out, delta.est_cost)
        await self._emit_system(
            "meter.update",
            stage=stage,
            offset=offset,
            payload={
                "agent_id": seat,
                "call_id": f"call-{self._call_counter:03d}",
                "tokens_in": delta.tokens_in,
                "tokens_out": delta.tokens_out,
                "wall_ms": delta.wall_ms,
                "est_cost": delta.est_cost,
            },
        )
        if outcome == "cost_ceiling" and check_ceiling:
            self._terminating = True
            raise CostCeilingBreached()

    async def _emit_orchestrator(
        self,
        type: str,
        *,
        stage: Stage | None,
        offset: int,
        reason: str,
        payload: dict[str, Any],
        meter_key: str | None = None,
    ) -> Event:
        await self.clock.wait_for(offset)
        event = await self._emit(
            type=type, stage=stage, offset=offset, actor=self.orchestrator, payload=payload, reason=reason
        )
        delta = self.scenario.orchestrator_meters.get(meter_key) if meter_key else None
        if delta is not None:
            await self._meter("orchestrator", delta, stage, self._last_offset)
        return event

    async def _emit_system(
        self, type: str, *, stage: Stage | None, offset: int, payload: dict[str, Any]
    ) -> Event:
        return await self._emit(type=type, stage=stage, offset=offset, actor="system", payload=payload)

    async def _emit_human(
        self, type: str, *, stage: Stage | None, payload: dict[str, Any], mark: str
    ) -> Event:
        offset = max(self._mark(mark), self._last_offset, self.clock.elapsed_offset_ms())
        return await self._emit(type=type, stage=stage, offset=offset, actor="human", payload=payload)

    async def _emit(
        self,
        *,
        type: str,
        stage: Stage | None,
        offset: int,
        actor: Agent | Literal["human", "system"],
        payload: dict[str, Any],
        reason: str | None = None,
        prompt_ref: str | None = None,
    ) -> Event:
        async with self._lock:
            if self.state.terminated:
                raise RuntimeError(f"cannot emit {type} after run.terminated")
            offset = max(offset, self._last_offset)
            self._last_offset = offset
            seq = len(self.events) + 1
            event = Event(
                event_id=self._id_factory(seq),
                run_id=self.run_id,
                seq=seq,
                ts=self.clock.ts(offset),
                type=type,
                stage=stage,
                actor=actor,
                reason=reason,
                prompt_ref=prompt_ref,
                payload=payload,
            )
            self.events.append(event)
            if self.recorder is not None:
                self.recorder.append(event)
            self.bus.publish(self.run_id, event.model_dump(mode="json", by_alias=True))
            return event

    async def _terminate(self, exit_value: Exit, reason: str, human_decision: str | None = None) -> None:
        self._terminating = True
        headline = self._headline(exit_value)
        if exit_value in ("reviewer_pass", "retry_exhausted"):
            try:
                proposed = await self.scenario.headline(exit_value, headline)
            except Exception:  # noqa: BLE001
                proposed = None
            if proposed is not None:
                for delta in proposed.meters:
                    await self._meter("orchestrator", delta, None, self._after(0), check_ceiling=False)
                if proposed.headline:
                    headline = proposed.headline
        if exit_value in ("stopped", "cost_ceiling"):
            # Control exits end now, not at the fixture's scripted end.
            offset = max(self._last_offset, self.clock.elapsed_offset_ms())
        else:
            offset = self._mark("end")
        summary = {
            "headline": headline,
            "missing": [
                {"item": item, "note": note, "source_event_id": source}
                for item, note, source in self.state.missing
            ],
            "unresolved_findings": list(self.state.unresolved_findings),
            "retries": {"count": self.state.retries, "budget": self.state.retry_budget},
            "readiness_verdict": self.state.readiness_verdict
            if exit_value in ("not_ready", "dry_intake")
            else None,
            "event_count": len(self.events) + 1,
            "elapsed_ms": max(offset, self._last_offset),
            "est_cost": round(self.state.est_cost, 4),
            "human_decision": human_decision,
        }
        await self.clock.wait_for(offset)
        await self._emit(
            type="run.terminated",
            stage=None,
            offset=offset,
            actor=self.orchestrator,
            payload={"exit": exit_value, "summary": summary},
            reason=reason,
        )
        self.state.terminate(exit_value)
        if self.recorder is not None:
            self.recorder.finish(exit_value, self.clock.ts(self._last_offset))

    def _headline(self, exit_value: Exit) -> str:
        if exit_value == "reviewer_pass":
            return (
                self.scenario.headline_pass_first
                if self.state.retries == 0
                else self.scenario.headline_pass_rework
            )
        if exit_value == "retry_exhausted":
            return "The retry budget ran out with findings unresolved."
        if exit_value == "blocker_escalated":
            return "A blocker was escalated: the run cannot continue without what is missing."
        if exit_value == "not_ready":
            count = len(self.state.missing)
            return f"Intake found the request not ready: {count} item{'s' if count != 1 else ''} missing."
        if exit_value == "dry_intake":
            verdict = (self.state.readiness_verdict or "ready").replace("_", " ")
            return f"Dry intake complete: verdict {verdict}."
        if exit_value == "cost_ceiling":
            return f"The cost ceiling of ${self.state.cost_ceiling:.2f} was reached."
        if exit_value == "stopped":
            return "The run was stopped."
        return "The Single-model run completed."
