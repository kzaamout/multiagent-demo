"""Run clock: fixture offsets to timestamps, paced sleeping for stubbed agents."""

from __future__ import annotations

import asyncio
import datetime as dt
import time

from app.schema.events import format_ts


class Clock:
    def __init__(self, start: dt.datetime, pace: float) -> None:
        if start.tzinfo is None:
            raise ValueError("clock start must be timezone-aware")
        if pace <= 0:
            raise ValueError("pace must be positive")
        self.start = start
        self.pace = pace
        self._wall_start = time.monotonic()

    def ts(self, offset_ms: int) -> str:
        return format_ts(self.start + dt.timedelta(milliseconds=offset_ms))

    def elapsed_offset_ms(self) -> int:
        """Wall time since start, expressed in fixture milliseconds (scaled by pace)."""
        return int((time.monotonic() - self._wall_start) * 1000 * self.pace)

    async def wait_for(self, offset_ms: int) -> None:
        delay = (offset_ms - self.elapsed_offset_ms()) / 1000.0 / self.pace
        if delay > 0:
            await asyncio.sleep(delay)


class VirtualClock(Clock):
    """No sleeping and no wall time: used by tests and the golden regenerator so that
    every timestamp is exactly the fixture offset."""

    def __init__(self, start: dt.datetime) -> None:
        super().__init__(start, pace=1.0)

    def elapsed_offset_ms(self) -> int:
        return 0

    async def wait_for(self, offset_ms: int) -> None:
        await asyncio.sleep(0)
