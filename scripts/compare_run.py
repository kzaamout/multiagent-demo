"""Compare a recorded run with its dataset's golden log (S3 evidence).

Usage: uv run python scripts/compare_run.py <run_id> [--runs runs] [--datasets datasets]

Prints the run's stage transitions, exit, retries, questions asked, blockers raised, and estimated
cost beside the golden log's, and exits 1 when the transitions or the exit differ. Golden logs are
compared on transitions and exit only; model text is never compared (datasets/README.md).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.runs.golden import compare, read_golden, terminal_exit, transitions  # noqa: E402
from app.schema.events import Event  # noqa: E402


def describe(events: list[Event]) -> dict[str, object]:
    last = events[-1] if events else None
    summary = last.payload.get("summary", {}) if last is not None and last.type == "run.terminated" else {}
    return {
        "transitions": " > ".join(
            f"{b}{' (back)' if direction == 'backward' else ''}" for _, b, direction in transitions(events)
        ),
        "exit": terminal_exit(events),
        "retries": (summary.get("retries") or {}).get("count"),
        "questions asked": sum(1 for e in events if e.type == "clarification.asked"),
        "blockers raised": sum(1 for e in events if e.type == "blocker.raised"),
        "estimated cost (USD)": summary.get("est_cost"),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("run_id")
    parser.add_argument("--runs", type=Path, default=ROOT / "runs")
    parser.add_argument("--datasets", type=Path, default=ROOT / "datasets")
    args = parser.parse_args(argv)

    path = args.runs / args.run_id / "events.jsonl"
    if not path.exists():
        print(f"no recording at {path}")
        return 2
    events = [
        Event.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line
    ]
    dataset_id = str(events[0].payload["dataset_id"])
    golden_path = args.datasets / dataset_id / "golden-events.jsonl"
    golden = read_golden(golden_path)
    result = compare(dataset_id, events, golden)

    print(f"run {args.run_id} on {dataset_id}")
    live, expected = describe(events), describe(golden)
    for key in live:
        print(f"  {key:22s} run: {live[key]}")
        if key in ("transitions", "exit"):
            print(f"  {'':22s} golden: {expected[key]}")
    print("MATCH" if result.ok else f"MISMATCH: {result.message}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
