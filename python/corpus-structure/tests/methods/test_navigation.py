"""Primary navigation fields and consumers retain exact roles without rematching."""

from copy import deepcopy
from dataclasses import replace

import pytest

from corpus_structure.methods.witnessed_source_links import (
    match_named_source_links,
    navigation_index,
    symbol_declarations,
)
from corpus_structure.semantic.characterization import LayerReport
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import StructuralPassage
from methods.m1_source_preparation_support import source
from methods.navigation_fixture import primary_navigation
from methods.scoped_relations_support import complete_native_fields


def fixture():
    view = complete_native_fields(
        source(
            "Old Control was renamed to New Control.\nLet x be a count.", labels=("text", "text")
        )
    )
    view = replace(view, items=tuple(dict(item, content_layer="body") for item in view.items))
    layers = primary_navigation(view)
    passage = StructuralPassage(
        passage_id="selected",
        source_ref="source",
        start=0,
        end=len(view.text),
        text=view.text,
        scope="work",
    )
    return view, layers, passage


def test_navigation_retains_named_and_declaration_roles_before_consumption(monkeypatch):
    view, layers, passage = fixture()
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
        primary_layers=layers,
        projection=view.ref.projection_digest,
    )
    renamed = [row for row in found.matches if row.kind == "renames"]
    assert len(renamed) == 1
    match = renamed[0]
    assert view.text[slice(*match.left)] == "Old Control"
    assert view.text[slice(*match.right)] == "New Control"
    assert match.witness.primary_node is not None
    assert match.witness.primary_node["layer"] in [pin.values() for pin in layers]
    index = navigation_index(layers, view.ref.projection_digest)
    piece = [p for p in view.pieces if p["kind"] == "native_text"][1]
    (declaration,) = symbol_declarations(index, piece["item_ref"], piece["start"], piece["end"])
    assert (declaration[1], declaration[2]) == ("x", "a count")
    assert declaration.primary_node is not None


def test_navigation_refuses_missing_primary_and_dangling_retained_role():
    view, layers, passage = fixture()
    missing = match_named_source_links(
        view.text,
        view.pieces,
        {item["self_ref"]: item for item in view.items},
        (passage,),
        primary_layers={},
        projection=view.ref.projection_digest,
    )
    assert missing.matches == () and missing.outcome() == "unsupported"
    pin, layer = next(
        (pin, layer)
        for pin, layer in layers.items()
        if any("navigation" in a for a in layer.payload["annotations"])
    )
    payload = deepcopy(layer.payload)
    next(a for a in payload["annotations"] if "navigation" in a)["navigation"]["roles"][0][
        "occurrences"
    ] = ["missing-source"]
    invalid = LayerReport(canonical_bytes(payload))
    mutated = dict(layers)
    del mutated[pin]
    mutated[invalid.reference(pin.task_id)] = invalid
    with pytest.raises(ValueError, match="unknown source occurrence"):
        navigation_index(mutated, view.ref.projection_digest)


def test_artifact_fields_and_targets_are_consumed_without_source_recognition(monkeypatch):
    from corpus_structure.methods.artifact_identity import discover_identity_records
    from corpus_structure.semantic.constructions import navigation
    from corpus_structure.semantic.proposals import native_source_frame
    from methods.scoped_relations_support import original_inputs

    view = complete_native_fields(
        source(
            'Table 5.1 (alias: "T5")\n'
            "See Table 5.2 (hereafter Table 6.1 in numbering namespace Main).\n"
            "Table 6.1 (numbering namespace: Main) (revision: new)",
            labels=("caption", "text", "caption"),
        )
    )
    layers = primary_navigation(view, annotations=(), formal=True)
    inputs = original_inputs(view)
    monkeypatch.setattr(
        navigation,
        "source_alias_fields",
        lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("consumer recognized source aliases")
        ),
    )
    monkeypatch.setattr(navigation, "_ARTIFACT", None)
    records = discover_identity_records(
        native_source_frame(view, ()),
        inputs,
        inputs.sources[0].identity,
        "work",
        primary_layers=layers,
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
        row.primary_node == row.artifact.primary_node and row.primary_node is not None
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
    primary = primary_navigation(view, annotations=())
    index = navigation_index(primary, view.ref.projection_digest)
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
    from types import SimpleNamespace

    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.methods.scoped_relations import (
        ScopedRelationsConfig,
        ScopedRelationsMethod,
    )
    from corpus_structure.semantic.observations import source_python

    class Reader:
        def source_view(self, _):
            return view

        def primary_characterization(self, _, *, families):
            # This table has no linguistic token population; navigation is independently retained.
            return {}

        def characterization_layers(self, pins):
            assert set(pins) == set(primary)
            return primary

    cfg = ScopedRelationsConfig(characterization_layers=tuple(pin.values() for pin in primary))
    unit = SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, view.ref.id, view.ref.key))
    (result,) = ScopedRelationsMethod().run(
        (unit,), cfg, SimpleNamespace(reader=Reader(), check_active=lambda: None)
    )
    assert result.contributions is not None
    cell_values = [
        source_python(row["value"])
        for row in result.contributions
        if row.get("value") is not None
        and source_python(row["value"]).get("role") in {"header", "row_label", "cell"}
    ]
    assert len(cell_values) == len(cells)
    assert all(len(value["table_geometry_basis"]) == 5 for value in cell_values)
