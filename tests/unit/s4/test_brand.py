"""Brand fallbacks: wordmark for a missing logo, default colour for a bad value (spec FR-013)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.compile.brand import DEFAULT_COLOUR, read_brand


def _write(folder: Path, text: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "brand.yaml").write_text(text, encoding="utf-8")
    return folder


def test_missing_logo_selects_the_wordmark(tmp_path: Path) -> None:
    brand = read_brand(
        _write(
            tmp_path / "d", 'prospect_name: "Acme"\nlogo_path: "brand/logo.png"\nprimary_colour: "#1F3A5F"\n'
        )
    )
    assert brand.uses_wordmark and brand.logo_path is None
    assert brand.primary_colour == "#1F3A5F"
    assert any("wordmark" in a for a in brand.assumptions)


def test_present_logo_is_used(tmp_path: Path) -> None:
    folder = _write(
        tmp_path / "d", 'prospect_name: "Acme"\nlogo_path: "brand/logo.png"\nprimary_colour: "#AABBCC"\n'
    )
    (folder / "brand").mkdir()
    (folder / "brand" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    brand = read_brand(folder)
    assert brand.logo_path is not None and brand.logo_path.name == "logo.png"
    assert brand.assumptions == ()


def test_bad_colour_falls_back_and_is_an_assumption(tmp_path: Path) -> None:
    brand = read_brand(_write(tmp_path / "d", 'prospect_name: "Acme"\nprimary_colour: "navy"\n'))
    assert brand.primary_colour == DEFAULT_COLOUR
    assert any("primary_colour" in a for a in brand.assumptions)


def test_logo_outside_the_dataset_is_ignored(tmp_path: Path) -> None:
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"x")
    brand = read_brand(_write(tmp_path / "d", 'prospect_name: "Acme"\nlogo_path: "../outside.png"\n'))
    assert brand.logo_path is None


def test_missing_name_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        read_brand(_write(tmp_path / "d", 'logo_path: ""\n'))
