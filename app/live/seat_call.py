"""One seat call: a fresh Strands Agent, invoked once, observed while it runs (research D1, D3).

While the agent works, hooks turn each finished model call into a usage record and the text it
wrote before calling tools into progress lines, and each tool call into a tool record. The
final reply is validated against the seat's shape; one retry carries the validation error. A
provider failure is retried once on a fresh agent. Error reasons are written here and never
include provider exception text, which could carry credentials or request details.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel
from strands import Agent
from strands.hooks import (
    AfterModelCallEvent,
    AfterToolCallEvent,
    BeforeModelCallEvent,
    HookProvider,
    HookRegistry,
)
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
    image_input: bool = False
    """Whether the model takes image content; the Reviewer needs it for the compiled pages (S4)."""
    settings: dict[str, Any] = field(default_factory=dict)
    """The hyperparameters this seat ran with, as resolved from the registry: temperature, num_ctx, think,
    max_tokens. Written into every attempt line so a run records what it used, not what the config says today."""


def estimated_cost(tokens_in: int, tokens_out: int, price_in: float, price_out: float) -> float:
    return round(tokens_in / 1_000_000 * price_in + tokens_out / 1_000_000 * price_out, 6)


# What the feed says while a seat works, written from the tool call rather than asked of the model.
PROGRESS_WORDS: dict[str, tuple[str, str]] = {
    "vision_read_drawing": ("Reading sheet", "sheet"),
    "document_parse_pdf": ("Reading", "file"),
    "document_extract_attachments": ("Listing what the request came with", ""),
    "quantity_calculate": ("Totalling the takeoff", "items"),
    "price_list_lookup": ("Pricing the bill of materials", "items"),
    "template_render": ("Filling the response template", ""),
    "compile_trigger": ("Committing the draft", "version"),
}


def progress_for(tool: str, arguments: dict[str, Any]) -> str:
    """One line for the feed, from a tool call. Names the thing when the call names one."""
    words = PROGRESS_WORDS.get(tool)
    if words is None:
        return tool.replace("_", " ").capitalize()
    phrase, key = words
    value = arguments.get(key)
    if isinstance(value, list):
        return f"{phrase}, {len(value)} lines"
    if value in (None, ""):
        return phrase
    return f"{phrase} {value}"


class _Observer(HookProvider):
    def __init__(self, queue: asyncio.Queue[CallItem], seat_model: SeatModel, log: ToolLog) -> None:
        self.queue = queue
        self.seat_model = seat_model
        self.log = log
        self._call_started: float | None = None

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeModelCallEvent, self._before_model)
        registry.add_callback(AfterModelCallEvent, self._after_model)
        registry.add_callback(AfterToolCallEvent, self._after_tool)

    def _before_model(self, event: BeforeModelCallEvent) -> None:
        self._call_started = time.monotonic()

    def _after_model(self, event: AfterModelCallEvent) -> None:
        response = event.stop_response
        # wall_ms is measured here; latency_ms is what the provider reports (schema 1.1.0).
        started, self._call_started = self._call_started, None
        wall_ms = int(round((time.monotonic() - started) * 1000)) if started is not None else 0
        if response is None:
            return
        message = response.message
        metadata: dict[str, Any] = dict(message.get("metadata") or {})
        usage: dict[str, Any] = dict(metadata.get("usage") or {})
        metrics: dict[str, Any] = dict(metadata.get("metrics") or {})
        tokens_in = int(usage.get("inputTokens", 0))
        tokens_out = int(usage.get("outputTokens", 0))
        blocks = message.get("content") or []
        uses = [block["toolUse"] for block in blocks if "toolUse" in block]
        if uses:
            said = False
            for block in blocks:
                for line in str(block.get("text", "")).splitlines():
                    line = line.strip()
                    if line:
                        said = True
                        self.queue.put_nowait(
                            CallItem("progress", text=without_em_dashes(line)[:MAX_PROGRESS_CHARS])
                        )
            if not said:
                # The seats were asked to narrate before every tool call, and the failure that follows is
                # a seat treating that line as its whole reply: the largest single failure on the team.
                # The engine knows what is being called and on what, so it writes the line instead and the
                # instruction leaves the prompts (spec 010).
                for use in uses:
                    line = progress_for(str(use.get("name", "")), dict(use.get("input") or {}))
                    if line:
                        self.queue.put_nowait(CallItem("progress", text=line[:MAX_PROGRESS_CHARS]))
        self.queue.put_nowait(
            CallItem(
                "usage",
                usage=MeterDelta(
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    wall_ms=wall_ms,
                    latency_ms=int(metrics.get("latencyMs", 0)),
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
        images: list[bytes] | None = None,
        corrections: int = 1,
    ) -> None:
        self.corrections = max(0, corrections)
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
        self.images = list(images or [])
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

    def _force_json(self, agent: Agent, on: bool) -> None:
        """Make the provider require JSON of the next reply, for a correction only (spec 010).

        Ollama takes a `format` field that constrains the reply, and our provider passes extra request
        fields straight through. Setting it for the whole call is unsafe: with tools offered and a format
        set, the model stops calling them and answers from nothing. A probe on 2026-09-18 asked for a
        sheet to be read and got an invented headline about a sheet never opened.

        On a correction the tool results are already in the conversation, so nothing is skipped by
        requiring the shape: the seat has done the work and is being asked to hand it over properly. That
        is where narration costs us, so that is the only place this is turned on.
        """
        model = getattr(agent, "model", None)
        if model is None or not hasattr(model, "update_config") or not hasattr(model, "get_config"):
            return
        config = dict(model.get_config() or {})
        extra = dict(config.get("additional_args") or {})
        if "format" in extra and not on:
            extra.pop("format")
        elif on:
            extra["format"] = "json"
        else:
            return
        try:
            model.update_config(additional_args=extra)
        except Exception:  # noqa: BLE001
            pass  # a provider that will not take it keeps its own behaviour

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

    def _first_message(self, prompt: str) -> Any:
        """The prompt text, plus one image block per page when the call carries pages (S4)."""
        if not self.images:
            return prompt
        blocks: list[dict[str, Any]] = [{"text": prompt}]
        for png in self.images:
            blocks.append({"image": {"format": "png", "source": {"bytes": png}}})
        return blocks

    async def _invoke(
        self, agent: Agent, prompt: Any, queue: asyncio.Queue[CallItem]
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
                async for item in self._invoke(agent, self._first_message(prompt), queue):
                    if isinstance(item, str):
                        text = item
                    else:
                        if item.kind == "tool" and item.tool is not None and item.tool.ok:
                            self.tools_used.append(item.tool.name)
                        yield item
            except AgentFailure:
                raise
            except MaxTokensReachedException:
                # Retrying would repeat the whole call, tool reads included, and stop at the same limit.
                self._attempt(attempt, False, "", "the reply hit the model's output limit")
                raise AgentFailure(
                    f"The {self.role} on {label} reached its output limit before finishing the reply, so the run stops."
                ) from None
            except Exception as error:  # noqa: BLE001
                self._attempt(attempt, False, "", f"the model could not be reached: {type(error).__name__}")
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
                last_error: ReplyError = first_error
                # Each correction stays on the same agent, so tool results already read are kept. Most seats
                # get one correction; a seat doing the whole job alone gets more (S5, the Single-model actor).
                for number in range(2, self.corrections + 2):
                    correction = (
                        "Your reply was not accepted: "
                        f"{last_error}. Fix this, using your tools if needed, then reply again with only the corrected JSON object."
                    )
                    text = ""
                    self._force_json(agent, True)
                    try:
                        async for item in self._invoke(agent, correction, queue):
                            if isinstance(item, str):
                                text = item
                            else:
                                if item.kind == "tool" and item.tool is not None and item.tool.ok:
                                    self.tools_used.append(item.tool.name)
                                yield item
                    except Exception:  # noqa: BLE001
                        raise AgentFailure(
                            f"The {self.role} on {label} failed while correcting its reply, so the run stops."
                        ) from None
                    finally:
                        self._force_json(agent, False)
                    try:
                        reply = self._accept(text)
                        self._attempt(number, True, text)
                        yield CallItem("reply", reply=reply)
                        return
                    except ReplyError as next_error:
                        self._attempt(number, False, text, str(next_error))
                        last_error = next_error
                times = "twice" if self.corrections == 1 else f"{self.corrections + 1} times"
                raise AgentFailure(
                    f"The {self.role} on {label} returned an invalid reply {times}, so the run stops.",
                    invalid_reply=True,
                ) from None
        raise AgentFailure(f"The {self.role} on {label} produced no reply, so the run stops.")
