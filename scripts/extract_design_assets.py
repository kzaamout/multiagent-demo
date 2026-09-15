"""Extract fonts and the human-figure icon from the Claude Design bundles.

Reads design/*.html (never writes there), decodes the bundler manifest, and writes
the woff2 faces and the SVG icon into app/web/static. Font file names are derived
from the @font-face declarations in the decoded page template so they are readable.
"""

from __future__ import annotations

import base64
import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESIGN = ROOT / "design"
STATIC = ROOT / "app" / "web" / "static"

FAMILY_SLUG = {"Inter": "inter", "JetBrains Mono": "jetbrains-mono", "Space Grotesk": "space-grotesk"}


def load_bundle(path: Path) -> tuple[dict[str, dict[str, object]], str]:
    text = path.read_text(encoding="utf-8")
    manifest = re.search(r'<script type="__bundler/manifest">(.*?)</script>', text, re.S)
    template = re.search(r'<script type="__bundler/template">(.*?)</script>', text, re.S)
    if not manifest or not template:
        raise SystemExit(f"{path.name}: not a Claude Design bundle")
    return json.loads(manifest.group(1)), json.loads(template.group(1))


def decode_asset(entry: dict[str, object]) -> bytes:
    raw = base64.b64decode(str(entry["data"]))
    if entry.get("compressed"):
        raw = gzip.decompress(raw)
    return raw


def font_faces(template: str) -> list[tuple[str, str, str, str]]:
    """Return (family, weight, range_comment, asset_id) for each @font-face block."""
    faces: list[tuple[str, str, str, str]] = []
    pattern = re.compile(
        r"/\* (?P<range>[a-z-]+) \*/\s*@font-face \{\s*font-family: '(?P<family>[^']+)';.*?"
        r"font-weight: (?P<weight>\d+);.*?src: url\(\"(?P<asset>[0-9a-f-]+)\"\)",
        re.S,
    )
    for m in pattern.finditer(template):
        faces.append((m.group("family"), m.group("weight"), m.group("range"), m.group("asset")))
    return faces


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    fonts_dir = STATIC / "fonts"
    img_dir = STATIC / "img"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    written: dict[str, str] = {}
    for page in ["Demo", "Introduction", "Login", "Settings", "Preflight"]:
        manifest, template = load_bundle(DESIGN / f"{page}.html")
        for family, weight, rng, asset_id in font_faces(template):
            name = f"{FAMILY_SLUG.get(family, family.lower())}-{weight}-{rng}.woff2"
            target = fonts_dir / name
            if target.exists():
                continue
            entry = manifest.get(asset_id)
            if not entry:
                print(f"warning: {page}: asset {asset_id} for {name} missing")
                continue
            target.write_bytes(decode_asset(entry))
            written[name] = f"{page} {asset_id}"
        for asset_id, entry in manifest.items():
            if entry.get("mime") == "image/svg+xml":
                target = img_dir / "person.svg"
                if not target.exists():
                    target.write_bytes(decode_asset(entry))
                    written["person.svg"] = f"{page} {asset_id}"

    for name, src in sorted(written.items()):
        print(f"wrote {name:40} from {src}")
    print(f"{len(written)} files written; fonts present: {len(list(fonts_dir.glob('*.woff2')))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
