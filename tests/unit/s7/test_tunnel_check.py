"""The tunnel check with an injected fetch (S7 research D8)."""

from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.live.providers import ModelConfig
from app.preflight.checks import NO_TUNNEL_HOSTNAME, TUNNEL_DOWN, CheckContext, check_tunnel, checks_for
from app.preflight.header import AMBER
from app.preflight.result import FAIL, PASS, SKIP


def context(tmp_path: Path, hostname: str) -> CheckContext:
    return CheckContext(
        settings=Settings(runs_dir=tmp_path / "runs", tunnel_hostname=hostname),
        config=ModelConfig(providers={}, models={}, seats={}),
        availability={},
    )


async def test_pass_names_the_hostname_and_time(tmp_path: Path) -> None:
    ctx = context(tmp_path, "demo.example.com")
    seen: list[str] = []

    def fetch(url: str, _timeout: float) -> tuple[int, int]:
        seen.append(url)
        return 200, 320

    ctx.fetch = fetch
    result = await check_tunnel(ctx)
    assert (result.status, result.detail) == (PASS, "demo.example.com answered in 320 ms")
    assert seen == ["https://demo.example.com/login"]


async def test_transport_error_reads_not_connected(tmp_path: Path) -> None:
    ctx = context(tmp_path, "demo.example.com")

    def down(_url: str, _timeout: float) -> tuple[int, int]:
        raise ConnectionError("refused")

    ctx.fetch = down
    result = await check_tunnel(ctx)
    assert (result.status, result.detail) == (FAIL, TUNNEL_DOWN)


async def test_other_status_is_reported(tmp_path: Path) -> None:
    ctx = context(tmp_path, "demo.example.com")
    ctx.fetch = lambda _u, _t: (530, 40)
    result = await check_tunnel(ctx)
    assert (result.status, result.detail) == (FAIL, "HTTP 530 from the tunnel")


async def test_no_hostname_is_not_applicable(tmp_path: Path) -> None:
    ctx = context(tmp_path, "")
    result = await check_tunnel(ctx)
    assert (result.status, result.detail) == (SKIP, NO_TUNNEL_HOSTNAME)
    assert any(c.id == "tunnel" for c in checks_for(ctx))
    # A tunnel failure turns the dot amber, never red (spec 012 research D8).
    assert "tunnel" in AMBER
