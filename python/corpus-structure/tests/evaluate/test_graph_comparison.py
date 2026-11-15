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



def test_source_assessment_and_reified_task_profiles_do_not_relabel_each_other():
    from corpus_structure.semantic.data_operation_model import compiled_snapshot_projections

    profiles = {profile.name: profile for profile in compiled_snapshot_projections()}
    selected, task = profiles["assessment"], profiles["task-assessment"]
    assert selected.source_contract == "selected-characterization-records"
    assert {"annotations", "terms", "choice_member", "named_binding"} <= set(selected.node_kinds)
    assert "child" in selected.relationship_kinds
    assert "entity" not in selected.node_kinds
    assert task.node_kinds == ("entity", "assertion", "group", "member")
    assert task.relationship_kinds == ("subject", "object", "requires", "member", "root")
    assert task.selection == "protected-question-and-prediction"
    assert task.attributes == "protected-asymmetric-fields"
