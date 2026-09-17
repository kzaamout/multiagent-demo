"""The Introduction as a PDF for the leave-behind (S6 decision 7a), through the S4 pipeline.

One markdown file carries the seven sections with the three diagrams as SVG images at their slots
and the team as a list; pandoc and Typst turn it into `runs/_intro/introduction.pdf`. The PDF is
regenerated only when a content file, the diagram or team modules, or the template is newer.
"""

from __future__ import annotations

from pathlib import Path

from app.compile.pipeline import TEMPLATES, render_markdown, tools_available
from app.config import ROOT, Settings
from app.intro.content import CONTENT_DIR, Block, Section, sections
from app.intro.diagrams import diagrams
from app.intro.team import team_cards

INTRO_TEMPLATE = TEMPLATES / "introduction.typ"
OUT_DIR_NAME = "_intro"
TITLE = "One request in. One reviewed deliverable out."


def _block_markdown(block: Block) -> str:
    if block.kind == "paragraph":
        return block.lines[0]
    if block.kind == "heading":
        return f"### {block.lines[0]}"
    if block.kind == "ordered":
        return "\n".join(f"{i}. {line}" for i, line in enumerate(block.lines, start=1))
    if block.kind == "bulleted":
        return "\n".join(f"- {line}" for line in block.lines)
    if block.kind == "table":
        head, *rest = block.rows
        lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        lines += ["| " + " | ".join(row) + " |" for row in rest]
        return "\n".join(lines)
    return ""


def _section_markdown(section: Section, diagram_files: dict[str, str]) -> str:
    parts = [f"## {section.title}", ""]
    if section.id == "faq":
        for question, answer in section.faq:
            parts.append(f"**{question}** {answer}")
            parts.append("")
    else:
        for block in section.blocks:
            parts.append(_block_markdown(block))
            parts.append("")
    if section.diagram and section.diagram in diagram_files:
        parts.append(f"![{section.diagram}]({diagram_files[section.diagram]})")
        parts.append("")
    if section.id == "the-team":
        parts.append("### The seats at a glance")
        parts.append("")
        for card in team_cards():
            model = card.model if not card.swap_in else "swaps in for the appraisal workflow"
            parts.append(
                f"- **{card.names}, {card.role}.** Tools: {card.tools}. Sees: {card.sees}. Model today: {model}."
            )
        parts.append("")
    return "\n".join(parts)


def sources_newer_than(target: Path) -> bool:
    if not target.is_file():
        return True
    stamp = target.stat().st_mtime
    watched = [
        *sorted(CONTENT_DIR.glob("*.md")),
        INTRO_TEMPLATE,
        ROOT / "app" / "intro" / "diagrams.py",
        ROOT / "app" / "intro" / "team.py",
        ROOT / "app" / "intro" / "pdf.py",
    ]
    return any(p.is_file() and p.stat().st_mtime > stamp for p in watched)


def render_pdf(settings: Settings, force: bool = False) -> Path:
    """Write the Introduction PDF and return its path; skip the compile when nothing changed."""
    out_dir = settings.runs_dir / OUT_DIR_NAME
    pdf = out_dir / "introduction.pdf"
    if not force and not sources_newer_than(pdf):
        return pdf
    out_dir.mkdir(parents=True, exist_ok=True)
    diagram_files: dict[str, str] = {}
    for name, diagram in diagrams().items():
        path = out_dir / f"{name}.svg"
        path.write_text(diagram.svg, encoding="utf-8", newline="\n")
        diagram_files[name] = path.name
    body = "\n".join(_section_markdown(s, diagram_files) for s in sections())
    return render_markdown(body, INTRO_TEMPLATE, {"title": TITLE}, out_dir, "introduction")


def missing_tools() -> list[str]:
    return [name for name, version in tools_available().items() if version is None]
