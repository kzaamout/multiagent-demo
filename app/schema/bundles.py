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
    images: list[str] = []
    """Run-relative paths of page images sent with the call as image content (S4, the Reviewer)."""

    def sections(self) -> list[tuple[str, str]]:
        """The six sections the prompt toggle shows, in order."""
        return [
            ("System instructions", self.system),
            ("Context provided", self.context_slice),
            ("Task", self.task),
            ("Tools available", "\n".join(self.tools) if self.tools else "(none)"),
            ("Model", self.model.label),
            ("Pages", "\n".join(self.images) if self.images else "(none)"),
        ]
