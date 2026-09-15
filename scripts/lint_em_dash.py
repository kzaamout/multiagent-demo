"""Em-dash lint (constitution IX and XVI).

Fails when U+2014 appears in any git-tracked text file, in anything under runs/, or in any
path given on the command line.

Two classes of tracked file are handled specially, because the project may not edit them:
- Vendor tooling installed by Spec Kit (.claude/skills/, and .specify/ except memory/) is
  excluded. It is not project content and is overwritten on upgrade.
- The Claude Design bundles in design/*.html are never edited (design/README.md). Their
  bundler loader script is vendor code and is skipped; the decoded page template, which is
  the design content, is linted.
Every exclusion is listed in VENDOR_PREFIXES and reported in the output.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

EM_DASH = "—"
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".woff2", ".woff", ".ttf", ".pdf", ".ico", ".zip"}
VENDOR_PREFIXES = (".claude/skills/", ".specify/")
VENDOR_KEEP = (".specify/memory/",)
DESIGN_BUNDLE = re.compile(r"^design/[^/]+\.html$")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def tracked_files(root: Path) -> list[str]:
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]
    return [name for name in out.decode("utf-8").split("\0") if name]


def is_vendor(rel: str) -> bool:
    return rel.startswith(VENDOR_PREFIXES) and not rel.startswith(VENDOR_KEEP)


def design_template(text: str) -> str | None:
    match = re.search(r'<script type="__bundler/template">(.*?)</script>', text, re.S)
    if not match:
        return None
    decoded = json.loads(match.group(1))
    return decoded if isinstance(decoded, str) else json.dumps(decoded)


def scan_text(label: str, text: str) -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if EM_DASH in line:
            hits.append((label, lineno, line.strip()[:120]))
    return hits


def run(root: Path, extra: list[str]) -> tuple[list[tuple[str, int, str]], int, list[str]]:
    hits: list[tuple[str, int, str]] = []
    skipped: list[str] = []
    scanned = 0
    candidates: list[tuple[str, Path]] = [(rel, root / rel) for rel in tracked_files(root)]
    runs = root / "runs"
    if runs.exists():
        candidates.extend((p.relative_to(root).as_posix(), p) for p in runs.rglob("*") if p.is_file())
    for arg in extra:
        p = Path(arg)
        files = [q for q in p.rglob("*") if q.is_file()] if p.is_dir() else [p] if p.is_file() else []
        candidates.extend((str(q), q) for q in files)

    seen: set[Path] = set()
    for rel, path in candidates:
        resolved = path.resolve()
        if resolved in seen or path.suffix.lower() in BINARY_SUFFIXES or not path.exists():
            continue
        seen.add(resolved)
        if is_vendor(rel):
            skipped.append(rel)
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        if DESIGN_BUNDLE.match(rel):
            template = design_template(text)
            if template is None:
                hits.extend(scan_text(rel, text))
            else:
                hits.extend(scan_text(f"{rel} (decoded page template)", template))
            continue
        hits.extend(scan_text(rel, text))
    return hits, scanned, skipped


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    hits, scanned, skipped = run(repo_root(), argv)
    if hits:
        for label, lineno, snippet in hits:
            print(f"em dash: {label}:{lineno}: {snippet}")
        print(f"FAIL: {len(hits)} em dash occurrence(s) in {len({h[0] for h in hits})} file(s)")
        return 1
    print(f"ok: no em dashes in {scanned} files ({len(skipped)} vendor tooling files excluded)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
