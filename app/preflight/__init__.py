"""Pre-flight checks for demo day (spec 0.8 section 2.4; slice S7; spec 012).

One row per model in the registry and the fixed rows, run from the Pre-flight page and stored as
`runs/preflight.json` (schema 2, facts only). The dot in every page header and `/api/meta` are worked
out from the stored rows against the seats in force on each read. A seat change rechecks the chosen
model. The checks are not events and never touch a run.
"""

from __future__ import annotations

from app.preflight.checks import CheckContext, checks_for
from app.preflight.header import HeaderState, header_state
from app.preflight.result import (
    CheckResult,
    PreflightResult,
    format_stamp,
    load_result,
    merge,
    save_result,
)
from app.preflight.runner import header_json, payload, recheck, recheck_payload, run_preflight

__all__ = [
    "CheckContext",
    "CheckResult",
    "HeaderState",
    "PreflightResult",
    "checks_for",
    "format_stamp",
    "header_json",
    "header_state",
    "load_result",
    "merge",
    "payload",
    "recheck",
    "recheck_payload",
    "run_preflight",
    "save_result",
]
