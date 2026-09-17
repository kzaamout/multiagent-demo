"""Write the Introduction PDF for the leave-behind (S6).

Usage: uv run python scripts/intro_pdf.py [--out PATH] [--force]

Prints the PDF's path. Exits 2, naming the tool, when pandoc or Typst is missing.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.intro.pdf import missing_tools, render_pdf  # noqa: E402


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", help="copy the PDF to this path as well")
    parser.add_argument("--force", action="store_true", help="compile even when nothing changed")
    args = parser.parse_args(argv)
    missing = missing_tools()
    if missing:
        print("compiler missing: " + ", ".join(missing))
        return 2
    pdf = render_pdf(load_settings(), force=args.force)
    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pdf, target)
        pdf = target
    print(pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
