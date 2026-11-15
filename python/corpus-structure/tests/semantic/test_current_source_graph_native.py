"""Current computational PDF source containment and portable selected graph custody."""

from corpus_structure.semantic.data_operation_json import json_loads
from corpus_structure.semantic.graph_inspection import GraphInspectionRequest, read_graph_inspection
from semantic.current_pdf_source_support import PROJECT
from semantic.current_pdf_source_support import current_pdf_source as current_pdf_source
from semantic.selected_graph_test_support import _offline_snapshot, _selected_snapshot


def test_actual_computational_source_hierarchy_keeps_native_pointer_custody(
    current_pdf_source, tmp_path
):
    from corpus_structure.serve.demand_export import export_demand_result

    case, kernel = current_pdf_source, current_pdf_source.kernel
    demand = case.demand_id
    request = GraphInspectionRequest(
        release_id=kernel.prepared.release_id,
        demand_id=demand,
        project_id=PROJECT,
        projection="source-hierarchy",
    )
    reader_engine = kernel.purpose("read")
    snapshot = _selected_snapshot(reader_engine.begin, kernel.prepared, request)
    assert snapshot.nodes
    assert {node.kind for node in snapshot.nodes} == {"record"}
    pointers = {json_loads(node.payload_json)["atom"]["self_ref"] for node in snapshot.nodes}
    assert all(pointer.startswith("#/") for pointer in pointers)
    assert "#/texts/0" in pointers
    assert any(
        json_loads(node.payload_json)["atom"].get("text") == "Alice was running."
        for node in snapshot.nodes
    )
    assert all(edge.relation == "contains" for edge in snapshot.occurrences)
    assert snapshot.occurrences
    inspected = read_graph_inspection(reader_engine.begin, request)
    assert inspected.standing == snapshot.standing
    assert inspected.unknowns == snapshot.unknowns
    assert inspected.examined_nodes == len(snapshot.nodes)
    assert inspected.examined_occurrences == len(snapshot.occurrences)
    with reader_engine.begin() as connection:
        destination = tmp_path / "source"
        manifest = export_demand_result(
            connection,
            demand,
            project_id=PROJECT,
            destination=destination,
            format="jsonl",
        )
    pinned = request.model_copy(
        update={"read_id": manifest["cut"]["read_id"], "expected_cut": manifest["cut_id"]}
    )
    live = _selected_snapshot(reader_engine.begin, kernel.prepared, pinned)
    assert _offline_snapshot(destination, "source-hierarchy").identity == live.identity
