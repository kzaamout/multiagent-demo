"""Working time on the server (spec 012 research D15): the hold rule in Python, the same cases the
browser test gives the page's reducer, and the timeline's Time column."""

from __future__ import annotations

import datetime as dt
from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.compile.timeline import timeline_markdown
from app.config import load_settings
from app.runs.recorder import read_events
from app.runs.working_time import working_ms, working_times
from app.schema.events import Event

START = dt.datetime(2026, 9, 21, 9, 0, tzinfo=dt.UTC)
ASK = {"question_ids": ["q1"]}
BLOCKER = {"question_ids": ["b1"], "blocker": {"blocker_id": "b1"}}


def events(*steps: tuple[str, int, dict[str, Any]]) -> list[Event]:
    return [
        cast(
            Event,
            SimpleNamespace(
                event_id=f"e{i}",
                type=kind,
                payload=payload,
                ts=(START + dt.timedelta(milliseconds=ms)).isoformat().replace("+00:00", "Z"),
            ),
        )
        for i, (kind, ms, payload) in enumerate(steps)
    ]


@pytest.mark.parametrize(
    ("steps", "expected"),
    [
        (
            [
                ("run.started", 0, {}),
                ("run.paused", 10000, {}),
                ("run.resumed", 40000, {}),
                ("run.terminated", 50000, {}),
            ],
            20000,
        ),
        (
            [
                ("run.started", 0, {}),
                ("clarification.asked", 10000, ASK),
                ("run.paused", 15000, {}),
                ("clarification.answered", 20000, {"question_id": "q1"}),
                ("run.resumed", 30000, {}),
                ("run.terminated", 40000, {}),
            ],
            20000,
        ),
        (
            [
                ("run.started", 0, {}),
                ("clarification.asked", 5000, BLOCKER),
                ("clarification.answered", 25000, {"question_id": "b1"}),
                ("run.terminated", 35000, {}),
            ],
            15000,
        ),
        (
            [("run.started", 0, {}), ("clarification.asked", 5000, BLOCKER), ("run.terminated", 30000, {})],
            5000,
        ),
        (
            [
                ("run.started", 0, {}),
                ("handoff.ready", 60000, {}),
                ("human.approved", 90000, {}),
                ("draft.committed", 95000, {}),
                ("run.terminated", 97000, {}),
            ],
            67000,
        ),
    ],
    ids=[
        "pause",
        "pause during a batch",
        "blocker answered",
        "stopped on a blocker",
        "handoff then closing work",
    ],
)
def test_the_hand_built_cases_the_page_is_given(
    steps: list[tuple[str, int, dict[str, Any]]], expected: int
) -> None:
    assert working_ms(events(*steps)) == expected


def test_working_time_never_decreases_and_is_zero_before_the_start() -> None:
    times = working_times(
        events(
            ("run.started", 0, {}),
            ("clarification.asked", 1000, ASK),
            ("clarification.answered", 9000, {"question_id": "q1"}),
            ("run.terminated", 9500, {}),
        )
    )
    assert times == [0, 1000, 1000, 1500]
    assert working_ms([]) == 0


def test_the_timeline_prints_working_time() -> None:
    golden = read_events(load_settings().datasets_dir / "planted-inconsistency" / "golden-events.jsonl")
    table = [
        line for line in timeline_markdown(golden).splitlines() if line.startswith("| ") and ":" in line[:8]
    ]
    for line, work in zip(table, working_times(golden), strict=True):
        seconds = work // 1000
        assert line.startswith(f"| {seconds // 60:02d}:{seconds % 60:02d} |"), line
    # By the end the times run 13 s behind the timestamps: 12 s on the clarification, 1 s on approval.
    last = golden[-1]
    total = (
        dt.datetime.fromisoformat(last.ts.replace("Z", "+00:00"))
        - dt.datetime.fromisoformat(golden[0].ts.replace("Z", "+00:00"))
    ).total_seconds()
    assert total * 1000 - working_ms(golden) == 13000
