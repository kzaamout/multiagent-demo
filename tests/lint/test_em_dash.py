from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
DASH = chr(0x2014)


def lint_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("lint_em_dash", ROOT / "scripts" / "lint_em_dash.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["lint_em_dash"] = module
    spec.loader.exec_module(module)
    return module


def test_repository_has_no_em_dashes() -> None:
    lint = lint_module()
    hits, scanned, _ = lint.run(ROOT, [])
    assert scanned > 40
    assert hits == [], hits[:5]


def test_lint_catches_an_em_dash(tmp_path: Path) -> None:
    lint = lint_module()
    bad = tmp_path / "copy.md"
    bad.write_text("fine line\nnot fine " + DASH + " here\n", encoding="utf-8")
    hits, _, _ = lint.run(ROOT, [str(tmp_path)])
    assert any(h[1] == 2 and "copy.md" in h[0] for h in hits)


def test_vendor_exclusions_are_explicit() -> None:
    lint = lint_module()
    assert lint.is_vendor(".claude/skills/speckit-plan/SKILL.md")
    assert lint.is_vendor(".specify/templates/plan-template.md")
    assert not lint.is_vendor(".specify/memory/constitution.md")
    assert not lint.is_vendor("app/web/pages/demo.html")


def test_design_bundle_template_is_linted() -> None:
    lint = lint_module()
    template = '"<p>ok \\u2014 not ok</p>"'
    bundle = (
        "<script>// loader "
        + DASH
        + ' vendor</script><script type="__bundler/template">'
        + template
        + "</script>"
    )
    decoded = lint.design_template(bundle)
    assert decoded is not None and DASH in decoded
