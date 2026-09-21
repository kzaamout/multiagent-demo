"""Run the pre-flight checks, store the rows, and serve the page's payload (S7 research D1; spec 012
research D6, D8, D10).

A full run probes every cloud model at the same time, alongside the rows that must run in order.
A recheck after a seat change reruns only the chosen model's rows and the env row and merges them
into the stored result. Neither is an event or touches a run.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.live.providers import ModelConfig
from app.preflight.checks import (
    Check,
    CheckContext,
    checks_for,
    cloud_model_checks,
    recheck_checks,
    sequential_checks,
)
from app.preflight.header import HeaderState, header_state, rows_on_read, seats_on_model
from app.preflight.result import (
    FAIL,
    PASS,
    PENDING,
    CheckResult,
    PreflightResult,
    format_stamp,
    load_result,
    merge,
    now_iso,
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
    return CheckResult(check.id, check.name, FAIL, detail, elapsed, now_iso(), dict(check.subject))


async def _in_order(checks: list[Check], ctx: CheckContext) -> list[CheckResult]:
    return [await _run_one(check, ctx) for check in checks]


async def run_preflight(ctx: CheckContext) -> PreflightResult:
    """Every cloud model probed at the same time, alongside the ordered rows; then the stored result
    in the page's order."""
    ran_at = now_iso()
    cloud = cloud_model_checks(ctx)
    probes = asyncio.gather(*(_run_one(check, ctx) for check in cloud))
    ordered = _in_order(sequential_checks(ctx), ctx)
    cloud_rows, ordered_rows = await asyncio.gather(probes, ordered)
    by_id = {row.id: row for row in [*cloud_rows, *ordered_rows]}
    rows = tuple(by_id[check.id] for check in checks_for(ctx))
    result = PreflightResult(run_mode=ctx.settings.run_mode, ran_at=ran_at, checks=rows)
    save_result(ctx.settings.runs_dir, result)
    return result


async def recheck(ctx: CheckContext, model_key: str) -> tuple[CheckResult, ...]:
    """Rerun what a seat change touches and merge it into the stored result (research D10).
    Raises ValueError for a key the registry does not hold."""
    checks = recheck_checks(ctx, model_key)
    rows = await _in_order(checks, ctx)
    runs_dir = ctx.settings.runs_dir
    save_result(runs_dir, merge(load_result(runs_dir), rows, ctx.settings.run_mode))
    return tuple(rows)


def header_json(state: HeaderState) -> dict[str, str]:
    return {"status": state.status, "glyph": state.glyph, "title": state.title}


def row_json(row: CheckResult, on_model: dict[str, list[str]]) -> dict[str, Any]:
    body = row.to_json()
    if row.subject.get("kind") == "model":
        body["seats"] = list(on_model.get(str(row.subject.get("model_key", "")), []))
    return body


def payload(result: PreflightResult | None, ctx: CheckContext, *, running: bool = False) -> dict[str, Any]:
    """What the Pre-flight page renders (contracts/http-api.md): the stored rows as read for the
    seats in force, the family row, the counts, and the header state. With nothing stored, every
    row pending."""
    config = ctx.config
    on_model = seats_on_model(config)
    if result is None:
        rows = [
            CheckResult(c.id, c.name, PENDING, "Pending", 0, "", dict(c.subject)) for c in checks_for(ctx)
        ]
        rows.append(rows_on_read(None, config)[-1])
    else:
        rows = rows_on_read(result, config)
    ran_at = result.ran_at if result is not None else None
    # Until a full pre-flight has run there is nothing to count: a family row worked out on read, or
    # a few rechecked rows, must never read as "All checks pass".
    counted = rows if ran_at else []
    return {
        "run_mode": ctx.settings.run_mode,
        "ran_at": ran_at,
        "stamp": format_stamp(ran_at) if ran_at else "",
        "passed": sum(1 for r in counted if r.status == PASS),
        "applicable": sum(1 for r in counted if r.status in (PASS, FAIL)),
        "running": running,
        "header": header_json(header_state(result, config, ctx.settings.run_mode)),
        "checks": [row_json(r, on_model) for r in rows],
    }


def recheck_payload(rows: tuple[CheckResult, ...], ctx: CheckContext) -> dict[str, Any]:
    config: ModelConfig = ctx.config
    on_model = seats_on_model(config)
    read = [
        row
        for row in rows_on_read(load_result(ctx.settings.runs_dir), config)
        if row.id in {r.id for r in rows}
    ]
    return {
        "checks": [row_json(r, on_model) for r in read],
        "header": header_json(
            header_state(load_result(ctx.settings.runs_dir), config, ctx.settings.run_mode)
        ),
    }
