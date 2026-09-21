"""The rows spec 012 adds or changes: recordings, the stored result's merge, concurrent probes, and
names-only env facts (research D6, D7, D9)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.live.seat_call import SeatModel
from app.preflight.checks import check_env, check_intro_recording, check_replays, recheck_checks
from app.preflight.result import FAIL, PASS, CheckResult, PreflightResult, load_result, merge, save_result
from app.preflight.runner import payload, recheck, run_preflight
from tests.unit.s7.test_preflight_checks import MARKER, context


async def test_intro_recording_and_replays_rows(tmp_path: Path) -> None:
    ctx = context(tmp_path, {"estimator": "sonnet"})
    assert (await check_intro_recording(ctx)).status == PASS
    assert (await check_replays(ctx)).status == PASS
    ctx.intro_recording_present = lambda: False
    ctx.datasets_without_replay = lambda: ["prospect-b", "prospect-c"]
    intro = await check_intro_recording(ctx)
    assert (intro.status, intro.detail) == (FAIL, "The pinned run is not on this machine")
    replays = await check_replays(ctx)
    assert (replays.status, replays.detail) == (FAIL, "No recording or golden log for prospect-b, prospect-c")


def test_merge_replaces_by_id_keeps_ran_at_and_starts_without_a_full_run() -> None:
    first = CheckResult("model:a", "A", PASS, "ok", 1, "2026-09-21T09:00:00")
    other = CheckResult("disk", "Disk", PASS, "ok", 1, "2026-09-21T09:00:00")
    stored = PreflightResult("laptop", "2026-09-21T09:00:00", (first, other))
    newer = CheckResult("model:a", "A", FAIL, "no", 1, "2026-09-21T09:30:00")
    added = CheckResult("model:b", "B", PASS, "ok", 1, "2026-09-21T09:30:00")
    merged = merge(stored, [newer, added], "laptop")
    assert merged.ran_at == "2026-09-21T09:00:00"
    assert [c.id for c in merged.checks] == ["model:a", "disk", "model:b"]
    assert merged.row("model:a") == newer and merged.row("disk") == other
    fresh = merge(None, [newer], "laptop")
    assert fresh.ran_at is None and fresh.checks == (newer,)


def test_nothing_counts_until_a_full_preflight_has_run(tmp_path: Path) -> None:
    """The family row passes on read before anything has run; it must not read as all checks pass."""
    ctx = context(tmp_path, {"writer": "sonnet", "reviewer": "gemini"})
    pending = payload(None, ctx)
    assert (pending["passed"], pending["applicable"]) == (0, 0)
    assert next(c for c in pending["checks"] if c["id"] == "family")["status"] == PASS
    rechecked = merge(
        None, [CheckResult("model:gemini", "G", PASS, "ok", 1, "2026-09-21T09:30:00")], "laptop"
    )
    assert (payload(rechecked, ctx)["passed"], payload(rechecked, ctx)["applicable"]) == (0, 0)


def test_a_result_with_only_rechecks_round_trips(tmp_path: Path) -> None:
    fresh = merge(None, [CheckResult("model:a", "A", PASS, "ok", 1, "2026-09-21T09:30:00")], "laptop")
    save_result(tmp_path, fresh)
    assert load_result(tmp_path) == fresh


async def test_every_cloud_probe_starts_before_the_first_finishes(tmp_path: Path) -> None:
    ctx = context(tmp_path, {"estimator": "sonnet"}, {"bedrock": True, "google": True, "xai": True})
    started: list[str] = []
    all_started = asyncio.Event()

    async def probe(seat_model: SeatModel) -> None:
        started.append(seat_model.model.model_id)
        if len(started) == 3:
            all_started.set()
        await asyncio.wait_for(all_started.wait(), 2.0)

    ctx.probe = probe
    result = await run_preflight(ctx)
    cloud = [
        c for c in result.checks if c.subject.get("kind") == "model" and c.subject.get("provider") != "ollama"
    ]
    assert len(started) == 3
    assert {c.status for c in cloud} == {PASS}


async def test_env_facts_carry_names_never_values(tmp_path: Path) -> None:
    ctx = context(tmp_path, {"reviewer": "gemini"}, demo_password=MARKER)
    ctx.env = {"XAI_API_KEY": MARKER}
    row = await check_env(ctx)
    assert MARKER not in str(row.to_json())
    assert row.subject["keys_missing"] == {"google": "GEMINI_API_KEY"}


def test_recheck_rows_for_cloud_and_local_models(tmp_path: Path) -> None:
    ctx = context(tmp_path, {"estimator": "sonnet"})
    assert [c.id for c in recheck_checks(ctx, "gemini")] == ["model:gemini", "env"]
    assert [c.id for c in recheck_checks(ctx, "qwen")] == ["ollama", "model:qwen", "env"]
    with pytest.raises(ValueError, match="unknown model nope"):
        recheck_checks(ctx, "nope")


async def test_recheck_merges_into_the_stored_result(tmp_path: Path) -> None:
    ctx = context(tmp_path, {"estimator": "sonnet"}, {"bedrock": True, "google": True})
    await run_preflight(ctx)
    before = load_result(ctx.settings.runs_dir)
    assert before is not None

    async def refuse(_: SeatModel) -> None:
        raise RuntimeError("404")

    ctx.probe = refuse
    rows = await recheck(ctx, "gemini")
    assert [r.id for r in rows] == ["model:gemini", "env"]
    after = load_result(ctx.settings.runs_dir)
    assert after is not None and after.ran_at == before.ran_at
    assert after.row("model:gemini") is not None and after.row("model:gemini").status == FAIL  # type: ignore[union-attr]
    assert after.row("disk") == before.row("disk")
