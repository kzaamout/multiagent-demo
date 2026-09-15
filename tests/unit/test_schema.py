from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from app.schema.bundles import PromptBundle
from app.schema.events import (
    AGENT_MESSAGE_TYPES,
    ORCHESTRATOR_TYPES,
    PAYLOAD_MODELS,
    Event,
    validate_run,
)

MODEL = {"provider": "bedrock", "model_id": "claude-sonnet", "label": "claude-sonnet via Bedrock"}
ORCH = {"agent_id": "orchestrator", "name": "Oscar", "role": "Orchestrator", "model": MODEL}
ANNA = {"agent_id": "intake", "name": "Anna", "role": "Intake Analyst", "model": MODEL}
SUMMARY: dict[str, Any] = {
    "headline": "h",
    "missing": [],
    "unresolved_findings": [],
    "retries": {"count": 0, "budget": 2},
    "readiness_verdict": None,
    "event_count": 2,
    "elapsed_ms": 10,
    "est_cost": 0.0,
    "human_decision": None,
}

PAYLOADS: dict[str, dict[str, Any]] = {
    "run.started": {
        "workflow": "electrical_rfp",
        "dataset_id": "clean-run",
        "mode": "team",
        "roster": [ORCH],
    },
    "stage.changed": {"from": None, "to": "intake", "direction": "forward", "target_reason": "r"},
    "intake.brief": {"brief": {"project": "p"}},
    "intake.readiness": {
        "verdict": "ready",
        "checklist": [{"item": "x", "status": "pass", "note": ""}],
        "legibility": [{"page": "E-1", "confidence": 0.9}],
    },
    "clarification.needed": {
        "question_id": "q",
        "question": "?",
        "why_it_matters": "w",
        "proposed_default": "d",
        "blocking": True,
    },
    "clarification.asked": {"question_ids": ["q"], "blocker": None},
    "clarification.answered": {"question_id": "q", "answer": "a", "action": "answer"},
    "assumption.accepted": {"question_id": "q", "default_used": "d"},
    "plan.created": {
        "subtasks": [{"task_id": "t1", "title": "T", "agent_id": "estimator", "depends_on": [], "scope": []}]
    },
    "task.dispatched": {"task_id": "t1", "agent_id": "estimator", "inputs_summary": "s"},
    "task.progress": {"task_id": "t1", "agent_id": "estimator", "message": "m"},
    "tool.called": {
        "task_id": "t1",
        "agent_id": "estimator",
        "tool": "t",
        "args_summary": "a",
        "result_summary": "r",
        "duration_ms": 1,
    },
    "task.completed": {
        "task_id": "t1",
        "agent_id": "estimator",
        "result": {},
        "provenance": [{"tool": "t", "source": "s", "confidence": 1.0}],
    },
    "blocker.raised": {
        "blocker_id": "b",
        "task_id": "t1",
        "agent_id": "estimator",
        "description": "d",
        "needs_human": True,
        "route_back_to": None,
    },
    "draft.committed": {
        "version": 1,
        "markdown_path": "d.md",
        "provenance_tags": [{"tag_id": "e1", "source_event_id": "x"}],
    },
    "artifact.compiled": {"version": 1, "pdf_path": None, "page_images": []},
    "review.verdict": {
        "verdict": "fail",
        "findings": [
            {
                "id": "f",
                "severity": "major",
                "text": "t",
                "evidence": "e",
                "route_to": "work",
                "agent_id": "estimator",
            }
        ],
    },
    "retry.incremented": {"count": 1, "budget": 2},
    "handoff.ready": {
        "exit_determination": "reviewer_pass",
        "package": {
            "pdf_path": None,
            "page_images": [],
            "verdict_event_id": "v",
            "unresolved_findings": [],
            "assumptions": [],
            "clarifications": [],
            "event_log_path": "p",
        },
    },
    "human.approved": {"decision": "approve", "notes": ""},
    "knowledge.appended": {
        "client_id": "c",
        "entries": [{"question_id": "q", "answer": "a", "source_event_id": "x"}],
    },
    "run.paused": {"by": "human"},
    "run.resumed": {"by": "human"},
    "model.changed": {"agent_id": "estimator", "from_model": MODEL, "to_model": MODEL},
    "meter.update": {
        "agent_id": "estimator",
        "call_id": "c1",
        "tokens_in": 1,
        "tokens_out": 1,
        "wall_ms": 1,
        "est_cost": 0.01,
    },
    "run.terminated": {"exit": "reviewer_pass", "summary": SUMMARY},
}


def envelope(type_: str, **overrides: Any) -> dict[str, Any]:
    if type_ in ORCHESTRATOR_TYPES:
        actor: Any = ORCH
        reason: Any = "A one-sentence reason."
    elif type_ in ("clarification.answered", "human.approved"):
        actor, reason = "human", None
    elif type_ in ("meter.update", "model.changed", "artifact.compiled"):
        actor, reason = "system", None
    else:
        actor, reason = ANNA, None
    data: dict[str, Any] = {
        "event_id": "e1",
        "run_id": "r1",
        "seq": 1,
        "ts": "2026-09-14T09:12:00.000Z",
        "type": type_,
        "stage": None if type_ in ("run.started", "run.terminated") else "intake",
        "actor": actor,
        "reason": reason,
        "prompt_ref": "pb-1" if type_ in AGENT_MESSAGE_TYPES else None,
        "payload": PAYLOADS[type_],
    }
    data.update(overrides)
    return data


def test_every_event_type_has_a_payload_model_and_validates() -> None:
    assert set(PAYLOADS) == set(PAYLOAD_MODELS)
    for type_ in PAYLOADS:
        Event.model_validate(envelope(type_))


def test_wrong_payload_for_type_fails() -> None:
    with pytest.raises(ValidationError):
        Event.model_validate(envelope("stage.changed", payload=PAYLOADS["run.paused"]))


def test_orchestrator_event_requires_reason() -> None:
    with pytest.raises(ValidationError, match="reason"):
        Event.model_validate(envelope("plan.created", reason=None))


def test_orchestrator_types_must_come_from_the_orchestrator() -> None:
    with pytest.raises(ValidationError, match="Orchestrator"):
        Event.model_validate(envelope("stage.changed", actor=ANNA, reason="r"))


def test_agent_message_requires_prompt_ref() -> None:
    with pytest.raises(ValidationError, match="prompt_ref"):
        Event.model_validate(envelope("task.progress", prompt_ref=None))


def test_human_events_require_human_actor() -> None:
    with pytest.raises(ValidationError, match="human"):
        Event.model_validate(envelope("human.approved", actor=ANNA))


def test_stageless_types_reject_a_stage() -> None:
    with pytest.raises(ValidationError, match="no stage"):
        Event.model_validate(envelope("run.started", stage="intake"))


def test_all_eight_exits_accepted() -> None:
    for exit_value in [
        "reviewer_pass",
        "retry_exhausted",
        "blocker_escalated",
        "not_ready",
        "cost_ceiling",
        "stopped",
        "single_complete",
        "dry_intake",
    ]:
        payload = {"exit": exit_value, "summary": dict(SUMMARY, readiness_verdict="ready")}
        Event.model_validate(envelope("run.terminated", payload=payload))
    with pytest.raises(ValidationError):
        Event.model_validate(envelope("run.terminated", payload={"exit": "other", "summary": SUMMARY}))


def test_timestamp_requires_timezone() -> None:
    with pytest.raises(ValidationError):
        Event.model_validate(envelope("run.started", ts="2026-09-14T09:12:00"))


def test_line_round_trip_keeps_from_alias() -> None:
    event = Event.model_validate(envelope("stage.changed"))
    line = event.to_line()
    assert '"from": null' in line
    assert Event.from_line(line) == event


def test_validate_run_rules() -> None:
    first = Event.model_validate(envelope("run.started"))
    last = Event.model_validate(envelope("run.terminated", seq=2, event_id="e2"))
    assert validate_run([first, last]) == []
    assert "last event is not run.terminated" in validate_run([first])
    gap = Event.model_validate(envelope("run.terminated", seq=3, event_id="e3"))
    assert any("seq 3" in p for p in validate_run([first, gap]))


def test_prompt_bundle_sections() -> None:
    bundle = PromptBundle(prompt_ref="pb", system="s", context_slice="c", task="t", tools=[], model=MODEL)
    labels = [label for label, _ in bundle.sections()]
    assert labels == ["System instructions", "Context provided", "Task", "Tools available", "Model"]
