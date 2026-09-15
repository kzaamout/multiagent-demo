"""JSON Schema export for the frozen event schema."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from app.schema.bundles import PromptBundle
from app.schema.events import PAYLOAD_MODELS, SCHEMA_VERSION, Event

ROOT = Path(__file__).resolve().parent.parent.parent
TARGET = ROOT / "docs" / "schema" / f"events-v{SCHEMA_VERSION}.json"


def build_schema() -> dict[str, Any]:
    payloads = {name: model.model_json_schema(by_alias=True) for name, model in PAYLOAD_MODELS.items()}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"Sterling AI multi-agent demo events v{SCHEMA_VERSION}",
        "version": SCHEMA_VERSION,
        "envelope": Event.model_json_schema(by_alias=True),
        "payloads": payloads,
        "prompt_bundle": PromptBundle.model_json_schema(by_alias=True),
    }


def render() -> str:
    return json.dumps(build_schema(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(render(), encoding="utf-8", newline="\n")
    sys.stdout.write(f"wrote {TARGET.relative_to(ROOT)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
