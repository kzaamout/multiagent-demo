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
    1300,
    8,
    1910,
    48,
    "nav order Pre-flight, Introduction, Demo, Settings (spec 0.7, S3b); build stamp added to every header; pre-flight dot pending",
    "S7",
)
LOOP_REASON = Rect(
    1380,
    166,
    1900,
    202,
    "stage label under the loop strip with the Orchestrator's reason (spec 0.7, S3b); the export has no such line",
    "kept",
)
DRY_INTAKE = Rect(
    536,
    208,
    760,
    256,
    "Dry intake toggle added to the composer and wired in S3 (pre-S1 decision 2); the export has no such control",
    "kept",
)
ARTIFACT_BODY = Rect(
    1280,
    316,
    1896,
    940,
    "compiled pages of the run with provenance markers (S4); the export shows a static mock of pages "
    "with other content, so the region is reviewed for family consistency, not compared pixel by pixel",
    "kept",
)
DRY_INTAKE_UNDER_BANNER = Rect(
    536,
    440,
    760,
    488,
    "Dry intake toggle added to the composer and wired in S3 (pre-S1 decision 2); the export has no such control",
    "kept",
)
ARTIFACT_BODY_UNDER_BANNER = Rect(
    1280, 548, 1896, 940, "compiled pages of the run (S4); the export's mock pages differ in content", "kept"
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
    "demo-paused": [HEADER_NAV, LOOP_REASON, DRY_INTAKE_UNDER_BANNER, ARTIFACT_BODY_UNDER_BANNER],
    "demo-running": [HEADER_NAV, LOOP_REASON, DRY_INTAKE, ARTIFACT_BODY],
    "demo-terminated": [
        HEADER_NAV,
        LOOP_REASON,
        DRY_INTAKE,
        ARTIFACT_BODY,
        COMPARE_STRIP,
        COMPARISON_LINE,
        HANDOFF_EYEBROW,
    ],
    "login": [],
    "settings": [
        Rect(
            1300,
            8,
            1910,
            48,
            "nav order (spec 0.7, S3b) and pre-flight dot added to the Settings header (decision)",
            "S7",
        )
    ],
    "settings-dropdown": [
        Rect(
            1300,
            8,
            1910,
            48,
            "nav order (spec 0.7, S3b) and pre-flight dot added to the Settings header (decision)",
            "S7",
        )
    ],
    "preflight-pending": [
        Rect(
            1300,
            8,
            1910,
            48,
            "nav order (spec 0.7, S3b), build stamp and pre-flight dot added to the header (decision)",
            "S7",
        )
    ],
}
