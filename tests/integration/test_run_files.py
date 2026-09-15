from __future__ import annotations

from pathlib import Path

import httpx

from app.config import Settings
from app.main import create_app


async def test_run_files_are_served_read_only_inside_the_run_folder(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    draft = runs / "run-1" / "drafts" / "draft-v1.md"
    draft.parent.mkdir(parents=True)
    draft.write_text("# Proposal\n\nTotal {{$10|src:e1}}.\n", encoding="utf-8")
    (tmp_path / "secret.md").write_text("outside", encoding="utf-8")
    (runs / "run-1" / "notes.txt").write_text("not served", encoding="utf-8")
    app = create_app(Settings(runs_dir=runs, agent_mode="stub"))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        ok = await client.get("/api/runs/run-1/files/drafts/draft-v1.md")
        assert ok.status_code == 200 and "{{$10|src:e1}}" in ok.text
        for bad in [
            "/api/runs/run-1/files/../../secret.md",
            "/api/runs/run-1/files/..%2F..%2Fsecret.md",
            "/api/runs/..%2F/files/secret.md",
            "/api/runs/run-1/files/notes.txt",
            "/api/runs/run-1/files/drafts/draft-v9.md",
        ]:
            assert (await client.get(bad)).status_code == 404, bad
