"""An app whose pre-flight runs the real row set with every outside call injected (spec 012)."""

from __future__ import annotations

import asyncio
from collections import namedtuple
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from fastapi import FastAPI

from app.config import ROOT, Settings
from app.live.providers import Availability, ModelConfig
from app.live.seat_call import SeatModel
from app.main import create_app
from app.preflight import checks as checks_module
from app.preflight.checks import CheckContext
from app.schema.events import Model
from tests.unit.s7.test_preflight_checks import compiled

MARKER = "zq9-secret-marker-7f3a"
EXPORT_CONFIG = ROOT / "tests" / "fixtures" / "models-export.yaml"
Usage = namedtuple("Usage", "total used free")
AVAILABILITY = {
    "bedrock": Availability("bedrock", True, "credentials resolved"),
    "google": Availability("google", True, "key present"),
    "xai": Availability("xai", False, "no credentials in .env"),
    "anthropic": Availability("anthropic", False, "no credentials in .env"),
    "ollama": Availability("ollama", True, "reachable, models present"),
}


@dataclass
class Probes:
    """Which model ids fail, which calls were made, and an optional gate a probe waits on."""

    failing: set[str] = field(default_factory=set)
    calls: list[str] = field(default_factory=list)
    gate: asyncio.Event | None = None

    async def probe(self, seat_model: SeatModel) -> None:
        self.calls.append(seat_model.model.model_id)
        if self.gate is not None:
            await self.gate.wait()
        if seat_model.model.model_id in self.failing:
            raise RuntimeError(f"404 {MARKER}")


def fake_factory(config: ModelConfig, seat: str) -> SeatModel:
    spec = config.seat_spec(seat)
    return SeatModel(
        strands_model=cast(Any, object()),
        model=Model(provider=spec.provider, model_id=spec.model_id, label=spec.label),
        price_in=0,
        price_out=0,
    )


def app_client(
    tmp_path: Path, probes: Probes, monkeypatch: pytest.MonkeyPatch, **settings: Any
) -> httpx.AsyncClient:
    app = make_app(tmp_path, probes, monkeypatch, **settings)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def make_app(tmp_path: Path, probes: Probes, monkeypatch: pytest.MonkeyPatch, **settings: Any) -> FastAPI:
    monkeypatch.setattr(checks_module, "tools_available", lambda: {"typst": "0.15.1", "pandoc": "3.10.2"})
    cfg = Settings(runs_dir=tmp_path / "runs", agent_mode="stub", **settings)

    def context() -> CheckContext:
        return CheckContext(
            settings=cfg,
            config=ModelConfig(providers={}, models={}, seats={}),
            availability=dict(AVAILABILITY),
            seat_model_factory=fake_factory,
            probe=probes.probe,
            fetch=lambda _url, _t: (200, 5),
            tags=lambda _host, _t: {"llama3.1:8b"},
            disk_usage=lambda _p: Usage(100e9, 52e9, 48e9),
            compile=lambda folder, _md: compiled(folder, 2),
            aws_credentials=lambda: True,
            env={"GEMINI_API_KEY": MARKER},
        )

    return create_app(
        cfg,
        model_config=ModelConfig.load(EXPORT_CONFIG),
        availability=dict(AVAILABILITY),
        preflight_context=context,
    )


def dot(html: str) -> tuple[str, str, str]:
    start = html.index('data-part="preflight-indicator"')
    fragment = html[start : html.index("</span>", start)]
    status = fragment.split('data-status="')[1].split('"')[0]
    title = fragment.split('title="')[1].split('"')[0]
    glyph = fragment.rsplit(">", 1)[1]
    return status, glyph, title
