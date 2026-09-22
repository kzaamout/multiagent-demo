"""The pipeline turns the fixture draft into pages, markers and page text (spec FR-001 to FR-004)."""

from __future__ import annotations

import json
import re
import struct
from pathlib import Path

import pytest

from app.compile import Compiled, CompileError, compile_draft, read_brand
from app.compile.markers import marker_label
from app.compile.pipeline import read_compiled
from app.live.documents import parse_pdf
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
        assert m["label"] == marker_label(m["n"]), "the label the page prints is stored beside the position"
        assert 1 <= m["page"] <= record.page_count
        width, height = sizes[m["page"] - 1]
        assert 0 <= m["x"] <= width and 0 <= m["y"] <= height
    prepared = (run_folder / "artifacts" / "v1" / "draft-v1.prepared.md").read_text(encoding="utf-8")
    table = re.findall(r"^\| ([a-z]+) \| [a-z0-9_]+ \| [^|]+ \|$", prepared, re.M)
    assert table == [m["label"] for m in markers], "the Provenance table lists the same labels in order"


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
    disagree. In the page text a marker is now written in brackets, apart from the figure, and it is a
    letter, the one the page image shows (spec 013 FR-004)."""
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
    assert "$79,063.75 [a]" in text and "$79,063.75 [c]" in text and "45 troffers [b]" in text
    assert not re.search(r" \[\d+\]", text), "no marker is written as a number"
    assert not re.search(r"\d\.\d{3,}", text), "no figure gains a decimal place from its marker"
    assert record.marker_count == 4, "the displayed page keeps its superscript markers and their positions"
    assert not list(folder.glob("*.text.pdf")), "the reading compile is removed"


def test_the_displayed_page_prints_letters_past_z(tmp_path: Path) -> None:
    """Spec 013 SC-001: on the page as displayed every marker is a letter, markers 27 on carry two, and
    no tagged figure is followed by a digit that is not its own."""
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    (dataset / "brand.yaml").write_text('prospect_name: "Fictional Prospect Ltd."\n', encoding="utf-8")
    lines = [f"- Line {n} costs {{{{${n},000.75|src:pricing}}}}." for n in range(1, 31)]
    markdown = "# Proposal\n\n## Pricing summary\n\n" + "\n".join(lines) + "\n"
    record = compile_draft(tmp_path / "run", 1, markdown, read_brand(dataset))
    folder = tmp_path / "run" / "artifacts" / "v1"
    typ = (folder / "draft-v1.typ").read_text(encoding="utf-8")
    assert '#prov(27, "aa",' in typ and '#prov(30, "ad",' in typ
    markers = json.loads((folder / "markers.json").read_text(encoding="utf-8"))
    assert [m["label"] for m in markers][24:] == ["y", "z", "aa", "ab", "ac", "ad"]
    shown = " ".join(p.text for p in parse_pdf(tmp_path / "run" / record.pdf_path))
    assert "$1,000.75" in shown and "$30,000.75" in shown
    assert not re.search(r",000\.75\d", shown), (
        "no figure on the displayed page gains a digit from its marker"
    )
