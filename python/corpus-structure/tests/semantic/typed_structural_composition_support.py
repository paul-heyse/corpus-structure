"""Literal current source inputs shared by exact structural composition controls."""

from semantic.structural_products_support import input_from_passages, inputs


def threshold_inputs(left, right, scope="scope"):
    return inputs(left, right, starts=(0, 0), scope=scope)


def revision_inputs(left, right, *, same_source=True):
    return input_from_passages((
        dict(passage_id="b", document="book-a" if same_source else "book-b", text=right,
             start=len(left) + 1, parent="rule", effective_version="R2"),
        dict(passage_id="a", document="book-a", text=left, start=0,
             parent="rule", effective_version="R1"),
    ))
