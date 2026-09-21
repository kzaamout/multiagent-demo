"""A run's working time, its compute time: the time since `run.started` less the time a human wait
was open (spec 012 research D2 and D15).

The same rule as the Demo page's reducer (`WorkClock` in `reducer.js`); the browser suite checks the
two agree at every event of every golden log. A hold opens and closes on events the schema already
has, and overlapping holds count once:

- a clarification batch, from `clarification.asked` to the answer to its last question;
- a blocker, from `clarification.asked` with a blocker to its answer;
- a Pause, from `run.paused` to `run.resumed`;
- the Handoff approval, from `handoff.ready` to `human.approved`.

`run.terminated` closes every hold. Nothing here is stored: the figure is always derived from events.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence

from app.schema.events import Event, parse_ts


def _ms(ts: str) -> int:
    """A timestamp in whole milliseconds since the epoch, without floating point."""
    moment = parse_ts(ts)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=dt.UTC)
    delta = moment - dt.datetime(1970, 1, 1, tzinfo=dt.UTC)
    return delta // dt.timedelta(milliseconds=1)


class _Work:
    def __init__(self) -> None:
        self.start: int | None = None
        self.holds: set[str] = set()
        self.held = 0
        self.since: int | None = None
        self.pending: dict[str, set[str]] = {}
        self.work = 0

    def open(self, key: str, t: int) -> None:
        if key in self.holds:
            return
        if not self.holds:
            self.since = t
        self.holds.add(key)

    def close(self, key: str, t: int) -> None:
        if key not in self.holds:
            return
        self.holds.discard(key)
        if not self.holds and self.since is not None:
            self.held += max(0, t - self.since)
            self.since = None

    def at(self, t: int) -> int:
        if self.start is None:
            return 0
        held = self.held + (max(0, t - self.since) if self.since is not None else 0)
        return max(0, t - self.start - held)

    def see(self, event: Event) -> int:
        t = _ms(event.ts)
        payload = event.payload if isinstance(event.payload, dict) else {}
        kind = event.type
        if kind == "run.started":
            self.start = t
        elif kind == "clarification.asked":
            blocker = payload.get("blocker")
            questions = list(payload.get("question_ids") or [])
            if blocker:
                self.open(f"blocker:{blocker['blocker_id']}", t)
            elif questions:
                key = f"ask:{event.event_id}"
                self.pending[key] = set(questions)
                self.open(key, t)
        elif kind == "clarification.answered":
            question = str(payload.get("question_id", ""))
            self.close(f"blocker:{question}", t)
            for key, waiting in self.pending.items():
                if question in waiting:
                    waiting.discard(question)
                    if not waiting:
                        self.close(key, t)
        elif kind == "run.paused":
            self.open("pause", t)
        elif kind == "run.resumed":
            self.close("pause", t)
        elif kind == "handoff.ready":
            self.open("handoff", t)
        elif kind == "human.approved":
            self.close("handoff", t)
        elif kind == "run.terminated":
            for key in list(self.holds):
                self.close(key, t)
        self.work = max(self.work, self.at(t))
        return self.work


def working_times(events: Sequence[Event]) -> list[int]:
    """The working time at each event, in milliseconds, in event order."""
    work = _Work()
    return [work.see(event) for event in events]


def working_ms(events: Sequence[Event]) -> int:
    """The working time at the last event: a finished run's compute time."""
    times = working_times(events)
    return times[-1] if times else 0
