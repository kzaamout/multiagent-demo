"""The pre-flight dot in every header, worked out on each read (spec 012 research D8 and D9).

The stored rows are facts. Whether a failed row turns the dot red, amber, or not at all depends on
the seats in force and the run mode when the page loads, so it is decided here and never stored:

- red: a model a seat is on; Ollama while a seat is local in Laptop mode; a seat still on a local
  model in Cloud mode; a key for a seat's provider; Typst; page PNG export; disk space; the login
  pair in Cloud mode only.
- amber: the tunnel; the Reviewer and the Writer on one model family; the Introduction recording;
  a dataset with nothing to replay.
- grey: nothing checked yet, or a seat's model has no row.
- green: otherwise, with a count of the failed rows that do not touch the current seats.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace

from app.live.providers import ModelConfig, family_of
from app.preflight.checks import env_verdict
from app.preflight.result import (
    FAIL,
    GLYPHS,
    PASS,
    PENDING,
    SKIP,
    WARN,
    CheckResult,
    PreflightResult,
    format_stamp,
    now_iso,
)

RED_FIXED = ("typst", "png", "disk")
AMBER = ("tunnel", "family", "intro-recording", "replays")
FAMILY_ID = "family"
FAMILY_NAME = "Reviewer and Writer on different model families"


@dataclass(frozen=True)
class HeaderState:
    status: str
    glyph: str
    title: str


def seat_label(seat: str) -> str:
    return seat[:1].upper() + seat[1:]


def seats_on_model(config: ModelConfig) -> dict[str, list[str]]:
    """Model key to the seats on it now."""
    found: dict[str, list[str]] = {}
    for seat, choice in config.seats.items():
        found.setdefault(choice.model, []).append(seat)
    return found


def _seat_phrase(seats: list[str]) -> str:
    names = [seat_label(s) for s in seats]
    return f"the {' and '.join(names)} seat{'s' if len(names) > 1 else ''}"


def family_row(config: ModelConfig) -> CheckResult:
    """Worked out from the seats in force, never stored (research D9)."""
    if "reviewer" not in config.seats or "writer" not in config.seats:
        return CheckResult(FAMILY_ID, FAMILY_NAME, SKIP, "No Reviewer or Writer seat", 0, now_iso())
    reviewer = family_of(config.seat_spec("reviewer"))
    writer = family_of(config.seat_spec("writer"))
    if reviewer == writer:
        detail = f"The Reviewer shares the Writer's model family ({reviewer}); the review is weaker for it"
        return CheckResult(FAMILY_ID, FAMILY_NAME, FAIL, detail, 0, now_iso())
    return CheckResult(
        FAMILY_ID, FAMILY_NAME, PASS, f"Reviewer on {reviewer}, Writer on {writer}", 0, now_iso()
    )


def env_on_read(row: CheckResult, config: ModelConfig) -> CheckResult:
    """The env row's status and detail for the seats in force (data model, "The env row on read")."""
    if row.subject.get("kind") != "env":
        return row
    seat_providers = {config.seat_spec(s).provider for s in config.seats}
    status, detail = env_verdict(row.subject, seat_providers)
    return replace(row, status=status, detail=detail)


def rows_on_read(result: PreflightResult | None, config: ModelConfig) -> list[CheckResult]:
    """The stored rows with the env row worked out for the current seats, then the family row."""
    stored = [env_on_read(r, config) for r in result.checks] if result is not None else []
    return [*stored, family_row(config)]


def _newest(rows: list[CheckResult], fallback: str | None) -> str:
    stamps = [r.checked_at for r in rows if r.checked_at]
    if not stamps:
        return format_stamp(fallback) if fallback else ""
    return format_stamp(max(stamps, key=lambda s: dt.datetime.fromisoformat(s).timestamp()))


def _with_stamp(text: str, stamp: str) -> str:
    return f"{text}, {stamp}" if stamp else text


def header_state(result: PreflightResult | None, config: ModelConfig, run_mode: str) -> HeaderState:
    rows = rows_on_read(result, config)
    ran_at = result.ran_at if result is not None else None
    on_model = seats_on_model(config)
    local_seats = [s for s in config.seats if config.seat_spec(s).provider == "ollama"]
    red: list[tuple[str, list[CheckResult]]] = []
    amber: list[tuple[str, list[CheckResult]]] = []
    other = 0

    if run_mode == "cloud" and local_seats:
        red.append((f"Pre-flight: {_seat_phrase(local_seats)} on local models in Cloud mode", []))
    for row in rows:
        if row.status != FAIL:
            continue
        kind = row.subject.get("kind")
        if kind == "model":
            key = str(row.subject.get("model_key", ""))
            seats = on_model.get(key, [])
            if seats and key in config.models:
                red.append(
                    (f"Pre-flight: {config.models[key].label} failed for {_seat_phrase(seats)}", [row])
                )
            else:
                other += 1
        elif row.id == "ollama":
            if run_mode != "cloud" and local_seats:
                red.append((f"Pre-flight: Ollama not reachable for {_seat_phrase(local_seats)}", [row]))
            elif run_mode != "cloud":
                other += 1
        elif row.id in RED_FIXED:
            red.append((f"Pre-flight: {row.name} failed", [row]))
        elif kind == "env":
            login = list(row.subject.get("login_missing", []))
            seat_providers = {config.seat_spec(s).provider for s in config.seats}
            keys = row.subject.get("keys_missing", {})
            seat_keys = [keys[p] for p in sorted(keys) if p in seat_providers]
            if seat_keys:
                red.append((f"Pre-flight: {', '.join(seat_keys)} missing for a seat's provider", [row]))
            elif login and run_mode == "cloud":
                red.append(("Pre-flight: the login pair is missing in Cloud mode", [row]))
            else:
                other += 1
        elif row.id in AMBER:
            amber.append((f"Pre-flight: {_amber_text(row)}", [row]))
        else:
            other += 1

    if red:
        text, deciding = red[0]
        return HeaderState(FAIL, GLYPHS[FAIL], _with_stamp(text, _newest(deciding, ran_at)))
    if amber:
        text, deciding = amber[0]
        return HeaderState(WARN, GLYPHS[WARN], _with_stamp(text, _newest(deciding, ran_at)))
    if result is None:
        return HeaderState(PENDING, GLYPHS[PENDING], "Pre-flight: not run yet")
    checked = {r.id for r in rows}
    for seat, choice in config.seats.items():
        if f"model:{choice.model}" not in checked and choice.model in config.models:
            label = config.models[choice.model].label
            return HeaderState(
                PENDING, GLYPHS[PENDING], f"Pre-flight: {label} ({seat_label(seat)} seat) not checked yet"
            )
    stamp = _newest([r for r in rows if r.id != FAMILY_ID], ran_at)
    if other:
        noun = "row" if other == 1 else "rows"
        text = f"Pre-flight: checks for the current seats pass, {other} other {noun} failed"
    else:
        text = "Pre-flight: all checks pass"
    return HeaderState(PASS, GLYPHS[PASS], _with_stamp(text, stamp))


def _amber_text(row: CheckResult) -> str:
    if row.id == FAMILY_ID:
        return "the Reviewer shares the Writer's model family"
    if row.id == "intro-recording":
        return "the Introduction recording is not on this machine"
    return row.detail
