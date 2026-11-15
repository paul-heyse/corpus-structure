"""Original captured source containment; semantic graphs are not coerced to trees."""

from hashlib import sha256
from typing import Any

from .data_operation_identity import decode_semantic_value
from .data_operation_json import json_bytes
from .graph_inspection import GraphNode, GraphOccurrence, GraphSnapshot
from .graph_runtime import nx


def source_hierarchy_snapshot(prepared, model, cut, index):
    specification = model.projection_definition("source-hierarchy")
    contracts = {
        identity.key
        for identity in model.identities
        if identity.domain == "kind"
        and any(
            kind.semantic_id == identity.owner and kind.name == "DdoSelectedNativeSource"
            for kind in model.kinds
        )
    }
    nodes, edges, unknowns = {}, [], []

    def reference(value):
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, dict) and set(value) == {"$ref"}:
            return value["$ref"]
        raise ValueError("source containment reference is not a captured native pointer")

    from itertools import chain

    from .data_product_reference import DataProductMemberReference, DataProductReference

    products = (
        (row["id"], None, row["kind_contract"], row["canonical_body"])
        for row in index.rows("kb.data_product")
    )
    members = (
        (row["product_id"], row["member_id"], row["kind_contract"], row["body"])
        for row in index.rows("kb.data_product_member")
    )
    for product_id, member_id, kind_contract, meaning in chain(products, members):
        if kind_contract not in contracts:
            continue
        address = (
            product_id
            if member_id is None
            else DataProductMemberReference(DataProductReference(product_id), member_id).identity
        )
        body = prepared.validate_json(
            "DdoSelectedNativeSource", json_bytes(decode_semantic_value(meaning))
        ).model_dump(mode="python", exclude_unset=True)
        atoms: dict[str, dict[str, Any]] = {}
        for atom in (*body.get("ancestors", ()), *body.get("items", ())):
            pointer = atom["self_ref"]
            if pointer in atoms and atoms[pointer] != atom:
                raise ValueError("captured source repeats a pointer with different facts")
            atoms[pointer] = atom
        graph = nx.DiGraph(backend="networkx")
        graph.add_nodes_from(atoms)
        for pointer, atom in atoms.items():
            identity = address + ":" + pointer
            nodes[identity] = GraphNode(
                identity=identity,
                kind="record",
                payload_json=json_bytes(
                    dict(
                        product_id=product_id, member_id=member_id, source=body["source"], atom=atom
                    )
                ).decode(),
            )
            parent = reference(atom.get("parent"))
            if parent in atoms:
                graph.add_edge(parent, pointer)
                siblings = [reference(child) for child in atoms[parent].get("children", ())]
                position = siblings.index(pointer) if pointer in siblings else None
                edges.append(
                    GraphOccurrence(
                        identity="source-containment:"
                        + sha256(json_bytes([product_id, member_id, parent, pointer])).hexdigest(),
                        source=address + ":" + parent,
                        target=identity,
                        relation="contains",
                        position=position,
                    )
                )
            elif parent is not None:
                unknowns.append(identity + ": parent outside captured source scope: " + parent)
        for pointer, atom in atoms.items():
            children = tuple(reference(child) for child in atom.get("children", ()))
            if len(set(children)) != len(children):
                raise ValueError("captured source repeats an original containment child")
            for child in children:
                if child not in atoms:
                    unknowns.append(
                        address
                        + ":"
                        + pointer
                        + ": child outside captured source scope: "
                        + str(child)
                    )
                elif reference(atoms[child].get("parent")) != pointer:
                    raise ValueError("captured source parent and child containment disagree")
        if graph and not nx.is_forest(graph, backend="networkx"):
            raise ValueError("captured single-parent containment is cyclic")
        for component in nx.weakly_connected_components(graph, backend="networkx"):
            if not nx.is_arborescence(graph.subgraph(component), backend="networkx"):
                raise ValueError(
                    "captured source component is not original single-parent containment"
                )
    if not nodes:
        unknowns.append("selected closure contains no declared native source hierarchy")
    return GraphSnapshot(
        projection="source-hierarchy",
        specification=specification.identity_bytes.hex(),
        orientation="parent-to-child",
        pins_json=json_bytes({**cut.record, "cut_id": cut.identity}).decode(),
        nodes=tuple(nodes[key] for key in sorted(nodes)),
        occurrences=tuple(sorted(edges, key=lambda edge: edge.identity)),
        standing="partial" if unknowns else "complete",
        unknowns=tuple(unknowns),
    )
