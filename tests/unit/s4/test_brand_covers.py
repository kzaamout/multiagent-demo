"""The cover carries the prospect's brand for every dataset, wordmark when no logo file exists (spec FR-013)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.compile import compile_draft, read_brand
from app.runs.registry import discover_datasets

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "app" / "agents" / "stubs" / "fixtures" / "draft-fixture.md"

pytestmark = pytest.mark.compiler


def _page_one_text(run_folder: Path) -> str:
    texts = json.loads((run_folder / "artifacts" / "v1" / "pages.json").read_text(encoding="utf-8"))
    return str(texts[0])


@pytest.mark.dataset
@pytest.mark.parametrize("dataset_id", [d.id for d in discover_datasets(ROOT / "datasets")])
def test_every_dataset_cover_names_the_prospect(dataset_id: str, tmp_path: Path) -> None:
    info = next(d for d in discover_datasets(ROOT / "datasets") if d.id == dataset_id)
    brand = read_brand(info.folder)
    record = compile_draft(tmp_path / "run", 1, FIXTURE.read_text(encoding="utf-8"), brand)
    assert record.page_count >= 2
    assert brand.prospect_name in _page_one_text(tmp_path / "run")
    if brand.logo_path is None:
        assert brand.uses_wordmark and any("wordmark" in a for a in brand.assumptions)
    else:
        assert (tmp_path / "run" / "artifacts" / "v1" / f"logo{brand.logo_path.suffix.lower()}").is_file()


def test_a_long_prospect_name_wraps_and_stays_whole(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    name = "The Consolidated Municipal Infrastructure Renewal Partnership Board of Greater Quillbrook"
    (dataset / "brand.yaml").write_text(
        f'prospect_name: "{name}"\nprimary_colour: "#1F3A5F"\n', encoding="utf-8"
    )
    compile_draft(tmp_path / "run", 1, FIXTURE.read_text(encoding="utf-8"), read_brand(dataset))
    text = " ".join(_page_one_text(tmp_path / "run").split())
    assert name in text


def test_a_bad_colour_compiles_with_the_default(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    (dataset / "brand.yaml").write_text('prospect_name: "Acme"\nprimary_colour: "navy"\n', encoding="utf-8")
    brand = read_brand(dataset)
    record = compile_draft(tmp_path / "run", 1, FIXTURE.read_text(encoding="utf-8"), brand)
    assert record.page_count >= 2 and any("primary_colour" in a for a in brand.assumptions)
