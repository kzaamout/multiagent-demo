"""Per-stream event bus feeding the server-sent event endpoint.

A stream is a live run (stream id equals run id) or a replay session. Subscribers get
the backlog after a given seq, then live events, with no duplicates.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

EventDict = dict[str, Any]


@dataclass
class _Stream:
    events: list[EventDict] = field(default_factory=list)
    subscribers: set[asyncio.Queue[EventDict | None]] = field(default_factory=set)
    closed: bool = False


class StreamBus:
    def __init__(self) -> None:
        self._streams: dict[str, _Stream] = {}

    def open(self, stream_id: str) -> None:
        self._streams.setdefault(stream_id, _Stream())

    def exists(self, stream_id: str) -> bool:
        return stream_id in self._streams

    def is_closed(self, stream_id: str) -> bool:
        stream = self._streams.get(stream_id)
        return stream is None or stream.closed

    def events(self, stream_id: str) -> list[EventDict]:
        stream = self._streams.get(stream_id)
        return list(stream.events) if stream else []

    def publish(self, stream_id: str, event: EventDict) -> None:
        stream = self._streams.setdefault(stream_id, _Stream())
        if stream.closed:
            raise RuntimeError(f"stream {stream_id} is closed")
        stream.events.append(event)
        for queue in list(stream.subscribers):
            queue.put_nowait(event)

    def close(self, stream_id: str) -> None:
        stream = self._streams.get(stream_id)
        if stream is None or stream.closed:
            return
        stream.closed = True
        for queue in list(stream.subscribers):
            queue.put_nowait(None)

    async def subscribe(self, stream_id: str, since_seq: int = 0) -> AsyncIterator[EventDict]:
        stream = self._streams.setdefault(stream_id, _Stream())
        queue: asyncio.Queue[EventDict | None] = asyncio.Queue()
        stream.subscribers.add(queue)
        try:
            last = since_seq
            for event in list(stream.events):
                if int(event["seq"]) > last:
                    last = int(event["seq"])
                    yield event
            if stream.closed:
                return
            while True:
                item = await queue.get()
                if item is None:
                    return
                if int(item["seq"]) <= last:
                    continue
                last = int(item["seq"])
                yield item
        finally:
            stream.subscribers.discard(queue)
