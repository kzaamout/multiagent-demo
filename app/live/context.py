"""Context slices: the exact material a seat is given for one call.

The Orchestrator assembles material from the run state; this module keeps only what the seat's
definition allows and renders it as the text stored in the prompt bundle. A slice is built
once and sent as built, so the prompt toggle shows what the model saw.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.seats.definitions import ALL_KINDS, SEAT_DEFINITIONS


@dataclass(frozen=True)
class Material:
    kind: str
    label: str
    text: str
    source_id: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in ALL_KINDS:
            raise ValueError(f"unknown material kind {self.kind}")


@dataclass(frozen=True)
class ContextSlice:
    agent_id: str
    items: tuple[Material, ...]
    withheld: tuple[str, ...] = field(default_factory=tuple)

    def kinds(self) -> set[str]:
        return {m.kind for m in self.items}

    def render(self) -> str:
        blocks: list[str] = []
        for item in self.items:
            header = f"## {item.label}"
            if item.source_id:
                header += f" (source id: {item.source_id})"
            blocks.append(f"{header}\n{item.text.strip()}")
        return "\n\n".join(blocks)


def build_context(agent_id: str, materials: list[Material]) -> ContextSlice:
    """Keep the materials this seat may see, in the order given, and record what was withheld."""
    definition = SEAT_DEFINITIONS[agent_id]
    kept: list[Material] = []
    withheld: list[str] = []
    for material in materials:
        if definition.may_see(material.kind):
            kept.append(material)
        else:
            withheld.append(material.kind)
    return ContextSlice(agent_id=agent_id, items=tuple(kept), withheld=tuple(withheld))
