"""Every header carries the running checkout's short git hash and commit date (spec 2.2, roadmap S7)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import httpx
import pytest

from app.config import ROOT, Settings
from app.main import create_app


def git(*args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip("git is not available")
    if out.returncode != 0:
        pytest.skip("not a git checkout")
    return out.stdout.strip()


async def test_build_stamp_matches_git_on_every_page(tmp_path: Path) -> None:
    short = git("rev-parse", "--short", "HEAD")
    date = git("log", "-1", "--format=%cs")
    stamp = f"build {short} · {date}"
    app = create_app(Settings(runs_dir=tmp_path / "runs", agent_mode="stub"))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        for path in ("/demo", "/settings", "/preflight"):
            html = (await client.get(path)).text
            assert stamp in html, path
            assert "{{BUILD_STAMP}}" not in html and "{{PREFLIGHT_" not in html, path
        meta = (await client.get("/api/meta")).json()
        assert meta["build"] == {"hash": short, "date": date}
