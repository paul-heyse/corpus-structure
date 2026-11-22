"""Primary navigation fields and consumers retain exact roles without rematching."""

import json

import pytest
from semantic.artifact_identity_support import reference_for

from corpus_structure.methods.witnessed_source_links import (
    match_named_source_links,
    symbol_declarations,
)
from corpus_structure.semantic.construction_products import CharacterizationSnapshot
from corpus_structure.semantic.constructions.navigation import NativeNavigationIndex
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import StructuralPassage
from methods.m1_source_preparation_support import projection, source
from methods.navigation_fixture import source_primary_products


def fixture():
    view = source(
        "Old Control was renamed to New Control.\nLet x be a count.", labels=("text", "text")
    )
    view = projection(
        view.text,
        pieces=view.pieces,
        items=tuple(dict(item, content_layer="body") for item in view.items),
    )
    primary = source_primary_products(view)
    passage = StructuralPassage(
        passage_id="selected",
        source_ref="source",
        start=0,
        end=len(view.text),
        text=view.text,
        scope="work",
    )
    return view, primary, passage


def test_navigation_retains_named_and_declaration_roles_before_consumption(monkeypatch):
    view, primary, passage = fixture()
    from corpus_structure.semantic.constructions import navigation

    monkeypatch.setattr(
        navigation,
        "_named_recipe",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("consumer reran primary matching")),
    )
    found = match_named_source_links(
        view.text,
        view.pieces,
        {item["self_ref"]: item for item in view.items},
        (passage,),
        navigation=primary.navigation,
    )
    renamed = [row for row in found.matches if row.kind == "renames"]
    assert len(renamed) == 1
    match = renamed[0]
    assert view.text[slice(*match.left)] == "Old Control"
    assert match.right is not None
    assert view.text[slice(*match.right)] == "New Control"
    assert match.witness.primary_node is not None
    assert match.witness.primary_node["product_id"] == primary.construction.semantic_id
    index = primary.navigation
    piece = [p for p in view.pieces if p["kind"] == "native_text"][1]
    (declaration,) = symbol_declarations(index, piece["item_ref"], piece["start"], piece["end"])
    assert (declaration[1], declaration[2]) == ("x", "a count")
    assert declaration.primary_node is not None


def test_navigation_refuses_missing_primary_and_dangling_retained_role():
    view, primary, passage = fixture()
    missing = match_named_source_links(
        view.text,
        view.pieces,
        {item["self_ref"]: item for item in view.items},
        (passage,),
        navigation=NativeNavigationIndex((), primary.source),
    )
    assert missing.matches == () and missing.outcome() == "unsupported"
    payload = json.loads(primary.construction.content)
    next(packet["body"] for packet in payload["members"] if "navigation" in packet["body"])[
        "navigation"
    ]["roles"][0]["occurrences"] = ["missing-source"]
    invalid = CharacterizationSnapshot(primary.construction.semantic_id, canonical_bytes(payload))
    with pytest.raises(ValueError, match="unknown declared source occurrence"):
        NativeNavigationIndex((invalid,), primary.source)


def test_artifact_fields_and_targets_are_consumed_without_source_recognition(monkeypatch):
    from corpus_structure.semantic.artifact_products import native_artifact_records
    from corpus_structure.semantic.constructions import navigation
    from methods.scoped_relations_support import original_inputs

    view = source(
        'Table 5.1 (alias: "T5")\n'
        "See Table 5.2 (hereafter Table 6.1 in numbering namespace Main).\n"
        "Table 6.1 (numbering namespace: Main) (revision: new)",
        labels=("caption", "text", "caption"),
    )
    primary = source_primary_products(view, annotations=())
    inputs = original_inputs(view)
    monkeypatch.setattr(
        navigation,
        "source_alias_fields",
        lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("consumer recognized source aliases")
        ),
    )
    monkeypatch.setattr(navigation, "_ARTIFACT", None)
    records = native_artifact_records(
        view,
        primary.source,
        inputs,
        inputs.sources[0].identity,
        "work",
        primary.navigation,
        reference_for=reference_for,
    )

    aliases = [row for row in records if row.artifact.controlled_code == "5.1"]
    assert len(aliases) == 1 and aliases[0].artifact.aliases == ("T5",)
    references = [row.explicit_reference for row in records if row.explicit_reference is not None]
    assert len(references) == 1
    assert (references[0].target_code, references[0].target_numbering) == ("6.1", "Main")
    assert references[0].primary_node is not None
    target = next(
        row
        for row in records
        if row.artifact.occurrence_role == "caption" and row.artifact.controlled_code == "6.1"
    )
    assert (target.numbering.value, target.revision.value) == ("Main", "new")
    assert all(
        row.primary_node is not None and row.primary_node["role"] == "constructions"
        for row in records
    )


def test_table_header_geometry_uses_primary_cell_roles():
    from corpus_structure.methods.scoped_relations import _measure_table_geometry
    from methods.m1_source_preparation_support import native_table_source, table_cell

    cells = [
        dict(table_cell("n=10", 0, 1), end_col_offset_idx=3),
        dict(table_cell("n=20", 0, 3), end_col_offset_idx=5),
        table_cell("Frequency", 1, 1),
        table_cell("Relative frequency", 1, 2),
        table_cell("Frequency", 1, 3),
        table_cell("Relative frequency", 1, 4),
        table_cell("Outcome", 1, 0),
        table_cell("A", 2, 0),
    ]
    view = native_table_source(cells)
    primary = source_primary_products(view, annotations=())
    index = primary.navigation
    table = next(item for item in view.items if item["label"] == "table")
    mapped = _measure_table_geometry(table, navigation=index)["data"]["table_cells"]
    assert [i for i, cell in enumerate(mapped) if cell.get("column_header")] == list(range(7))
    assert [i for i, cell in enumerate(mapped) if cell.get("row_header")] == [7]
    assert [
        (fact.payload["cell_index"], fact.payload["geometry_role"])
        for fact in index.select("table_geometry")
    ] == [
        (2, "frequency"),
        (3, "relative_frequency"),
        (4, "frequency"),
        (5, "relative_frequency"),
        (6, "row_key"),
    ]
    from corpus_structure.semantic.observations import source_python
    from methods.scoped_relations_support import discover_relations

    result = discover_relations(view, primary=primary)
    cell_values = [
        source_python(row["value"])
        for row in result["contributions"]
        if row.get("value") is not None
        and source_python(row["value"]).get("role") in {"header", "row_label", "cell"}
    ]
    assert len(cell_values) == len(cells)
    assert all(len(value["table_geometry_basis"]) == 5 for value in cell_values)
