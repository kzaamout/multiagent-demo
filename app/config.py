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
    datasets_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("DATASETS_DIR") or ROOT / "datasets")
    )
    pages_dir: Path = field(default_factory=lambda: ROOT / "app" / "web" / "pages")
    static_dir: Path = field(default_factory=lambda: ROOT / "app" / "web" / "static")
    review_max_cycles: int = 4
    cost_ceiling: float = 5.00
    stub_pace: float = 4.0
    workflow: str = "electrical_rfp"
    schema_version: str = "1.1.0"
    long_lead_days: int = 28
    agent_mode: str = "auto"  # auto: live when a dataset's inputs are curated, else stub; stub: always stub
    public_run_id: str = "f2dda488-0a2f-457a-9ef1-33fcac05fa70"
    """The one recorded run the public Introduction replay serves (spec 2.1, 6; S6 decision 1a).
    The default is the S4 Planted inconsistency run of 2026-09-17; PUBLIC_RUN_ID overrides it."""
    # S7 (spec 2.8, 2.9): the shared login pair, the run mode, and the tunnel hostname, all from .env.
    # The pair is compared in constant time by app.auth and never serialized; both empty means no login.
    run_mode: str = "laptop"  # laptop: local models through Ollama; cloud: cloud providers only
    demo_username: str = ""
    demo_password: str = ""
    tunnel_hostname: str = ""

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
    run_mode = os.environ.get("RUN_MODE", "laptop").strip() or "laptop"
    if run_mode not in ("laptop", "cloud"):
        raise ValueError("RUN_MODE must be laptop or cloud")
    return Settings(
        run_mode=run_mode,
        demo_username=os.environ.get("DEMO_USERNAME", ""),
        demo_password=os.environ.get("DEMO_PASSWORD", ""),
        tunnel_hostname=os.environ.get("TUNNEL_HOSTNAME", "").strip(),
        runs_dir=Path(runs) if runs else ROOT / "runs",
        knowledge_dir=Path(knowledge) if knowledge else ROOT / "knowledge",
        long_lead_days=_int("LONG_LEAD_DAYS", 28),
        agent_mode=mode,
        datasets_dir=Path(datasets) if datasets else ROOT / "datasets",
        review_max_cycles=_int("REVIEW_MAX_CYCLES", 4),
        cost_ceiling=_float("COST_CEILING", 5.00),
        stub_pace=_float("STUB_PACE", 4.0),
        workflow=os.environ.get("WORKFLOW", "electrical_rfp"),
        public_run_id=os.environ.get("PUBLIC_RUN_ID") or Settings.public_run_id,
    )
