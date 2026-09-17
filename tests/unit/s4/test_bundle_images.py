"""A bundle can carry page images, shown as a Pages section in the prompt toggle (spec FR-007)."""

from __future__ import annotations

from app.schema.bundles import PromptBundle
from app.schema.events import Model


def _bundle(images: list[str]) -> PromptBundle:
    return PromptBundle(
        prompt_ref="pb-test-01",
        system="You are the Reviewer.",
        context_slice="## Brief\nx",
        task="Review draft v1.",
        tools=[],
        model=Model(provider="test", model_id="scripted", label="scripted"),
        images=images,
    )


def test_images_default_to_none_and_show_as_a_section() -> None:
    plain = _bundle([])
    assert plain.images == []
    assert [label for label, _ in plain.sections()][-1] == "Pages"
    assert dict(plain.sections())["Pages"] == "(none)"
    with_pages = _bundle(["artifacts/v1/page-01.png", "artifacts/v1/page-02.png"])
    assert dict(with_pages.sections())["Pages"] == "artifacts/v1/page-01.png\nartifacts/v1/page-02.png"


def test_bundle_round_trips_through_json() -> None:
    bundle = _bundle(["artifacts/v1/page-01.png"])
    again = PromptBundle.model_validate_json(bundle.model_dump_json())
    assert again.images == ["artifacts/v1/page-01.png"]
