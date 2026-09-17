"""What each dataset expects of each seat, read back from a run's events (owner decision 2026-09-17, the
model sweep). A dataset README states its planted defect and the expected behaviour; these checks are that
statement in code, so a seat's correctness is the share of its dataset's checks the run met. A seat with no
check of its own on a dataset is scored on the run's golden match instead, and a dataset with no golden
scores nothing. Nothing here judges model text quality; it asks whether the seat did the thing the scenario
was built to make it do.

Checks per dataset (from datasets/<id>/README.md):
- clean-run: Intake ready; Estimator no blocker; Pricing completed; Writer committed v1; Reviewer passed v1.
- not-ready: Intake stops the run naming the deadline and the specification; nothing dispatched.
- missing-sheet: Intake lets the run reach Work; Estimator raises the LP-2 blocker; exit blocker_escalated.
- planted-inconsistency: Estimator names E-001 and E-002; Writer's v1 carries the disagreement; Reviewer
  fails v1 and routes it to Work; the run reworks once.
- missing-price: Pricing reports the exit sign unpriced; Writer's v1 states the exclusion; Reviewer passes
  with nothing above minor.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import load_settings
from app.runs.golden import compare, read_golden, terminal_exit
from app.schema.events import Event

SEATS = ("orchestrator", "intake", "estimator", "pricing", "writer", "reviewer")


def _payload(event: Event) -> dict[str, Any]:
    return event.payload if isinstance(event.payload, dict) else {}


def _text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False).lower() if not isinstance(value, str) else value.lower()


def _first(events: list[Event], event_type: str, agent_id: str | None = None) -> Event | None:
    for event in events:
        if event.type == event_type and (agent_id is None or _payload(event).get("agent_id") == agent_id):
            return event
    return None


def _readiness(events: list[Event]) -> str:
    event = _first(events, "intake.readiness")
    return str(_payload(event).get("verdict", "")) if event is not None else ""


def _stages(events: list[Event]) -> list[str]:
    return [str(_payload(e).get("to", "")) for e in events if e.type == "stage.changed"]


def _draft_text(folder: Path, version: int = 1) -> str:
    path = folder / "drafts" / f"draft-v{version}.md"
    try:
        return path.read_text(encoding="utf-8").lower()
    except OSError:
        return ""


def _first_verdict(events: list[Event]) -> dict[str, Any]:
    event = _first(events, "review.verdict")
    return _payload(event) if event is not None else {}


def _missing_items(events: list[Event]) -> str:
    last = events[-1] if events else None
    if last is None or last.type != "run.terminated":
        return ""
    summary = _payload(last).get("summary") or {}
    return _text(summary.get("missing") or [])


def golden_match(dataset_id: str, events: list[Event]) -> tuple[bool | None, str]:
    """Stage sequence and exit against the dataset's golden log; None when there is no golden to compare."""
    if not dataset_id:
        return None, "no dataset"
    path = load_settings().datasets_dir / dataset_id / "golden-events.jsonl"
    if not path.exists():
        return None, "no golden log"
    try:
        result = compare(dataset_id, events, read_golden(path))
    except (OSError, ValueError) as error:
        return None, f"golden unreadable: {error}"
    return result.ok, result.message


def dataset_checks(dataset_id: str, events: list[Event], folder: Path) -> dict[str, dict[str, bool]]:
    """The dataset's own checks per seat. Seats without a check here fall back to the golden match."""
    checks: dict[str, dict[str, bool]] = {}
    stages = _stages(events)
    verdict = _first_verdict(events)
    exit_value = terminal_exit(events) or ""
    if dataset_id == "clean-run":
        checks["intake"] = {"ready": _readiness(events) in ("ready", "ready_with_assumptions")}
        checks["estimator"] = {"no_blocker": _first(events, "blocker.raised", "estimator") is None}
        checks["pricing"] = {"completed": _first(events, "task.completed", "pricing") is not None}
        checks["writer"] = {"draft_v1": _first(events, "draft.committed") is not None}
        checks["reviewer"] = {
            "passed_v1": verdict.get("verdict") == "pass"
            and not any(f.get("severity") in ("blocker", "major") for f in verdict.get("findings") or [])
        }
    elif dataset_id == "not-ready":
        missing = _missing_items(events)
        checks["intake"] = {
            "not_ready": _readiness(events) == "not_ready" and exit_value == "not_ready",
            "names_deadline": "deadline" in missing or "closing" in missing,
            "names_specification": "specification" in missing,
        }
        checks["orchestrator"] = {"nothing_dispatched": _first(events, "task.dispatched") is None}
    elif dataset_id == "missing-sheet":
        blocker = _first(events, "blocker.raised", "estimator")
        blocker_text = _text(_payload(blocker).get("description", "")) if blocker is not None else ""
        checks["intake"] = {"reached_work": "work" in stages}
        checks["estimator"] = {"blocker_names_lp2": "lp-2" in blocker_text or "e-003" in blocker_text}
        checks["orchestrator"] = {"blocker_escalated": exit_value == "blocker_escalated"}
    elif dataset_id == "planted-inconsistency":
        completed = _first(events, "task.completed", "estimator")
        result_text = _text(_payload(completed).get("result", "")) if completed is not None else ""
        draft = _draft_text(folder, 1)
        findings = verdict.get("findings") or []
        checks["estimator"] = {"names_both_sheets": "e-001" in result_text and "e-002" in result_text}
        checks["writer"] = {"v1_carries_disagreement": "200 a" in draft and "225 a" in draft}
        checks["reviewer"] = {
            "failed_v1_to_work": verdict.get("verdict") == "fail"
            and any(f.get("route_to") == "work" for f in findings)
        }
        checks["orchestrator"] = {
            "reworked_once": stages.count("work") == 2 and exit_value == "reviewer_pass"
        }
    elif dataset_id == "missing-price":
        completed = _first(events, "task.completed", "pricing")
        result_text = _text(_payload(completed).get("result", "")) if completed is not None else ""
        draft = _draft_text(folder, 1)
        findings = verdict.get("findings") or []
        checks["pricing"] = {"exit_sign_unpriced": "exit sign" in result_text}
        checks["writer"] = {"v1_states_exclusion": "exit sign" in draft and "exclu" in draft}
        checks["reviewer"] = {
            "passed_minor_at_most": verdict.get("verdict") == "pass"
            and not any(f.get("severity") in ("blocker", "major") for f in findings)
        }
        checks["orchestrator"] = {"reviewer_pass": exit_value == "reviewer_pass"}
    return checks


def seat_checks(dataset_id: str, events: list[Event], folder: Path) -> dict[str, dict[str, bool]]:
    """Every seat's checks for the run: the dataset's own where it has them, else the golden match."""
    own = dataset_checks(dataset_id, events, folder)
    matched, _ = golden_match(dataset_id, events)
    result: dict[str, dict[str, bool]] = {}
    for seat in SEATS:
        if seat in own:
            result[seat] = own[seat]
        elif matched is not None:
            result[seat] = {"golden_match": matched}
    return result
