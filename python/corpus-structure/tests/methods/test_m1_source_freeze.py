"""Reference source freezing composes retained custody without inference demand."""

from corpus_structure.orchestrate.m1 import source_graph


def test_source_only_graph_has_no_annotation_model_resolution_or_agent_stage():
    graph = source_graph("source-only")
    assert not graph.policy_propose
    assert [(step.config, step.upstream) for _, steps in graph.stages for step in steps] == [
        ("ingest.pdf_integrated/default", ()),
    ]
