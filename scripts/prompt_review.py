"""What the recorded runs say a seat should be taught next (owner decision 2026-09-18).

    uv run python scripts/prompt_review.py             # print the review
    uv run python scripts/prompt_review.py --write     # also refresh docs/prompt-review.md

Teaching a seat from its own rejections fixed the largest failures on this team: Pricing skipping its price
tool, the Writer leaving money untagged, three seats replying with narration. Each time the work was the
same, reading what was refused and writing the example back into the seat's instructions. This does the
reading.

It suggests, it never edits. Every suggestion quotes the real refusal and names the runs it came from, and
leaves the one line that matters, what the seat should have sent instead, for a person to write. That line
is a judgment about the trade's conventions and the scenario, and a tool that guessed it would eventually
teach a seat something false with every appearance of evidence.

Two kinds of finding:

- Counted: a category of refusal a seat is still producing on the instructions it runs on now. Refusals
  against wording that has since been rewritten are left out, because they say what an old prompt did.
- Detected: a failure that no count would show, where the run did something the scenario says it should
  not. A blocker on a job with nothing missing, a ready job stopped at Intake, an answered question graded
  as a failure, a passing run that left the golden route. These fire on a single occurrence, because one
  invented blocker in front of a prospect costs more than three malformed fields.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import ROOT, load_settings
from app.runs.expectations import EXPECTS_NOT_READY, PLANTS_A_BLOCKER
from app.runs.metrics import METRICS_FILE, categorise, read_attempts
from app.seats.definitions import SEAT_DEFINITIONS, instructions_version

RUNS = load_settings().runs_dir
REVIEW = ROOT / "docs" / "prompt-review.md"
SEAT_FILES = ROOT / "config" / "electrical-bid" / "seats"
MIN_FOR_SUGGESTION = 3
EXAMPLES_PER_FINDING = 2

# What a counted category means for the seat, and where the lesson belongs. The text after the category is
# read by a person deciding whether to teach, so it says the shape of the failure, not the fix.
CATEGORY_NOTES: dict[str, str] = {
    "no_json": "the seat ended its turn on a progress line and never sent the JSON object",
    "invalid_json": "the seat sent JSON that could not be parsed, usually a brace or a quote",
    "wrong_shape": "the seat sent valid JSON missing a field the reply must carry",
    "tool_not_used": "the seat wrote numbers it was supposed to get from a tool",
    "figures_not_from_tool": "a figure in the reply is not the one its tool returned, or the tool call failed",
    "amount_not_in_sources": "the draft carried a dollar amount that appears in nothing the Writer was given",
    "provenance_tags": "the draft carried figures with no tag saying which output they came from",
    "concern_dropped": "a specialist's concern never reached the assumptions section",
    "checklist_grading": "the readiness grades and the verdict did not agree, or a gap was left unasked",
    "compile_failed": "the draft did not compile, so it could not become a version",
    "blocker_as_concern": "something that stops the work was carried as a concern",
    "output_limit": "the reply ran past the model's output limit, which is a setting rather than a lesson",
    "provider_error": "the provider could not be reached, which is not the seat's doing",
}
# Categories a lesson cannot fix, so the review says so rather than suggesting wording.
NOT_A_LESSON = frozenset({"output_limit", "provider_error", "route_drift"})
NOT_A_LESSON_NOTES: dict[str, str] = {
    "output_limit": "raise max_tokens for that seat, or ask it for a shorter summary",
    "provider_error": "the provider was unreachable, which no wording changes",
    "route_drift": "read the golden log first. A run that passes first time legitimately misses a golden "
    "that records a rework, and re-recording the golden is the fix. Only chase the seat when the detour "
    "is real, such as a route back to Intake nothing asked for",
}


@dataclass
class Finding:
    seat: str
    kind: str
    headline: str
    runs: list[str] = field(default_factory=list)
    examples: list[tuple[str, str]] = field(default_factory=list)
    """(what was refused, the refusal text) pairs, quoted from the recording."""
    note: str = ""
    where: str = "seat instructions"
    detected: bool = False

    @property
    def count(self) -> int:
        return len(self.runs)


def _read(path: Path) -> dict[str, Any]:
    try:
        return dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {}


def _events(folder: Path) -> list[dict[str, Any]]:
    path = folder / "events.jsonl"
    if not path.exists():
        return []
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, ValueError):
        return []


def _rejected_reply(folder: Path, prompt_ref: str, attempt: int) -> str:
    """What the seat actually sent, from the reply kept beside the recording."""
    path = folder / "rejected" / f"{prompt_ref}-{attempt}.txt"
    try:
        body = path.read_text(encoding="utf-8", errors="replace").split("\n", 1)
        return " ".join(body[1].split())[:200] if len(body) > 1 else ""
    except OSError:
        return ""


def _knowledge_topics() -> set[str]:
    """The topics the client knowledge file already answers, as bare words to match a checklist item."""
    topics: set[str] = set()
    for path in sorted(load_settings().knowledge_dir.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            if line.startswith("- q_") and ":" in line:
                topics.add(line[3:].split(":", 1)[0].strip().removeprefix("q_"))
    return topics


def folders(runs_dir: Path = RUNS) -> list[Path]:
    return sorted(p for p in runs_dir.glob("*") if p.is_dir() and not p.name.startswith("_"))


def counted(runs_dir: Path = RUNS, current: dict[str, str] | None = None) -> list[Finding]:
    """Refusal categories a seat still produces on the instructions it runs on now."""
    versions = current if current is not None else {s: instructions_version(s) for s in SEAT_DEFINITIONS}
    buckets: dict[tuple[str, str], Finding] = {}
    for folder in folders(runs_dir):
        for attempt in read_attempts(folder):
            if attempt.accepted or not attempt.error:
                continue
            seat = attempt.agent_id
            if not seat or (seat in versions and attempt.instructions != versions[seat]):
                continue
            kind = categorise(attempt.error)
            key = (seat, kind)
            finding = buckets.get(key)
            if finding is None:
                finding = Finding(
                    seat=seat,
                    kind=kind,
                    headline=CATEGORY_NOTES.get(kind, "an unrecognised refusal, worth reading in full"),
                    note="a setting or the provider, not a lesson" if kind in NOT_A_LESSON else "",
                )
                buckets[key] = finding
            finding.runs.append(folder.name[:8])
            if len(finding.examples) < EXAMPLES_PER_FINDING:
                sent = _rejected_reply(folder, attempt.prompt_ref, attempt.attempt)
                finding.examples.append((sent, " ".join(attempt.error.split())[:240]))
    return [f for f in buckets.values() if f.count >= MIN_FOR_SUGGESTION]


def detected(runs_dir: Path = RUNS, current: dict[str, str] | None = None) -> list[Finding]:
    """Failures no count would show: the run did what the scenario says it should not.

    A run whose seat was taught something since is left out, the same way counted refusals are, so a
    lesson already written does not keep asking to be written again.
    """
    versions = current if current is not None else {s: instructions_version(s) for s in SEAT_DEFINITIONS}
    found: dict[tuple[str, str], Finding] = {}

    def on_current(metrics: dict[str, Any], seat: str) -> bool:
        row = next((r for r in metrics.get("seats", []) if r.get("agent_id") == seat), None)
        if row is None:
            return False
        return bool(row.get("instructions", "") == versions.get(seat, ""))

    def add(seat: str, kind: str, headline: str, run: str, sent: str, why: str, where: str) -> None:
        finding = found.get((seat, kind))
        if finding is None:
            finding = Finding(seat=seat, kind=kind, headline=headline, where=where, detected=True)
            found[(seat, kind)] = finding
        finding.runs.append(run)
        if len(finding.examples) < EXAMPLES_PER_FINDING:
            finding.examples.append((sent, why))

    topics = _knowledge_topics()
    for folder in folders(runs_dir):
        metrics = _read(folder / METRICS_FILE)
        dataset, exit_value = metrics.get("dataset_id", ""), metrics.get("exit", "")
        if not dataset:
            continue
        events = _events(folder)
        run = folder.name[:8]

        if dataset not in PLANTS_A_BLOCKER and on_current(metrics, "estimator"):
            for event in events:
                if event["type"] != "blocker.raised":
                    continue
                payload = event.get("payload") or {}
                add(
                    str(payload.get("agent_id", "estimator")),
                    "invented_blocker",
                    f"a blocker was raised on {dataset}, which plants none, so the run stopped for a human "
                    "over something that was not missing",
                    run,
                    " ".join(str(payload.get("description", "")).split())[:200],
                    "the dataset README plants no blocker here",
                    "seat instructions",
                )

        if exit_value == "not_ready" and dataset not in EXPECTS_NOT_READY and on_current(metrics, "intake"):
            readiness = next((e for e in events if e["type"] == "intake.readiness"), None)
            failed = [
                c
                for c in ((readiness or {}).get("payload") or {}).get("checklist", [])
                if c.get("status") == "fail"
            ]
            answered = [c for c in failed if any(t and t in str(c.get("item", "")) for t in topics)]
            for item in failed:
                is_answered = item in answered
                add(
                    "intake",
                    "knowledge_answer_overridden" if is_answered else "ready_job_stopped",
                    (
                        "an item the client knowledge file already answers was graded fail, which stops a "
                        "job the human has already unblocked once"
                        if is_answered
                        else f"{dataset} was stopped at Intake, though only the Not ready dataset is meant "
                        "to stop there, so no specialist did any work"
                    ),
                    run,
                    f"{item.get('item', '')}: {' '.join(str(item.get('note', '')).split())[:140]}",
                    "the knowledge file answers this topic" if is_answered else "the run ended not_ready",
                    "seat instructions, and the precedence between the checklist and the knowledge file"
                    if is_answered
                    else "seat instructions",
                )

        if exit_value in ("reviewer_pass", "retry_exhausted") and metrics.get("golden_match") is False:
            add(
                "orchestrator",
                "route_drift",
                "the run finished but not by the route its golden log records, so a rehearsed demo would "
                "show a different path than the one it was rehearsed on",
                run,
                f"exit {exit_value} on {dataset}",
                str(metrics.get("golden_note", ""))[:200],
                "the dataset's golden log, or the seat that took the detour",
            )
    return list(found.values())


def draft(finding: Finding, number: int) -> list[str]:
    """The example block in the shape the seat files already use, with the judgment left blank."""
    if finding.kind in NOT_A_LESSON:
        return [f"No example drafted: {NOT_A_LESSON_NOTES.get(finding.kind, finding.note)}."]
    lines = [f"{number}. TITLE THE LESSON IN ONE LINE"]
    sent, why = finding.examples[0]
    lines.append(f"Sent back: {sent or 'see the run folder, the reply was not kept'}")
    lines.append(f"The reason given: {why}")
    lines.append("Send instead: TO FILL, what the seat should have sent and why it is right")
    return lines


def render(counted_findings: list[Finding], detected_findings: list[Finding]) -> str:
    body = [
        "# What the runs say to teach next",
        "",
        "Generated by `uv run python scripts/prompt_review.py --write` from every run under `runs/`. It "
        "suggests and never edits. Each finding quotes a real refusal and names the runs it came from, and "
        "leaves the line that matters, what the seat should have sent instead, for a person to write.",
        "",
        f"Counted findings need {MIN_FOR_SUGGESTION} or more refusals on the instructions that seat runs on "
        "now. Detected findings fire on one occurrence, because a run that does what the scenario says it "
        "should not costs more than a malformed field.",
        "",
    ]
    if not counted_findings and not detected_findings:
        return "\n".join([*body, "Nothing to suggest: no seat is failing on the wording it runs on now.", ""])

    order = list(SEAT_DEFINITIONS)
    everything = sorted(
        counted_findings + detected_findings,
        key=lambda f: (order.index(f.seat) if f.seat in order else 99, not f.detected, -f.count),
    )
    number = 0
    current_seat = ""
    for finding in everything:
        if finding.seat != current_seat:
            current_seat = finding.seat
            number = 0
            file_name = (
                SEAT_DEFINITIONS[finding.seat].instructions_file if finding.seat in SEAT_DEFINITIONS else ""
            )
            body += [f"## {finding.seat}", "", f"Instructions: `config/electrical-bid/seats/{file_name}`", ""]
        number += 1
        kind = "detected" if finding.detected else "counted"
        body += [
            f"### {finding.kind} ({kind}, {finding.count})",
            "",
            finding.headline + ".",
            "",
            f"Runs: {', '.join(sorted(set(finding.runs))[:8])}"
            + (" and more" if len(set(finding.runs)) > 8 else ""),
            "",
            f"Where the lesson belongs: {finding.where}.",
            "",
            "```",
            *draft(finding, number),
            "```",
            "",
        ]
        if len(finding.examples) > 1:
            sent, why = finding.examples[1]
            body += [f"A second occurrence, for wording: {why}", ""]
    return "\n".join(body)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--write", action="store_true", help="refresh docs/prompt-review.md")
    args = parser.parse_args()
    text = render(counted(), detected())
    print(text)
    if args.write:
        try:
            REVIEW.write_text(text, encoding="utf-8", newline="\n")
        except PermissionError:
            print(f"NOT written, the file is open in another program: {REVIEW.relative_to(ROOT)}")
            return 1
        print(f"written: {REVIEW.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
