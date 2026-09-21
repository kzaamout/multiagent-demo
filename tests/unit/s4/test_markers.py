"""Tags become lettered marker calls in document order (spec FR-004; spec 013 FR-001, FR-002, FR-005)."""

from __future__ import annotations

import pytest

from app.compile.markers import appendix, marker_label, prepare_markdown, with_appendix


@pytest.mark.parametrize(
    ("n", "label"),
    [
        (1, "a"),
        (2, "b"),
        (26, "z"),
        (27, "aa"),
        (28, "ab"),
        (52, "az"),
        (53, "ba"),
        (702, "zz"),
        (703, "aaa"),
    ],
)
def test_marker_label_counts_as_spreadsheet_columns(n: int, label: str) -> None:
    assert marker_label(n) == label


@pytest.mark.parametrize("n", [0, -1])
def test_marker_label_refuses_a_number_below_one(n: int) -> None:
    with pytest.raises(ValueError):
        marker_label(n)


def test_marker_labels_are_distinct_and_only_letters() -> None:
    labels = [marker_label(n) for n in range(1, 1001)]
    assert len(set(labels)) == 1000
    assert all(label.isascii() and label.isalpha() and label.islower() for label in labels)


def test_tag_in_table_cell_heading_and_body_become_markers() -> None:
    markdown = (
        "## Total {{36860.5|src:pricing}} CAD\n\n"
        "Labour {{139.45|src:takeoff}} hours and {{11|src:takeoff}} circuits.\n\n"
        "| Item | Amount |\n|---|---|\n| Troffer | {{6532.0|src:pricing}} |\n"
    )
    prepared, markers = prepare_markdown(markdown)
    assert [m.n for m in markers] == [1, 2, 3, 4]
    assert [m.label for m in markers] == ["a", "b", "c", "d"]
    assert [m.tag_id for m in markers] == ["t01", "t02", "t03", "t04"]
    assert [m.source_id for m in markers] == ["pricing", "takeoff", "takeoff", "pricing"]
    assert '36860.5`#prov(1, "a", "pricing")`{=typst}' in prepared
    assert '| Troffer | 6532.0`#prov(4, "d", "pricing")`{=typst} |' in prepared
    assert "{{" not in prepared


def test_two_tags_on_one_line_are_two_markers() -> None:
    prepared, markers = prepare_markdown("{{1|src:a}} and {{2|src:b}}")
    assert len(markers) == 2 and prepared.count("#prov(") == 2


def test_markers_past_z_carry_two_letters() -> None:
    prepared, markers = prepare_markdown(" ".join(f"{{{{{n}|src:pricing}}}}" for n in range(1, 31)))
    assert [m.label for m in markers[25:]] == ["z", "aa", "ab", "ac", "ad"]
    assert '#prov(27, "aa", "pricing")' in prepared


def test_appendix_lists_every_marker_and_names_unresolved_sources() -> None:
    _, markers = prepare_markdown("{{1|src:takeoff}} {{2|src:ghost}}")
    table = appendix(markers, {"takeoff": "Takeoff complete"})
    assert "| a | takeoff | Takeoff complete |" in table
    assert "| b | ghost | unresolved |" in table


def test_with_appendix_extends_the_provenance_section_or_adds_it() -> None:
    _, markers = prepare_markdown("{{1|src:takeoff}}")
    extended = with_appendix("Body\n\n## Provenance\n\n- Estimator (source id: takeoff)\n", markers, {})
    assert extended.count("## Provenance") == 1 and "| a | takeoff |" in extended
    added = with_appendix("Body only\n", markers, {})
    assert "## Provenance" in added and "| a | takeoff |" in added
