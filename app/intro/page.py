"""The Introduction page: the export's shell with the sections, diagrams, team grid and replay
frame rendered into it at request time (spec 2.1, S6)."""

from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import ROOT, Settings
from app.intro.content import Section, render_blocks, sections
from app.intro.diagrams import diagrams
from app.intro.team import TeamCard, team_cards

PAGE_PATH = ROOT / "app" / "web" / "pages" / "introduction.html"
WIDE = {"architecture", "the-team", "aws", "replay"}


@dataclass(frozen=True)
class PinnedRun:
    run_id: str
    dataset_id: str
    exit: str
    has_pages: bool
    available: bool


def pinned_run(settings: Settings, events: list[Any]) -> PinnedRun:
    """What the frame's caption says about the pinned recording; `events` may be empty."""
    if not events:
        return PinnedRun(settings.public_run_id, "", "", False, False)
    first, last = events[0], events[-1]
    dataset = str(first.payload.get("dataset_id", "")) if isinstance(first.payload, dict) else ""
    exit_value = (
        str(last.payload.get("exit", ""))
        if last.type == "run.terminated" and isinstance(last.payload, dict)
        else ""
    )
    has_pages = any(
        e.type == "artifact.compiled" and isinstance(e.payload, dict) and e.payload.get("page_images")
        for e in events
    )
    return PinnedRun(settings.public_run_id, dataset, exit_value, has_pages, True)


def _e(text: str) -> str:
    return html.escape(text, quote=True)


def render_section(section: Section) -> str:
    first = section.id == "what-it-is"
    classes = ["intro-section"]
    if first:
        classes.append("is-first")
    if section.id in WIDE:
        classes.append("is-wide")
    heading = (
        f'<h1 class="intro-h1">{_e(section.title)}</h1>'
        if first
        else f'<h2 class="intro-h2">{_e(section.title)}</h2>'
    )
    if section.id == "faq":
        body = "".join(
            f'<div class="faq-item"><p><strong>{_e(q)}</strong> {_e(a)}</p></div>' for q, a in section.faq
        )
        body = f'<div class="faq-list">{body}</div>'
    else:
        body = f'<div class="intro-body">{render_blocks(section.blocks)}</div>'
    return (
        f'<section id="{section.id}" class="{" ".join(classes)}" data-part="intro-section">'
        f'<div class="intro-eyebrow">{_e(section.eyebrow)}</div>{heading}{body}'
        f"{{{{AFTER:{section.id}}}}}</section>"
    )


def render_team(cards: list[TeamCard]) -> str:
    items: list[str] = []
    for card in cards:
        hint = "swaps in for the appraisal workflow" if card.swap_in else "click for role, owns, sees, tools"
        items.append(
            f'<div class="team-card" data-part="team-card" data-agent="{_e(card.agent_id)}" data-open="false" role="button" tabindex="0">'
            f'<div class="team-card-top"><div class="agent agent-lg" data-part="agent-card">'
            f'<div class="avatar" data-part="avatar" style="background:{_e(card.colour)}">{_e(card.initials)}</div>'
            f'<div class="agent-text"><div class="agent-name" data-part="name">{_e(card.names)}, {_e(card.role)}</div>'
            f'<div class="agent-model" data-part="model">{_e(card.model)}</div></div></div>'
            f'<span class="team-hint">{_e(hint)}</span></div>'
            f'<p class="team-blurb">{_e(card.blurb)}</p>'
            f'<div class="team-detail" data-part="team-card-detail" hidden>'
            f'<span class="team-k">Role</span><span>{_e(card.role)}</span>'
            f'<span class="team-k">Owns</span><span>{_e(card.owns)}</span>'
            f'<span class="team-k">Sees</span><span>{_e(card.sees)}</span>'
            f'<span class="team-k">Tools</span><span>{_e(card.tools)}</span></div></div>'
        )
    return f'<div class="team-grid" data-part="team-grid">{"".join(items)}</div>'


def render_replay(pinned: PinnedRun) -> str:
    if not pinned.available:
        note = "The pinned recording is not on this machine, so the replay is not shown."
        return (
            '<section id="replay" class="intro-section is-wide" data-part="replay">'
            '<div class="replay-head"><div class="intro-eyebrow">Replay of a recorded run</div></div>'
            f'<div class="replay-frame" data-part="replay-frame"><div class="replay-note">{_e(note)}</div></div></section>'
        )
    caption = f"Read-only · dataset {pinned.dataset_id} · exit {pinned.exit}"
    src = _e(f"/demo?public=1&run={pinned.run_id}&speed=1")
    return (
        '<section id="replay" class="intro-section is-wide" data-part="replay">'
        f'<div class="replay-head"><div class="intro-eyebrow">Replay of a recorded run</div><span class="replay-caption">{_e(caption)}</span></div>'
        f'<div class="replay-frame" data-part="replay-frame" data-run="{_e(pinned.run_id)}">'
        '<div class="replay-bar"><span class="replay-dot-label"><span class="replay-dot"></span>Replay</span>'
        '<span class="replay-speeds"><button type="button" class="replay-speed is-on" data-speed="1">1x</button>'
        '<button type="button" class="replay-speed" data-speed="4">4x</button></span></div>'
        f'<iframe class="replay-iframe" id="replay-iframe" title="Replay of a recorded run" src="{src}" loading="lazy"></iframe>'
        "</div></section>"
    )


def render_page(
    settings: Settings, seat_table: dict[str, Any] | None, events: list[Any], template_path: Path = PAGE_PATH
) -> str:
    """Fill the flattened page's slots. The build stamp placeholder is left for the route to fill."""
    shell = template_path.read_text(encoding="utf-8")
    figures = diagrams()
    body: list[str] = []
    for section in sections():
        rendered = render_section(section)
        after = ""
        if section.diagram and section.diagram in figures:
            figure = figures[section.diagram]
            after += f'<figure class="intro-figure" data-part="diagram" data-diagram="{_e(figure.name)}">{figure.svg}</figure>'
        if section.id == "the-team":
            after += render_team(team_cards(seat_table))
        body.append(rendered.replace(f"{{{{AFTER:{section.id}}}}}", after))
    body.append(render_replay(pinned_run(settings, events)))
    return shell.replace("{{SECTIONS}}", "".join(body))
