"""A dataset's expectations of each seat, read from a run's events (app/runs/expectations.py)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.runs import expectations
from app.runs.expectations import dataset_checks, golden_match, seat_checks
from app.runs.golden import write_golden
from app.schema.events import AGENT_MESSAGE_TYPES, ORCHESTRATOR_TYPES, Event

RUN = "11111111-1111-4111-8111-111111111111"


ORCHESTRATOR = {
    "agent_id": "orchestrator",
    "name": "Oscar",
    "role": "Orchestrator",
    "model": {"provider": "ollama", "model_id": "qwen3.5:9b", "label": "qwen3.5 9b, local"},
}


def seat_actor(agent_id: str) -> dict[str, Any]:
    return {**ORCHESTRATOR, "agent_id": agent_id, "name": agent_id.title(), "role": agent_id.title()}


def ev(seq: int, type_: str, payload: dict[str, Any], stage: str | None = "work") -> Event:
    """A valid event of any type: Orchestrator events carry a reason, seat messages a prompt ref."""
    body: dict[str, Any] = {
        "event_id": f"00000000-0000-4000-8000-{seq:012d}",
        "run_id": RUN,
        "seq": seq,
        "ts": "2026-09-17T12:00:00.000Z",
        "type": type_,
        "actor": "system",
        "stage": stage,
        "payload": payload,
    }
    if type_ in ORCHESTRATOR_TYPES:
        body["actor"] = ORCHESTRATOR
        body["reason"] = "The Orchestrator moves the run on."
    elif type_ in AGENT_MESSAGE_TYPES:
        body["actor"] = seat_actor(
            str(payload.get("agent_id") or ("reviewer" if type_ == "review.verdict" else "intake"))
        )
        body["prompt_ref"] = f"pb-{seq:02d}"
    return Event.model_validate(body)


def started(dataset_id: str) -> Event:
    return ev(
        1,
        "run.started",
        {"workflow": "electrical_rfp", "dataset_id": dataset_id, "mode": "team", "roster": []},
        None,
    )


def terminated(seq: int, exit_value: str, missing: list[dict[str, str]] | None = None) -> Event:
    summary = {
        "headline": "h",
        "missing": missing or [],
        "unresolved_findings": [],
        "retries": {"count": 0, "budget": 3},
        "readiness_verdict": None,
        "event_count": seq,
        "elapsed_ms": 1,
        "est_cost": 0.0,
        "human_decision": None,
    }
    return ev(seq, "run.terminated", {"exit": exit_value, "summary": summary}, None)


def stage(seq: int, to: str, direction: str = "forward") -> Event:
    return ev(
        seq,
        "stage.changed",
        {"from": None, "to": to, "direction": direction, "target_reason": "The stage moves on."},
        None,
    )


@pytest.fixture
def datasets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "datasets"
    folder.mkdir()
    monkeypatch.setattr(expectations, "load_settings", lambda: SimpleNamespace(datasets_dir=folder))
    return folder


def test_not_ready_scores_intake_on_naming_both_gaps(tmp_path: Path, datasets: Path) -> None:
    events = [
        started("not-ready"),
        stage(2, "intake"),
        ev(3, "intake.readiness", {"verdict": "not_ready", "checklist": [], "legibility": []}, "intake"),
        terminated(
            4,
            "not_ready",
            [
                {"item": "No submission deadline", "note": "", "source_event_id": ""},
                {"item": "Division 26 specification absent", "note": "", "source_event_id": ""},
            ],
        ),
    ]
    checks = dataset_checks("not-ready", events, tmp_path)
    assert checks["intake"] == {"not_ready": True, "names_deadline": True, "names_specification": True}
    assert checks["orchestrator"] == {"nothing_dispatched": True}


def test_planted_inconsistency_reads_the_estimator_the_draft_and_the_verdict(
    tmp_path: Path, datasets: Path
) -> None:
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "draft-v1.md").write_text(
        "Panel LP-1: 225 A on E-001, 200 A on E-002.", encoding="utf-8"
    )
    events = [
        started("planted-inconsistency"),
        stage(2, "work"),
        ev(
            3,
            "task.completed",
            {
                "task_id": "t1",
                "agent_id": "estimator",
                "result": {"concerns": ["E-002 says 200 A, E-001 says 225 A"]},
                "provenance": [],
            },
        ),
        stage(4, "assemble"),
        stage(5, "review"),
        ev(
            6,
            "review.verdict",
            {
                "verdict": "fail",
                "findings": [
                    {
                        "id": "f1",
                        "severity": "major",
                        "text": "",
                        "evidence": "",
                        "route_to": "work",
                        "agent_id": "estimator",
                    }
                ],
            },
            "review",
        ),
        stage(7, "work", "backward"),
        stage(8, "assemble"),
        stage(9, "review"),
        stage(10, "handoff"),
        terminated(11, "reviewer_pass"),
    ]
    checks = dataset_checks("planted-inconsistency", events, tmp_path)
    assert checks == {
        "estimator": {"names_both_sheets": True},
        "writer": {"v1_carries_disagreement": True},
        "reviewer": {"failed_v1_to_work": True},
        "orchestrator": {"reworked_once": True},
    }


def test_a_seat_without_its_own_check_takes_the_golden_match(tmp_path: Path, datasets: Path) -> None:
    golden = [
        started("missing-sheet"),
        stage(2, "intake"),
        stage(3, "plan"),
        stage(4, "work"),
        terminated(5, "blocker_escalated"),
    ]
    (datasets / "missing-sheet").mkdir()
    write_golden(datasets / "missing-sheet" / "golden-events.jsonl", golden)
    run = [
        started("missing-sheet"),
        stage(2, "intake"),
        stage(3, "plan"),
        stage(4, "work"),
        ev(
            5,
            "blocker.raised",
            {
                "blocker_id": "b",
                "task_id": "t",
                "agent_id": "estimator",
                "description": "Panel schedule for LP-2 is missing",
                "needs_human": True,
                "route_back_to": None,
            },
        ),
        terminated(6, "blocker_escalated"),
    ]
    assert golden_match("missing-sheet", run) == (
        True,
        "missing-sheet: 3 transitions and exit blocker_escalated match",
    )
    checks = seat_checks("missing-sheet", run, tmp_path)
    assert checks["estimator"] == {"blocker_names_lp2": True}
    assert checks["pricing"] == {"golden_match": True} and checks["writer"] == {"golden_match": True}


def test_no_golden_means_no_fallback_check(tmp_path: Path, datasets: Path) -> None:
    run = [started("clean-run"), stage(2, "intake"), terminated(3, "stopped")]
    assert golden_match("clean-run", run) == (None, "no golden log")
    checks = seat_checks("clean-run", run, tmp_path)
    assert "orchestrator" not in checks and checks["intake"] == {"ready": False}
