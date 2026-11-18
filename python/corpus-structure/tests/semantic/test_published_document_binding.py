"""Independent exact semantic-pin constraint for published documents."""

from sqlalchemy import UniqueConstraint

from corpus_structure.semantic.metadata import get_metadata


def test_published_revision_keeps_exact_semantic_pin_composite_key():
    published = get_metadata().tables["ops.pdf_published_revision"]
    assert any(
        isinstance(constraint, UniqueConstraint)
        and tuple(column.name for column in constraint.columns)
        == ("build_id", "task_id", "product_key", "logical_digest")
        for constraint in published.constraints
    )
