"""The pipeline turns the fixture draft into pages, markers and page text (spec FR-001 to FR-004)."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from app.compile import Compiled, CompileError, compile_draft, read_brand
from app.compile.pipeline import read_compiled
from app.tools.template import find_tags

pytestmark = pytest.mark.compiler

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "app" / "agents" / "stubs" / "fixtures" / "draft-fixture.md"


def _png_size(path: Path) -> tuple[int, int]:
    head = path.read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", head[16:24])
    return width, height


@pytest.fixture(scope="module")
def compiled(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Compiled]:
    run_folder = tmp_path_factory.mktemp("run")
    dataset = tmp_path_factory.mktemp("dataset")
    (dataset / "brand.yaml").write_text(
        'prospect_name: "Fictional Prospect Ltd."\nlogo_path: "brand/logo.png"\nprimary_colour: "#1F3A5F"\n',
        encoding="utf-8",
    )
    markdown = FIXTURE.read_text(encoding="utf-8")
    record = compile_draft(
        run_folder,
        1,
        markdown,
        read_brand(dataset),
        sources={"takeoff": "ev-1", "pricing": "ev-2"},
        headlines={"takeoff": "Takeoff complete", "pricing": "Costing complete"},
    )
    return run_folder, record


def test_pages_markers_and_text_are_written(compiled: tuple[Path, Compiled]) -> None:
    run_folder, record = compiled
    assert record.page_count >= 2 and len(record.page_images) == record.page_count
    assert record.pdf_path == "artifacts/v1/draft-v1.pdf" and (run_folder / record.pdf_path).is_file()
    assert record.page_images[0] == "artifacts/v1/page-01.png"
    assert (run_folder / "artifacts" / "v1" / "draft-v1.typ").is_file(), "the intermediate source is kept"
    assert record.unresolved == []
    assert read_compiled(run_folder, 1) == record and read_compiled(run_folder, 2) is None


def test_every_tag_has_a_marker_inside_its_page(compiled: tuple[Path, Compiled]) -> None:
    run_folder, record = compiled
    markers = json.loads((run_folder / "artifacts" / "v1" / "markers.json").read_text(encoding="utf-8"))
    tags = find_tags(FIXTURE.read_text(encoding="utf-8"))
    assert record.marker_count == len(tags) == len(markers)
    sizes = [_png_size(run_folder / p) for p in record.page_images]
    for m, tag in zip(markers, tags, strict=True):
        assert m["tag_id"] == tag.tag_id and m["source_id"] == tag.source_id
        assert 1 <= m["page"] <= record.page_count
        width, height = sizes[m["page"] - 1]
        assert 0 <= m["x"] <= width and 0 <= m["y"] <= height


def test_page_text_has_one_entry_per_page_and_the_cover_names_the_prospect(
    compiled: tuple[Path, Compiled],
) -> None:
    run_folder, record = compiled
    texts = json.loads((run_folder / "artifacts" / "v1" / "pages.json").read_text(encoding="utf-8"))
    assert len(texts) == record.page_count
    assert "Fictional Prospect Ltd." in texts[0], "wordmark on the cover for a dataset without a logo"
    assert any("Schedule of values" in t for t in texts)
    assert all(chr(0x2014) not in t for t in texts)


def test_malformed_markup_raises_compile_error(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    (dataset / "brand.yaml").write_text('prospect_name: "Acme"\n', encoding="utf-8")
    bad = "# Title\n\n`#let (`{=typst}\n"
    with pytest.raises(CompileError) as caught:
        compile_draft(tmp_path / "run", 1, bad, read_brand(dataset))
    assert "typst" in str(caught.value)


def test_a_marker_is_never_read_as_part_of_its_figure(tmp_path: Path) -> None:
    """Run 0c99f479: one price tagged five times reached the Reviewer as 79,063.751 to 79,063.755, and
    it failed the draft for stating five different prices. 113 of its 125 blocker findings say figures
    disagree. In the page text a marker is now written in brackets, apart from the figure."""
    import re

    dataset = tmp_path / "dataset"
    dataset.mkdir()
    (dataset / "brand.yaml").write_text('prospect_name: "Fictional Prospect Ltd."\n', encoding="utf-8")
    markdown = (
        "# Proposal\n\n## Executive summary\n\nOur price is {{$79,063.75|src:pricing}} for {{45 troffers|src:takeoff}}.\n\n"
        "## Pricing summary\n\nThe total is {{$79,063.75|src:pricing}}, labour {{$13,284.80|src:pricing}}.\n"
    )
    record = compile_draft(tmp_path / "run", 1, markdown, read_brand(dataset))
    folder = tmp_path / "run" / "artifacts" / "v1"
    text = " ".join(json.loads((folder / "pages.json").read_text(encoding="utf-8")))
    assert "$79,063.75 [1]" in text and "$79,063.75 [3]" in text and "45 troffers [2]" in text
    assert not re.search(r"\d\.\d{3,}", text), "no figure gains a decimal place from its marker"
    assert record.marker_count == 4, "the displayed page keeps its superscript markers and their positions"
    assert not list(folder.glob("*.text.pdf")), "the reading compile is removed"
