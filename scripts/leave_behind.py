"""Produce the leave-behind for a run: the proposal PDF, the run timeline PDF with the run's
metrics beside it, and the Introduction PDF (spec 0.7 section 8, slice S7).

Usage: uv run python scripts/leave_behind.py [--run RUN_ID] [--out DIR] [--force]

Without --run, the newest recording that finished its job is used. Without --out, the files go to
runs/<run_id>/leave-behind/. Prints each path. Exits 2, naming the tool, when pandoc or Typst is
missing, and 1 with one line when no suitable recording exists.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.leave_behind import LeaveBehindError, build_leave_behind  # noqa: E402


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--run", help="the run id; default: the newest recording that finished its job")
    parser.add_argument("--out", help="folder for the files; default: runs/<run_id>/leave-behind/")
    parser.add_argument(
        "--force", action="store_true", help="recompile the Introduction PDF even when unchanged"
    )
    args = parser.parse_args(argv)
    try:
        result = build_leave_behind(
            load_settings(), run_id=args.run, out_dir=Path(args.out) if args.out else None, force=args.force
        )
    except LeaveBehindError as error:
        print(error)
        return 2 if str(error).startswith("compiler missing") else 1
    print(f"run {result.run_id}")
    for path in [*result.pdfs, *([result.metrics] if result.metrics else [])]:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
