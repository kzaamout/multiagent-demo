"""The seat model guide's calculation: the figure, its ranking, the picks and their reasons (spec 014)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from app.live.providers import ModelConfig
from app.runs import guide
from app.runs.guide import (
    MIN_RUNS_FOR_BEST,
    SeatRecord,
    current,
    guide_table,
    instruction_accuracy,
    metrics_of,
    pick,
    records,
    runs_called,
    unclassified,
    whole_percent,
    wilson_lower,
)
from app.seats.definitions import needs_image_input
from tests.unit.guide.support import seat_row, write_run

MODELS: dict[str, dict[str, Any]] = {
    "alpha": {"label": "alpha, local", "weights": "open", "image_input": True},
    "beta": {"label": "beta, local", "weights": "open", "image_input": True},
    "text": {"label": "text, local", "weights": "open", "image_input": False},
    "cloud": {"label": "cloud one", "weights": "proprietary", "image_input": True},
    "cloud-two": {"label": "cloud two", "weights": "proprietary", "image_input": True},
    "mystery": {"label": "mystery, local", "image_input": True},
}


def config(tmp_path: Path, seats: dict[str, str] | None = None) -> ModelConfig:
    models = {
        key: {"provider": "ollama", "model_id": f"{key}:1b", "temperature": True, **value}
        for key, value in MODELS.items()
    }
    chosen = seats or {s: "alpha" for s in guide.SEAT_ORDER}
    data = {
        "providers": {"ollama": {"label": "Ollama"}},
        "models": models,
        "seats": {seat: {"model": key} for seat, key in chosen.items()},
    }
    path = tmp_path / "models.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return ModelConfig.load(path)


def recs(*rows: tuple[str, str, int, int, int]) -> dict[tuple[str, str], SeatRecord]:
    """Records from (seat, model, runs, replies, first_time), spread over that many runs."""
    runs: list[dict[str, Any]] = []
    for seat, model, count, replies, first in rows:
        for i in range(count):
            r = replies // count + (1 if i < replies % count else 0)
            f = first // count + (1 if i < first % count else 0)
            runs.append({"seats": [seat_row(seat, model, r, f, calls=max(r, 1))]})
    return records(runs)


def test_seat_needs_image_input_where_it_reads_pages() -> None:
    assert [s for s in ("estimator", "reviewer", "single") if needs_image_input(s)] == [
        "estimator",
        "reviewer",
        "single",
    ]
    assert not any(needs_image_input(s) for s in ("orchestrator", "intake", "pricing", "writer"))


def test_the_figure_the_rounding_and_the_bound() -> None:
    assert instruction_accuracy(0, 0) is None and whole_percent(0, 0) is None and wilson_lower(0, 0) is None
    assert instruction_accuracy(1, 4) == 0.25
    assert (whole_percent(212, 226), whole_percent(29, 31), whole_percent(100, 248)) == (94, 94, 40)
    assert whole_percent(390, 397) == 98 and whole_percent(0, 12) == 0
    assert round(wilson_lower(13, 13) or 0, 3) == 0.772
    assert round(wilson_lower(390, 397) or 0, 3) == 0.964
    assert (wilson_lower(0, 10) or 0) == pytest.approx(0.0, abs=1e-12)


def test_records_sum_across_settings_and_versions_and_skip_seats_that_never_ran() -> None:
    first = seat_row("writer", "alpha, local", 3, 1)
    first["settings"], first["instructions"] = {"temperature": 0.1}, "v1"
    second = seat_row("writer", "alpha, local", 5, 4)
    second["settings"], second["instructions"] = {"temperature": 0.7}, "v2"
    idle = seat_row("pricing", "alpha, local", 0, 0, calls=0)
    runs = [{"seats": [first, idle]}, {"seats": [second]}, {"seats": [idle]}]
    table = records(runs)
    assert table == {
        ("writer", "alpha, local"): SeatRecord("writer", "alpha, local", runs=2, replies=8, first_time=5)
    }
    assert runs_called(runs) == 2, "a run in which no seat made a call adds nothing"


def test_a_long_near_perfect_record_outranks_a_short_perfect_one(tmp_path: Path) -> None:
    table = recs(("orchestrator", "beta, local", 8, 13, 13), ("orchestrator", "alpha, local", 12, 397, 390))
    chosen = pick("orchestrator", "open", table, config(tmp_path))
    assert chosen.status == "pick" and chosen.model_key == "alpha"
    assert chosen.record is not None and (chosen.record.percent, chosen.record.first_time) == (98, 390)


def test_too_few_runs_and_no_runs_are_told_apart(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    table = recs(("intake", "cloud one", MIN_RUNS_FOR_BEST - 1, 10, 10))
    assert pick("intake", "proprietary", table, cfg).status == "too_few_runs"
    assert pick("pricing", "proprietary", table, cfg).status == "no_runs"
    assert pick("intake", "open", table, cfg).as_json() == {"status": "no_runs"}


def test_ties_go_to_more_replies_then_to_the_registry_order(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    same = recs(("writer", "beta, local", 5, 10, 5), ("writer", "alpha, local", 5, 10, 5))
    assert pick("writer", "open", same, cfg).model_key == "alpha"
    # None accepted first time gives a bound of 0 whatever the count, so the bounds tie and more replies win.
    none_first = recs(("writer", "alpha, local", 5, 5, 0), ("writer", "beta, local", 5, 10, 0))
    assert pick("writer", "open", none_first, cfg).model_key == "beta"


def test_models_that_cannot_be_chosen_or_classified_are_never_picked(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    table = recs(
        ("writer", "ghost, local", 10, 100, 100),  # recorded, but no longer in the registry
        ("writer", "mystery, local", 10, 100, 100),  # in the registry, no weights
        ("writer", "alpha, local", 6, 20, 10),
    )
    assert pick("writer", "open", table, cfg).model_key == "alpha"
    assert pick("writer", "proprietary", table, cfg).status == "no_runs"
    assert unclassified(cfg) == ["mystery, local"]


def test_a_text_only_model_is_never_named_where_the_seat_reads_images(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    for seat in ("reviewer", "estimator"):
        table = recs((seat, "text, local", 6, 20, 20), (seat, "beta, local", 6, 20, 18))
        assert pick(seat, "open", table, cfg).model_key == "beta"
    table = recs(("writer", "text, local", 6, 20, 20), ("writer", "beta, local", 6, 20, 18))
    assert pick("writer", "open", table, cfg).model_key == "text"


def test_current_is_the_seat_model_whatever_its_runs_and_none_without_replies(tmp_path: Path) -> None:
    cfg = config(tmp_path, {s: ("beta" if s == "writer" else "alpha") for s in guide.SEAT_ORDER})
    table = recs(("writer", "beta, local", 1, 12, 0), ("pricing", "alpha, local", 2, 0, 0))
    now = current("writer", table, cfg)
    assert now is not None and (now.runs, now.replies, now.percent) == (1, 12, 0)
    assert current("pricing", table, cfg) is None, "calls but no replies"
    assert current("intake", table, cfg) is None, "never ran"


def test_the_table_has_every_settings_seat_and_both_kinds(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    table = recs(("estimator", "cloud one", 5, 31, 29), ("estimator", "alpha, local", 6, 20, 9))
    out = guide_table(table, 11, cfg)
    assert (out["runs"], out["min_runs"]) == (11, 5)
    assert list(out["seats"]) == ["orchestrator", "intake", "estimator", "pricing", "writer", "reviewer"]
    estimator = out["seats"]["estimator"]
    assert estimator["proprietary"] == {
        "status": "pick",
        "model_key": "cloud",
        "model": "cloud one",
        "runs": 5,
        "replies": 31,
        "first_time": 29,
        "percent": 94,
    }
    assert estimator["open"]["model"] == "alpha, local" and estimator["current"]["percent"] == 45
    assert out["seats"]["writer"] == {
        "current": None,
        "open": {"status": "no_runs"},
        "proprietary": {"status": "no_runs"},
    }


def test_an_unreadable_metrics_file_does_not_stop_the_guide(tmp_path: Path) -> None:
    folder = write_run(tmp_path, "broken", [seat_row("writer", "alpha, local", 1, 1)])
    (folder / "metrics.json").write_text("{not json", encoding="utf-8")
    assert metrics_of(folder) is None
    assert metrics_of(tmp_path / "missing") is None


def counting(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record which folders the guide reads, by wrapping `metrics_of` where SeatGuide calls it."""
    reads: list[str] = []
    real = guide.metrics_of

    def spy(folder: Path) -> dict[str, Any] | None:
        reads.append(folder.name)
        return real(folder)

    monkeypatch.setattr(guide, "metrics_of", spy)
    return reads


def test_the_guide_rereads_only_folders_that_changed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    reads = counting(monkeypatch)
    runs = tmp_path / "runs"
    for i in range(3):
        write_run(runs, f"run-{i}", [seat_row("writer", "alpha, local", 4, 2)])
    seat_guide = guide.SeatGuide(runs)
    first, count = seat_guide.refresh()
    assert sorted(reads) == ["run-0", "run-1", "run-2"] and count == 3
    assert first[("writer", "alpha, local")].replies == 12

    reads.clear()
    again, count = seat_guide.refresh()
    assert reads == [] and again is first and count == 3, "nothing changed: nothing read, nothing summed"

    write_run(runs, "run-3", [seat_row("writer", "alpha, local", 4, 4)])
    added, count = seat_guide.refresh()
    assert reads == ["run-3"] and count == 4 and added[("writer", "alpha, local")].first_time == 10

    reads.clear()
    write_run(runs, "run-0", [seat_row("writer", "alpha, local", 40, 40)])  # a rewritten metrics.json
    changed, _ = seat_guide.refresh()
    assert reads == ["run-0"] and changed[("writer", "alpha, local")].replies == 52

    reads.clear()
    shutil.rmtree(runs / "run-1")
    removed, count = seat_guide.refresh()
    assert reads == [] and count == 3 and removed[("writer", "alpha, local")].replies == 48


def test_an_unfinished_run_is_reread_as_its_log_grows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reads: list[str] = []
    canned = {"seats": [seat_row("writer", "alpha, local", 2, 1)]}

    def spy(folder: Path) -> dict[str, Any] | None:
        reads.append(folder.name)
        return canned

    monkeypatch.setattr(guide, "metrics_of", spy)
    runs = tmp_path / "runs"
    folder = write_run(runs, "going", [], finished=False)
    seat_guide = guide.SeatGuide(runs)
    seat_guide.refresh()
    seat_guide.refresh()
    assert reads == ["going"], "an unchanged log is not read twice"
    with (folder / "events.jsonl").open("a", encoding="utf-8") as log:
        log.write("{}\n")
    seat_guide.refresh()
    assert reads == ["going", "going"]


def test_the_live_run_waits_until_it_is_no_longer_excluded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reads = counting(monkeypatch)
    runs = tmp_path / "runs"
    write_run(runs, "done", [seat_row("writer", "alpha, local", 4, 2)])
    write_run(runs, "live", [seat_row("writer", "alpha, local", 6, 6)])
    seat_guide = guide.SeatGuide(runs)
    during, count = seat_guide.refresh(exclude_run="live")
    assert "live" not in reads and count == 1 and during[("writer", "alpha, local")].replies == 4
    after, count = seat_guide.refresh()
    assert count == 2 and after[("writer", "alpha, local")].replies == 10


def test_the_table_follows_a_swap_without_rereading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    reads = counting(monkeypatch)
    runs = tmp_path / "runs"
    write_run(runs, "a", [seat_row("writer", "alpha, local", 4, 2), seat_row("writer", "beta, local", 0, 0)])
    write_run(runs, "b", [seat_row("writer", "beta, local", 5, 5)])
    seat_guide = guide.SeatGuide(runs)
    on_alpha = seat_guide.table(config(tmp_path))
    reads.clear()
    on_beta = seat_guide.table(
        config(tmp_path, {s: ("beta" if s == "writer" else "alpha") for s in guide.SEAT_ORDER})
    )
    assert reads == []
    assert on_alpha["seats"]["writer"]["current"]["model"] == "alpha, local"
    assert on_beta["seats"]["writer"]["current"]["model"] == "beta, local"
