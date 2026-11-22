"""Characterization uses the common indexed product relation and nominal payload values."""

from corpus_structure.schema.physical import compile_physical, physical_source_closure
from corpus_structure.semantic.metadata import PHYSICAL_MODEL


def test_imported_physical_projection_owns_indexed_characterization_relations():
    sources = physical_source_closure(
        PHYSICAL_MODEL.name, lambda name: PHYSICAL_MODEL.with_name(name).read_bytes()
    )
    model = compile_physical(sources)
    assert {
        "kb.data_product",
        "kb.data_product_member",
        "kb.data_product_partition",
        "sem.data_rule",
        "kb.data_validity",
    } <= set(model.tables)
    assert "kb.CharacterizationExtent" not in model.tables
    assert "kb.characterization_membership" not in model.tables
    assert tuple(model.tables["kb.data_product_partition"].primary_key.columns.keys()) == (
        "product_id",
        "collection",
        "partition_key",
    )
    assert any(
        tuple(index.columns.keys()) == ("product_id", "collection", "ordinal")
        for index in model.tables["kb.data_product_partition"].indexes
    )
