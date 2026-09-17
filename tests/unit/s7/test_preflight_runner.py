"""Pre-flight results: classification, storage, the header state, and the runner (S7 research D1, D2)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from app.config import Settings
from app.live.providers import ModelConfig
from app.preflight.checks import Check, CheckContext
from app.preflight.result import (
    FAIL,
    PASS,
    PENDING,
    SKIP,
    WARN,
    CheckResult,
    build_result,
    format_stamp,
    header_state,
    load_result,
    overall,
    save_result,
)
from app.preflight.runner import pending_payload, run_preflight


def cr(check_id: str, status: str, essential: bool, detail: str = "d") -> CheckResult:
    return CheckResult(check_id, check_id.replace("_", " ").capitalize(), status, detail, essential, 1)


def context(tmp_path: Path) -> CheckContext:
    settings = Settings(runs_dir=tmp_path / "runs")
    return CheckContext(
        settings=settings, config=ModelConfig(providers={}, models={}, seats={}), availability={}
    )


def test_overall_follows_the_essential_flag() -> None:
    assert overall([cr("a", PASS, True), cr("b", PASS, False)]) == PASS
    assert overall([cr("a", PASS, True), cr("b", SKIP, False)]) == PASS
    assert overall([cr("a", PASS, True), cr("b", FAIL, False)]) == WARN
    assert overall([cr("a", FAIL, True), cr("b", FAIL, False)]) == FAIL
    assert overall([]) == PASS


def test_counts_exclude_skipped_checks() -> None:
    result = build_result(
        "laptop", "2026-09-14T08:12:00", [cr("a", PASS, True), cr("b", SKIP, False), cr("c", FAIL, False)]
    )
    assert (result.passed, result.applicable, result.status) == (1, 2, WARN)


def test_load_result_is_none_when_missing_corrupt_or_another_schema(tmp_path: Path) -> None:
    assert load_result(tmp_path) is None
    (tmp_path / "preflight.json").write_text("{not json", encoding="utf-8")
    assert load_result(tmp_path) is None
    (tmp_path / "preflight.json").write_text(
        json.dumps({"schema": 2, "ran_at": "x", "status": "pass"}), encoding="utf-8"
    )
    assert load_result(tmp_path) is None


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    result = build_result(
        "cloud", "2026-09-14T08:12:00-04:00", [cr("a", PASS, True), cr("tunnel", FAIL, False)]
    )
    path = save_result(tmp_path / "runs", result)
    assert path == tmp_path / "runs" / "preflight.json"
    assert load_result(tmp_path / "runs") == result


def test_header_state_for_the_four_states() -> None:
    pending = header_state(None)
    assert (pending.status, pending.glyph, pending.title) == (PENDING, "○", "Pre-flight: not run yet")
    ok = header_state(build_result("laptop", "2026-09-14T08:12:00", [cr("a", PASS, True)]))
    assert (ok.status, ok.glyph, ok.title) == (PASS, "✓", "Pre-flight: all checks pass, 14 Sep 2026, 08:12")
    warn = header_state(
        build_result("laptop", "2026-09-14T08:12:00", [cr("a", PASS, True), cr("tunnel", FAIL, False)])
    )
    assert (warn.status, warn.glyph) == (WARN, "!")
    assert warn.title == "Pre-flight: Tunnel failed (non-essential), 14 Sep 2026, 08:12"
    fail = header_state(
        build_result("laptop", "2026-09-14T08:12:00", [cr("tunnel", FAIL, False), cr("disk", FAIL, True)])
    )
    assert (fail.status, fail.glyph, fail.title) == (FAIL, "✕", "Pre-flight: Disk failed, 14 Sep 2026, 08:12")


def test_stamp_reads_like_the_export() -> None:
    assert format_stamp("2026-09-14T08:12:00") == "14 Sep 2026, 08:12"
    assert format_stamp("2026-09-04T08:12:00") == "4 Sep 2026, 08:12"


async def test_runner_stores_the_result_and_survives_bad_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def passes(_: CheckContext) -> CheckResult:
        return cr("ok", PASS, True, "fine")

    async def explodes(_: CheckContext) -> CheckResult:
        raise RuntimeError("secret=zq9")

    async def hangs(_: CheckContext) -> CheckResult:
        await asyncio.sleep(5)
        return cr("slow", PASS, False)

    checks = [
        Check("ok", "Ok", True, 1.0, passes),
        Check("boom", "Boom", False, 1.0, explodes),
        Check("slow", "Slow", False, 0.01, hangs),
    ]
    monkeypatch.setattr("app.preflight.runner.checks_for", lambda _ctx: checks)
    monkeypatch.setattr("app.preflight.runner.GRACE_S", 0.0)
    ctx = context(tmp_path)
    result = await run_preflight(ctx)
    by_id = {c.id: c for c in result.checks}
    assert by_id["ok"].status == PASS
    assert by_id["boom"].status == FAIL and by_id["boom"].detail == "check failed (RuntimeError)"
    assert "zq9" not in by_id["boom"].detail
    assert by_id["slow"].status == FAIL and by_id["slow"].detail == "no answer within 0 s"
    assert result.status == WARN
    assert load_result(ctx.settings.runs_dir) == result


def test_pending_payload_lists_every_check_pending(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def never(_: CheckContext) -> CheckResult:
        raise AssertionError("pending never runs a check")

    checks = [Check("a", "A", True, 1.0, never), Check("b", "B", False, 1.0, never)]
    monkeypatch.setattr("app.preflight.runner.checks_for", lambda _ctx: checks)
    body = pending_payload(context(tmp_path))
    assert body["status"] == PENDING and body["ran_at"] is None
    assert [c["name"] for c in body["checks"]] == ["A", "B"]
    assert {c["status"] for c in body["checks"]} == {PENDING}
    assert {c["detail"] for c in body["checks"]} == {"Pending"}
