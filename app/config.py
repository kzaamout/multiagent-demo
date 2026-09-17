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
    knowledge_dir: Path = field(default_factory=lambda: ROOT / "knowledge")
    # DATASETS_DIR is honoured here too, so a worktree shares the main checkout's local datasets.
    datasets_dir: Path = field(default_factory=lambda: Path(os.environ.get("DATASETS_DIR") or ROOT / "datasets"))
    pages_dir: Path = field(default_factory=lambda: ROOT / "app" / "web" / "pages")
    static_dir: Path = field(default_factory=lambda: ROOT / "app" / "web" / "static")
    review_max_cycles: int = 4
    cost_ceiling: float = 5.00
    stub_pace: float = 4.0
    workflow: str = "electrical_rfp"
    schema_version: str = "1.1.0"
    long_lead_days: int = 28
    agent_mode: str = "auto"  # auto: live when a dataset's inputs are curated, else stub; stub: always stub

    @property
    def retry_budget(self) -> int:
        """The maximum number of reworks: one fewer than the review cycles (schema 1.1.0)."""
        return max(self.review_max_cycles - 1, 0)


def load_settings(env_file: Path | None = None) -> Settings:
    """Load settings, reading .env from the repository root unless another file is given."""
    load_dotenv(env_file or ROOT / ".env", override=False)
    runs = os.environ.get("RUNS_DIR")
    datasets = os.environ.get("DATASETS_DIR")
    knowledge = os.environ.get("KNOWLEDGE_DIR")
    mode = os.environ.get("AGENT_MODE", "auto")
    if mode not in ("auto", "stub"):
        raise ValueError("AGENT_MODE must be auto or stub")
    return Settings(
        runs_dir=Path(runs) if runs else ROOT / "runs",
        knowledge_dir=Path(knowledge) if knowledge else ROOT / "knowledge",
        long_lead_days=_int("LONG_LEAD_DAYS", 28),
        agent_mode=mode,
        datasets_dir=Path(datasets) if datasets else ROOT / "datasets",
        review_max_cycles=_int("REVIEW_MAX_CYCLES", 4),
        cost_ceiling=_float("COST_CEILING", 5.00),
        stub_pace=_float("STUB_PACE", 4.0),
        workflow=os.environ.get("WORKFLOW", "electrical_rfp"),
    )
