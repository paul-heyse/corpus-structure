"""Input substitutability from the captured nominal inheritance graph.

Returned contracts identify actual concrete values. The declared role remains
the interface; publication and lineage never relabel a concrete value as it.
"""

from __future__ import annotations

import json
from collections.abc import Iterable

import networkx as nx

from .data_operation_model import EffectiveDataOperationModel


def input_kind_refinements(
    model: EffectiveDataOperationModel, roots: Iterable[str]
) -> dict[str, tuple[str, ...]]:
    kinds = {kind.semantic_id: kind for kind in model.kinds}
    graph = nx.DiGraph()
    graph.add_nodes_from(kinds)
    for edge in model.edges:
        if edge.relation != "inherits":
            continue
        if edge.source not in kinds or edge.target not in kinds:
            raise ValueError("nominal refinement has an unresolved inheritance endpoint")
        if kinds[edge.source].category != kinds[edge.target].category:
            raise ValueError("nominal refinement changes kind category")
        graph.add_edge(edge.target, edge.source)
    if not nx.is_directed_acyclic_graph(graph, backend="networkx"):
        raise ValueError("nominal refinement inheritance is cyclic")
    result = {}
    for root in sorted(set(roots)):
        if root not in kinds:
            raise ValueError("nominal input kind is absent")
        selected = {root, *nx.descendants(graph, root, backend="networkx")}
        if any(not kinds[kind].complete for kind in selected):
            raise ValueError("nominal input refinement includes an incomplete kind")
        result[root] = tuple(
            sorted(
                kind
                for kind in selected
                if not json.loads(kinds[kind].facts).get("abstract", False)
            )
        )
    return result


def input_kind_contracts(model: EffectiveDataOperationModel, roots: Iterable[str]):
    identities = {(item.owner, item.domain): item.key for item in model.identities}
    return {
        root: tuple(sorted(identities[kind, "kind"] for kind in family))
        for root, family in input_kind_refinements(model, roots).items()
    }
