"""Independent physical pairing controls for published document consumers."""

from sqlalchemy import UniqueConstraint

from corpus_structure.semantic.metadata import metadata


def test_source_and_render_bind_publication_pin_and_address_as_composite_keys():
    published = metadata.tables["ops.pdf_published_revision"]
    assert any(
        isinstance(constraint, UniqueConstraint)
        and tuple(column.name for column in constraint.columns)
        == ("build_id", "task_id", "product_key", "logical_digest")
        for constraint in published.constraints
    )
    for name, address, target in (
        ("kb.source_view", ("section_pointer",), "kb.pdf_record_access"),
        ("ops.native_region_artifact", ("pointer", "region_index"), "kb.pdf_record_region"),
    ):
        relation = metadata.tables[name]
        keys = {
            tuple(column.name for column in constraint.columns): (
                constraint.elements[0].target_fullname.rsplit(".", 1)[0],
                tuple(element.target_fullname.rsplit(".", 1)[1] for element in constraint.elements),
            )
            for constraint in relation.foreign_key_constraints
        }
        assert keys[
            ("native_build_id", "native_task_id", "native_product_key", "native_content_digest")
        ] == (
            "ops.pdf_published_revision",
            ("build_id", "task_id", "product_key", "logical_digest"),
        )
        assert keys[("native_build_id", "native_revision_id", *address)] == (
            target,
            ("product_id", "revision_id", "pointer", *address[1:]),
        )
        assert not relation.c.native_build_id.nullable
        assert not relation.c.native_revision_id.nullable
        assert any(
            str(getattr(constraint, "sqltext", "")) == "native_build_id = native_revision_id"
            for constraint in relation.constraints
        )
        assert all(not target.startswith("kb.native_document_") for target, _ in keys.values())
