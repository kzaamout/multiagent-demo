"""The Elapsed clock in Chromium (spec 012, User Story 1): working time from the events, ticking
between events at the run's rate, held while the run waits on the human, stopped at the end.
Time in the page is driven by Playwright's clock control where the test needs it to be exact.
Run with: uv run pytest -m visual"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import socket
import threading
import time
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
import uvicorn

from app.agents.stubs import planted_inconsistency
from app.config import Settings, load_settings
from app.main import create_app
from app.runs.working_time import working_times as server_working_times
from app.schema.events import Event, parse_ts
from tests.conftest import run_scenario

pytestmark = [pytest.mark.visual, pytest.mark.dataset]

PINNED = "00000000-0000-4000-8000-0000000000dd"
HOLD_TYPES = {
    "clarification.asked",
    "clarification.answered",
    "run.paused",
    "run.resumed",
    "handoff.ready",
    "human.approved",
}
T0 = dt.datetime(2026, 9, 21, 9, 0, tzinfo=dt.UTC)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def serve(settings: Settings) -> Iterator[str]:
    port = free_port()
    srv = uvicorn.Server(
        uvicorn.Config(create_app(settings), host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not srv.started and time.time() < deadline:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """A pinned recording for the public replay, which plays in the browser on its timers."""
    runs = tmp_path_factory.mktemp("runs")
    settings = Settings(runs_dir=runs, stub_pace=1000.0, agent_mode="stub", public_run_id=PINNED)
    # Recorded on its own thread: Playwright's sync API may already hold this thread's event loop.
    recorder = threading.Thread(
        target=lambda: asyncio.run(
            run_scenario(planted_inconsistency.SCENARIO, settings, record=True, run_id=PINNED)
        )
    )
    recorder.start()
    recorder.join()
    yield from serve(settings)


@pytest.fixture(scope="module")
def slow_server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """Stubbed runs at pace 1, so a run stays in its first working stretch for 52 s."""
    runs = tmp_path_factory.mktemp("runs")
    yield from serve(Settings(runs_dir=runs, stub_pace=1.0, agent_mode="stub"))


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        try:
            chromium = p.chromium.launch()
        except Exception as error:  # noqa: BLE001
            pytest.skip(f"Chromium not installed: {error}")
        yield chromium
        chromium.close()


@pytest.fixture
def page(browser: Any) -> Iterator[Any]:
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    pg = context.new_page()
    errors: list[str] = []
    pg.on("pageerror", lambda exc: errors.append(str(exc)))
    pg.errors = errors
    yield pg
    context.close()


# The page's reducer is checked against the server's copy of the hold rule (research D15).


def ts_ms(ts: str) -> int:
    return int(parse_ts(ts).timestamp() * 1000)


def working_times(events: list[dict[str, Any]]) -> dict[str, int]:
    parsed = [Event.from_line(json.dumps(e)) for e in events]
    return {e["event_id"]: w for e, w in zip(events, server_working_times(parsed), strict=True)}


def fmt_clock(ms: int) -> str:
    s = max(0, ms // 1000)
    return f"{s // 60:02d}:{s % 60:02d}"


def seconds(text: str) -> int:
    minutes, secs = text.strip().split(":")
    return int(minutes) * 60 + int(secs)


def golden_ids() -> list[str]:
    root = load_settings().datasets_dir
    return sorted(p.parent.name for p in root.glob("*/golden-events.jsonl"))


# (a) working time over every golden log, and the termination card agrees with it


def test_working_time_matches_the_hold_table_on_every_golden(page: Any, server: str) -> None:
    page.goto(server + "/demo")
    page.wait_for_function("() => window.S1Reducer && window.S1Clock")
    for dataset in golden_ids():
        events = httpx.get(f"{server}/api/datasets/{dataset}/golden").json()
        expected = working_times(events)
        got = page.evaluate(
            "(list) => { const v = S1Reducer.reduce(list, {}); return { at: v.workAt, final: v.clock.workMs, ended: v.clock.ended } }",
            events,
        )
        assert got["at"] == expected, dataset
        assert got["final"] == list(expected.values())[-1], dataset
        assert got["ended"] is True, dataset
    assert page.errors == []


def test_termination_card_shows_the_final_working_time(page: Any, server: str) -> None:
    for dataset in golden_ids():
        events = httpx.get(f"{server}/api/datasets/{dataset}/golden").json()
        final = list(working_times(events).values())[-1]
        page.goto(f"{server}/demo?golden={dataset}")
        page.wait_for_selector("article[data-kind='termination'] .term-eyebrow")
        assert page.inner_text("article[data-kind='termination'] .term-eyebrow").endswith(fmt_clock(final)), (
            dataset
        )
        assert page.inner_text("#elapsed") == fmt_clock(final), dataset
    assert page.errors == []


# (a2) holds the golden logs never exercise


def test_holds_from_hand_built_event_lists(page: Any, server: str) -> None:
    page.goto(server + "/demo")
    page.wait_for_function("() => window.S1Reducer && window.S1Reducer.WorkClock")
    ask = {"question_ids": ["q1"]}
    blocker = {"question_ids": ["b1"], "blocker": {"blocker_id": "b1"}}
    cases: dict[str, list[list[Any]]] = {
        "pause alone": [
            ["run.started", 0, {}],
            ["run.paused", 10000, {}],
            ["run.resumed", 40000, {}],
            ["run.terminated", 50000, {}],
        ],
        "pause during a question batch": [
            ["run.started", 0, {}],
            ["clarification.asked", 10000, ask],
            ["run.paused", 15000, {}],
            ["clarification.answered", 20000, {"question_id": "q1"}],
            ["run.resumed", 30000, {}],
            ["run.terminated", 40000, {}],
        ],
        "blocker answered": [
            ["run.started", 0, {}],
            ["clarification.asked", 5000, blocker],
            ["clarification.answered", 25000, {"question_id": "b1"}],
            ["run.terminated", 35000, {}],
        ],
        "blocker escalated": [
            ["run.started", 0, {}],
            ["clarification.asked", 5000, blocker],
            ["clarification.answered", 25000, {"question_id": "b1"}],
            ["run.terminated", 25000, {}],
        ],
        "stopped while a blocker waits": [
            ["run.started", 0, {}],
            ["clarification.asked", 5000, blocker],
            ["run.terminated", 30000, {}],
        ],
        "handoff then closing work": [
            ["run.started", 0, {}],
            ["handoff.ready", 60000, {}],
            ["human.approved", 90000, {}],
            ["draft.committed", 95000, {}],
            ["run.terminated", 97000, {}],
        ],
    }
    got = page.evaluate(
        """(cases) => { const out = {};
          Object.keys(cases).forEach(name => { const w = new S1Reducer.WorkClock();
            cases[name].forEach((c, i) => w.see({ type: c[0], payload: c[2], event_id: name + i }, c[1]));
            out[name] = { work: w.workMs, handoff: w.workAtHandoffMs }; });
          return out; }""",
        cases,
    )
    assert {k: v["work"] for k, v in got.items()} == {
        "pause alone": 20000,
        "pause during a question batch": 20000,
        "blocker answered": 15000,
        "blocker escalated": 5000,
        "stopped while a blocker waits": 5000,
        "handoff then closing work": 67000,
    }
    assert got["handoff then closing work"]["handoff"] == 60000


# (b), (c), (d), (g) the public replay, which plays on the page's own timers


def sample(page: Any) -> dict[str, Any]:
    return dict(
        page.evaluate(
            "() => { const s = window.__s1; return { text: document.getElementById('elapsed').textContent,"
            " shown: s.clock.shownMs, running: s.view.clock.running, ended: s.view.clock.ended, n: s.events.length } }"
        )
    )


def open_public_replay(page: Any, server: str, speed: int) -> None:
    page.clock.install(time=T0)
    page.clock.pause_at(T0 + dt.timedelta(seconds=1))
    page.goto(f"{server}/demo?public=1&run={PINNED}&speed={speed}&animate=0")
    deadline = time.time() + 20
    while not page.evaluate("() => !!(window.__s1 && window.__s1.events.length)"):
        assert time.time() < deadline, "the public replay did not start"
        page.clock.run_for(50)
        time.sleep(0.02)


@pytest.mark.parametrize("speed", [1, 4])
def test_public_replay_ticks_holds_and_stops(page: Any, server: str, speed: int) -> None:
    open_public_replay(page, server, speed)
    samples = [sample(page)]
    for _ in range(1200):
        if samples[-1]["ended"]:
            break
        page.clock.run_for(1000)
        samples.append(sample(page))
    assert samples[-1]["ended"], "the replay did not finish"
    types = page.evaluate("() => window.__s1.events.map(e => e.type)")
    rate = 1000 * speed
    # The replay stretches a zero gap to 150 ms of wall time and each event re-anchors the clock,
    # so the shown value may sit up to 150 ms of run time ahead and hold until the run catches up.
    slack = 200
    ticked = held = still = 0
    for before, after in zip(samples, samples[1:], strict=False):
        assert seconds(after["text"]) >= seconds(before["text"]), (before, after)  # FR-007
        crossed = set(types[before["n"] : after["n"]])
        working = before["running"] and after["running"] and not crossed & HOLD_TYPES
        if working and before["n"] == after["n"]:
            delta = after["shown"] - before["shown"]
            assert rate - slack <= delta <= rate + 5, (before, after)  # SC-001: the run's rate
            ticked += 1
        if working:
            still = still + 1 if after["text"] == before["text"] else 0
            assert still <= 1, (before, after)  # never two seconds without a change
        if (
            not before["running"]
            and not after["running"]
            and not before["ended"]
            and before["n"] == after["n"]
        ):
            assert after["text"] == before["text"], (before, after)
            held += 1
    assert ticked > 5
    assert speed == 4 or held >= 1, "the clarification wait was never sampled"
    events = page.evaluate("() => window.__s1.events")
    final = fmt_clock(list(working_times(events).values())[-1])
    assert samples[-1]["text"] == final
    page.clock.run_for(10000)  # SC-003
    assert page.inner_text("#elapsed") == final
    assert page.errors == []


# (e) a live stubbed run, reloaded mid-run


def test_reload_mid_run_shows_the_working_time_and_ticks(page: Any, slow_server: str) -> None:
    reply = httpx.post(f"{slow_server}/api/runs", json={"dataset_id": "planted-inconsistency"})
    assert reply.status_code == 201, reply.text
    run_id = reply.json()["run_id"]
    try:
        time.sleep(3.0)
        page.goto(slow_server + "/demo")
        page.wait_for_function("() => window.__s1 && window.__s1.view.clock.running")
        time.sleep(1.2)
        shown = seconds(page.inner_text("#elapsed"))
        meta = httpx.get(f"{slow_server}/api/meta").json()
        events = httpx.get(f"{slow_server}/api/runs/{run_id}/events").json()
        work = list(working_times(events).values())[-1]
        expected = (work + max(0, ts_ms(meta["live_run_clock"]["now"]) - ts_ms(events[-1]["ts"]))) / 1000
        assert abs(shown - expected) <= 1.5, (shown, expected)
        time.sleep(2.2)
        assert seconds(page.inner_text("#elapsed")) >= shown + 2
    finally:
        httpx.post(f"{slow_server}/api/runs/{run_id}/stop")
    assert page.errors == []


# (f) a fixed state never ticks


def test_golden_state_stays_still(page: Any, server: str) -> None:
    page.goto(server + "/demo?golden=planted-inconsistency&upto=30")
    page.wait_for_function("() => window.__s1 && window.__s1.events.length === 30")
    before = page.inner_text("#elapsed")
    time.sleep(2.5)
    assert page.inner_text("#elapsed") == before
    assert json.loads(page.evaluate("() => JSON.stringify(window.__s1.clock.anchor)")) is None
    assert page.errors == []


# Compute time on the Compare strip and the comparison line (decision 13)


def test_comparison_line_and_strip_show_compute_time(page: Any, server: str) -> None:
    page.goto(server + "/demo?golden=planted-inconsistency")
    page.wait_for_function("() => window.__s1 && window.__s1.events.length")
    page.evaluate(
        """() => {
          const s = window.__s1;
          s.ctx.comparison = {
            team: { est_cost: 0.42, elapsed_ms: 1020000, working_ms: 720000 },
            single: { est_cost: 0.05, elapsed_ms: 95000, working_ms: 95000, model_label: 'one model', summary: 'x' }
          };
          s.ui.schedule();
        }"""
    )
    page.wait_for_function(
        """() => document.querySelector('[data-part="comparison-line"]').textContent.startsWith('Team')"""
    )
    line = page.inner_text('[data-part="comparison-line"]')
    assert line.startswith("Team $0.42 in 12:00 · Single model $0.05 in 1:35"), line
    assert page.inner_text("#compare-summary") == "$0.05 · 1:35"
    assert page.errors == []
