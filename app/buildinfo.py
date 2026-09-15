"""Build stamp: short git hash and commit date, shown in every page header."""

from __future__ import annotations

import datetime as dt
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class BuildInfo:
    hash: str
    date: str

    @property
    def stamp(self) -> str:
        return f"build {self.hash} · {self.date}"


def _git(args: list[str], cwd: Path) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


@lru_cache(maxsize=1)
def build_info(root: Path | None = None) -> BuildInfo:
    cwd = root or Path(__file__).resolve().parent.parent
    short = _git(["rev-parse", "--short", "HEAD"], cwd)
    date = _git(["log", "-1", "--format=%cs"], cwd)
    if short is None:
        return BuildInfo(hash="no-git", date=dt.date.today().isoformat())
    return BuildInfo(hash=short, date=date or dt.date.today().isoformat())
