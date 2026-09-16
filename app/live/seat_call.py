"""One seat call: a fresh Strands Agent, invoked once, observed while it runs (research D1, D3).

While the agent works, hooks turn each finished model call into a usage record and the text it
wrote before calling tools into progress lines, and each tool call into a tool record. The
final reply is validated against the seat's shape; one retry carries the validation error. A
provider failure is retried once on a fresh agent. Error reasons are written here and never
include provider exception text, which could carry credentials or request details.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel
from strands import Agent
from strands.hooks import AfterModelCallEvent, AfterToolCallEvent, HookProvider, HookRegistry
from strands.models import Model as StrandsModel
from strands.tools.executors import SequentialToolExecutor
from strands.types.exceptions import MaxTokensReachedException

from app.agents.base import MeterDelta
from app.agents.source import AgentFailure
from app.live.replies import ReplyError, extract_json, without_em_dashes
from app.live.strands_tools import ToolLog
from app.schema.bundles import PromptBundle
from app.schema.events import Model

MAX_PROGRESS_CHARS = 200


@dataclass(frozen=True)
class ToolRecord:
    name: str
    args_summary: str
    result_summary: str
    duration_ms: int
    ok: bool


@dataclass(frozen=True)
class CallItem:
    kind: Literal["progress", "tool", "usage", "reply"]
    text: str = ""
    tool: ToolRecord | None = None
    usage: MeterDelta | None = None
    reply: BaseModel | None = None


@dataclass(frozen=True)
class SeatModel:
    """The Strands model for a seat plus the facts the events need about it."""

    strands_model: StrandsModel
    model: Model
    price_in: float
    price_out: float


def estimated_cost(tokens_in: int, tokens_out: int, price_in: float, price_out: float) -> float:
    return round(tokens_in / 1_000_000 * price_in + tokens_out / 1_000_000 * price_out, 6)


class _Observer(HookProvider):
    def __init__(self, queue: asyncio.Queue[CallItem], seat_model: SeatModel, log: ToolLog) -> None:
        self.queue = queue
        self.seat_model = seat_model
        self.log = log

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(AfterModelCallEvent, self._after_model)
        registry.add_callback(AfterToolCallEvent, self._after_tool)

    def _after_model(self, event: AfterModelCallEvent) -> None:
        response = event.stop_response
        if response is None:
            return
        message = response.message
        metadata: dict[str, Any] = dict(message.get("metadata") or {})
        usage: dict[str, Any] = dict(metadata.get("usage") or {})
        metrics: dict[str, Any] = dict(metadata.get("metrics") or {})
        tokens_in = int(usage.get("inputTokens", 0))
        tokens_out = int(usage.get("outputTokens", 0))
        blocks = message.get("content") or []
        if any("toolUse" in block for block in blocks):
            for block in blocks:
                for line in str(block.get("text", "")).splitlines():
                    line = line.strip()
                    if line:
                        self.queue.put_nowait(
                            CallItem("progress", text=without_em_dashes(line)[:MAX_PROGRESS_CHARS])
                        )
        self.queue.put_nowait(
            CallItem(
                "usage",
                usage=MeterDelta(
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    wall_ms=int(metrics.get("latencyMs", 0)),
                    est_cost=estimated_cost(
                        tokens_in, tokens_out, self.seat_model.price_in, self.seat_model.price_out
                    ),
                ),
            )
        )

    def _after_tool(self, event: AfterToolCallEvent) -> None:
        tool_use = event.tool_use
        use_id = str(tool_use.get("toolUseId"))
        args_summary, result_summary = self.log.summaries.get(use_id, ("", ""))
        ok = event.exception is None and event.result.get("status") == "success"
        if not ok and not result_summary:
            result_summary = "the tool reported an error"
        if not args_summary:
            args_summary = ", ".join(sorted(str(k) for k in (tool_use.get("input") or {})))[:200]
        self.queue.put_nowait(
            CallItem(
                "tool",
                tool=ToolRecord(
                    name=str(tool_use.get("name")),
                    args_summary=args_summary or "no arguments",
                    result_summary=result_summary,
                    duration_ms=int(round((event.duration or 0.0) * 1000)),
                    ok=ok,
                ),
            )
        )


def compose_prompt(task: str, context_text: str) -> str:
    return f"## Task\n{task.strip()}\n\n{context_text.strip()}\n"


def _tool_call_written_as_text(text: str, tool_names: set[str]) -> str | None:
    """Small models sometimes print a tool call as JSON instead of making it. Returns the tool's name."""
    try:
        data = extract_json(text)
    except ReplyError:
        return None
    name = data.get("name") or data.get("tool") or data.get("function")
    if (
        isinstance(name, str)
        and name in tool_names
        and ("parameters" in data or "arguments" in data or "input" in data)
    ):
        return name
    return None


Requirement = Callable[[BaseModel, list[str]], str | None]
"""Given a parsed reply and the tools used so far, a sentence saying what is missing, or None."""


class SeatCall:
    def __init__(
        self,
        *,
        agent_id: str,
        role: str,
        instructions: str,
        seat_model: SeatModel,
        tools: list[Any],
        log: ToolLog,
        bundle: PromptBundle,
        parse: Callable[[str], BaseModel],
        requirement: Requirement | None = None,
        on_attempt: Callable[[int, bool, str, str], None] | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.role = role
        self.instructions = instructions
        self.seat_model = seat_model
        self.tools = tools
        self.log = log
        self.bundle = bundle
        self.parse = parse
        self.requirement = requirement
        self.on_attempt = on_attempt
        self.tools_used: list[str] = []
        self.tool_names = {str(getattr(t, "tool_name", getattr(t, "__name__", ""))) for t in tools}

    def _attempt(self, attempt: int, accepted: bool, text: str, error: str = "") -> None:
        """Record how this attempt went. Diagnostics never stop a run."""
        if self.on_attempt is not None:
            try:
                self.on_attempt(attempt, accepted, text, error)
            except OSError:
                pass

    def _accept(self, text: str) -> BaseModel:
        """Parse the reply and apply the seat's requirement on how it was produced. Raises ReplyError."""
        try:
            reply = self.parse(text)
        except ReplyError as error:
            written = _tool_call_written_as_text(text, self.tool_names)
            if written:
                raise ReplyError(
                    f"you wrote a call to {written} as text instead of calling the tool. Call {written} as a tool, "
                    "wait for its result, then reply with the required JSON object"
                ) from error
            raise
        if self.requirement is not None:
            unmet = self.requirement(reply, self.tools_used)
            if unmet:
                raise ReplyError(unmet)
        return reply

    def _agent(self, queue: asyncio.Queue[CallItem]) -> Agent:
        return Agent(
            model=self.seat_model.strands_model,
            system_prompt=self.instructions,
            tools=self.tools,
            hooks=[_Observer(queue, self.seat_model, self.log)],
            callback_handler=None,
            name=self.agent_id,
            tool_executor=SequentialToolExecutor(),
            retry_strategy=None,
        )

    async def _invoke(
        self, agent: Agent, prompt: str, queue: asyncio.Queue[CallItem]
    ) -> AsyncIterator[CallItem | str]:
        task: asyncio.Task[Any] = asyncio.create_task(agent.invoke_async(prompt))
        try:
            while True:
                getter: asyncio.Task[CallItem] = asyncio.create_task(queue.get())
                done, _ = await asyncio.wait({task, getter}, return_when=asyncio.FIRST_COMPLETED)
                if getter in done:
                    yield getter.result()
                else:
                    getter.cancel()
                if task in done:
                    while not queue.empty():
                        yield queue.get_nowait()
                    break
            yield str(task.result())
        finally:
            if not task.done():
                task.cancel()

    async def run(self) -> AsyncIterator[CallItem]:
        prompt = compose_prompt(self.bundle.task, self.bundle.context_slice)
        label = self.seat_model.model.label
        for attempt in (1, 2):
            queue: asyncio.Queue[CallItem] = asyncio.Queue()
            agent = self._agent(queue)
            try:
                text = ""
                async for item in self._invoke(agent, prompt, queue):
                    if isinstance(item, str):
                        text = item
                    else:
                        if item.kind == "tool" and item.tool is not None:
                            self.tools_used.append(item.tool.name)
                        yield item
            except AgentFailure:
                raise
            except MaxTokensReachedException:
                # Retrying would repeat the whole call, tool reads included, and stop at the same limit.
                raise AgentFailure(
                    f"The {self.role} on {label} reached its output limit before finishing the reply, so the run stops."
                ) from None
            except Exception as error:  # noqa: BLE001
                if attempt == 2:
                    raise AgentFailure(
                        f"The {self.role} could not reach {label} after a retry ({type(error).__name__}), so the run stops."
                    ) from None
                continue
            try:
                reply = self._accept(text)
                self._attempt(1, True, text)
                yield CallItem("reply", reply=reply)
                return
            except ReplyError as first_error:
                self._attempt(1, False, text, str(first_error))
                correction = (
                    "Your reply was not accepted: "
                    f"{first_error}. Fix this, using your tools if needed, then reply again with only the corrected JSON object."
                )
                text = ""
                try:
                    async for item in self._invoke(agent, correction, queue):
                        if isinstance(item, str):
                            text = item
                        else:
                            if item.kind == "tool" and item.tool is not None:
                                self.tools_used.append(item.tool.name)
                            yield item
                except Exception:  # noqa: BLE001
                    raise AgentFailure(
                        f"The {self.role} on {label} failed while correcting its reply, so the run stops."
                    ) from None
                try:
                    reply = self._accept(text)
                    self._attempt(2, True, text)
                    yield CallItem("reply", reply=reply)
                    return
                except ReplyError as second_error:
                    self._attempt(2, False, text, str(second_error))
                    raise AgentFailure(
                        f"The {self.role} on {label} returned an invalid reply twice, so the run stops.",
                        invalid_reply=True,
                    ) from None
        raise AgentFailure(f"The {self.role} on {label} produced no reply, so the run stops.")
