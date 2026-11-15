"""Independent topology and actual process bootstrap controls."""

import os
import subprocess
import sys

import pytest

from corpus_structure.semantic.graph_runtime import nx
from corpus_structure.semantic.graph_topology import (
    boundary_edges,
    condensation,
    cyclic_components,
    ordered_nodes,
    rooted_closure,
    strong_components,
    witness_path,
)


def test_native_runtime_neutralizes_all_ambient_dispatch_priorities():
    environment = dict(os.environ)
    for suffix in ("", "_ALGOS", "_GENERATORS", "_CLASSES", "_BFS_LAYERS"):
        environment["NETWORKX_BACKEND_PRIORITY" + suffix] = "uninstalled-hostile-backend"
    environment["NETWORKX_AUTOMATIC_BACKENDS"] = "uninstalled-hostile-backend"
    completed = subprocess.run(
        [sys.executable, "-c", '''
from corpus_structure.semantic.graph_runtime import nx
assert dict(nx.config.backend_priority) == dict(algos=[],generators=[],classes=[])
assert nx.config.fallback_to_nx is False
from corpus_structure.semantic.graph_topology import condensation
G=nx.DiGraph(backend="networkx")
G.add_edges_from([("A","B"),("B","A"),("B","C")])
H=condensation(G)
assert type(H) is nx.DiGraph
assert {frozenset(v["members"]) for _,v in H.nodes(data=True)} == {frozenset(("A","B")),frozenset(("C",))}
assert len(H.edges) == 1
'''],
        env=environment, capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_native_runtime_resets_preexisting_function_specific_dispatch():
    completed = subprocess.run(
        [sys.executable, "-c", '''
import networkx as nx
nx.config.backend_priority = {"classes":["networkx"],"algos":["networkx"],"generators":["networkx"],"bfs_layers":["networkx"]}
from corpus_structure.semantic.graph_runtime import nx
assert dict(nx.config.backend_priority) == dict(algos=[],generators=[],classes=[])
'''], capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_multi_root_union_includes_roots_isolates_and_reconvergence():
    graph = nx.DiGraph(backend="networkx")
    graph.add_nodes_from(["alone", "A", "B", "C", "D"])
    graph.add_edges_from([("A", "C"), ("B", "C"), ("C", "D")])
    assert rooted_closure(graph, ["A", "B", "A", "alone"]) == {"A", "B", "C", "D", "alone"}
    assert rooted_closure(graph, ["D"], reverse=True) == {"A", "B", "C", "D"}
    assert rooted_closure(graph, []) == frozenset()
    with pytest.raises(ValueError, match="unknown"):
        rooted_closure(graph, ["absent"])


def test_scc_partition_distinguishes_self_loop_cycle_tail_and_isolate():
    graph = nx.DiGraph(backend="networkx")
    graph.add_nodes_from(["alone"])
    graph.add_edges_from([("A", "B"), ("B", "A"), ("B", "C"), ("S", "S")])
    components = strong_components(graph)
    assert set(components) == {frozenset({"A", "B"}), frozenset({"C"}), frozenset({"S"}), frozenset({"alone"})}
    assert set(cyclic_components(graph)) == {frozenset({"A", "B"}), frozenset({"S"})}
    quotient = condensation(graph, components)
    mapping = quotient.graph["mapping"]
    assert set(quotient.edges) == {(mapping["A"], mapping["C"])}
    with pytest.raises(nx.NetworkXUnfeasible):
        ordered_nodes(graph)


def test_boundary_preserves_parallel_occurrences_and_paths_are_topology_only():
    graph = nx.MultiDiGraph(backend="networkx")
    graph.add_nodes_from(["alone"])
    graph.add_edge("A", "B", key="role-one", role="left")
    graph.add_edge("A", "B", key="role-two", role="right")
    graph.add_edge("B", "C", key="tail")
    assert boundary_edges(graph, ["A"]) == (("A", "B", "role-one", {"role": "left"}), ("A", "B", "role-two", {"role": "right"}))
    assert {row[2] for row in boundary_edges(graph, ["B"], reverse=True)} == {"role-one", "role-two"}
    assert witness_path(graph, "A", "C") == ("A", "B", "C")
    assert witness_path(graph, "alone", "C") is None
    with pytest.raises(ValueError, match="unknown"):
        boundary_edges(graph, ["missing"])
    with pytest.raises(ValueError, match="unknown"):
        witness_path(graph, "missing", "C")
