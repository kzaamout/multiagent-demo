"""Prompt bundle: stored per call, referenced by prompt_ref on agent messages."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schema.events import Model


class PromptBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_ref: str
    system: str
    context_slice: str
    task: str
    tools: list[str]
    model: Model

    def sections(self) -> list[tuple[str, str]]:
        """The five sections the prompt toggle shows, in order."""
        return [
            ("System instructions", self.system),
            ("Context provided", self.context_slice),
            ("Task", self.task),
            ("Tools available", "\n".join(self.tools) if self.tools else "(none)"),
            ("Model", self.model.label),
        ]
