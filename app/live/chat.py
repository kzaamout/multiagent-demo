"""Chat with an agent, out of band (S5, spec 2.7, research D7).

A chat answers from the seat's instructions and the context of its last call in the run, on the seat's
current model, with no tools. It is not an event, is not recorded, is not replayed, and never touches the
run: the caller digests the run folder before and after in the test that guards this. The panel keeps the
conversation; the server keeps nothing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from app.agents.stubs import bundle_for
from app.live.seat_call import SeatModel, estimated_cost
from app.schema.bundles import PromptBundle
from app.schema.events import Agent, Event, Model

if TYPE_CHECKING:
    from strands.types.content import Message

    from app.runs.registry import Registry

READ_ONLY_LINE = (
    "You are now answering the presenter's questions about the run that just happened. This conversation "
    "is read-only: you cannot change instructions, state, or outputs, and you have no tools. Answer from "
    "your instructions above and the context of your last call, below. Plain English, no em dashes."
)
MAX_HISTORY = 20


class ChatRefused(Exception):
    """The chat cannot happen: wrong run state, unknown seat, or no bundle. `status` is the HTTP code."""

    def __init__(self, status: int, reason: str) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason


@dataclass(frozen=True)
class ChatReply:
    text: str
    model: Model
    tokens_in: int
    tokens_out: int
    est_cost: float
    latency_ms: int


def events_for_run(registry: Registry, run_id: str) -> list[Event] | None:
    """The run's events: live or finished in memory, a recording on disk, or a golden log by run id."""
    live = registry.get_run(run_id)
    if live is not None:
        return list(live.events)
    recorded = registry.read_recording(run_id)
    if recorded is not None:
        return recorded
    for info in registry.datasets.values():
        if not info.golden_path.exists():
            continue
        first = info.golden_path.read_text(encoding="utf-8").splitlines()[0]
        if Event.from_line(first).run_id == run_id:
            from app.runs.recorder import read_events

            return read_events(info.golden_path)
    return None


def chat_allowed(registry: Registry, run_id: str) -> bool:
    """Paused, terminated, or not in memory at all (a recording or a golden replay)."""
    live = registry.get_run(run_id)
    if live is None:
        return True
    return bool(live.state.terminated or live.state.paused or live.state.pending_human)


def find_bundle(registry: Registry, run_id: str, agent_id: str) -> tuple[PromptBundle, Agent] | None:
    """The prompt bundle of the seat's last call in the run, and the seat's card as recorded, or None."""
    events = events_for_run(registry, run_id)
    if not events:
        return None
    last = next(
        (
            e
            for e in reversed(events)
            if isinstance(e.actor, Agent) and e.actor.agent_id == agent_id and e.prompt_ref
        ),
        None,
    )
    if last is None or not last.prompt_ref:
        return None
    ref = last.prompt_ref
    live = registry.get_run(run_id)
    bundle: PromptBundle | None = live.bundles.get(ref) if live is not None else None
    if bundle is None:
        path = registry.settings.runs_dir / run_id / "prompts" / f"{ref}.json"
        if path.exists():
            bundle = PromptBundle.model_validate_json(path.read_text(encoding="utf-8"))
    if bundle is None:
        bundle = bundle_for(ref)
    if bundle is None:
        return None
    assert isinstance(last.actor, Agent)
    return bundle, last.actor


def system_prompt_for(bundle: PromptBundle) -> str:
    return f"{bundle.system}\n\n{READ_ONLY_LINE}\n\nContext of your last call:\n{bundle.context_slice}"


def _history(messages: list[dict[str, str]]) -> list[Message]:
    return cast(
        "list[Message]",
        [
            {
                "role": "assistant" if m.get("role") == "assistant" else "user",
                "content": [{"text": str(m.get("text", ""))}],
            }
            for m in messages[-MAX_HISTORY:]
        ],
    )


async def chat(seat_model: SeatModel, bundle: PromptBundle, messages: list[dict[str, str]]) -> ChatReply:
    """One reply from a fresh agent with no tools. Raises ChatRefused(502) with a one-line reason on failure."""
    if (
        not messages
        or messages[-1].get("role") == "assistant"
        or not str(messages[-1].get("text", "")).strip()
    ):
        raise ChatRefused(400, "the last message must be a question from the presenter")
    from strands import Agent as StrandsAgent

    history = _history(messages[:-1])
    question = str(messages[-1]["text"])
    agent = StrandsAgent(
        model=seat_model.strands_model,
        system_prompt=system_prompt_for(bundle),
        messages=history,
        tools=[],
        callback_handler=None,
        name=f"chat-{bundle.prompt_ref}",
        retry_strategy=None,
    )
    started = time.monotonic()
    try:
        result = await agent.invoke_async(question)
    except Exception as error:  # noqa: BLE001
        raise ChatRefused(502, f"The model could not be reached ({type(error).__name__}).") from None
    latency_ms = int((time.monotonic() - started) * 1000)
    blocks = result.message.get("content") or []
    text = "\n".join(str(b.get("text", "")) for b in blocks if isinstance(b, dict) and b.get("text")).strip()
    usage: dict[str, Any] = dict(getattr(result.metrics, "accumulated_usage", {}) or {})
    tokens_in = int(usage.get("inputTokens", 0))
    tokens_out = int(usage.get("outputTokens", 0))
    return ChatReply(
        text=text or "(no reply)",
        model=seat_model.model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        est_cost=estimated_cost(tokens_in, tokens_out, seat_model.price_in, seat_model.price_out),
        latency_ms=latency_ms,
    )


def folder_digest(folder: Path) -> dict[str, str]:
    """Every file under a run folder with its hash, for the byte-identical guarantee."""
    import hashlib

    return {
        p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }
