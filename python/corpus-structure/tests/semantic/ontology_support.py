"""Shared controlled inputs and builders for ontology support."""

from functools import lru_cache


def _bound_projection(*args, **kwargs):
    """Explicit trusted contract fixture; each test supplies its independent node universe."""
    from corpus_structure.semantic.ontology import GraphProjectionBinding, QualifiedGraphProjection

    model = _graph_model()
    contract = next(p for p in model.projections if p.id == "graph_validation")
    roots = tuple(str(row["id"]) for row in args[4])
    if len(args) > 7:
        roots += tuple(str(row["id"]) for row in args[7])
    return QualifiedGraphProjection(
        *args,
        contract_binding=GraphProjectionBinding(
            args[0],
            model.model_id,
            contract,
            next(op.outcomes for op in model.operations if op.id == "graph_validate"),
        ),
        source_universe=roots,
        snapshot_guard=lambda: True,
        **kwargs,
    )


@lru_cache(maxsize=1)
def _graph_model():
    from corpus_structure.semantic.contracts import (
        compile_execution_model,
        trusted_execution_inputs,
    )

    return compile_execution_model(trusted_execution_inputs())
