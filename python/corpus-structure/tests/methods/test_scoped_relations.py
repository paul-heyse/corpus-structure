"""Physical participant roles and native joins remain separate from semantic support."""

from dataclasses import replace

from corpus_structure.methods.scoped_relations import discover_relations
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.proposals import native_source_frame

from .test_m1_source_preparation import native_table_source, source, table_cell


def complete_native_fields(view):
    nodes = {node["self_ref"]: dict(node) for node in view.items}
    for piece in view.pieces:
        if piece.get("kind") == "native_text" and piece.get("cell_index") is None:
            nodes[piece["item_ref"]]["text"] = view.text[piece["start"] : piece["end"]]
    return replace(view, items=tuple(nodes.values()))


def test_native_table_roles_notes_and_units_keep_exact_cell_participants():
    view = native_table_source(
        (
            table_cell("Probability %", 0, 1, column_header=True),
            table_cell("Heads", 1, 0, row_header=True),
            table_cell("50", 1, 1),
            table_cell("50", 2, 1),
        ),
        caption="Table 5.1 Coin",
        note="Values are percentages.",
    )
    output = discover_relations(
        native_source_frame(complete_native_fields(view), ()), source_work="actual-parent-sha"
    )
    rows = output["contributions"]
    values = {r["contribution_id"]: source_python(r["value"]) for r in rows}
    cells = [r for r in rows if values[r["contribution_id"]].get("text") == "50"]
    assert len(cells) == 2 and cells[0]["occurrence_id"] != cells[1]["occurrence_id"]
    relations = [r for r in rows if r["kind"] == "relation"]
    assert {values[r["contribution_id"]]["relation"] for r in relations} >= {
        "header",
        "row_label",
        "unit",
        "note",
        "value_role",
    }
    assert all(
        r["standing"] == "retained_private" and r["component"]["interpretation"] == "unassessed"
        for r in relations
    )
    assert all(len(r["members"]) == 2 for r in relations)
    artifact = [
        values[r["contribution_id"]] for r in rows if r["semantic_type"] == "structural.artifact"
    ]
    assert artifact[0]["controlled_code"] == "5.1" and artifact[0]["title"] == "Coin"


def test_symbol_occurrences_and_source_order_cues_do_not_merge_repeated_symbols():
    view = source(
        "Let x be a value. Let x be another value. prepare sample before calculate mean.",
        labels=("text",),
    )
    output = discover_relations(native_source_frame(complete_native_fields(view), ()))
    rows = output["contributions"]
    values = {r["contribution_id"]: source_python(r["value"]) for r in rows}
    symbols = [r for r in rows if values[r["contribution_id"]].get("role") == "symbol"]
    assert len(symbols) == 2 and symbols[0]["occurrence_id"] != symbols[1]["occurrence_id"]
    relations = [values[r["contribution_id"]]["relation"] for r in rows if r["kind"] == "relation"]
    assert relations.count("declares") == 2 and relations.count("order") == 1


def test_source_without_authenticated_parent_binding_retains_no_artifact_identity():
    view = source("See Table 5.1.", labels=("text",))
    output = discover_relations(native_source_frame(complete_native_fields(view), ()))
    assert not any(r["semantic_type"] == "structural.artifact" for r in output["contributions"])
