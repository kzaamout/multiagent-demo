"""The seven content files render whole and in order (spec FR-001, SC-001)."""

from __future__ import annotations

import re
from pathlib import Path

from app.intro.content import CONTENT_DIR, ORDER, parse_blocks, plain_text, render_blocks, sections

EM_DASH = chr(0x2014)


def _paragraphs(path: Path) -> list[str]:
    text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
    out: list[str] = []
    for chunk in re.split(r"\n\s*\n", text):
        chunk = " ".join(line.strip() for line in chunk.splitlines() if line.strip())
        if (
            chunk
            and not chunk.startswith("#")
            and not chunk.startswith("|")
            and not chunk.startswith("-")
            and not re.match(r"^\d+\.", chunk)
        ):
            out.append(re.sub(r"\*\*|(?<![A-Za-z0-9_])_(?![A-Za-z0-9_])", "", chunk))
    return out


def test_seven_sections_in_the_spec_order() -> None:
    found = sections()
    assert [s.id for s in found] == [section_id for _, section_id, _ in ORDER]
    assert found[0].title.startswith("One request in.")
    assert [s.diagram for s in found] == [
        "architecture",
        "loop",
        None,
        None,
        None,
        "demo-vs-production",
        None,
    ] or [s.diagram for s in found] == [None, "architecture", "loop", None, None, "demo-vs-production", None]


def test_every_paragraph_of_every_file_is_in_the_plain_text() -> None:
    for (name, _, _), section in zip(ORDER, sections(), strict=True):
        for paragraph in _paragraphs(CONTENT_DIR / name):
            first_words = " ".join(paragraph.split()[:6])
            assert first_words in section.text, (name, first_words)
        assert "<!--" not in section.text and "diagram:" not in section.text


def test_the_aws_table_and_the_loop_list_render() -> None:
    by_id = {s.id: s for s in sections()}
    table = next(b for b in by_id["aws"].blocks if b.kind == "table")
    assert len(table.rows) == 9 and table.rows[0] == ("Demo", "Production")
    ordered = next(b for b in by_id["agentic-loop"].blocks if b.kind == "ordered")
    assert len(ordered.lines) == 6 and ordered.lines[0].startswith("**Intake.**")
    html = render_blocks(by_id["aws"].blocks)
    assert html.count("<tr>") == 9 and "<th>Demo</th>" in html
    assert render_blocks(by_id["agentic-loop"].blocks).count("<li>") == 6


def test_faq_pairs_and_no_em_dash() -> None:
    faq = next(s for s in sections() if s.id == "faq")
    assert len(faq.faq) == 10 and faq.faq[0][0].startswith("Is this one model")
    for section in sections():
        assert EM_DASH not in section.text and EM_DASH not in render_blocks(section.blocks)


def test_inline_markup_is_rendered_and_escaped() -> None:
    diagram, title, blocks = parse_blocks(
        "# T\n\nA **bold** and _soft_ word with <tag>.\n\n<!-- diagram: loop -->\n"
    )
    assert diagram == "loop" and title == "T"
    assert render_blocks(blocks) == "<p>A <strong>bold</strong> and <em>soft</em> word with &lt;tag&gt;.</p>"
    assert plain_text(blocks, title) == "T\nA bold and soft word with <tag>."
