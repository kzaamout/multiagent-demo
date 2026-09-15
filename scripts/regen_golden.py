"""Regenerate datasets/<id>/golden-events.jsonl from the stub scenarios.

Run only when a stub is deliberately changed. Refuses when stub files have uncommitted
changes unless --force is given, so a golden log always matches a committed stub.
Usage: uv run python scripts/regen_golden.py [--force] [dataset_id ...]
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.runs.golden import deterministic_run, terminal_exit, transitions, write_golden  # noqa: E402
from app.runs.registry import discover_datasets  # noqa: E402
from app.schema.events import validate_run  # noqa: E402


def stubs_dirty() -> bool:
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain", "--", "app/agents", "app/orchestrator", "app/schema"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return False
    return bool(out.strip())


async def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    force = "--force" in argv
    wanted = [a for a in argv if not a.startswith("--")]
    if stubs_dirty() and not force:
        print("refusing: stub, orchestrator, or schema files have uncommitted changes (use --force)")
        return 1
    settings = load_settings()
    for info in discover_datasets(settings.datasets_dir):
        if wanted and info.id not in wanted:
            continue
        events = await deterministic_run(settings, info.id)
        problems = validate_run(events)
        if problems:
            print(f"{info.id}: invalid run: {problems}")
            return 1
        write_golden(info.golden_path, events)
        path = " ".join(f"{t[0]}>{t[1]}" for t in transitions(events))
        print(f"{info.id:24} {len(events):3} events  exit {terminal_exit(events):18} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
