"""The header dot's policy, case by case (spec 012 research D8, FR-014 to FR-019)."""

from __future__ import annotations

from typing import Any

import pytest

from app.live.providers import ModelConfig, ModelSpec, SeatChoice
from app.preflight.header import header_state
from app.preflight.result import FAIL, PASS, PENDING, SKIP, WARN, CheckResult, PreflightResult

AT = "2026-09-21T09:12:00"
PROVIDERS: dict[str, dict[str, Any]] = {
    "bedrock": {"label": "Amazon Bedrock"},
    "google": {"label": "Google Gemini", "env_key": "GEMINI_API_KEY"},
    "ollama": {"label": "Ollama", "host": "http://localhost:11434"},
}


def spec(key: str, provider: str, model_id: str, label: str) -> ModelSpec:
    return ModelSpec(key, provider, model_id, label, True, True, 0, 0)


MODELS = {
    "sonnet": spec("sonnet", "bedrock", "us.anthropic.claude-sonnet-5", "claude-sonnet-5 via Bedrock"),
    "gemini": spec("gemini", "google", "gemini/gemini-3.8-flash", "gemini-3.8-flash via Google"),
    "old-gemini": spec("old-gemini", "google", "gemini/gemini-2.5-pro", "gemini-2.5-pro via Google"),
    "qwen": spec("qwen", "ollama", "qwen3.5:9b", "qwen3.5 9b, local"),
    "gemma": spec("gemma", "ollama", "gemma4:12b", "gemma4 12b, local"),
}
# Writer on qwen and Reviewer on gemma: different families.
SEATS = {"estimator": "sonnet", "writer": "qwen", "reviewer": "gemma", "pricing": "qwen"}


def config(**seats: str) -> ModelConfig:
    chosen = {**SEATS, **seats}
    return ModelConfig(PROVIDERS, MODELS, {s: SeatChoice(model=m) for s, m in chosen.items()})


def model_row(key: str, status: str = PASS) -> CheckResult:
    subject = {"kind": "model", "model_key": key, "provider": MODELS[key].provider}
    detail = "answered in 5 ms" if status == PASS else f"{key} did not answer (NotFoundError)"
    return CheckResult(f"model:{key}", f"{MODELS[key].label} answers", status, detail, 5, AT, subject)


def row(check_id: str, status: str = PASS, detail: str = "fine") -> CheckResult:
    return CheckResult(check_id, check_id.capitalize(), status, detail, 1, AT)


def env_row(
    login_missing: list[str] | None = None, keys_missing: dict[str, str] | None = None
) -> CheckResult:
    subject = {"kind": "env", "login_missing": login_missing or [], "keys_missing": keys_missing or {}}
    return CheckResult("env", ".env completeness", PASS, "stored", 1, AT, subject)


def result(*changes: CheckResult, drop: tuple[str, ...] = ()) -> PreflightResult:
    rows = {
        r.id: r
        for r in [
            *(model_row(k) for k in MODELS),
            *(row(i) for i in ("ollama", "typst", "png", "tunnel", "disk", "intro-recording", "replays")),
            env_row(),
        ]
    }
    for change in changes:
        rows[change.id] = change
    return PreflightResult("laptop", AT, tuple(r for i, r in rows.items() if i not in drop))


def test_everything_passing_is_green() -> None:
    state = header_state(result(), config(), "laptop")
    assert (state.status, state.glyph, state.title) == (
        PASS,
        "✓",
        "Pre-flight: all checks pass, 21 Sep 2026, 09:12",
    )


def test_an_unused_model_failing_leaves_the_dot_green_and_counts_it() -> None:
    state = header_state(result(model_row("old-gemini", FAIL)), config(), "laptop")
    assert state.status == PASS
    assert (
        state.title == "Pre-flight: checks for the current seats pass, 1 other row failed, 21 Sep 2026, 09:12"
    )


def test_a_seat_model_failing_is_red_and_names_the_model_and_seat() -> None:
    state = header_state(result(model_row("old-gemini", FAIL)), config(reviewer="old-gemini"), "laptop")
    assert (state.status, state.glyph) == (FAIL, "✕")
    assert (
        state.title
        == "Pre-flight: gemini-2.5-pro via Google failed for the Reviewer seat, 21 Sep 2026, 09:12"
    )


def test_the_same_rows_read_against_different_seats() -> None:
    stored = result(model_row("gemini", FAIL))
    assert header_state(stored, config(), "laptop").status == PASS
    assert header_state(stored, config(estimator="gemini"), "laptop").status == FAIL


def test_the_login_pair_counts_only_in_cloud_mode() -> None:
    stored = result(env_row(login_missing=["DEMO_USERNAME", "DEMO_PASSWORD"]))
    assert header_state(stored, config(), "laptop").status == PASS
    cloud = config(writer="sonnet", reviewer="gemini", pricing="sonnet")
    state = header_state(stored, cloud, "cloud")
    assert (state.status, state.title) == (
        FAIL,
        "Pre-flight: the login pair is missing in Cloud mode, 21 Sep 2026, 09:12",
    )


def test_a_missing_key_for_a_seat_provider_is_red_by_name_only() -> None:
    stored = result(env_row(keys_missing={"google": "GEMINI_API_KEY"}))
    assert header_state(stored, config(), "laptop").status == PASS
    state = header_state(stored, config(estimator="gemini"), "laptop")
    assert (state.status, state.title) == (
        FAIL,
        "Pre-flight: GEMINI_API_KEY missing for a seat's provider, 21 Sep 2026, 09:12",
    )


@pytest.mark.parametrize("check_id", ["typst", "png", "disk"])
def test_compile_png_and_disk_are_red_whatever_the_seats(check_id: str) -> None:
    state = header_state(result(row(check_id, FAIL)), config(), "laptop")
    assert state.status == FAIL
    assert state.title == f"Pre-flight: {check_id.capitalize()} failed, 21 Sep 2026, 09:12"


def test_ollama_is_red_only_with_a_local_seat_in_laptop_mode() -> None:
    stored = result(row("ollama", FAIL, "Ollama not reachable at localhost:11434"))
    state = header_state(stored, config(), "laptop")
    assert state.status == FAIL and "Ollama not reachable for the" in state.title
    cloud_only = config(writer="sonnet", reviewer="gemini", pricing="sonnet")
    assert header_state(stored, cloud_only, "laptop").status == PASS


def test_a_local_seat_in_cloud_mode_is_red() -> None:
    stored = result(row("ollama", SKIP))
    state = header_state(stored, config(writer="sonnet", reviewer="gemini"), "cloud")
    assert state.status == FAIL
    assert state.title.startswith("Pre-flight: the Pricing seat on local models in Cloud mode")


@pytest.mark.parametrize(
    ("change", "seats", "title"),
    [
        (row("tunnel", FAIL, "Tunnel not connected"), {}, "Pre-flight: Tunnel not connected"),
        (row("intro-recording", FAIL), {}, "Pre-flight: the Introduction recording is not on this machine"),
        (
            row("replays", FAIL, "No recording or golden log for prospect-a"),
            {},
            "Pre-flight: No recording or golden log for prospect-a",
        ),
        (None, {"reviewer": "qwen"}, "Pre-flight: the Reviewer shares the Writer's model family"),
    ],
)
def test_each_amber_condition_alone_is_amber_never_red(
    change: CheckResult | None, seats: dict[str, str], title: str
) -> None:
    stored = result(change) if change else result()
    state = header_state(stored, config(**seats), "laptop")
    assert (state.status, state.glyph) == (WARN, "!")
    assert state.title.startswith(title)


def test_red_wins_over_amber() -> None:
    stored = result(row("tunnel", FAIL, "Tunnel not connected"), row("disk", FAIL))
    assert header_state(stored, config(), "laptop").status == FAIL


def test_no_result_is_grey_and_a_seat_model_without_a_row_is_grey() -> None:
    assert (header_state(None, config(), "laptop").status, header_state(None, config(), "laptop").title) == (
        PENDING,
        "Pre-flight: not run yet",
    )
    state = header_state(result(drop=("model:sonnet",)), config(), "laptop")
    assert state.status == PENDING
    assert state.title == "Pre-flight: claude-sonnet-5 via Bedrock (Estimator seat) not checked yet"
    # A red condition still wins over an unchecked seat model.
    assert header_state(result(row("disk", FAIL), drop=("model:sonnet",)), config(), "laptop").status == FAIL
