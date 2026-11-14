"""Shared controlled inputs and builders for typed structural composition support."""

from semantic.structural_products_support import inputs


def threshold_inputs(left, right, scope="scope"):
    value = inputs()
    passages = tuple(
        p.model_copy(update=dict(text=t, start=0, end=len(t), scope=scope))
        for p, t in zip(value.passages, (left, right), strict=True)
    )
    return value.model_copy(update=dict(passages=passages))


def revision_inputs(left, right, *, same_source=True):
    inputs = threshold_inputs(left, right)
    older, newer = inputs.passages
    older = older.model_copy(update={"parent": "rule", "effective_version": "R1"})
    newer = newer.model_copy(
        update={
            "parent": "rule",
            "effective_version": "R2",
            "source_ref": older.source_ref if same_source else newer.source_ref,
            "start": older.end + 1,
            "end": older.end + 1 + len(newer.text),
        }
    )
    return inputs.model_copy(update={"passages": (newer, older)})
