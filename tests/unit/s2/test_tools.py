from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.orchestrator.knowledge_store import EMPTY_MARKER, KnowledgeStore
from app.schema.events import KnowledgeEntry
from app.tools.price_list import LookupRequest, PriceList, totals
from app.tools.quantity import QuantityItem, calculate
from app.tools.template import commit_draft, find_tags, render, strip_tags

D = Decimal


def test_quantity_waste_rounding_and_hours() -> None:
    result = calculate(
        [
            QuantityItem(
                "Duplex receptacle", "each", "device", (D(20), D(21)), "Branch circuits and devices", D("0.5")
            ),
            QuantityItem("#12 THHN", "metre", "wire", (D("1000"),), "Branch circuits and devices", D("0.02")),
            QuantityItem(
                "Panelboard 225A", "each", "equipment", (D(1),), "Service and distribution", D("8.0")
            ),
        ]
    )
    receptacle, wire, panel = result.lines
    assert receptacle.base_quantity == 41 and receptacle.quantity_with_waste == 42  # 41.82 rounded up
    assert wire.quantity_with_waste == D("1050.0")
    assert panel.quantity_with_waste == 1
    assert result.hours_by_group == {
        "Branch circuits and devices": D("40.50"),
        "Service and distribution": D("8.00"),
    }
    assert result.total_hours == D("48.50")


def test_quantity_refuses_negative_counts() -> None:
    with pytest.raises(ValueError):
        calculate([QuantityItem("x", "each", "device", (D(-1),))])


@pytest.fixture
def fixture_csv(tmp_path: Path) -> Path:
    path = tmp_path / "supplier-prices.csv"
    path.write_text(
        "item_code,description,unit,price,supplier,lead_time_days\n"
        "PNL-225,Panelboard 225A 42 circuit,each,2450.00,Supplier A,42\n"
        "PNL-225,Panelboard 225A 42 circuit,each,2390.00,Supplier C,10\n"
        "WIRE-12,Copper conductor #12 THHN,metre,1.15,Supplier B,3\n"
        "EXIT-LED,Exit sign LED,each,89.50,Supplier C,7\n",
        encoding="utf-8",
    )
    return path


def test_price_lookup_is_strict_and_prefers_supplier_order(fixture_csv: Path) -> None:
    prices = PriceList.from_csv(fixture_csv)
    lines = prices.lookup(
        [
            LookupRequest("L1", "Panelboard 225A 42 circuit", D(1), "each", "PNL-225"),
            LookupRequest("L2", "copper conductor  #12 thhn", D("1050"), "metre"),
            LookupRequest("L3", "Exit sign, LED", D(6), "each"),
            LookupRequest("L4", "Copper conductor #12 THHN", D("100"), "foot"),
        ],
        supplier_order=["Supplier A", "Supplier B", "Supplier C"],
        long_lead_days=28,
    )
    panel, wire, exit_sign, wrong_unit = lines
    assert panel.supplier == "Supplier A" and panel.extended == D("2450.00") and panel.long_lead
    assert wire.status == "priced" and wire.extended == D("1207.50") and not wire.long_lead
    assert exit_sign.status == "unpriced" and exit_sign.extended is None, "no near matches"
    assert wrong_unit.status == "unit_mismatch" and wrong_unit.extended is None


def test_totals_exclude_unpriced_and_round_to_cents(fixture_csv: Path) -> None:
    prices = PriceList.from_csv(fixture_csv)
    lines = prices.lookup(
        [LookupRequest("L1", "x", D(1), "each", "PNL-225"), LookupRequest("L2", "missing", D(3), "each")],
        supplier_order=["Supplier A"],
        long_lead_days=28,
    )
    t = totals(lines, markup_rate=D("0.15"), labour_hours=D("48.5"), labour_rate=D("95"))
    assert (t.material, t.markup, t.labour, t.total) == (
        D("2450.00"),
        D("367.50"),
        D("4607.50"),
        D("7425.00"),
    )


def test_price_fixture_requires_columns(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("code,price\nA,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        PriceList.from_csv(bad)


def test_template_render_tags_gaps_and_appendix(tmp_path: Path) -> None:
    rendered = render(
        {
            "executive_summary": "Main service {{225 A|src:evt-est}} at {{$7,425.00|src:evt-price}}.",
            "scope": "Distribution and lighting.",
            "pricing_summary": "Total {{$7,425.00|src:evt-price}}.",
            "assumptions": "Bid valid {{60 days|src:evt-brief}}.",
        },
        prospect_name="Fictional Prospect Ltd.",
        project="Northgate Library",
    )
    assert rendered.gaps == ("exclusions",)
    assert [t.source_id for t in rendered.tags] == ["evt-est", "evt-price", "evt-price", "evt-brief"]
    assert "| t01 | 225 A | evt-est |" in rendered.markdown
    assert "# Proposal for Fictional Prospect Ltd." in rendered.markdown
    assert strip_tags("Service {{225 A|src:evt-est}}.") == "Service 225 A."
    assert find_tags("no tags") == []
    with pytest.raises(ValueError):
        render({"cover_letter": "x"}, prospect_name="p", project="q")
    assert commit_draft(tmp_path, 2, rendered.markdown) == "drafts/draft-v2.md"
    assert (tmp_path / "drafts" / "draft-v2.md").read_text(encoding="utf-8") == rendered.markdown


def test_knowledge_store_seeds_once_and_appends_answers(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge")
    path = store.ensure("northgate-library", None)
    seeded = path.read_text(encoding="utf-8")
    assert EMPTY_MARKER in seeded and "Default markup on material: 15 percent" in seeded
    entry = KnowledgeEntry(question_id="q_bid_bond", answer="No bid bond", source_event_id="e1")
    store.append("northgate-library", [entry], run_id="r1", when="2026-09-14T09:13:04.000Z")
    text = store.read("northgate-library")
    assert EMPTY_MARKER not in text
    assert "- q_bid_bond: No bid bond (run r1, 2026-09-14T09:13:04.000Z)" in text
    assert text.index("Default markup") < text.index("q_bid_bond"), "standing facts untouched"
    store.append(
        "northgate-library",
        [KnowledgeEntry(question_id="q_site_visit", answer="None", source_event_id="e2")],
        run_id="r2",
        when="t",
    )
    assert store.answered_question_ids("northgate-library") == {"q_bid_bond", "q_site_visit"}
    store.ensure("northgate-library", None)
    assert "q_site_visit" in store.read("northgate-library"), "ensure never reseeds"
    with pytest.raises(ValueError):
        store.path_for("../escape")


def test_provenance_check_names_every_problem() -> None:
    from app.tools.template import provenance_problems

    context = "## Estimator output (source id: est-1)\n## Pricing output (source id: price-1)"
    assert (
        provenance_problems("We bid {{$6,362.94|src:price-1}} for {{25 troffers|src:est-1}}.", context) == []
    )
    problems = provenance_problems(
        "We bid $6,362.94 for {{25 troffers|src:made-up}}.\n## Provenance\n$1", context
    )
    assert any("made-up" in p for p in problems)
    assert not any("$6,362.94" in p for p in problems), (
        "an untagged amount is no longer refused here: it is held against what the Writer was given, in "
        "app.live.figures.amounts_not_in_context"
    )
    assert not any("$1" in p.split(": ", 1)[-1].split(", ") for p in problems), "the appendix is not checked"
    untagged = provenance_problems("No figures at all.", context)[0]
    assert untagged.startswith("the draft body has no usable provenance tags")
    assert "appendix do not count" in untagged, "the seat is told where the tags belong"
    assert "est-1, price-1" in untagged, "the seat is told which source ids it may cite"
    assert "<" not in untagged, "no placeholder for a seat to copy literally"
