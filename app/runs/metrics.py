"""Per-seat model performance, captured for every run.

Every run writes `runs/<id>/metrics.json`: one row per seat with the model it ran on, what it cost, how
long it took, and how often its reply was accepted first time. The quality side comes from the seat
attempt log, `runs/<id>/seat-calls.jsonl`, written as each attempt is accepted or rejected. Runs recorded
before the attempt log existed fall back to the rejected reply files, which carry the same reasons.

`scripts/model_report.py` aggregates these rows across runs so a seat's model can be chosen from data.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.schema.events import SCHEMA_VERSION, Event

ATTEMPTS_FILE = "seat-calls.jsonl"
METRICS_FILE = "metrics.json"
MANIFEST_FILE = "run.json"

# Why a reply was sent back, grouped so that a pattern is visible across runs. First match wins.
CATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    # json_shape held three failures with three different fixes, so it is split (owner decision
    # 2026-09-17): the seat never replied, the seat replied with broken JSON, or the seat replied with
    # valid JSON in the wrong structure. missing_fields was the third of those said in other words, so it
    # is folded in rather than kept beside it.
    ("no_json", ("no json object",)),
    ("invalid_json", ("is not valid json",)),
    ("wrong_shape", ("expected", "field required", "input should", "needs headline", "needs", "must")),
    ("checklist_grading", ("checklist", "verdict", "clarification")),
    ("compile_failed", ("does not compile",)),
    ("concern_dropped", ("concern is not carried", "no assumptions section")),
    ("provenance_tags", ("provenance", "src:", "source id")),
    ("tool_not_used", ("price_list_lookup", "quantity_calculate", "as text instead of calling")),
    ("blocker_as_concern", ("blocker, not a concern",)),
    ("output_limit", ("output limit", "max tokens")),
    ("provider_error", ("could not be reached",)),
)


def categorise(error: str) -> str:
    """The short name for a rejection reason, for counting across runs."""
    text = error.lower()
    for name, words in CATEGORIES:
        if any(word in text for word in words):
            return name
    return "other"


@dataclass
class SeatAttempt:
    prompt_ref: str
    agent_id: str
    model: str
    provider: str
    attempt: int
    accepted: bool
    error: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    """temperature, num_ctx, think, max_tokens as the seat resolved them (decision 5a); empty on old lines."""
    instructions: str = ""
    """The version of the seat's instructions this attempt ran on; empty on lines recorded before capture."""

    def line(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass
class SeatRow:
    """One seat on one model in one run."""

    agent_id: str
    role: str
    model: str
    provider: str
    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    wall_ms: int = 0
    est_cost: float = 0.0
    tool_calls: int = 0
    replies: int = 0
    accepted_first_time: int = 0
    corrections: int = 0
    stopped_run: int = 0
    """Set when this seat ran out of attempts and the run ended because of it."""
    reasons: dict[str, int] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    """The hyperparameters the seat ran with, from its attempt lines; empty when the run predates capture."""
    instructions: str = ""
    """The version of the seat's instructions, so a lesson taught to a seat starts a new row in the report."""
    checks: dict[str, bool] = field(default_factory=dict)
    """Correctness checks the dataset defines for this seat, each met or not (app/runs/expectations.py)."""

    def add_reason(self, error: str) -> None:
        name = categorise(error)
        self.reasons[name] = self.reasons.get(name, 0) + 1


def append_attempt(folder: Path, attempt: SeatAttempt) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ATTEMPTS_FILE).open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(attempt.line() + "\n")


def read_attempts(folder: Path) -> list[SeatAttempt]:
    path = folder / ATTEMPTS_FILE
    if not path.exists():
        return _attempts_from_rejected(folder)
    attempts: list[SeatAttempt] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            attempts.append(SeatAttempt(**json.loads(line)))
    return attempts


def _attempts_from_rejected(folder: Path) -> list[SeatAttempt]:
    """Older runs kept only the rejected replies. Their first line carries the reason."""
    rejected = folder / "rejected"
    if not rejected.exists():
        return []
    attempts: list[SeatAttempt] = []
    for path in sorted(rejected.glob("*.txt")):
        stem, _, number = path.stem.rpartition("-")
        first = path.read_text(encoding="utf-8").splitlines()[:1]
        error = first[0].removeprefix("Rejected: ") if first else ""
        attempts.append(
            SeatAttempt(
                prompt_ref=stem,
                agent_id="",
                model="",
                provider="",
                attempt=int(number) if number.isdigit() else 1,
                accepted=False,
                error=error,
            )
        )
    return attempts


# A recorded prompt bundle names its seat in its opening sentence, "You are Anna, the Intake Analyst on ...".
ROLE_WORDS: tuple[tuple[str, str], ...] = (
    ("intake analyst", "intake"),
    ("estimator", "estimator"),
    ("pricing", "pricing"),
    ("writer", "writer"),
    ("reviewer", "reviewer"),
    ("orchestrator", "orchestrator"),
)


def _seat_of_text(system: str) -> str:
    opening = system.split("\n", 1)[0].lower()
    for words, agent_id in ROLE_WORDS:
        if words in opening:
            return agent_id
    return ""


def _seat_of(prompt_ref: str, folder: Path) -> str:
    """The seat a recorded prompt bundle belongs to, for runs whose attempts predate the attempt log."""
    path = folder / "prompts" / f"{prompt_ref}.json"
    if not path.exists():
        return ""
    bundle = json.loads(path.read_text(encoding="utf-8"))
    return _seat_of_text(str(bundle.get("system", "")))


def _bundles_per_seat(folder: Path) -> dict[str, int]:
    """One recorded bundle is one seat call, so this counts the replies a seat was asked for."""
    counts: dict[str, int] = {}
    prompts = folder / "prompts"
    if not prompts.exists():
        return counts
    for path in sorted(prompts.glob("*.json")):
        try:
            bundle = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        agent_id = _seat_of_text(str(bundle.get("system", "")))
        if agent_id:
            counts[agent_id] = counts.get(agent_id, 0) + 1
    return counts


def run_metrics(events: list[Event], folder: Path) -> dict[str, Any]:
    """Run level facts plus one row per seat, ready to write beside the recording."""
    rows: dict[str, SeatRow] = {}
    started = next((e for e in events if e.type == "run.started"), None)
    dataset = ""
    if started is not None:
        dataset = str(started.payload.get("dataset_id", ""))
        for agent in started.payload.get("roster", []):
            model = agent.get("model") or {}
            rows[agent["agent_id"]] = SeatRow(
                agent_id=agent["agent_id"],
                role=agent.get("role", ""),
                model=str(model.get("label", "")),
                provider=str(model.get("provider", "")),
            )

    def row(agent_id: str) -> SeatRow | None:
        if not agent_id:
            return None
        if agent_id not in rows:
            rows[agent_id] = SeatRow(agent_id=agent_id, role="", model="", provider="")
        return rows[agent_id]

    for event in events:
        payload = event.payload or {}
        seat = row(str(payload.get("agent_id", "")))
        if seat is None:
            continue
        if event.type == "meter.update":
            seat.calls += 1
            seat.tokens_in += int(payload.get("tokens_in", 0))
            seat.tokens_out += int(payload.get("tokens_out", 0))
            seat.wall_ms += int(payload.get("wall_ms", 0))
            seat.est_cost += float(payload.get("est_cost", 0.0))
        elif event.type == "tool.called":
            seat.tool_calls += 1

    last = events[-1] if events else None
    exit_value = str((last.payload or {}).get("exit", "")) if last is not None else ""

    logged = (folder / ATTEMPTS_FILE).exists()
    final_rejected: dict[str, bool] = {}
    for attempt in read_attempts(folder):
        agent_id = attempt.agent_id or _seat_of(attempt.prompt_ref, folder)
        seat = row(agent_id)
        if seat is None:
            continue
        if attempt.model and not seat.model:
            seat.model, seat.provider = attempt.model, attempt.provider
        if attempt.settings:
            seat.settings = dict(attempt.settings)
        if attempt.instructions:
            seat.instructions = attempt.instructions
        final_rejected[agent_id] = not attempt.accepted
        if attempt.accepted:
            seat.replies += 1
            if attempt.attempt == 1:
                seat.accepted_first_time += 1
            else:
                seat.corrections += 1
        else:
            seat.add_reason(attempt.error)

    # A seat stopped the run when it ran out of attempts: its last attempt was refused and the run ended
    # `stopped`. Counting the second refusal instead was right only while a seat had two attempts; three
    # attempts (decision 2026-09-17) made a second refusal survivable, and runs that went on to pass were
    # being charged with a stop. The failed final attempt still counts as a reply the seat produced.
    for agent_id, rejected in final_rejected.items():
        seat = row(agent_id)
        if seat is not None and rejected and exit_value == "stopped":
            seat.stopped_run += 1
            if logged:
                seat.replies += 1

    if not logged:
        # Before the attempt log, only the rejected replies were kept. One recorded bundle is one seat
        # call, so the replies a seat produced are its bundles, and a first attempt that was rejected and
        # not rejected again was accepted after one correction.
        for agent_id, bundles in _bundles_per_seat(folder).items():
            seat = row(agent_id)
            if seat is None:
                continue
            rejections = sum(seat.reasons.values())
            seat.corrections = max(rejections - seat.stopped_run * 2, 0)
            seat.replies = bundles
            seat.accepted_first_time = max(bundles - seat.corrections - seat.stopped_run, 0)

    from app.runs.expectations import golden_match, seat_checks

    for agent_id, checks in seat_checks(dataset, events, folder).items():
        seat = row(agent_id)
        if seat is not None:
            seat.checks = checks
    matched, note = golden_match(dataset, events)
    return {
        "run_id": folder.name,
        "started_at": events[0].ts if events else "",
        "dataset_id": dataset,
        "exit": exit_value,
        "golden_match": matched,
        "golden_note": note,
        "events": len(events),
        "seats": [asdict(seat) for seat in rows.values()],
    }


def dataset_digest(folder: Path) -> str:
    """A digest of a dataset's inputs, so a recorded run names the files it was given."""
    if not folder.exists():
        return ""
    digest = hashlib.sha256()
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        digest.update(path.relative_to(folder).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def write_manifest(folder: Path, events: list[Event], extra: dict[str, Any]) -> Path:
    """The run manifest: what was run, on what, with which settings, and what the folder holds."""
    started = next((e for e in events if e.type == "run.started"), None)
    last = events[-1] if events else None
    payload = (started.payload if started else {}) or {}
    manifest = {
        "run_id": folder.name,
        "schema_version": SCHEMA_VERSION,
        "workflow": payload.get("workflow", ""),
        "dataset_id": payload.get("dataset_id", ""),
        "mode": payload.get("mode", ""),
        "roster": payload.get("roster", []),
        "started_at": events[0].ts if events else "",
        "ended_at": last.ts if last is not None else "",
        "exit": str((last.payload or {}).get("exit", "")) if last is not None else "",
        "events": len(events),
        "files": sorted(
            p.relative_to(folder).as_posix()
            for p in folder.rglob("*")
            if p.is_file() and p.name != MANIFEST_FILE
        ),
        **extra,
    }
    path = folder / MANIFEST_FILE
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return path


def write_metrics(folder: Path, events: list[Event]) -> Path:
    path = folder / METRICS_FILE
    data = run_metrics(events, folder)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return path
