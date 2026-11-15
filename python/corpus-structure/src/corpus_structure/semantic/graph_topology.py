"""Pure topology over owned, authenticated native NetworkX projections.

Domain extraction, typed occurrences, validity and payload ownership stay with
callers. These algorithms never grant selection, completeness or admission.
"""

from collections.abc import Hashable, Iterable

from .graph_runtime import nx


def rooted_closure[Node: Hashable](
    graph, roots: Iterable[Node], *, reverse=False
) -> frozenset[Node]:
    roots = tuple(dict.fromkeys(roots))
    if any(root not in graph for root in roots):
        raise ValueError("unknown graph root")
    if not roots:
        return frozenset()
    selected = nx.reverse_view(graph) if reverse else graph
    return frozenset(
        node for layer in nx.bfs_layers(selected, roots, backend="networkx") for node in layer
    )


def strong_components(graph):
    return tuple(
        frozenset(component)
        for component in nx.strongly_connected_components(graph, backend="networkx")
    )


def cyclic_components(graph):
    return tuple(
        component
        for component in strong_components(graph)
        if len(component) > 1 or any(graph.has_edge(node, node) for node in component)
    )


def condensation(graph, components=None):
    return nx.condensation(
        graph,
        scc=strong_components(graph) if components is None else components,
        backend="networkx",
    )


def ordered_nodes(graph, *, reverse=False, key=None):
    selected = nx.reverse_view(graph) if reverse else graph
    return tuple(nx.lexicographical_topological_sort(selected, key=key, backend="networkx"))


def witness_path(graph, source, target):
    if source not in graph or target not in graph:
        raise ValueError("unknown graph path endpoint")
    try:
        return tuple(nx.shortest_path(graph, source, target, weight=None, backend="networkx"))
    except nx.NetworkXNoPath:
        return None


def boundary_edges(graph, nodes, *, reverse=False):
    nodes = frozenset(nodes)
    if not nodes <= graph.nodes:
        raise ValueError("unknown graph boundary member")
    selected = nx.reverse_view(graph) if reverse else graph
    # Selected3.6 stubs omit the documented3.7 dispatch keyword here.
    return tuple(
        nx.edge_boundary(
            selected, nodes, keys=selected.is_multigraph(), data=True, backend="networkx"
        )
    )  # type: ignore[no-matching-overload]
