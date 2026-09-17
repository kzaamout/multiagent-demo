"""The Introduction's copy: the seven content files, read in order and rendered as they are.

The files are a controlled source (constitution X): nothing here rewrites a word. The markdown
subset they use is small and fixed (headings, paragraphs, bold and italic, lists, one pipe
table, HTML comments that carry diagram and layout notes), so a small in-house converter
renders it for the page and gives the plain text the content diff and the em-dash lint check.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.config import ROOT

CONTENT_DIR = ROOT / "content" / "intro"

ORDER: tuple[tuple[str, str, str], ...] = (
    ("01-what-it-is.md", "what-it-is", "What it is"),
    ("02-architecture.md", "architecture", "Architecture"),
    ("03-agentic-loop.md", "agentic-loop", "The agentic loop"),
    ("04-the-team.md", "the-team", "The team"),
    ("05-how-agents-differ.md", "how-agents-differ", "How agents differ"),
    ("06-real-in-your-aws-account.md", "aws", "In your AWS account"),
    ("07-faq.md", "faq", "FAQ"),
)
"""File, the export's section id, and the mono eyebrow above the heading, in the spec's order."""

DIAGRAM_NAMES = {"architecture": "architecture", "loop": "loop", "demo-vs-production": "demo-vs-production"}

_COMMENT = re.compile(r"<!--.*?-->", re.S)
_DIAGRAM = re.compile(r"<!--\s*diagram:\s*([a-z-]+)")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<![A-Za-z0-9_])_(.+?)_(?![A-Za-z0-9_])")


@dataclass(frozen=True)
class Block:
    kind: str
    """paragraph, ordered, bulleted, table, heading"""
    lines: tuple[str, ...] = ()
    rows: tuple[tuple[str, ...], ...] = ()
    level: int = 0


@dataclass(frozen=True)
class Section:
    id: str
    eyebrow: str
    title: str
    blocks: tuple[Block, ...]
    diagram: str | None
    text: str
    faq: tuple[tuple[str, str], ...] = field(default_factory=tuple)


def _inline_html(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = _BOLD.sub(r"<strong>\1</strong>", escaped)
    escaped = _ITALIC.sub(r"<em>\1</em>", escaped)
    return escaped


def _inline_text(text: str) -> str:
    return _ITALIC.sub(r"\1", _BOLD.sub(r"\1", text))


def parse_blocks(markdown: str) -> tuple[str | None, str, list[Block]]:
    """(diagram slot, title, blocks) for one file. Comments are dropped after the slot is read."""
    slot = _DIAGRAM.search(markdown)
    diagram = slot.group(1) if slot else None
    body = _COMMENT.sub("", markdown)
    title = ""
    blocks: list[Block] = []
    paragraph: list[str] = []
    list_kind: str | None = None
    items: list[str] = []
    table: list[tuple[str, ...]] = []

    def flush() -> None:
        nonlocal paragraph, list_kind, items, table
        if paragraph:
            blocks.append(Block("paragraph", (" ".join(paragraph),)))
            paragraph = []
        if items:
            blocks.append(Block(list_kind or "bulleted", tuple(items)))
            items = []
            list_kind = None
        if table:
            blocks.append(Block("table", rows=tuple(table)))
            table = []

    for raw in body.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if stripped.startswith("# ") and not title:
            flush()
            title = stripped[2:].strip()
            continue
        if stripped.startswith("## "):
            flush()
            blocks.append(Block("heading", (stripped[3:].strip(),), level=2))
            continue
        if stripped.startswith("|"):
            cells = tuple(c.strip() for c in stripped.strip("|").split("|"))
            if all(set(c) <= set("-: ") for c in cells):
                continue
            if paragraph or items:
                flush()
            table.append(cells)
            continue
        ordered = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if ordered:
            if table or paragraph or (items and list_kind != "ordered"):
                flush()
            list_kind = "ordered"
            items.append(ordered.group(2))
            continue
        if stripped.startswith("- "):
            if table or paragraph or (items and list_kind != "bulleted"):
                flush()
            list_kind = "bulleted"
            items.append(stripped[2:])
            continue
        if items and line.startswith("  "):
            items[-1] = items[-1] + " " + stripped
            continue
        if table:
            flush()
        paragraph.append(stripped)
    flush()
    return diagram, title, blocks


def _faq_pairs(blocks: list[Block]) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    for block in blocks:
        if block.kind != "paragraph":
            continue
        match = _BOLD.match(block.lines[0])
        if match:
            pairs.append((match.group(1), block.lines[0][match.end() :].strip()))
    return tuple(pairs)


def plain_text(blocks: list[Block] | tuple[Block, ...], title: str) -> str:
    parts = [title]
    for block in blocks:
        if block.kind == "table":
            parts.extend(" ".join(_inline_text(c) for c in row) for row in block.rows)
        else:
            parts.extend(_inline_text(line) for line in block.lines)
    return "\n".join(p for p in parts if p)


def render_blocks(blocks: tuple[Block, ...] | list[Block]) -> str:
    out: list[str] = []
    for block in blocks:
        if block.kind == "paragraph":
            out.append(f"<p>{_inline_html(block.lines[0])}</p>")
        elif block.kind == "heading":
            out.append(f"<h3>{_inline_html(block.lines[0])}</h3>")
        elif block.kind in ("ordered", "bulleted"):
            tag = "ol" if block.kind == "ordered" else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{_inline_html(i)}</li>" for i in block.lines) + f"</{tag}>")
        elif block.kind == "table":
            head, *rest = block.rows
            out.append(
                "<table><thead><tr>"
                + "".join(f"<th>{_inline_html(c)}</th>" for c in head)
                + "</tr></thead><tbody>"
                + "".join(
                    "<tr>" + "".join(f"<td>{_inline_html(c)}</td>" for c in row) + "</tr>" for row in rest
                )
                + "</tbody></table>"
            )
    return "\n".join(out)


def sections(folder: Path = CONTENT_DIR) -> list[Section]:
    """The seven sections in the spec's order. A missing file is an error, never a blank section."""
    result: list[Section] = []
    for name, section_id, eyebrow in ORDER:
        path = folder / name
        if not path.is_file():
            raise FileNotFoundError(f"Introduction content file missing: {path}")
        diagram, title, blocks = parse_blocks(path.read_text(encoding="utf-8"))
        result.append(
            Section(
                id=section_id,
                eyebrow=eyebrow,
                title=title,
                blocks=tuple(blocks),
                diagram=diagram,
                text=plain_text(blocks, title),
                faq=_faq_pairs(blocks) if section_id == "faq" else (),
            )
        )
    return result
