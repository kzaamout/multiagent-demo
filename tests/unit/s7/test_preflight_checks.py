"""Each pre-flight check with its outside calls injected (S7 research D3, D4, D7, D9).

No network, no compiler, no model: the context carries scripted probes. Detail lines are checked
for the export's wording and for never carrying a value from the environment (constitution XVII).
"""

from __future__ import annotations

import asyncio
from collections import namedtuple
from pathlib import Path
from typing import Any, cast

import pytest

from app.compile.pipeline import Compiled, CompileError
from app.config import Settings
from app.live.providers import Availability, ModelConfig, ModelSpec, SeatChoice
from app.live.seat_call import SeatModel
from app.preflight import checks as checks_module
from app.preflight.checks import (
    ALL_KEYS_PRESENT,
    CLOUD_MODE_SKIP,
    CheckContext,
    check_disk,
    check_env,
    check_ollama,
    check_png,
    check_typst,
    checks_for,
    provider_checks,
)
from app.preflight.result import FAIL, PASS, SKIP
from app.schema.events import Model

MARKER = "zq9-secret-marker-7f3a"
Usage = namedtuple("Usage", "total used free")


def make_config(seats: dict[str, str]) -> ModelConfig:
    providers: dict[str, dict[str, Any]] = {
        "bedrock": {"label": "Amazon Bedrock", "region": "ca-central-1"},
        "google": {"label": "Google Gemini", "env_key": "GEMINI_API_KEY"},
        "xai": {"label": "xAI", "env_key": "XAI_API_KEY"},
        "ollama": {"label": "Ollama", "host": "http://localhost:11434"},
    }
    models = {
        "sonnet": ModelSpec(
            key="sonnet",
            provider="bedrock",
            model_id="us.anthropic.claude-sonnet-5",
            label="claude-sonnet-5 via Bedrock",
            image_input=True,
            temperature=False,
            price_in=2.2,
            price_out=11.0,
        ),
        "gemini": ModelSpec(
            key="gemini",
            provider="google",
            model_id="gemini/gemini-2.5-pro",
            label="gemini-2.5-pro via Google",
            image_input=True,
            temperature=True,
            price_in=1.25,
            price_out=10.0,
        ),
        "grok": ModelSpec(
            key="grok",
            provider="xai",
            model_id="xai/grok-4.6",
            label="grok-4.6 via xAI",
            image_input=True,
            temperature=True,
            price_in=2.0,
            price_out=6.0,
        ),
        "qwen": ModelSpec(
            key="qwen",
            provider="ollama",
            model_id="qwen3.5:9b",
            label="qwen3.5 9b, local",
            image_input=True,
            temperature=True,
            price_in=0,
            price_out=0,
        ),
    }
    return ModelConfig(
        providers=providers, models=models, seats={s: SeatChoice(model=m) for s, m in seats.items()}
    )


def fake_factory(config: ModelConfig, seat: str) -> SeatModel:
    spec = config.seat_spec(seat)
    return SeatModel(
        strands_model=cast(Any, object()),
        model=Model(provider=spec.provider, model_id=spec.model_id, label=spec.label),
        price_in=0,
        price_out=0,
    )


async def probe_ok(_: SeatModel) -> None:
    return None


def context(
    tmp_path: Path, seats: dict[str, str], available: dict[str, bool] | None = None, **settings: Any
) -> CheckContext:
    available = available or {}
    availability = {
        name: Availability(name, ok, "key present" if ok else "no credentials in .env")
        for name, ok in available.items()
    }
    return CheckContext(
        settings=Settings(runs_dir=tmp_path / "runs", **settings),
        config=make_config(seats),
        availability=availability,
        seat_model_factory=fake_factory,
        probe=probe_ok,
        fetch=lambda _url, _t: (200, 5),
        tags=lambda _host, _t: {"qwen3.5:9b"},
        disk_usage=lambda _p: Usage(100e9, 52e9, 48e9),
        compile=lambda folder, _md: compiled(folder, 2),
        aws_credentials=lambda: True,
        env={"GEMINI_API_KEY": "k"},
    )


def compiled(folder: Path, pages: int) -> Compiled:
    return Compiled(
        version=1,
        pdf_path="artifacts/v1/draft-v1.pdf",
        page_images=[f"artifacts/v1/page-{i:02d}.png" for i in range(1, pages + 1)],
        marker_count=0,
        unresolved=[],
        page_count=pages,
        elapsed_ms=1234,
        tool_versions={"typst": "0.15.1", "pandoc": "3.10.2"},
        markers_path="artifacts/v1/markers.json",
        pages_path="artifacts/v1/pages.json",
        typ_path="artifacts/v1/draft-v1.typ",
    )


# Provider rows


def test_provider_rows_come_from_seats_and_present_keys(tmp_path: Path) -> None:
    ctx = context(
        tmp_path, {"estimator": "sonnet", "reviewer": "qwen"}, {"bedrock": True, "google": True, "xai": False}
    )
    rows = provider_checks(ctx)
    assert [(r.id, r.name, r.essential) for r in rows] == [
        ("provider:bedrock", "Amazon Bedrock responds", True),
        ("provider:google", "Google Gemini responds", False),
    ]


async def test_provider_pass_names_the_seat_model(tmp_path: Path) -> None:
    ctx = context(tmp_path, {"estimator": "sonnet"}, {"bedrock": True})
    result = await provider_checks(ctx)[0].run(ctx)
    assert result.status == PASS and result.essential
    assert result.detail.startswith("claude-sonnet-5 answered in ")


async def test_provider_failure_carries_the_class_never_the_message(tmp_path: Path) -> None:
    ctx = context(tmp_path, {"reviewer": "gemini"}, {"google": True})

    async def refuse(_: SeatModel) -> None:
        raise RuntimeError(f"401 for key {MARKER}")

    ctx.probe = refuse
    result = await provider_checks(ctx)[0].run(ctx)
    assert result.status == FAIL
    assert result.detail == "gemini-2.5-pro did not answer (RuntimeError)"
    assert MARKER not in result.detail


async def test_provider_timeout_names_the_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = context(tmp_path, {"estimator": "sonnet"}, {"bedrock": True})

    async def slow(_: SeatModel) -> None:
        await asyncio.sleep(1)

    ctx.probe = slow
    monkeypatch.setattr(checks_module, "PROVIDER_TIMEOUT_S", 0.01)
    result = await provider_checks(ctx)[0].run(ctx)
    assert result.status == FAIL and result.detail.startswith("no answer within ")


# Ollama


async def test_ollama_pass_lists_the_seat_models(tmp_path: Path) -> None:
    ctx = context(tmp_path, {"reviewer": "qwen"})
    result = await check_ollama(ctx)
    assert (result.status, result.essential, result.detail) == (
        PASS,
        True,
        "qwen3.5:9b present at localhost:11434",
    )


async def test_ollama_missing_model_and_unreachable(tmp_path: Path) -> None:
    ctx = context(tmp_path, {"reviewer": "qwen"})
    ctx.tags = lambda _h, _t: set()
    assert (await check_ollama(ctx)).detail == "not pulled: qwen3.5:9b"

    def down(_h: str, _t: float) -> set[str]:
        raise ConnectionError("refused")

    ctx.tags = down
    result = await check_ollama(ctx)
    assert (result.status, result.detail) == (FAIL, "Ollama not reachable at localhost:11434")


async def test_ollama_in_cloud_mode_skips_or_names_the_local_seats(tmp_path: Path) -> None:
    clean = context(tmp_path, {"estimator": "sonnet"}, run_mode="cloud")
    result = await check_ollama(clean)
    assert (result.status, result.essential, result.detail) == (SKIP, False, CLOUD_MODE_SKIP)
    stuck = context(tmp_path, {"estimator": "sonnet", "pricing": "qwen"}, run_mode="cloud")
    result = await check_ollama(stuck)
    assert (result.status, result.essential) == (FAIL, True)
    assert result.detail == "pricing still on local models; move them in Settings"


# Typst and PNG


async def test_typst_and_png_rows_from_one_compile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks_module, "tools_available", lambda: {"typst": "0.15.1", "pandoc": "3.10.2"})
    ctx = context(tmp_path, {"estimator": "sonnet"})
    typst = await check_typst(ctx)
    assert (typst.status, typst.detail) == (PASS, "typst 0.15.1, 2 pages in 1.2 s")
    png = await check_png(ctx)
    assert (png.status, png.detail) == (PASS, "2 PNGs written to runs/preflight/")


async def test_typst_failures_and_png_without_a_compile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(checks_module, "tools_available", lambda: {"typst": None, "pandoc": "3.10.2"})
    ctx = context(tmp_path, {"estimator": "sonnet"})
    assert (await check_typst(ctx)).detail == "typst not on the path"
    assert (await check_png(ctx)).detail == "no compile to export"

    monkeypatch.setattr(checks_module, "tools_available", lambda: {"typst": "0.15.1", "pandoc": "3.10.2"})

    def broken(_folder: Path, _md: str) -> Compiled:
        raise CompileError("typst pdf: error: unknown variable\nmore")

    ctx.compile = broken
    result = await check_typst(ctx)
    assert (result.status, result.detail) == (FAIL, "typst pdf: error: unknown variable")
    ctx.compile = lambda folder, _md: compiled(folder, 0)
    assert (await check_typst(ctx)).status == PASS
    assert (await check_png(ctx)).detail == "Export produced 0 files"


# Disk


async def test_disk_around_the_threshold(tmp_path: Path) -> None:
    ctx = context(tmp_path, {"estimator": "sonnet"})
    assert (await check_disk(ctx)).detail == "48 GB free"
    ctx.disk_usage = lambda _p: Usage(100e9, 97e9, 3.2e9)
    result = await check_disk(ctx)
    assert (result.status, result.essential, result.detail) == (FAIL, True, "Under 5 GB free (3.2 GB)")

    def unreadable(_p: Path) -> Usage:
        raise OSError("no such drive")

    ctx.disk_usage = unreadable
    assert (await check_disk(ctx)).detail == "could not read free space"


# .env completeness


async def test_env_completeness_lists_missing_names_per_mode(tmp_path: Path) -> None:
    ctx = context(tmp_path, {"estimator": "sonnet", "reviewer": "gemini", "pricing": "qwen"})
    ctx.env = {}
    ctx.aws_credentials = lambda: False
    result = await check_env(ctx)
    assert (result.status, result.essential) == (FAIL, True)
    assert result.detail == "Missing DEMO_USERNAME, DEMO_PASSWORD, AWS credentials, GEMINI_API_KEY"
    ready = context(
        tmp_path, {"estimator": "sonnet", "reviewer": "gemini"}, demo_username="p", demo_password="s"
    )
    assert (await check_env(ready)).detail == ALL_KEYS_PRESENT
    # A provider no seat uses is not required, even with an env key defined for it.
    only_local = context(tmp_path, {"pricing": "qwen"}, demo_username="p", demo_password="s")
    only_local.env = {}
    assert (await check_env(only_local)).detail == ALL_KEYS_PRESENT


# Order and leaks


async def test_checks_in_page_order_and_no_value_from_env_in_any_detail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(checks_module, "tools_available", lambda: {"typst": "0.15.1", "pandoc": "3.10.2"})
    ctx = context(
        tmp_path,
        {"estimator": "sonnet", "reviewer": "gemini", "pricing": "qwen"},
        {"bedrock": True, "google": True},
        demo_password=MARKER,
    )
    ctx.env = {"GEMINI_API_KEY": MARKER}

    async def leaky(_: SeatModel) -> None:
        raise RuntimeError(MARKER)

    ctx.probe = leaky
    checks = checks_for(ctx)
    assert [c.id for c in checks] == [
        "provider:bedrock",
        "provider:google",
        "ollama",
        "typst",
        "png",
        "tunnel",
        "disk",
        "env",
    ]
    results = [await c.run(ctx) for c in checks]
    for result in results:
        assert MARKER not in result.detail, result.id
    assert results[5].status == SKIP  # no tunnel hostname in these settings
