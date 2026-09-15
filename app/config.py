"""Application settings.

Values come from the environment and from .env (never from code). No credentials are
read in S1; later slices add provider keys, which stay in .env only (constitution XVII).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    runs_dir: Path = field(default_factory=lambda: ROOT / "runs")
    datasets_dir: Path = field(default_factory=lambda: ROOT / "datasets")
    pages_dir: Path = field(default_factory=lambda: ROOT / "app" / "web" / "pages")
    static_dir: Path = field(default_factory=lambda: ROOT / "app" / "web" / "static")
    retry_budget: int = 2
    cost_ceiling: float = 5.00
    stub_pace: float = 4.0
    workflow: str = "electrical_rfp"
    schema_version: str = "1.0.0"


def load_settings(env_file: Path | None = None) -> Settings:
    """Load settings, reading .env from the repository root unless another file is given."""
    load_dotenv(env_file or ROOT / ".env", override=False)
    runs = os.environ.get("RUNS_DIR")
    datasets = os.environ.get("DATASETS_DIR")
    return Settings(
        runs_dir=Path(runs) if runs else ROOT / "runs",
        datasets_dir=Path(datasets) if datasets else ROOT / "datasets",
        retry_budget=_int("RETRY_BUDGET", 2),
        cost_ceiling=_float("COST_CEILING", 5.00),
        stub_pace=_float("STUB_PACE", 4.0),
        workflow=os.environ.get("WORKFLOW", "electrical_rfp"),
    )
