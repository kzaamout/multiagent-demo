"""Pre-flight checks for demo day (spec 0.7 section 2.4, slice S7).

Eight checks, each classed essential or non-essential, run from the Pre-flight page and stored as
`runs/preflight.json`. The stored result drives the dot in every page header and `/api/meta`. The
checks are not events and never touch a run.
"""

from __future__ import annotations

from app.preflight.checks import CheckContext, checks_for
from app.preflight.result import (
    CheckResult,
    HeaderState,
    PreflightResult,
    format_stamp,
    header_state,
    load_result,
    save_result,
)
from app.preflight.runner import pending_payload, result_payload, run_preflight

__all__ = [
    "CheckContext",
    "CheckResult",
    "HeaderState",
    "PreflightResult",
    "checks_for",
    "format_stamp",
    "header_state",
    "load_result",
    "pending_payload",
    "result_payload",
    "run_preflight",
    "save_result",
]
