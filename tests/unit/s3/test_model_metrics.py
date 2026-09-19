"""Every run records how each seat's model performed, and the report aggregates it across runs."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

from app.runs.metrics import (
    ATTEMPTS_FILE,
    METRICS_FILE,
    SeatAttempt,
    append_attempt,
    categorise,
    run_metrics,
    write_metrics,
)
from app.runs.recorder import read_events
from app.schema.events import Event

ROOT = Path(__file__).resolve().parents[3]


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("model_report", ROOT / "scripts" / "model_report.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # the script's dataclasses resolve their annotations through here
    spec.loader.exec_module(module)
    return module


ORCHESTRATOR = {
    "agent_id": "orchestrator",
    "name": "Oscar",
    "role": "Orchestrator",
    "model": {"provider": "ollama", "model_id": "qwen3.5:9b", "label": "qwen3.5 9b, local"},
}
WRITER = {
    "agent_id": "writer",
    "name": "Willa",
    "role": "Writer",
    "model": {"provider": "ollama", "model_id": "qwen3.5:9b", "label": "qwen3.5 9b, local"},
}


def event(seq: int, type_: str, payload: dict[str, object], **extra: object) -> str:
    body: dict[str, object] = {
        "event_id": f"00000000-0000-4000-8000-{seq:012d}",
        "run_id": "11111111-1111-4111-8111-111111111111",
        "seq": seq,
        "ts": "2026-09-15T12:00:00.000Z",
        "type": type_,
        "actor": "system",
        "stage": "work",
        "payload": payload,
    }
    body.update(extra)
    return json.dumps(body)


def write_run(folder: Path) -> list[Event]:
    folder.mkdir(parents=True, exist_ok=True)
    roster = [WRITER]
    lines = [
        event(
            1,
            "run.started",
            {"workflow": "electrical_rfp", "dataset_id": "clean-run", "mode": "team", "roster": roster},
            actor=ORCHESTRATOR,
            stage=None,
            reason="The run begins.",
        ),
        event(
            2,
            "meter.update",
            {
                "agent_id": "writer",
                "call_id": "c1",
                "tokens_in": 9000,
                "tokens_out": 2000,
                "wall_ms": 30000,
                "est_cost": 0.0,
            },
        ),
        event(
            3,
            "tool.called",
            {
                "agent_id": "writer",
                "task_id": "t3",
                "tool": "template_render",
                "args_summary": "",
                "result_summary": "",
                "duration_ms": 120,
            },
            actor=WRITER,
            prompt_ref="pb-r1-05",
        ),
        event(
            4,
            "run.terminated",
            {
                "exit": "reviewer_pass",
                "summary": {
                    "headline": "Passed",
                    "missing": [],
                    "unresolved_findings": [],
                    "retries": {"count": 0, "budget": 2},
                    "event_count": 4,
                    "elapsed_ms": 400,
                    "est_cost": 0.0,
                },
            },
            actor=ORCHESTRATOR,
            stage=None,
            reason="The Reviewer passed the proposal.",
        ),
    ]
    (folder / "events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return read_events(folder / "events.jsonl")


def test_a_run_records_what_each_seat_cost_and_how_often_it_was_accepted(tmp_path: Path) -> None:
    folder = tmp_path / "runs" / "r1"
    events = write_run(folder)
    ref = "pb-r1-05"
    for attempt, accepted, error in (
        (1, False, "the draft has no usable provenance tags. Tag every figure"),
        (2, True, ""),
    ):
        append_attempt(
            folder,
            SeatAttempt(ref, "writer", "qwen3.5 9b, local", "ollama", attempt, accepted, error),
        )

    path = write_metrics(folder, events)
    assert path.name == METRICS_FILE
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["dataset_id"] == "clean-run" and data["exit"] == "reviewer_pass"
    writer = next(seat for seat in data["seats"] if seat["agent_id"] == "writer")
    assert writer["model"] == "qwen3.5 9b, local"
    assert writer["calls"] == 1 and writer["tokens_in"] == 9000 and writer["wall_ms"] == 30000
    assert writer["tool_calls"] == 1
    assert writer["replies"] == 1 and writer["corrections"] == 1 and writer["accepted_first_time"] == 0
    assert writer["reasons"] == {"provenance_tags": 1}


def test_a_run_with_no_attempt_log_is_read_from_its_rejected_replies(tmp_path: Path) -> None:
    folder = tmp_path / "runs" / "r2"
    events = write_run(folder)
    (folder / "prompts").mkdir()
    (folder / "prompts" / "pb-r2-05.json").write_text(
        json.dumps({"system": "You are Willa, the Writer on an electrical RFP team.", "model": {}}),
        encoding="utf-8",
    )
    (folder / "rejected").mkdir()
    (folder / "rejected" / "pb-r2-05-1.txt").write_text(
        "Rejected: the draft has no usable provenance tags\n\n{}\n", encoding="utf-8"
    )
    data = run_metrics(events, folder)
    writer = next(seat for seat in data["seats"] if seat["agent_id"] == "writer")
    assert writer["replies"] == 1, "one recorded bundle is one seat call"
    assert writer["corrections"] == 1 and writer["accepted_first_time"] == 0
    assert writer["reasons"] == {"provenance_tags": 1}


def test_the_report_groups_by_seat_and_model(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    for name in ("r1", "r2"):
        folder = runs / name
        events = write_run(folder)
        append_attempt(folder, SeatAttempt("pb-1", "writer", "qwen3.5 9b, local", "ollama", 1, True, ""))
        write_metrics(folder, events)

    module = load_script()
    groups, collected = module.collect(runs)
    assert len(collected) == 2
    writer = next(g for g in groups if g.agent_id == "writer")
    assert writer.runs == 2 and writer.calls == 2 and writer.replies == 2
    assert writer.first_time_rate == 1.0
    assert writer.tokens_in_per_call == 9000 and writer.seconds_per_call == 30.0
    text = module.report(groups, collected)
    assert "| writer | qwen3.5 9b, local |" in text and "Runs recorded: 2" in text


def test_a_seat_that_never_replied_is_still_counted() -> None:
    assert categorise("the reply hit the model's output limit") == "output_limit"
    assert categorise("the model could not be reached: ConnectionError") == "provider_error"


def test_reasons_are_grouped_so_a_pattern_shows() -> None:
    assert categorise("the draft has no usable provenance tags") == "provenance_tags"
    assert categorise("no price came from price_list_lookup") == "tool_not_used"
    assert (
        categorise("L1 troffer: your unit_price is 185.0, the lookup returned 142.00")
        == "figures_not_from_tool"
    )
    assert categorise("price_list_lookup returned no result in this turn") == "figures_not_from_tool"
    assert categorise("EMT 21 mm: your quantity is 32.0, the Estimator's is 5.0") == "figures_not_from_tool"
    assert (
        categorise("these dollar amounts appear in nothing you were given: $36,882.58")
        == "amount_not_in_sources"
    )
    assert (
        categorise("the Estimator's concern is not carried in the Assumptions section") == "concern_dropped"
    )
    assert (
        categorise("verdict ready_with_assumptions contradicts the checklist grades") == "checklist_grading"
    )
    assert categorise("something new") == "other"


def test_a_run_folder_says_what_it_is(tmp_path: Path) -> None:
    from app.runs.metrics import MANIFEST_FILE, dataset_digest, write_manifest

    folder = tmp_path / "runs" / "r3"
    events = write_run(folder)
    append_attempt(folder, SeatAttempt("pb-1", "writer", "qwen3.5 9b, local", "ollama", 1, True, ""))
    path = write_manifest(folder, events, {"config": {"cost_ceiling": 1.0}})
    assert path.name == MANIFEST_FILE
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["dataset_id"] == "clean-run" and manifest["exit"] == "reviewer_pass"
    assert manifest["roster"][0]["agent_id"] == "writer"
    assert manifest["config"]["cost_ceiling"] == 1.0
    assert "events.jsonl" in manifest["files"] and ATTEMPTS_FILE in manifest["files"]

    inputs = tmp_path / "inputs"
    (inputs / "drawings").mkdir(parents=True)
    (inputs / "drawings" / "E-001.pdf").write_bytes(b"one")
    first = dataset_digest(inputs)
    assert first and first == dataset_digest(inputs), "the same inputs give the same digest"
    (inputs / "drawings" / "E-001.pdf").write_bytes(b"two")
    assert dataset_digest(inputs) != first, "changed inputs give a different digest"
