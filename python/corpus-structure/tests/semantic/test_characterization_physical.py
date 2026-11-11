"""Trusted imported physical tables compile while imported payload types stay values."""

from corpus_structure.schema.physical import compile_physical, physical_source_closure
from corpus_structure.semantic.metadata import PHYSICAL_MODEL


def test_imported_physical_projection_owns_indexed_characterization_relations():
    sources = physical_source_closure(
        PHYSICAL_MODEL.name, lambda name: PHYSICAL_MODEL.with_name(name).read_bytes()
    )
    model = compile_physical(sources)
    assert {
        "ops.characterization_product",
        "kb.characterization_membership",
        "kb.characterization_extent",
    } <= set(model.tables)
    assert "kb.CharacterizationExtent" not in model.tables
    assert tuple(model.tables["kb.characterization_membership"].primary_key.columns.keys()) == (
        "task_id",
        "product_key",
        "content_digest",
        "local_id",
    )
    assert any(
        tuple(index.columns.keys()) == ("task_id", "product_key", "content_digest", "owner_id")
        for index in model.tables["kb.characterization_membership"].indexes
    )
