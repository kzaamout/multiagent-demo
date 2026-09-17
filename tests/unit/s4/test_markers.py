"""Tags become numbered marker calls in document order (spec FR-004)."""

from __future__ import annotations

from app.compile.markers import appendix, prepare_markdown, with_appendix


def test_tag_in_table_cell_heading_and_body_become_markers() -> None:
    markdown = (
        "## Total {{36860.5|src:pricing}} CAD\n\n"
        "Labour {{139.45|src:takeoff}} hours and {{11|src:takeoff}} circuits.\n\n"
        "| Item | Amount |\n|---|---|\n| Troffer | {{6532.0|src:pricing}} |\n"
    )
    prepared, markers = prepare_markdown(markdown)
    assert [m.n for m in markers] == [1, 2, 3, 4]
    assert [m.tag_id for m in markers] == ["t01", "t02", "t03", "t04"]
    assert [m.source_id for m in markers] == ["pricing", "takeoff", "takeoff", "pricing"]
    assert '36860.5`#prov(1, "pricing")`{=typst}' in prepared
    assert '| Troffer | 6532.0`#prov(4, "pricing")`{=typst} |' in prepared
    assert "{{" not in prepared


def test_two_tags_on_one_line_are_two_markers() -> None:
    prepared, markers = prepare_markdown("{{1|src:a}} and {{2|src:b}}")
    assert len(markers) == 2 and prepared.count("#prov(") == 2


def test_appendix_lists_every_marker_and_names_unresolved_sources() -> None:
    _, markers = prepare_markdown("{{1|src:takeoff}} {{2|src:ghost}}")
    table = appendix(markers, {"takeoff": "Takeoff complete"})
    assert "| 1 | takeoff | Takeoff complete |" in table
    assert "| 2 | ghost | unresolved |" in table


def test_with_appendix_extends_the_provenance_section_or_adds_it() -> None:
    _, markers = prepare_markdown("{{1|src:takeoff}}")
    extended = with_appendix("Body\n\n## Provenance\n\n- Estimator (source id: takeoff)\n", markers, {})
    assert extended.count("## Provenance") == 1 and "| 1 | takeoff |" in extended
    added = with_appendix("Body only\n", markers, {})
    assert "## Provenance" in added and "| 1 | takeoff |" in added
