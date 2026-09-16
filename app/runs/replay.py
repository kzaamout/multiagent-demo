"""Replay: re-emit a recorded run verbatim over the stream, at the recorded gaps divided by speed.

A replay writes nothing under runs/. Event ids, run id, seq, and timestamps are the originals.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app.runs.bus import StreamBus
from app.runs.recorder import read_events
from app.schema.events import Event, parse_ts


@dataclass
class ReplaySession:
    dataset_id: str
    source: str
    path: Path
    speed: float
    bus: StreamBus
    session_id: str = field(default_factory=lambda: f"replay-{uuid.uuid4()}")
    events: list[Event] = field(default_factory=list)
    task: asyncio.Task[None] | None = None

    def load(self) -> None:
        self.events = read_events(self.path)
        if not self.events:
            raise ValueError(f"{self.path} holds no events")

    @property
    def run_id(self) -> str:
        return self.events[0].run_id

    def start(self) -> None:
        if not self.events:
            self.load()
        self.bus.open(self.session_id)
        self.task = asyncio.create_task(self._play())

    def gaps(self) -> list[float]:
        """Seconds to wait before each event, already divided by speed."""
        result: list[float] = []
        previous = parse_ts(self.events[0].ts)
        for event in self.events:
            ts = parse_ts(event.ts)
            result.append(max(0.0, (ts - previous).total_seconds()) / self.speed)
            previous = ts
        return result

    async def _play(self) -> None:
        try:
            for gap, event in zip(self.gaps(), self.events, strict=True):
                if gap > 0:
                    await asyncio.sleep(gap)
                self.bus.publish(self.session_id, event.model_dump(mode="json", by_alias=True))
        finally:
            self.bus.close(self.session_id)
