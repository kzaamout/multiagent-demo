"""Pre-flight results: one record per check, stored as facts (spec 012 data-model.md, schema 2).

Nothing here is an event. The stored file under the runs folder holds each row's status, detail,
and what it is about; whether a failed row turns the header dot red, amber, or not at all depends
on the seats in force when it is read, so it is decided in `app.preflight.header`, never stored.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

SCHEMA = 2
RESULT_FILE = "preflight.json"

PASS = "pass"
FAIL = "fail"
SKIP = "skip"
PENDING = "pending"
WARN = "warn"

GLYPHS = {PENDING: "○", PASS: "✓", WARN: "!", FAIL: "✕"}

FIXED: dict[str, Any] = {"kind": "fixed"}


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


@dataclass(frozen=True)
class CheckResult:
    id: str
    name: str
    status: str
    detail: str
    elapsed_ms: int = 0
    checked_at: str = ""
    subject: dict[str, Any] = field(default_factory=lambda: dict(FIXED))

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "elapsed_ms": self.elapsed_ms,
            "checked_at": self.checked_at,
            "subject": dict(self.subject),
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> CheckResult:
        subject = data.get("subject") or FIXED
        if not isinstance(subject, dict):
            raise ValueError("subject must be an object")
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            status=str(data["status"]),
            detail=str(data.get("detail", "")),
            elapsed_ms=int(data.get("elapsed_ms", 0)),
            checked_at=str(data.get("checked_at", "")),
            subject=dict(subject),
        )

    def stamped(self, when: str) -> CheckResult:
        return replace(self, checked_at=when)


@dataclass(frozen=True)
class PreflightResult:
    run_mode: str
    ran_at: str | None
    checks: tuple[CheckResult, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "run_mode": self.run_mode,
            "ran_at": self.ran_at,
            "checks": [c.to_json() for c in self.checks],
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> PreflightResult:
        if int(data.get("schema", 0)) != SCHEMA:
            raise ValueError(f"preflight result schema {data.get('schema')} is not {SCHEMA}")
        ran_at = data.get("ran_at")
        return cls(
            run_mode=str(data.get("run_mode", "laptop")),
            ran_at=str(ran_at) if ran_at else None,
            checks=tuple(CheckResult.from_json(c) for c in data.get("checks", [])),
        )

    def row(self, check_id: str) -> CheckResult | None:
        return next((c for c in self.checks if c.id == check_id), None)


def merge(result: PreflightResult | None, rows: list[CheckResult], run_mode: str) -> PreflightResult:
    """Replace stored rows by id and append new ones; `ran_at` stays the last full pre-flight's.
    With nothing stored, a result with only these rows and no full run (data model, merge rule)."""
    if result is None:
        return PreflightResult(run_mode=run_mode, ran_at=None, checks=tuple(rows))
    by_id = {r.id: r for r in rows}
    merged = [by_id.pop(c.id, c) for c in result.checks]
    merged.extend(r for r in rows if r.id in by_id)
    return PreflightResult(run_mode=result.run_mode, ran_at=result.ran_at, checks=tuple(merged))


def result_path(runs_dir: Path) -> Path:
    return runs_dir / RESULT_FILE


def load_result(runs_dir: Path) -> PreflightResult | None:
    """The stored result, or None when there is none, it cannot be read, or it is another schema.
    Never a guess: an older file reads as "not run yet"."""
    path = result_path(runs_dir)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return PreflightResult.from_json(data)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def save_result(runs_dir: Path, result: PreflightResult) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = result_path(runs_dir)
    path.write_text(json.dumps(result.to_json(), indent=1), encoding="utf-8", newline="\n")
    return path


def format_stamp(ran_at: str) -> str:
    """The export's stamp: "14 Sep 2026, 08:12" in local time. A naive value is taken as local."""
    when = dt.datetime.fromisoformat(ran_at)
    if when.tzinfo is not None:
        when = when.astimezone()
    return f"{when.day} {when:%b %Y, %H:%M}"
