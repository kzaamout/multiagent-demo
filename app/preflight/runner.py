"""Run the pre-flight checks in order, store the result, and serve the page's payload (S7 research D1)."""

from __future__ import annotations

import asyncio
import datetime as dt
import time
from typing import Any

from app.preflight.checks import Check, CheckContext, checks_for
from app.preflight.result import (
    FAIL,
    PENDING,
    CheckResult,
    PreflightResult,
    build_result,
    format_stamp,
    save_result,
)

GRACE_S = 5.0


async def _run_one(check: Check, ctx: CheckContext) -> CheckResult:
    started = time.monotonic()
    try:
        return await asyncio.wait_for(check.run(ctx), check.timeout_s + GRACE_S)
    except TimeoutError:
        detail = f"no answer within {int(check.timeout_s)} s"
    except Exception as error:  # noqa: BLE001
        detail = f"check failed ({type(error).__name__})"
    elapsed = int((time.monotonic() - started) * 1000)
    return CheckResult(check.id, check.name, FAIL, detail, check.essential, elapsed)


async def run_preflight(ctx: CheckContext) -> PreflightResult:
    """Every check in order, one after another, then the stored result."""
    ran_at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    results: list[CheckResult] = []
    for check in checks_for(ctx):
        results.append(await _run_one(check, ctx))
    result = build_result(ctx.settings.run_mode, ran_at, results)
    save_result(ctx.settings.runs_dir, result)
    return result


def pending_payload(ctx: CheckContext) -> dict[str, Any]:
    """What GET /api/preflight answers when nothing is stored: every row pending."""
    return {
        "status": PENDING,
        "run_mode": ctx.settings.run_mode,
        "ran_at": None,
        "stamp": "",
        "passed": 0,
        "applicable": 0,
        "checks": [
            {
                "id": c.id,
                "name": c.name,
                "status": PENDING,
                "detail": "Pending",
                "essential": c.essential,
                "elapsed_ms": 0,
            }
            for c in checks_for(ctx)
        ],
    }


def result_payload(result: PreflightResult) -> dict[str, Any]:
    body = result.to_json()
    body.pop("schema", None)
    body["stamp"] = format_stamp(result.ran_at)
    return body
