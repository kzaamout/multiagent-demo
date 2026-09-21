"""Scripts and styles are revalidated on every load, so an updated server's files are never shadowed
by an older cached copy (spec 012 research D16)."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.main import create_app


@pytest.mark.parametrize("path", ["/static/js/demo.js", "/static/js/clock.js", "/static/css/app.css"])
async def test_static_files_must_be_revalidated(tmp_path: Path, path: str) -> None:
    app = create_app(Settings(runs_dir=tmp_path / "runs", agent_mode="stub"))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        first = await client.get(path)
        assert first.status_code == 200
        assert first.headers["cache-control"] == "no-cache"
        etag = first.headers["etag"]
        again = await client.get(path, headers={"If-None-Match": etag})
        assert again.status_code == 304
        assert again.headers["cache-control"] == "no-cache"
