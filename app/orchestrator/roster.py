"""Seats, names, colours, and default models (spec 4.1 to 4.3, colours from the export)."""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.schema.events import Agent, Model


@dataclass(frozen=True)
class Seat:
    agent_id: str
    role: str
    names: tuple[str, str]
    colour: str
    default_model: Model
    workflows: tuple[str, ...]


BEDROCK_SONNET = Model(provider="bedrock", model_id="claude-sonnet", label="claude-sonnet via Bedrock")
BEDROCK_SONNET_VISION = Model(
    provider="bedrock", model_id="claude-sonnet", label="claude-sonnet via Bedrock (vision)"
)
OLLAMA_LLAMA = Model(provider="ollama", model_id="llama3.1:8b", label="llama3.1 8b, local")
GOOGLE_GEMINI = Model(provider="google", model_id="gemini-2.5-pro", label="gemini-2.5-pro via Google")

SEATS: tuple[Seat, ...] = (
    Seat("orchestrator", "Orchestrator", ("Oscar", "Olivia"), "#17171c", BEDROCK_SONNET, ("electrical_rfp", "appraisal")),
    Seat("intake", "Intake Analyst", ("Anna", "Arjun"), "#003c33", BEDROCK_SONNET, ("electrical_rfp", "appraisal")),
    Seat("estimator", "Estimator", ("Elias", "Elena"), "#b45309", BEDROCK_SONNET_VISION, ("electrical_rfp",)),
    Seat("pricing", "Pricing", ("Pavel", "Priya"), "#1863dc", OLLAMA_LLAMA, ("electrical_rfp",)),
    Seat("writer", "Writer", ("Wesley", "Willa"), "#071829", BEDROCK_SONNET, ("electrical_rfp", "appraisal")),
    Seat("reviewer", "Reviewer", ("Rafael", "Rosa"), "#b30000", GOOGLE_GEMINI, ("electrical_rfp", "appraisal")),
    Seat("case", "Case Manager", ("Carlos", "Clara"), "#2f6b5e", BEDROCK_SONNET, ("appraisal",)),
    Seat("market", "Market Analyst", ("Marcus", "Maya"), "#4a4a8a", OLLAMA_LLAMA, ("appraisal",)),
)

SEAT_BY_ID: dict[str, Seat] = {seat.agent_id: seat for seat in SEATS}
HUMAN_COLOUR = "#75758a"

EXPORT_NAMES: dict[str, str] = {
    "orchestrator": "Oscar",
    "intake": "Anna",
    "estimator": "Elena",
    "pricing": "Pavel",
    "writer": "Willa",
    "reviewer": "Rafael",
    "case": "Clara",
    "market": "Marcus",
}


def seats_for(workflow: str) -> list[Seat]:
    return [seat for seat in SEATS if workflow in seat.workflows]


def build_roster(
    workflow: str,
    seed: int | None = None,
    names: dict[str, str] | None = None,
) -> dict[str, Agent]:
    """Choose one of the two names per seat at random (or from an override) for one run."""
    rng = random.Random(seed)
    roster: dict[str, Agent] = {}
    for seat in seats_for(workflow):
        override = (names or {}).get(seat.agent_id)
        if override is not None:
            if override not in seat.names:
                raise ValueError(f"{override} is not a name for seat {seat.agent_id}")
            name = override
        else:
            name = rng.choice(seat.names)
        roster[seat.agent_id] = Agent(
            agent_id=seat.agent_id, name=name, role=seat.role, model=seat.default_model
        )
    return roster


def colour_for(agent_id: str) -> str:
    seat = SEAT_BY_ID.get(agent_id)
    return seat.colour if seat else HUMAN_COLOUR
