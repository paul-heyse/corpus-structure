"""Independent mapping controls for shared protected graph comparison."""

from corpus_structure.evaluate.graph_comparison import attributed_graph, comparison_mappings


def test_witness_allows_extra_parallel_relationship_between_mapped_nodes():
    nodes = [
        ("root", dict(meaning={"kind": "predicate"}, focus=True)),
        ("arg", dict(meaning={"kind": "argument"}, focus=False)),
    ]
    expected = attributed_graph(nodes, [("root", "arg", {"role": "subject"})])
    actual = attributed_graph(
        nodes, [("root", "arg", {"role": "subject"}), ("root", "arg", {"role": "context"})]
    )
    assert list(
        comparison_mappings(actual, expected, mode="witness", policy="expected-fields")
    ) == [{"root": "root", "arg": "arg"}]
    assert not list(comparison_mappings(actual, expected, mode="exact", policy="expected-fields"))
