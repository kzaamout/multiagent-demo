"""A scripted Strands model for tests (research D11). Test double only; never a selectable model.

Each call to `stream` plays the next turn. A turn is a list of blocks, `{"text": ...}` or
`{"tool": name, "input": {...}}`, or a function of the prompt text returning such a list, or an
exception instance to raise. Usage is reported per call so meters can be checked.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

from strands.models import Model

Block = dict[str, Any]


class Hang:
    """A turn that never returns, standing in for a long provider call with no output."""


HANG = Hang()


class WaitFor:
    """A turn that waits for a test to release it, then plays its blocks."""

    def __init__(self, release: asyncio.Event, blocks: list[Block]) -> None:
        self.release = release
        self.blocks = blocks


Turn = list[Block] | Callable[[str], list[Block]] | BaseException | Hang | WaitFor


def _prompt_text(messages: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for message in messages:
        for block in message.get("content", []):
            if "text" in block:
                parts.append(str(block["text"]))
    return "\n".join(parts)


class ScriptedModel(Model):
    def __init__(self, turns: list[Turn], tokens_in: int = 1200, tokens_out: int = 300) -> None:
        self.turns = list(turns)
        self.calls = 0
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.config: dict[str, Any] = {"model_id": "scripted"}
        self.prompts: list[str] = []
        self.messages: list[Any] = []
        """The raw message lists of every call, so a test can check image blocks as well as text."""

    def update_config(self, **model_config: Any) -> None:
        self.config.update(model_config)

    def get_config(self) -> Any:
        return self.config

    async def structured_output(  # type: ignore[override]
        self, output_model: Any, prompt: Any, system_prompt: str | None = None, **kwargs: Any
    ) -> AsyncIterator[dict[str, Any]]:
        raise NotImplementedError("the application validates JSON replies itself")
        yield {}  # pragma: no cover

    async def stream(  # type: ignore[override]
        self,
        messages: Any,
        tool_specs: Any = None,
        system_prompt: str | None = None,
        *,
        tool_choice: Any = None,
        system_prompt_content: Any = None,
        invocation_state: Any = None,
        cancel_signal: Any = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        if not self.turns:
            raise AssertionError(f"scripted model ran out of turns after {self.calls} calls")
        turn = self.turns.pop(0)
        self.calls += 1
        text = _prompt_text(messages)
        self.prompts.append(text)
        self.messages.append(messages)
        if isinstance(turn, BaseException):
            raise turn
        if isinstance(turn, Hang):
            await asyncio.Event().wait()
            return
        if isinstance(turn, WaitFor):
            await turn.release.wait()
            blocks = turn.blocks
        else:
            blocks = turn(text) if callable(turn) else turn
        stop = "end_turn"
        yield {"messageStart": {"role": "assistant"}}
        for index, block in enumerate(blocks):
            if "text" in block:
                yield {"contentBlockStart": {"start": {}}}
                yield {"contentBlockDelta": {"delta": {"text": str(block["text"])}}}
                yield {"contentBlockStop": {}}
            else:
                stop = "tool_use"
                use_id = f"tu-{self.calls}-{index}"
                yield {
                    "contentBlockStart": {"start": {"toolUse": {"name": block["tool"], "toolUseId": use_id}}}
                }
                yield {
                    "contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(block.get("input", {}))}}}
                }
                yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": stop}}
        yield {
            "metadata": {
                "usage": {
                    "inputTokens": self.tokens_in,
                    "outputTokens": self.tokens_out,
                    "totalTokens": self.tokens_in + self.tokens_out,
                },
                "metrics": {"latencyMs": 40},
            }
        }


def reply(data: dict[str, Any]) -> list[Block]:
    return [{"text": json.dumps(data)}]
