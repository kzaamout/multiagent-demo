"""Pre-flight results: one record per check, one stored result per run (S7 data-model.md).

Nothing here is an event. The stored file under the runs folder is the single source the page
rows, the header dot on every page, and `/api/meta` read from (research D1).
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SCHEMA = 1
RESULT_FILE = "preflight.json"

PASS = "pass"
FAIL = "fail"
SKIP = "skip"
PENDING = "pending"
WARN = "warn"

GLYPHS = {PENDING: "○", PASS: "✓", WARN: "!", FAIL: "✕"}


@dataclass(frozen=True)
class CheckResult:
    id: str
    name: str
    status: str
    detail: str
    essential: bool
    elapsed_ms: int = 0

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> CheckResult:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            status=str(data["status"]),
            detail=str(data.get("detail", "")),
            essential=bool(data.get("essential", False)),
            elapsed_ms=int(data.get("elapsed_ms", 0)),
        )


@dataclass(frozen=True)
class PreflightResult:
    run_mode: str
    ran_at: str
    status: str
    passed: int
    applicable: int
    checks: tuple[CheckResult, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "run_mode": self.run_mode,
            "ran_at": self.ran_at,
            "status": self.status,
            "passed": self.passed,
            "applicable": self.applicable,
            "checks": [c.to_json() for c in self.checks],
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> PreflightResult:
        if int(data.get("schema", 0)) != SCHEMA:
            raise ValueError(f"preflight result schema {data.get('schema')} is not {SCHEMA}")
        checks = tuple(CheckResult.from_json(c) for c in data.get("checks", []))
        return cls(
            run_mode=str(data.get("run_mode", "laptop")),
            ran_at=str(data["ran_at"]),
            status=str(data["status"]),
            passed=int(data.get("passed", 0)),
            applicable=int(data.get("applicable", 0)),
            checks=checks,
        )


def overall(checks: list[CheckResult] | tuple[CheckResult, ...]) -> str:
    """fail when an essential check failed, warn when only non-essential ones did, else pass (research D2)."""
    failed = [c for c in checks if c.status == FAIL]
    if any(c.essential for c in failed):
        return FAIL
    if failed:
        return WARN
    return PASS


def build_result(run_mode: str, ran_at: str, checks: list[CheckResult]) -> PreflightResult:
    passed = sum(1 for c in checks if c.status == PASS)
    applicable = sum(1 for c in checks if c.status in (PASS, FAIL))
    return PreflightResult(
        run_mode=run_mode,
        ran_at=ran_at,
        status=overall(checks),
        passed=passed,
        applicable=applicable,
        checks=tuple(checks),
    )


def result_path(runs_dir: Path) -> Path:
    return runs_dir / RESULT_FILE


def load_result(runs_dir: Path) -> PreflightResult | None:
    """The stored result, or None when there is none or it cannot be read. Never a guess."""
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


@dataclass(frozen=True)
class HeaderState:
    status: str
    glyph: str
    title: str


def header_state(result: PreflightResult | None) -> HeaderState:
    """What the dot in every header shows, from the stored result alone (spec 2.4)."""
    if result is None:
        return HeaderState(PENDING, GLYPHS[PENDING], "Pre-flight: not run yet")
    stamp = format_stamp(result.ran_at)
    failed = [c for c in result.checks if c.status == FAIL]
    if result.status == FAIL:
        first = next((c for c in failed if c.essential), failed[0] if failed else None)
        name = first.name if first else "an essential check"
        return HeaderState(FAIL, GLYPHS[FAIL], f"Pre-flight: {name} failed, {stamp}")
    if result.status == WARN:
        name = failed[0].name if failed else "a non-essential check"
        return HeaderState(WARN, GLYPHS[WARN], f"Pre-flight: {name} failed (non-essential), {stamp}")
    return HeaderState(PASS, GLYPHS[PASS], f"Pre-flight: all checks pass, {stamp}")
