"""Immutable semantic reference API; references remain private to the evaluator."""



def context_refs(batch):
    """Pure pre-pivot fixture context projection, retained for alignment parity consumers."""
    from corpus_structure.core import batch as B
    from corpus_structure.core.vocab import StatementKind, StatementRole

    def context_only(sentences):
        return bool(sentences) and all(s.startswith("c") for s in sentences)

    result = {
        s.local_ref
        for s in batch.statements
        if isinstance(s, B.AuthoredStatement)
        and s.kind == StatementKind.ASSUMPTION
        and not isinstance(s.anchor, str)
        and context_only(s.anchor)
    }
    result.update(
        c.local_ref
        for c in batch.claims
        if c.statement_role == StatementRole.PREMISE
        and context_only([e.sentence for e in c.evidence])
    )
    return frozenset(result)
