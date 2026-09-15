"""Regions excluded from the S1 screenshot comparison, each with its reason and the slice
that removes it. Coordinates are pixels at 1920 by 1080 (x0, y0, x1, y1, inclusive).

Every mask is either a region whose content is deferred to a later slice by the roadmap, or
an approved addition to the export (docs/roadmap.md decisions, design/README.md deviations,
docs/design-deviations.md owner decisions).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x0: int
    y0: int
    x1: int
    y1: int
    reason: str
    removed_in: str


HEADER_NAV = Rect(
    1340, 8, 1910, 48, "build stamp added to every header and pre-flight dot pending (decision)", "S7"
)
DRY_INTAKE = Rect(536, 208, 760, 256, "Dry intake toggle added to the composer (pre-S1 decision 2)", "S3")
ARTIFACT_BODY = Rect(
    1280, 316, 1896, 940, "artifact panel placeholder; compiled pages and Edit and Reject arrive in S4", "S4"
)
DRY_INTAKE_UNDER_BANNER = Rect(
    536, 440, 760, 488, "Dry intake toggle added to the composer (pre-S1 decision 2)", "S3"
)
ARTIFACT_BODY_UNDER_BANNER = Rect(
    1280, 548, 1896, 940, "artifact panel placeholder; compiled pages arrive in S4", "S4"
)
COMPARE_STRIP = Rect(1280, 264, 1896, 304, "Compare strip content arrives with Single-model mode", "S5")
COMPARISON_LINE = Rect(
    1586, 960, 1910, 1040, "Team vs Single comparison line arrives with Single-model mode", "S5"
)

HANDOFF_EYEBROW = Rect(
    48,
    800,
    256,
    822,
    "Handoff eyebrow reads Ready for approval until the run ends (owner decision 2026-09-15)",
    "kept",
)

MASKS: dict[str, list[Rect]] = {
    "demo-idle": [HEADER_NAV, DRY_INTAKE, ARTIFACT_BODY],
    "demo-paused": [HEADER_NAV, DRY_INTAKE_UNDER_BANNER, ARTIFACT_BODY_UNDER_BANNER],
    "demo-running": [HEADER_NAV, DRY_INTAKE, ARTIFACT_BODY],
    "demo-terminated": [
        HEADER_NAV,
        DRY_INTAKE,
        ARTIFACT_BODY,
        COMPARE_STRIP,
        COMPARISON_LINE,
        HANDOFF_EYEBROW,
    ],
    "login": [],
    "settings": [Rect(1480, 8, 1910, 48, "pre-flight dot added to the Settings header (decision)", "S7")],
    "preflight-pending": [
        Rect(1340, 8, 1910, 48, "build stamp and pre-flight dot added to the header (decision)", "S7")
    ],
}
