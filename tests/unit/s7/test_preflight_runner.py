"""Pre-flight results: storage and the runner (S7 research D1; spec 012 research D6, D7).
The header policy that replaced S7's essential flag is tested in tests/unit/s12/test_header_policy.py."""

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
    CheckResult,
    PreflightResult,
    format_stamp,
    load_result,
    save_result,
)
from app.preflight.runner import payload, run_preflight


def cr(check_id: str, status: str, detail: str = "d") -> CheckResult:
    return CheckResult(
        check_id, check_id.replace("_", " ").capitalize(), status, detail, 1, "2026-09-14T08:12:00"
    )


def context(tmp_path: Path) -> CheckContext:
    settings = Settings(runs_dir=tmp_path / "runs")
    return CheckContext(
        settings=settings, config=ModelConfig(providers={}, models={}, seats={}), availability={}
    )


def test_counts_exclude_skipped_checks(tmp_path: Path) -> None:
    result = PreflightResult("laptop", "2026-09-14T08:12:00", (cr("a", PASS), cr("b", SKIP), cr("c", FAIL)))
    body = payload(result, context(tmp_path))
    # The family row is not applicable with no Reviewer or Writer seat, so it counts for neither.
    assert (body["passed"], body["applicable"]) == (1, 2)


def test_load_result_is_none_when_missing_corrupt_or_another_schema(tmp_path: Path) -> None:
    assert load_result(tmp_path) is None
    (tmp_path / "preflight.json").write_text("{not json", encoding="utf-8")
    assert load_result(tmp_path) is None
    (tmp_path / "preflight.json").write_text(
        json.dumps({"schema": 1, "ran_at": "x", "status": "pass", "checks": []}), encoding="utf-8"
    )
    assert load_result(tmp_path) is None


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    result = PreflightResult("cloud", "2026-09-14T08:12:00-04:00", (cr("a", PASS), cr("tunnel", FAIL)))
    path = save_result(tmp_path / "runs", result)
    assert path == tmp_path / "runs" / "preflight.json"
    assert load_result(tmp_path / "runs") == result


def test_stamp_reads_like_the_export() -> None:
    assert format_stamp("2026-09-14T08:12:00") == "14 Sep 2026, 08:12"
    assert format_stamp("2026-09-04T08:12:00") == "4 Sep 2026, 08:12"


async def test_runner_stores_the_result_and_survives_bad_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def passes(_: CheckContext) -> CheckResult:
        return cr("ok", PASS, "fine")

    async def explodes(_: CheckContext) -> CheckResult:
        raise RuntimeError("secret=zq9")

    async def hangs(_: CheckContext) -> CheckResult:
        await asyncio.sleep(5)
        return cr("slow", PASS)

    checks = [
        Check("ok", "Ok", 1.0, passes),
        Check("boom", "Boom", 1.0, explodes),
        Check("slow", "Slow", 0.01, hangs),
    ]
    monkeypatch.setattr("app.preflight.runner.cloud_model_checks", lambda _ctx: [])
    monkeypatch.setattr("app.preflight.runner.sequential_checks", lambda _ctx: checks)
    monkeypatch.setattr("app.preflight.runner.checks_for", lambda _ctx: checks)
    monkeypatch.setattr("app.preflight.runner.GRACE_S", 0.0)
    ctx = context(tmp_path)
    result = await run_preflight(ctx)
    by_id = {c.id: c for c in result.checks}
    assert by_id["ok"].status == PASS
    assert by_id["boom"].status == FAIL and by_id["boom"].detail == "check failed (RuntimeError)"
    assert "zq9" not in by_id["boom"].detail
    assert by_id["slow"].status == FAIL and by_id["slow"].detail == "no answer within 0 s"
    assert result.ran_at is not None
    assert load_result(ctx.settings.runs_dir) == result


def test_pending_payload_lists_every_check_pending(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def never(_: CheckContext) -> CheckResult:
        raise AssertionError("pending never runs a check")

    checks = [Check("a", "A", 1.0, never), Check("b", "B", 1.0, never)]
    monkeypatch.setattr("app.preflight.runner.checks_for", lambda _ctx: checks)
    body = payload(None, context(tmp_path))
    assert body["header"]["status"] == PENDING and body["ran_at"] is None
    assert [c["name"] for c in body["checks"]][:2] == ["A", "B"]
    assert {c["status"] for c in body["checks"][:2]} == {PENDING}
    assert {c["detail"] for c in body["checks"][:2]} == {"Pending"}
    assert body["checks"][-1]["id"] == "family"
