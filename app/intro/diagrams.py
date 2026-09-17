"""The Introduction's three diagrams as SVG, from one description (S6 decisions 2a and 3a).

The architecture is the export's band layout drawn as SVG so the page and the PDF carry the
same drawing: renderers, the event stream bus, the Orchestrator with its six-stage strip and
retry badge, the six agent cards, tool boxes under the specialists and the Writer only, the model
providers along the bottom with dotted lines, and the human figure with the one door. The
demo-versus-production figure draws the architecture twice with badge sets. The loop figure
reproduces the Demo strip's geometry, fully lit, with the backward arrows labelled and the exits
card. Colours and sizes are the export's.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

INK = "#17171c"
GREY = "#75758a"
LINE = "#d9d9dd"
PAPER = "#eeece7"
WHITE = "#ffffff"
RED = "#b30000"
BLUE = "#1863dc"
FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', Menlo, Consolas, monospace"

SEATS: tuple[tuple[str, str, str, str], ...] = (
    ("orchestrator", "Orchestrator", "O", "#17171c"),
    ("intake", "Intake Analyst", "A", "#003c33"),
    ("estimator", "Estimator", "E", "#b45309"),
    ("pricing", "Pricing", "P", "#1863dc"),
    ("writer", "Writer", "W", "#071829"),
    ("reviewer", "Reviewer", "R", "#b30000"),
)
TOOLS: dict[str, tuple[str, ...]] = {
    "intake": ("document parser", "document preparation"),
    "estimator": ("drawing reader", "quantity calculator"),
    "pricing": ("price list",),
    "writer": ("template", "compiler"),
}
PROVIDERS = ("Bedrock", "Anthropic", "Gemini", "Grok", "Local")
STAGES = ("Intake", "Plan", "Work", "Assemble", "Review", "Handoff")
EXITS = ("Reviewer passed", "Review limit reached", "Blocker escalated", "Not ready")

DEMO_BADGES = {
    "renderers": "laptop browser",
    "orchestrator": "local Python process",
    "agents": "local Python process",
    "tools": "Python functions",
    "memory": "knowledge file",
    "providers": "Bedrock plus keys in .env",
}
AWS_BADGES = {
    "renderers": "Slack, email, your tools",
    "orchestrator": "AgentCore Runtime",
    "agents": "AgentCore Runtime",
    "tools": "AgentCore Gateway",
    "memory": "AgentCore Memory",
    "providers": "Bedrock; Gateway for others",
    "observability": "AgentCore Observability",
    "identity": "AgentCore Identity",
}


@dataclass(frozen=True)
class Diagram:
    name: str
    svg: str
    text: str


def _t(
    x: float,
    y: float,
    text: str,
    size: float = 13,
    fill: str = INK,
    weight: int = 400,
    anchor: str = "start",
    mono: bool = False,
) -> str:
    family = MONO if mono else FONT
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" fill="{fill}" '
        f'font-weight="{weight}" text-anchor="{anchor}">{html.escape(text, quote=False)}</text>'
    )


def _box(
    x: float,
    y: float,
    w: float,
    h: float,
    fill: str = WHITE,
    stroke: str = LINE,
    r: float = 8,
    dash: str = "",
    width: float = 1,
) -> str:
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"{extra}/>'


def _badge(x: float, y: float, text: str, aws: bool) -> str:
    w = 7.2 * len(text) + 18
    fill = "#e8f0ff" if aws else PAPER
    fg = BLUE if aws else INK
    return _box(x, y, w, 20, fill=fill, stroke=fill, r=10) + _t(
        x + w / 2, y + 14, text, 11, fg, anchor="middle"
    )


def _band_label(y: float, text: str) -> str:
    return _t(20, y, text.upper(), 11, GREY, mono=True)


def _human(x: float, y: float) -> str:
    return (
        f'<circle cx="{x}" cy="{y}" r="9" fill="none" stroke="{INK}" stroke-width="1.6"/>'
        f'<path d="M{x - 16} {y + 36} a16 16 0 0 1 32 0" fill="none" stroke="{INK}" stroke-width="1.6"/>'
    )


def _architecture_body(ox: float, badges: dict[str, str] | None, aws: bool, width: float = 900) -> list[str]:
    """The bands at horizontal offset `ox`, `width` wide."""
    parts: list[str] = []
    x0 = ox + 20
    # With badges, a column on the right keeps them off the bands.
    inner = width - 40 - (170 if badges else 0)
    bx = x0 + inner + 14
    # Renderers
    parts.append(_band_label(30 + 0, ""))
    parts.append(_t(x0, 30, "RENDERERS", 11, GREY, mono=True))
    parts.append(_box(x0 + 110, 12, 150, 40) + _t(x0 + 185, 37, "Web UI", 14, INK, 500, "middle"))
    parts.append(
        _box(x0 + 280, 12, 150, 40, fill="#f5f5f7", stroke=LINE)
        + _t(x0 + 355, 37, "Slack", 14, GREY, 400, "middle")
    )
    parts.append(
        _box(x0 + 396, 18, 42, 16, fill=PAPER, stroke=PAPER, r=8)
        + _t(x0 + 417, 30, "future", 9, GREY, anchor="middle")
    )
    if badges:
        parts.append(_badge(bx, 22, badges["renderers"], aws))
    # Event stream bus
    parts.append(_t(x0, 92, "EVENT STREAM", 11, GREY, mono=True))
    parts.append(f'<line x1="{x0 + 110}" y1="86" x2="{x0 + inner}" y2="86" stroke="{INK}" stroke-width="3"/>')
    for cx in (x0 + 185, x0 + 355):
        parts.append(f'<line x1="{cx}" y1="52" x2="{cx}" y2="86" stroke="{GREY}" stroke-width="1.2"/>')
    parts.append(_t(x0 + inner, 78, "typed events, one per action", 11, GREY, anchor="end"))
    # Orchestrator
    oy = 112
    parts.append(_t(x0, oy + 26, "ORCHESTRATOR", 11, GREY, mono=True))
    box_w = inner - 110 - 96
    parts.append(_box(x0 + 110, oy, box_w, 74, stroke=INK, r=12))
    parts.append(_t(x0 + 126, oy + 22, "Orchestrator: the only component that changes state", 13, INK, 500))
    sx = x0 + 126
    step = (box_w - 32 - 92) / 6
    for i, stage in enumerate(STAGES):
        stx = sx + i * step
        parts.append(
            _box(stx, oy + 34, step - 10, 28, fill=INK, stroke=INK, r=14)
            + _t(stx + (step - 10) / 2, oy + 52, stage, 12, WHITE, anchor="middle")
        )
        if i < len(STAGES) - 1:
            parts.append(_t(stx + step - 5, oy + 52, ">", 12, GREY, anchor="middle"))
    badge_x = sx + 6 * step + 4
    parts.append(
        _box(badge_x, oy + 36, 84, 22, fill=PAPER, stroke=PAPER, r=11)
        + _t(badge_x + 42, oy + 51, "retry N of M", 10, INK, anchor="middle", mono=True)
    )
    parts.append(
        f'<line x1="{x0 + 185}" y1="86" x2="{x0 + 185}" y2="{oy}" stroke="{GREY}" stroke-width="1.2"/>'
    )
    if badges:
        parts.append(_badge(x0 + 126, oy - 24, badges["orchestrator"], aws))
    # Human, one door
    hx = x0 + inner - 22
    parts.append(_human(hx, oy + 16))
    parts.append(
        f'<line x1="{x0 + 110 + box_w + 4}" y1="{oy + 37}" x2="{hx - 22}" y2="{oy + 37}" stroke="{INK}" stroke-width="1.6" marker-end="url(#arrow)"/>'
    )
    parts.append(_t(x0 + 110 + box_w + 34, oy + 62, "one door", 10, INK, anchor="middle"))
    parts.append(_t(hx, oy + 72, "You", 11, INK, anchor="middle"))
    # Agents
    ay = 208
    parts.append(_t(x0, ay + 30, "AGENTS", 11, GREY, mono=True))
    card_w = (inner - 110) / 6 - 8
    for i, (_agent_id, role, initial, colour) in enumerate(SEATS):
        cx = x0 + 110 + i * (card_w + 8)
        parts.append(_box(cx, ay, card_w, 56))
        parts.append(f'<circle cx="{cx + 22}" cy="{ay + 28}" r="14" fill="{colour}"/>')
        parts.append(_t(cx + 22, ay + 33, initial, 12, WHITE, 500, "middle"))
        parts.append(_t(cx + 44, ay + 25, role, 11, INK, 500))
        parts.append(_t(cx + 44, ay + 41, "model in grey", 10, GREY))
        parts.append(
            f'<line x1="{cx + card_w / 2}" y1="{oy + 74}" x2="{cx + card_w / 2}" y2="{ay}" stroke="{GREY}" stroke-width="1" stroke-dasharray="2 3"/>'
        )
    if badges:
        parts.append(_badge(bx, ay - 22, badges["agents"], aws))
    # Tools
    ty = 284
    parts.append(_t(x0, ty + 16, "TOOLS", 11, GREY, mono=True))
    for i, (agent_id, _, _, _) in enumerate(SEATS):
        cx = x0 + 110 + i * (card_w + 8)
        for j, tool in enumerate(TOOLS.get(agent_id, ())):
            parts.append(
                _box(cx, ty + j * 22, card_w, 18, fill=PAPER, stroke=LINE, r=4)
                + _t(cx + 6, ty + 13 + j * 22, tool, 10, INK)
            )
    if badges:
        parts.append(_badge(bx, ty - 2, badges["tools"], aws))
        parts.append(_badge(bx, ty + 22, badges["memory"], aws))
    # Providers
    py = 352
    parts.append(_t(x0, py + 30, "MODEL PROVIDERS", 11, GREY, mono=True))
    pw = (inner - 110) / 5 - 8
    for i, provider in enumerate(PROVIDERS):
        px = x0 + 110 + i * (pw + 8)
        parts.append(
            _box(px, py + 12, pw, 30)
            + _t(
                px + pw / 2, py + 31, provider, 12, INK if provider != "Local" else "#2f6b5e", anchor="middle"
            )
        )
        target = x0 + 110 + (i + 0.5) * (card_w + 8)
        parts.append(
            f'<line x1="{px + pw / 2}" y1="{py + 12}" x2="{target}" y2="{ay + 56}" stroke="{GREY}" stroke-width="1" stroke-dasharray="3 4"/>'
        )
    if badges:
        parts.append(_badge(bx, py + 16, badges["providers"], aws))
        if "observability" in badges:
            parts.append(_badge(x0 + 110, py + 52, badges["observability"], aws))
            parts.append(_badge(x0 + 330, py + 52, badges["identity"], aws))
    return parts


def _wrap(name: str, width: float, height: float, parts: list[str], title: str) -> Diagram:
    defs = (
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="{INK}"/></marker>'
        '<marker id="arrow-red" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="{RED}"/></marker></defs>'
    )
    body = "".join(parts)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" width="100%" '
        f'role="img" aria-label="{html.escape(title)}" data-diagram="{name}">{defs}'
        f'<rect x="0" y="0" width="{width:.0f}" height="{height:.0f}" fill="{WHITE}"/>{body}</svg>'
    )
    text = " ".join(html.unescape(t) for t in re.findall(r">([^<>]+)</text>", svg))
    return Diagram(name=name, svg=svg, text=text)


def architecture_svg() -> Diagram:
    return _wrap(
        "architecture",
        900,
        420,
        _architecture_body(0, None, False),
        "Architecture: renderers, event stream, orchestrator, agents, tools, model providers",
    )


def demo_vs_production_svg() -> Diagram:
    parts: list[str] = []
    parts.append(_t(20, 26, "DEMO", 12, INK, 500, mono=True))
    parts.append(_t(1020 + 20, 26, "YOUR AWS ACCOUNT", 12, BLUE, 500, mono=True))
    parts.append(f'<line x1="1010" y1="10" x2="1010" y2="470" stroke="{LINE}" stroke-width="1"/>')
    parts.append(
        f'<g transform="translate(0,30)">{"".join(_architecture_body(0, DEMO_BADGES, False, width=1000))}</g>'
    )
    parts.append(
        f'<g transform="translate(1020,30)">{"".join(_architecture_body(0, AWS_BADGES, True, width=1000))}</g>'
    )
    return _wrap(
        "demo-vs-production",
        2020,
        480,
        parts,
        "Demo versus production: the same shapes on a laptop and in your AWS account",
    )


def loop_svg() -> Diagram:
    parts: list[str] = []
    y = 70
    pill_w, gap = 118, 40
    x0 = 30
    centers: list[float] = []
    for i, stage in enumerate(STAGES):
        x = x0 + i * (pill_w + gap)
        centers.append(x + pill_w / 2)
        parts.append(_box(x, y, pill_w, 44, fill=INK, stroke=INK, r=22))
        parts.append(_t(x + 20, y + 28, "✓", 13, WHITE, 500))
        parts.append(_t(x + 38, y + 28, stage, 15, WHITE, 500))
        if stage in ("Intake", "Work", "Handoff"):
            parts.append(
                f'<circle cx="{x + pill_w - 16}" cy="{y + 17}" r="4" fill="none" stroke="{WHITE}" stroke-width="1.4"/>'
            )
            parts.append(
                f'<path d="M{x + pill_w - 24} {y + 31} a8 8 0 0 1 16 0" fill="none" stroke="{WHITE}" stroke-width="1.4"/>'
            )
        if i < len(STAGES) - 1:
            parts.append(
                f'<line x1="{x + pill_w + 6}" y1="{y + 22}" x2="{x + pill_w + gap - 8}" y2="{y + 22}" stroke="{INK}" stroke-width="1.6" marker-end="url(#arrow)"/>'
            )
    # retry badge on Review
    rx = x0 + 4 * (pill_w + gap) + pill_w - 30
    parts.append(
        _box(rx - 26, y - 26, 92, 20, fill=INK, stroke=INK, r=10)
        + _t(rx + 20, y - 12, "retry N of M", 10, WHITE, anchor="middle", mono=True)
    )

    # backward arrows, each labelled below its curve on a white plate so the text never sits on a line
    def back(from_i: int, to_i: int, depth: float, label: str) -> None:
        sx, tx = centers[from_i], centers[to_i]
        parts.append(
            f'<path d="M{sx} {y + 46} C {sx} {y + 46 + depth}, {tx} {y + 46 + depth}, {tx} {y + 48}" fill="none" stroke="{RED}" stroke-width="1.8" marker-end="url(#arrow-red)"/>'
        )
        lx, ly = (sx + tx) / 2, y + 46 + depth * 0.75 + 16
        w = 6.3 * len(label) + 12
        parts.append(_box(lx - w / 2, ly - 12, w, 17, fill=WHITE, stroke=WHITE, r=4))
        parts.append(_t(lx, ly, label, 11, RED, anchor="middle"))

    back(4, 3, 36, "Review to Assemble: the writing is wrong")
    back(4, 2, 76, "Review to Work: a source figure is wrong")
    back(2, 0, 116, "Work to Intake: the brief is incomplete")
    # exits card off Handoff, and Not ready off Intake
    cx = centers[5] - 190
    cy = y + 150
    parts.append(
        f'<line x1="{centers[5]}" y1="{y + 44}" x2="{centers[5]}" y2="{cy}" stroke="{INK}" stroke-width="1.4" marker-end="url(#arrow)"/>'
    )
    parts.append(_box(cx, cy, 250, 118, stroke=INK, r=12))
    parts.append(_t(cx + 14, cy + 22, "The run ends one of four ways", 12, INK, 500))
    for i, exit_name in enumerate(EXITS):
        parts.append(_t(cx + 14, cy + 44 + i * 20, "• " + exit_name, 12, INK))
    nx = centers[0]
    parts.append(
        f'<line x1="{nx}" y1="{y + 44}" x2="{nx}" y2="{cy + 40}" stroke="{GREY}" stroke-width="1.2" stroke-dasharray="3 4" marker-end="url(#arrow)"/>'
    )
    parts.append(_box(nx - 80, cy + 44, 160, 40, fill=PAPER, stroke=PAPER, r=8))
    parts.append(_t(nx, cy + 61, "Not ready", 12, INK, 500, anchor="middle"))
    parts.append(_t(nx, cy + 76, "stops the run at Intake", 11, GREY, anchor="middle"))
    return _wrap(
        "loop",
        1000,
        340,
        parts,
        "The agentic loop: six stages, forward arrows, three labelled backward arrows, four exits",
    )


def diagrams() -> dict[str, Diagram]:
    return {d.name: d for d in (architecture_svg(), loop_svg(), demo_vs_production_svg())}
