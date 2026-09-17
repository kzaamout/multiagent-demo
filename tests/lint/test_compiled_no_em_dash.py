"""No em dash reaches a compiled page (constitution IX covers generated content and deliverables)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.compile import compile_draft, read_brand

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "app" / "agents" / "stubs" / "fixtures" / "draft-fixture.md"


@pytest.mark.compiler
def test_compiled_pages_carry_no_em_dash(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    (dataset / "brand.yaml").write_text('prospect_name: "Acme Holdings"\n', encoding="utf-8")
    record = compile_draft(tmp_path / "run", 1, FIXTURE.read_text(encoding="utf-8"), read_brand(dataset))
    texts = json.loads((tmp_path / "run" / record.pages_path).read_text(encoding="utf-8"))
    assert all(chr(0x2014) not in t for t in texts)
