"""Provider registry and Strands model factory from config/models.yaml (research D8, D9).

Availability is a boolean and a reason. Credential values are never read into the registry's
state: Bedrock asks boto3 whether credentials resolve, Gemini and xAI check that their key
variable is set, and Ollama is asked which models it has.
"""

from __future__ import annotations

import dataclasses
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import yaml

from app.config import ROOT
from app.live.seat_call import SeatModel
from app.schema.events import Agent, Model

MODELS_PATH = ROOT / "config" / "models.yaml"


@dataclass(frozen=True)
class ModelSpec:
    key: str
    provider: str
    model_id: str
    label: str
    image_input: bool
    temperature: bool
    price_in: float
    price_out: float
    options: dict[str, Any] | None = None
    additional_args: dict[str, Any] | None = None
    max_tokens: int | None = None

    def model_object(self) -> Model:
        return Model(provider=self.provider, model_id=self.model_id, label=self.label)


@dataclass(frozen=True)
class SeatChoice:
    model: str
    temperature: float | None = None


@dataclass(frozen=True)
class Availability:
    provider: str
    available: bool
    reason: str


@dataclass(frozen=True)
class ModelConfig:
    providers: dict[str, dict[str, Any]]
    models: dict[str, ModelSpec]
    seats: dict[str, SeatChoice]

    @classmethod
    def load(cls, path: Path = MODELS_PATH) -> ModelConfig:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        models = {
            key: ModelSpec(
                key=key,
                provider=str(value["provider"]),
                model_id=str(value["model_id"]),
                label=str(value["label"]),
                image_input=bool(value.get("image_input", False)),
                temperature=bool(value.get("temperature", True)),
                price_in=float(value.get("price_in", 0)),
                price_out=float(value.get("price_out", 0)),
                options=dict(value["options"]) if value.get("options") else None,
                additional_args=dict(value["additional_args"]) if value.get("additional_args") else None,
                max_tokens=int(value["max_tokens"]) if value.get("max_tokens") else None,
            )
            for key, value in data["models"].items()
        }
        seats = {
            seat: SeatChoice(model=str(value["model"]), temperature=value.get("temperature"))
            for seat, value in data["seats"].items()
        }
        for seat, choice in seats.items():
            if choice.model not in models:
                raise ValueError(f"seat {seat} uses unknown model {choice.model}")
            if choice.temperature is not None and not models[choice.model].temperature:
                raise ValueError(f"seat {seat}: {choice.model} does not accept a temperature")
        return cls(providers=dict(data["providers"]), models=models, seats=seats)

    def seat_spec(self, agent_id: str) -> ModelSpec:
        return self.models[self.seats[agent_id].model]

    def with_seat(self, agent_id: str, model_key: str) -> ModelConfig:
        """This configuration with one seat moved to another model (an in-memory swap, S5 research D1).
        The seat's temperature is kept only when the new model accepts one."""
        if model_key not in self.models:
            raise ValueError(f"unknown model {model_key}")
        previous = self.seats.get(agent_id)
        temperature = previous.temperature if previous and self.models[model_key].temperature else None
        seats = {**self.seats, agent_id: SeatChoice(model=model_key, temperature=temperature)}
        return dataclasses.replace(self, seats=seats)


_FAMILY_WORD = re.compile(r"[a-z]+")


def family_of(spec: ModelSpec) -> str:
    """The model family a seat is on, for the Reviewer and Writer rule (constitution VI): the vendor's
    family word from the model id, such as claude, gemini, llama, qwen, gemma, or grok."""
    name = spec.model_id.rsplit("/", 1)[-1].lower()
    segments = [s for s in name.split(".") if s and s[0].isalpha()]
    candidate = segments[-1] if segments else name
    match = _FAMILY_WORD.search(candidate)
    return match.group(0) if match else candidate


def _bedrock_available(region: str | None) -> Availability:
    try:
        import boto3

        session = boto3.Session(region_name=region) if region else boto3.Session()
        has_credentials = session.get_credentials() is not None
        has_region = bool(session.region_name)
    except Exception:  # noqa: BLE001
        return Availability("bedrock", False, "boto3 could not start a session")
    if not has_credentials:
        return Availability("bedrock", False, "no AWS credentials in .env or the AWS profile chain")
    if not has_region:
        return Availability("bedrock", False, "no AWS region configured")
    return Availability("bedrock", True, "credentials resolved")


def _ollama_available(host: str, wanted: set[str], timeout: float = 2.0) -> Availability:
    try:
        response = httpx.get(f"{host.rstrip('/')}/api/tags", timeout=timeout)
        response.raise_for_status()
        names = {str(m.get("name")) for m in response.json().get("models", [])}
    except Exception:  # noqa: BLE001
        return Availability("ollama", False, f"Ollama not reachable at {host}")
    missing = sorted(w for w in wanted if w not in names and f"{w}:latest" not in names)
    if missing:
        return Availability("ollama", False, f"not pulled: {', '.join(missing)}")
    return Availability("ollama", True, "reachable, models present")


def check_availability(config: ModelConfig) -> dict[str, Availability]:
    result: dict[str, Availability] = {}
    for name, provider in config.providers.items():
        if name == "bedrock":
            result[name] = _bedrock_available(provider.get("region"))
        elif name == "ollama":
            wanted = {m.model_id for m in config.models.values() if m.provider == "ollama"}
            seat_models = {
                config.seat_spec(s).model_id for s in config.seats if config.seat_spec(s).provider == "ollama"
            }
            result[name] = _ollama_available(
                str(provider.get("host", "http://localhost:11434")), seat_models or wanted
            )
        else:
            key = str(provider.get("env_key", ""))
            present = bool(key) and bool(os.environ.get(key))
            result[name] = Availability(name, present, "key present" if present else "no credentials in .env")
    return result


def unavailable_seats(config: ModelConfig, availability: dict[str, Availability]) -> list[str]:
    """One sentence per seat whose provider is not available."""
    problems: list[str] = []
    for seat in config.seats:
        spec = config.seat_spec(seat)
        state = availability.get(spec.provider)
        if state is None or not state.available:
            reason = state.reason if state else "provider not configured"
            problems.append(f"{seat} needs {spec.label}: {reason}")
    return problems


def resolved_settings(spec: ModelSpec, choice: SeatChoice) -> dict[str, Any]:
    """The hyperparameters a seat runs with, in one shape for every provider. A value the provider fixes or
    the model defaults is named as such rather than guessed."""
    if choice.temperature is not None:
        temperature: Any = choice.temperature
    elif spec.temperature is False:
        temperature = "fixed by the provider"
    else:
        temperature = "model default"
    options = spec.options or {}
    extra = spec.additional_args or {}
    think: Any = "model default"
    if "think" in extra:
        think = bool(extra["think"])
    elif isinstance(extra.get("thinking"), dict) and "type" in extra["thinking"]:
        think = extra["thinking"]["type"] != "disabled"
    return {
        "temperature": temperature,
        "num_ctx": options.get("num_ctx", "model default"),
        "think": think,
        "max_tokens": spec.max_tokens or "model default",
    }


def strands_model_for(config: ModelConfig, agent_id: str) -> SeatModel:
    """Build the real Strands model for a seat. Only called for live runs with providers available."""
    spec = config.seat_spec(agent_id)
    choice = config.seats[agent_id]
    provider = config.providers[spec.provider]
    strands_model: Any
    if spec.provider == "bedrock":
        from strands.models import BedrockModel

        kwargs: dict[str, Any] = {"model_id": spec.model_id, "region_name": provider.get("region")}
        if choice.temperature is not None:
            kwargs["temperature"] = choice.temperature
        if spec.max_tokens:
            kwargs["max_tokens"] = spec.max_tokens
        if spec.additional_args:
            kwargs["additional_request_fields"] = dict(spec.additional_args)
        strands_model = BedrockModel(**kwargs)
    elif spec.provider == "ollama":
        from strands.models.ollama import OllamaModel

        kwargs = {"model_id": spec.model_id}
        if choice.temperature is not None:
            kwargs["temperature"] = choice.temperature
        if spec.options:
            kwargs["options"] = dict(spec.options)
        if spec.additional_args:
            kwargs["additional_args"] = dict(spec.additional_args)
        if spec.max_tokens:
            kwargs["max_tokens"] = spec.max_tokens
        strands_model = OllamaModel(str(provider.get("host", "http://localhost:11434")), **kwargs)
    elif spec.provider in ("google", "xai"):
        from strands.models.litellm import LiteLLMModel

        params: dict[str, Any] = {}
        if choice.temperature is not None:
            params["temperature"] = choice.temperature
        if spec.max_tokens:
            params["max_tokens"] = spec.max_tokens
        strands_model = LiteLLMModel(model_id=spec.model_id, params=params)
    else:
        raise ValueError(f"no Strands provider for {spec.provider}")
    return SeatModel(
        strands_model=strands_model,
        model=spec.model_object(),
        price_in=spec.price_in,
        price_out=spec.price_out,
        image_input=spec.image_input,
        settings=resolved_settings(spec, choice),
    )


class LiveUnavailable(RuntimeError):
    """A live run cannot start because a seat's provider or model is unavailable or unfit."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


SeatModelFactory = Callable[[str], SeatModel]


def live_roster(
    roster: dict[str, Agent], factory: SeatModelFactory
) -> tuple[dict[str, Agent], dict[str, SeatModel]]:
    """The run's roster with each seat's truthful model, and the seat models to call."""
    seat_models = {seat: factory(seat) for seat in roster}
    reviewer = seat_models.get("reviewer")
    if reviewer is not None and not reviewer.image_input:
        # The Reviewer judges the compiled page images (spec stage 5, S4 FR-008).
        raise LiveUnavailable(
            [
                f"the Reviewer's model {reviewer.model.label} cannot read page images; choose one with image_input"
            ]
        )
    updated = {
        seat: agent.model_copy(update={"model": seat_models[seat].model}) for seat, agent in roster.items()
    }
    return updated, seat_models
