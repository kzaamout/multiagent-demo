"""End-to-end through the Demo page in Chromium with live stubbed runs: every human touchpoint
is exercised by clicking the page, never by calling the API directly.
Run with: uv run pytest -m visual"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import uvicorn

from app.config import Settings
from app.main import create_app

pytestmark = [pytest.mark.visual, pytest.mark.dataset]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[str, Path]]:
    runs = tmp_path_factory.mktemp("runs")
    port = free_port()
    app = create_app(Settings(runs_dir=runs, stub_pace=120.0, agent_mode="stub"))
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not srv.started and time.time() < deadline:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}", runs
    srv.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def page(server: tuple[str, Path]) -> Iterator[Any]:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as error:  # noqa: BLE001
            pytest.skip(f"Chromium not installed: {error}")
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        pg = context.new_page()
        errors: list[str] = []
        pg.on("pageerror", lambda exc: errors.append(str(exc)))
        pg.errors = errors
        yield pg
        browser.close()


def choose_dataset(page: Any, label: str) -> None:
    page.click("#dataset-select")
    page.click(f"#dataset-menu .menu-item:has-text('{label}')")


def last_event_type(page: Any) -> str:
    return str(
        page.evaluate("() => { const e = window.__s1.events; return e.length ? e[e.length - 1].type : '' }")
    )


def test_planted_inconsistency_through_the_page(page: Any, server: tuple[str, Path]) -> None:
    base, runs = server
    page.goto(base + "/demo")
    page.wait_for_selector("#dataset-value:has-text('02')")
    choose_dataset(page, "02 · Planted inconsistency")
    page.click("#btn-run")

    page.wait_for_selector("#banner:not([hidden])", timeout=20000)
    assert page.get_attribute('.node[data-stage="intake"]', "data-state") == "paused"
    inputs = page.locator("#banner-questions input")
    assert inputs.count() == 2
    assert inputs.nth(1).input_value() == "No, base bid only"
    inputs.nth(1).fill("base bid only")
    page.click("#banner-resume")
    page.wait_for_selector("#banner", state="hidden", timeout=20000)

    page.wait_for_selector('path[data-arrow="review-work"][data-fired="true"]', timeout=30000)
    page.wait_for_selector(".retry-badge:has-text('retry 1 of 3')")
    page.wait_for_selector("#btn-approve:not([disabled])", timeout=30000)
    card = page.locator('article[data-kind="termination"]')
    assert "exit: reviewer_pass" in card.inner_text()
    assert card.locator(".term-eyebrow").inner_text().lower().startswith("ready for approval")
    page.click("#btn-approve")
    page.wait_for_function(
        "() => window.__s1 && window.__s1.events.length && window.__s1.events[window.__s1.events.length - 1].type === 'run.terminated'",
        timeout=20000,
    )
    page.wait_for_selector("article[data-kind='termination']:has-text('Your decision')")
    assert last_event_type(page) == "run.terminated"
    assert card.locator(".term-eyebrow").inner_text().lower().startswith("run ended")

    answered = page.locator("article[data-kind='human-answer']").first.inner_text()
    assert "208Y/120 V, base bid only" in answered
    assert all(
        page.get_attribute(f'.node[data-stage="{s}"]', "data-state") == "complete"
        for s in ["intake", "plan", "work", "assemble", "review", "handoff"]
    )
    raw = page.inner_text("#raw-label")
    assert raw.startswith("Raw turns · 65")
    assert list(runs.glob("*/events.jsonl")), "the run was recorded"
    # Tracker: every forward connector was crossed, nothing is live, and the label carries the headline.
    assert page.locator(".fwd[data-filled='true']").count() == 5
    assert page.locator("article[data-live='true']").count() == 0
    assert "Run ended" in page.inner_text("#loop-reason")
    assert page.errors == []


def test_prompt_toggle_shows_bundle(page: Any) -> None:
    thread = page.locator("article[data-kind='agent-message']").first
    thread.locator(".card-hd").click()
    thread.locator("button[data-action='prompt']").click()
    panel = thread.locator(".prompt-panel")
    panel.wait_for()
    page.wait_for_selector(
        "article[data-kind='agent-message'] .prompt-sec-label:has-text('System instructions')"
    )
    text = panel.inner_text()
    for label in ["SYSTEM INSTRUCTIONS", "CONTEXT PROVIDED", "TASK", "TOOLS AVAILABLE", "MODEL"]:
        assert label in text.upper()
    note = page.locator("article[data-card='start']")
    note.locator(".card-hd").click()
    page.wait_for_selector("article[data-card='start'] .why")
    assert "Why" in page.inner_text("article[data-card='start']")


def test_threads_start_collapsed_with_a_live_indicator(page: Any, server: tuple[str, Path]) -> None:
    """Spec 0.7, 2.2: threads render collapsed, the live state and unread count follow events only."""
    base, _ = server
    from tests.visual.capture_app import golden_seq

    page.goto(base + f"/demo?golden=planted-inconsistency&upto={golden_seq('running')}")
    page.wait_for_selector("article[data-kind='specialist-thread'][data-agent='estimator']")
    estimator = page.locator("article[data-kind='specialist-thread'][data-agent='estimator']")
    assert estimator.locator(".chev-sm").inner_text() == "▸", "threads start collapsed"
    assert estimator.get_attribute("data-live") == "true"
    assert estimator.locator(".unread-chip").inner_text() == "3 new"
    pricing = page.locator("article[data-kind='specialist-thread'][data-agent='pricing']")
    assert pricing.get_attribute("data-live") == "true" and pricing.locator(".unread-chip").count() == 0
    assert page.get_attribute(".node[data-stage='work']", "data-state") == "active"
    assert page.get_attribute(".fwd[data-link='plan-work']", "data-filled") == "true"
    assert page.get_attribute(".fwd[data-link='work-assemble']", "data-filled") == "false"
    label = page.inner_text("#loop-reason")
    assert label.startswith("Work ·") and len(label) > 8
    estimator.locator(".card-hd").click()
    page.wait_for_selector("article[data-agent='estimator'] .replies")
    assert estimator.locator(".unread-chip").count() == 0, "opening the thread marks its replies seen"
    estimator.locator(".card-hd").click()
    page.wait_for_function(
        "() => document.querySelector(\"article[data-agent='estimator'] .chev-sm\").textContent === '▸'"
    )
    assert estimator.locator(".unread-chip").count() == 0, "nothing new since the collapse"
    # After termination the same page shows completed nodes and no live card.
    page.goto(base + f"/demo?golden=planted-inconsistency&upto={golden_seq('terminated')}")
    page.wait_for_selector("article[data-kind='termination']")
    assert page.locator("article[data-live='true']").count() == 0
    assert page.locator("path[data-arrow='review-work'][data-fired='true']").count() == 1
    assert page.inner_text("#loop-reason").startswith("Handoff ·")
    assert page.errors == []
    page.goto(base + "/demo")
    page.wait_for_selector("#dataset-value:has-text('02')")


def test_missing_sheet_escalate_through_the_page(page: Any) -> None:
    choose_dataset(page, "03 · Missing sheet")
    page.click("#btn-run")
    blocker = page.locator("article[data-kind='blocker']")
    blocker.wait_for(timeout=30000)
    assert page.get_attribute('.node[data-stage="work"]', "data-state") == "paused"
    blocker.locator("button[data-action='blocker-escalate']").click()
    page.wait_for_selector("article[data-kind='termination'][data-exit='blocker_escalated']", timeout=20000)
    term = page.inner_text("article[data-kind='termination']")
    assert "What is missing" in term and "LP-2" in term
    assert page.errors == []


def test_replay_at_4x_plays_golden_log(page: Any) -> None:
    choose_dataset(page, "05 · Not ready")
    page.click("#speed-4")
    started = time.monotonic()
    page.click("#btn-replay")
    page.wait_for_selector("article[data-kind='termination'][data-exit='not_ready']", timeout=20000)
    elapsed = time.monotonic() - started
    assert 4.0 <= elapsed <= 12.0, elapsed
    term = page.inner_text("article[data-kind='termination']")
    assert "Submission deadline" in term and "Division 26 specification" in term
    ids = page.evaluate("() => window.__s1.events.map(e => e.event_id)")
    assert len(ids) == 6
    assert page.errors == []


def cards_text(page: Any) -> list[str]:
    return list(
        page.evaluate(
            "() => Array.from(document.querySelectorAll('article.card')).map(a => a.getAttribute('data-kind') + '|' + a.querySelector('.summary, .term-headline').textContent + '|' + (a.querySelector('.time, .term-eyebrow') || {}).textContent)"
        )
    )


def test_replay_matches_recorded_display(page: Any, server: tuple[str, Path]) -> None:
    """Criterion 2: a replay renders the same feed, loop strip, and meters as its recording."""
    base, _ = server
    page.goto(base + "/demo")
    choose_dataset(page, "02 · Planted inconsistency")
    page.wait_for_selector("#btn-replay[title*='most recent recording']")
    page.click("#speed-4")
    page.click("#btn-replay")
    page.wait_for_function(
        "() => window.__s1 && window.__s1.events.length && window.__s1.events[window.__s1.events.length - 1].type === 'run.terminated'",
        timeout=180000,
    )
    page.wait_for_timeout(300)
    replay = cards_text(page)
    replay_nodes = page.evaluate(
        "() => Array.from(document.querySelectorAll('.node')).map(n => n.dataset.state)"
    )
    replay_meters = (
        page.inner_text("#agent-meters") + page.inner_text("#run-total") + page.inner_text("#elapsed")
    )
    run_id = page.evaluate("() => window.__s1.view.runId")
    page.goto(base + f"/demo?run={run_id}")
    page.wait_for_function("() => window.__s1 && window.__s1.events.length > 60")
    page.wait_for_timeout(300)
    assert cards_text(page) == replay
    assert (
        page.evaluate("() => Array.from(document.querySelectorAll('.node')).map(n => n.dataset.state)")
        == replay_nodes
    )
    assert (
        page.inner_text("#agent-meters") + page.inner_text("#run-total") + page.inner_text("#elapsed")
        == replay_meters
    )
    assert page.errors == []


def test_replay_fires_every_arrow_pulse(page: Any, server: tuple[str, Path]) -> None:
    """Spec 0.7, 2.2: forward and backward arrows pulse once per stage.changed, in replay as in a live run."""
    base, _ = server
    page.goto(base + "/demo")
    choose_dataset(page, "02 · Planted inconsistency")
    page.click("#speed-4")
    page.click("#btn-replay")
    page.wait_for_function(
        "() => window.__s1 && window.__s1.events.length && window.__s1.events[window.__s1.events.length - 1].type === 'run.terminated'",
        timeout=180000,
    )
    assert page.locator(".fwd.is-firing").count() == 5
    assert page.locator("path.is-firing").count() == 1
    assert page.locator(".node[data-state='complete']").count() == 6
    assert page.errors == []


def test_draft_renderer_keeps_provenance_tags_whole_inside_table_cells(
    page: Any, server: tuple[str, Path]
) -> None:
    base, _ = server
    page.goto(base + "/demo")
    page.wait_for_function("() => window.S1Draft && window.S1Draft.renderMarkdown")
    markdown = (
        "| Item | Qty | Extended |"
        + chr(10)
        + "|---|---|---|"
        + chr(10)
        + "| Troffer | 46 | {{6532.00|src:e1}} |"
    )
    html = page.evaluate("(md) => window.S1Draft.renderMarkdown(md)", markdown)
    assert html.count('class="prov"') == 1 and "{{" not in html and "src:" not in html
    assert html.count("<td>") == 3, "the tag's pipe does not split the cell"


def _stage_events(transitions: list[tuple[str | None, str, str]], *, ended: bool) -> list[dict[str, Any]]:
    """A minimal event list shaped like a run: start, the given stage transitions, optional end."""
    actor = {"agent_id": "orchestrator", "name": "Oscar", "role": "Orchestrator", "model": {"label": "stub"}}
    events: list[dict[str, Any]] = [
        {
            "event_id": "e0",
            "run_id": "r",
            "seq": 1,
            "ts": "2026-09-16T10:00:00.000Z",
            "type": "run.started",
            "stage": None,
            "actor": actor,
            "reason": "start",
            "payload": {
                "workflow": "electrical_rfp",
                "dataset_id": "clean-run",
                "mode": "single",
                "roster": [],
            },
        }
    ]
    for i, (src, dst, direction) in enumerate(transitions, start=1):
        events.append(
            {
                "event_id": f"e{i}",
                "run_id": "r",
                "seq": i + 1,
                "ts": "2026-09-16T10:00:01.000Z",
                "type": "stage.changed",
                "stage": dst,
                "actor": actor,
                "reason": "next",
                "payload": {"from": src, "to": dst, "direction": direction, "target_reason": f"into {dst}"},
            }
        )
    if ended:
        events.append(
            {
                "event_id": "end",
                "run_id": "r",
                "seq": len(events) + 1,
                "ts": "2026-09-16T10:00:02.000Z",
                "type": "run.terminated",
                "stage": None,
                "actor": actor,
                "reason": "done",
                "payload": {"exit": "single_complete", "summary": {"headline": "Single model finished"}},
            }
        )
    return events


def test_reducer_marks_skipped_stages_bypassed(page: Any, server: tuple[str, Path]) -> None:
    """Spec 0.7, 2.2: a stage a forward transition skips renders bypassed, never idle, and every
    connector the jump crosses fills. No Team-mode run skips a stage, so the reducer is fed a
    Single-model shaped list directly."""
    base, _ = server
    page.goto(base + "/demo")
    page.wait_for_function("() => window.S1Reducer && window.S1Reducer.reduce")
    reduce = "(events) => window.S1Reducer.reduce(events)"

    running = _stage_events([(None, "intake", "forward"), ("intake", "work", "forward")], ended=False)
    view = page.evaluate(reduce, running)
    assert view["nodes"] == {
        "intake": "complete",
        "plan": "bypassed",
        "work": "active",
        "assemble": "idle",
        "review": "idle",
        "handoff": "idle",
    }
    assert view["stageReason"] == "into work"
    assert set(view["forwardFired"]) == {"intake-plan", "plan-work"}, "both crossed connectors fill"

    single = _stage_events(
        [
            (None, "intake", "forward"),
            ("intake", "work", "forward"),
            ("work", "assemble", "forward"),
            ("assemble", "handoff", "forward"),
        ],
        ended=True,
    )
    view = page.evaluate(reduce, single)
    assert view["nodes"]["plan"] == "bypassed" and view["nodes"]["review"] == "bypassed"
    assert [s for s, state in view["nodes"].items() if state == "complete"] == [
        "intake",
        "work",
        "assemble",
        "handoff",
    ]
    assert len(view["forwardFired"]) == 5, "every forward connector filled"
    assert view["stageReason"] == "Single model finished", "the termination headline replaces the stage label"

    entered_later = _stage_events(
        [
            (None, "intake", "forward"),
            ("intake", "work", "forward"),
            ("work", "plan", "backward"),
            ("plan", "work", "forward"),
        ],
        ended=False,
    )
    view = page.evaluate(reduce, entered_later)
    assert view["nodes"]["plan"] == "complete", (
        "a bypassed stage that is later entered is complete, not bypassed"
    )
    assert page.errors == []
