"""Pure attributed comparison shared by retained and native selected assessment.

Domain adapters supply meaning and focus; candidate mappings do not establish
joint-choice feasibility or support. Those decisions remain with their owners.
"""

from collections import Counter
from collections.abc import Iterable
from typing import Any, Literal

from corpus_structure.semantic.graph_runtime import nx
from corpus_structure.semantic.identity import canonical_bytes

ComparisonMode = Literal["exact", "witness"]
ComparisonPolicy = Literal["exact", "expected-fields"]


def attributed_graph(nodes: Iterable[tuple[Any, dict]], edges: Iterable[tuple[Any, Any, dict]]):
    """Authenticate identities before NetworkX can auto-create missing endpoints."""
    graph = nx.MultiDiGraph(backend="networkx")
    for identity, attributes in nodes:
        if identity in graph:
            raise ValueError("assessment graph repeats a node identity")
        graph.add_node(identity, **attributes)
    for source, target, attributes in edges:
        if source not in graph or target not in graph:
            raise ValueError("assessment graph edge lacks an exact selected target")
        graph.add_edge(source, target, **attributes)
    return graph


def rooted_graph(record):
    if record["root"] not in {node["id"] for node in record["nodes"]}:
        raise ValueError("assessment graph lacks its exact root")
    return attributed_graph(
        ((node["id"], dict(meaning=node["value"], focus=node["id"] == record["root"])) for node in record["nodes"]),
        ((node["id"], edge["target"], {k: v for k, v in edge.items() if k != "target"}) for node in record["nodes"] for edge in node["edges"]),
    )


def comparison_mappings(actual, expected, *, mode: ComparisonMode, policy: ComparisonPolicy):
    """Yield actual-to-expected mappings; callers assess every relevant candidate."""
    from networkx.algorithms.isomorphism import MultiDiGraphMatcher

    if mode not in {"exact", "witness"} or policy not in {"exact", "expected-fields"}:
        raise ValueError("unknown assessment comparison interpretation")

    def node_match(left, right):
        if policy == "exact":
            return canonical_bytes(left) == canonical_bytes(right)
        return left.get("focus") == right.get("focus") and all(
            key in left.get("meaning", {}) and left["meaning"][key] == value
            for key, value in right.get("meaning", {}).items()
        )

    def edge_match(left, right):
        actual_edges = Counter(canonical_bytes(dict(edge)) for edge in left.values())
        expected_edges = Counter(canonical_bytes(dict(edge)) for edge in right.values())
        return actual_edges == expected_edges if mode == "exact" else actual_edges >= expected_edges

    matcher = MultiDiGraphMatcher(actual, expected, node_match=node_match, edge_match=edge_match)
    return matcher.isomorphisms_iter() if mode == "exact" else matcher.subgraph_monomorphisms_iter()
