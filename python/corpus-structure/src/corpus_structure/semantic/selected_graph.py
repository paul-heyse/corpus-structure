"""Selected native record incidence, acquired through the protected read owner."""

from hashlib import sha256

from .data_operation_json import json_bytes
from .graph_inspection import GraphNode, GraphOccurrence, GraphSnapshot

# Foreign references are interpreted by the released native record schema, not
# inferred by recursively scanning arbitrary JSON strings.
_REFERENCES = {
    "request_id": "ops.data_request",
    "derivation_id": "ops.data_derivation",
    "support_derivation_id": "ops.data_derivation",
    "admission_use_id": "ops.demand_use",
    "admission_id": "ops.original_source_admission",
    "product_id": "kb.data_product",
    "intent_id": "ops.data_completion_intent",
}


def selected_graph_snapshot(connection, prepared, request):
    from .data_operation_admission import bound_data_operation_model
    from .demand_results import SelectedGraphBudgetExceeded, selected_record_index

    model = bound_data_operation_model(prepared)
    specification = model.projection_definition(request.projection)
    if request.projection not in {"bound-requests", "selected-support"}:
        raise ValueError("this projection requires its source/assessment acquisition owner")
    if request.project_id is None:
        raise ValueError("selected graph requires an explicit project")
    pins = dict(
        release_id=prepared.release_id, demand_id=request.demand_id, project_id=request.project_id
    )
    try:
        with selected_record_index(
            connection,
            request.demand_id,
            project_id=request.project_id,
            scope=request.scope,
            read_id=request.read_id,
            expected_cut=request.expected_cut,
            max_bytes=min(request.max_examined_bytes, 8388608),
            max_total_bytes=request.max_examined_bytes,
        ) as (cut, index):
            if cut.record["release_id"] != prepared.release_id:
                raise ValueError("selected graph release differs from native cut")
            pins.update(cut.record)
            pins["cut_id"] = cut.identity
            records = tuple(index.records())
    except SelectedGraphBudgetExceeded as error:
        return GraphSnapshot(
            projection=request.projection,
            specification=specification.identity_bytes.hex(),
            pins_json=json_bytes(pins).decode(),
            nodes=(),
            occurrences=(),
            standing="partial",
            unknowns=(str(error),),
        )
    nodes = {
        record["key"]: GraphNode(
            identity=record["key"],
            kind=record["relation"],
            payload_json=json_bytes(record["record"]).decode(),
        )
        for record in records
    }
    by_id = {
        (row["relation"], row["record"]["id"]): row["key"]
        for row in records
        if "id" in row["record"]
    }
    occurrences = []

    def edge(owner, target, role, position=None):
        identity = (
            "graph-occurrence:" + sha256(json_bytes([owner, target, role, position])).hexdigest()
        )
        occurrences.append(
            GraphOccurrence(
                identity=identity,
                source=owner,
                target=target,
                relation="native-reference",
                role=role,
                position=position,
            )
        )

    for item in records:
        row = item["record"]
        for field, relation in _REFERENCES.items():
            target = by_id.get((relation, row.get(field)))
            if target is not None:
                edge(item["key"], target, field)
        if item["relation"] == "ops.demand_use":
            for position, reference in enumerate(row.get("selection", {}).get("support", ())):
                for field, relation in _REFERENCES.items():
                    target = by_id.get((relation, reference.get(field)))
                    if target is not None:
                        edge(item["key"], target, "selected-support." + field, position)
            for position, population in enumerate(row.get("selection", {}).get("populations", ())):
                target = by_id.get(("ops.data_population", population["population_id"]))
                if target is not None:
                    edge(item["key"], target, "selected-population", position)
    return GraphSnapshot(
        projection=request.projection,
        specification=specification.identity_bytes.hex(),
        pins_json=json_bytes(pins).decode(),
        nodes=tuple(nodes[name] for name in sorted(nodes)),
        occurrences=tuple(sorted(occurrences, key=lambda edge: edge.identity)),
    )
