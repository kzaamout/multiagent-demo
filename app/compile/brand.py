"""The prospect's brand for the cover, from the dataset's brand.yaml (S4 decisions 7a and 8a).

A missing logo file selects a wordmark drawn from the prospect name. A colour that is not a
six-digit hex value falls back to the template default and is reported as an assumption, so the
run can record it (CLAUDE.md rule 14: state what could not be read, never guess).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_COLOUR = "#1F3A5F"
HEX_COLOUR = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class Brand:
    prospect_name: str
    logo_path: Path | None
    primary_colour: str
    assumptions: tuple[str, ...] = ()

    @property
    def uses_wordmark(self) -> bool:
        return self.logo_path is None


def read_brand(dataset_folder: Path) -> Brand:
    """Read `brand.yaml` from the dataset folder. The logo path is resolved inside that folder only."""
    path = dataset_folder / "brand.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None
    data = raw if isinstance(raw, dict) else {}
    name = str(data.get("prospect_name") or "").strip()
    if not name:
        raise ValueError(f"{path} has no prospect_name")
    assumptions: list[str] = []

    logo: Path | None = None
    logo_value = str(data.get("logo_path") or "").strip()
    if logo_value:
        candidate = (dataset_folder / logo_value).resolve()
        if candidate.is_file() and candidate.is_relative_to(dataset_folder.resolve()):
            logo = candidate
    if logo is None:
        assumptions.append(
            "brand logo file is missing from the dataset; the cover carries a wordmark drawn from the prospect name"
        )

    colour = str(data.get("primary_colour") or "").strip()
    if not HEX_COLOUR.match(colour):
        colour = DEFAULT_COLOUR
        assumptions.append(
            "brand primary_colour is not a six-digit hex colour; the template default was used"
        )

    return Brand(prospect_name=name, logo_path=logo, primary_colour=colour, assumptions=tuple(assumptions))
