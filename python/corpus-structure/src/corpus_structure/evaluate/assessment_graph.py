"""Authenticated selected characterization graphs for shared graph inspection.

This bridge projects a prediction selection only. It neither acquires protected
answers nor combines an independently authored reference with its predictions.
"""

from hashlib import sha256

from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_product_reference import DataProductReference
from corpus_structure.semantic.declared_formal_readings import SelectedCharacterizationInventories
from corpus_structure.semantic.graph_inspection import GraphNode, GraphOccurrence, GraphSnapshot

from .characterization_assessment import LayerProjection, WitnessGraphBudgetExceeded


def assessment_graph_snapshot(prepared, cut, index, *, members, max_bytes=8388608):
    """Build one faithful graph from explicit nominal members of the pinned read."""
    model = bound_data_operation_model(prepared)
    specification = model.projection_definition("assessment")
    if cut.record["release_id"] != prepared.release_id:
        raise ValueError("assessment graph release differs from the selected cut")
    products = index.mapping("kb.data_product", ("id",))
    member_rows = index.mapping("kb.data_product_member", ("product_id", "member_id"))
    roots = tuple(dict.fromkeys(members))
    if not roots:
        return GraphSnapshot(projection="assessment", specification=specification.identity_bytes.hex(), pins_json=json_bytes(dict(**cut.record, cut_id=cut.identity)).decode(), nodes=(), occurrences=(), standing="unavailable", unknowns=("no explicit assessed member population was selected",))
    for product, member in roots:
        if products.get(product) is None or member_rows.get((product, member)) is None:
            raise ValueError("assessment root is outside the selected native member closure")
    inventories = SelectedCharacterizationInventories(products)
    projection = LayerProjection(lambda pin: inventories[DataProductReference(pin["product_id"])].payload)
    pins = dict(**cut.record, cut_id=cut.identity, model_digest=sha256(model.content).hexdigest(), assessment_standing="prediction-only")
    try:
        graph = projection.graph_many([({"product_id": product}, member) for product, member in roots], max_bytes=max_bytes, witness_closure=True)
    except WitnessGraphBudgetExceeded as error:
        return GraphSnapshot(projection="assessment", specification=specification.identity_bytes.hex(), pins_json=json_bytes(pins).decode(), nodes=(), occurrences=(), standing="partial", unknowns=(str(error),))
    # Local traversal names are never public identity. Qualify every node by the
    # exact product/member address supplied by the authenticated inventory adapter.
    names = {node["id"]: "assessment-node:" + sha256(json_bytes(node["qualified_identity"])).hexdigest() for node in graph["nodes"]}
    nodes = tuple(sorted((GraphNode(identity=names[node["id"]], kind=node["value"]["collection"], payload_json=json_bytes(dict(value=node["value"], qualified_identity=node["qualified_identity"], root=node["id"] in graph["roots"])).decode()) for node in graph["nodes"]), key=lambda node: node.identity))
    occurrences = []
    for node in graph["nodes"]:
        for position, edge in enumerate(node["edges"]):
            attributes = {key: value for key, value in edge.items() if key != "target"}
            occurrences.append(GraphOccurrence(identity="assessment-occurrence:" + sha256(json_bytes([names[node["id"]], names[edge["target"]], attributes, position])).hexdigest(), source=names[node["id"]], target=names[edge["target"]], relation=edge["label"], role=edge.get("role", ""), position=edge.get("position"), attributes_json=json_bytes(attributes).decode()))
    if not {node.kind for node in nodes} <= set(specification.node_kinds) or not {edge.relation for edge in occurrences} <= set(specification.relationship_kinds):
        raise ValueError("selected assessment facts exceed the admitted projection vocabulary")
    return GraphSnapshot(projection="assessment", specification=specification.identity_bytes.hex(), pins_json=json_bytes(pins).decode(), nodes=nodes, occurrences=tuple(sorted(occurrences, key=lambda edge: edge.identity)))
