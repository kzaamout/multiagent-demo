"""template.render and compile.trigger for the Writer (S2 markdown interim; Typst arrives in S4).

Provenance tags are written as {{value|src:<source_id>}} (owner decision, 2026-09-14). The
provenance appendix is generated from the tags actually present, so it cannot drift from the
body.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.config import ROOT

TEMPLATE_PATH = ROOT / "templates" / "rfp-response.md"
SECTIONS = (
    "executive_summary",
    "scope",
    "pricing_summary",
    "schedule_of_values",
    "assumptions",
    "exclusions",
)
REQUIRED_SECTIONS = ("executive_summary", "scope", "pricing_summary", "assumptions", "exclusions")
TAG = re.compile(r"\{\{\s*([^|{}]+?)\s*\|\s*src:\s*([A-Za-z0-9_.:-]+)\s*\}\}")
SLOT = re.compile(r"\{\{([a-z_]+)\}\}")


@dataclass(frozen=True)
class Tag:
    tag_id: str
    value: str
    source_id: str


@dataclass(frozen=True)
class Rendered:
    markdown: str
    tags: tuple[Tag, ...]
    gaps: tuple[str, ...]


MONEY = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?")
SOURCE_ID = re.compile(r"\(source id: ([A-Za-z0-9_.:-]+)\)")


def provenance_problems(markdown: str, offered_context: str) -> list[str]:
    """What stops a draft's provenance from being checkable: no tags, tags naming sources the Writer was
    never given. The appendix is excluded.

    It once refused any dollar amount without a tag. Deciding which figures need a tag is a judgment, and
    the rule refused zeros, the labour rate and line extensions while proving nothing about where a number
    came from. An untagged amount is now held against what the Writer was given instead, in
    app.live.figures.amounts_not_in_context (spec 010, phase 1.7)."""
    body = markdown.split("\n## Provenance", 1)[0]
    tags = find_tags(body)
    offered = set(SOURCE_ID.findall(offered_context))
    problems: list[str] = []
    if not tags:
        known = sorted(offered)
        example = known[0] if known else "8f2a10c4"
        problems.append(
            "the draft body has no usable provenance tags. Tag every figure in the body, in every section, with "
            f"the source id of the output it came from, for example {{{{225 A|src:{example}}}}}. Tags in the "
            "provenance appendix do not count. Your source ids are: " + ", ".join(known)
        )
    unknown = sorted({tag.source_id for tag in tags if tag.source_id not in offered})
    if unknown:
        problems.append("these tags name a source id that is not in your context: " + ", ".join(unknown[:5]))
    return problems


def untagged_money(markdown: str) -> list[str]:
    """Dollar amounts in the body that carry no provenance tag, in the order they appear (spec 010)."""
    body = markdown.split("\n## Provenance", 1)[0]
    return list(dict.fromkeys(MONEY.findall(TAG.sub("", body))))


def find_tags(markdown: str) -> list[Tag]:
    return [Tag(f"t{i:02d}", m.group(1), m.group(2)) for i, m in enumerate(TAG.finditer(markdown), start=1)]


def strip_tags(markdown: str) -> str:
    """The reader's view: tag syntax removed, values kept."""
    return TAG.sub(lambda m: m.group(1), markdown)


def render(
    sections: dict[str, str],
    *,
    prospect_name: str,
    project: str,
    template_path: Path = TEMPLATE_PATH,
) -> Rendered:
    unknown = sorted(set(sections) - set(SECTIONS))
    if unknown:
        raise ValueError(f"unknown template sections {unknown}")
    gaps = tuple(s for s in REQUIRED_SECTIONS if not sections.get(s, "").strip())
    body_sections = {s: sections.get(s, "").strip() or "_Not supplied._" for s in SECTIONS}
    body_text = "\n".join(body_sections.values())
    tags = find_tags(body_text)
    if tags:
        appendix = "| Tag | Value | Source |\n|---|---|---|\n" + "\n".join(
            f"| {t.tag_id} | {t.value} | {t.source_id} |" for t in tags
        )
    else:
        appendix = "_No tagged figures._"
    values = {
        "prospect_name": prospect_name,
        "project": project,
        **body_sections,
        "provenance_appendix": appendix,
    }
    template = template_path.read_text(encoding="utf-8")

    def fill(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            raise ValueError(f"template slot {key} has no value")
        return values[key]

    return Rendered(SLOT.sub(fill, template), tuple(tags), gaps)


def commit_draft(run_folder: Path, version: int, markdown: str) -> str:
    """compile.trigger in S2: store the draft for the run and return its path relative to the run folder."""
    relative = f"drafts/draft-v{version}.md"
    path = run_folder / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8", newline="\n")
    return relative
