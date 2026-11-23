"""Characterization uses the common indexed product relation and nominal payload values."""

from sqlalchemy import CheckConstraint, UniqueConstraint

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


def test_retained_population_has_a_prepublication_parent_and_private_visibility_edge():
    sources = physical_source_closure(
        PHYSICAL_MODEL.name, lambda name: PHYSICAL_MODEL.with_name(name).read_bytes()
    )
    model = compile_physical(sources)
    parent_key = ("intent_id", "output_role", "output_position", "collection", "partition_key")
    retained = model.tables["ops.data_retained_population"]
    items = model.tables["ops.data_retained_population_item"]
    published = model.tables["kb.data_product_population"]

    assert tuple(retained.primary_key.columns.keys()) == parent_key
    assert tuple(items.primary_key.columns.keys()) == (*parent_key, "item_ordinal")
    assert tuple(published.primary_key.columns.keys()) == (
        "product_id",
        "collection",
        "partition_key",
    )
    for relation in (retained, items, published):
        assert relation.info["read_roles"] == ()
        assert relation.info["immutability"] == "intrinsic"
    assert retained.info["frontier_guard"] == items.info["frontier_guard"] == "exempt"
    assert {foreign.target_fullname for foreign in retained.foreign_keys} == {
        "ops.data_completion_intent.id"
    }
    assert {
        tuple(element.target_fullname for element in constraint.elements)
        for constraint in items.foreign_key_constraints
    } == {tuple(f"ops.data_retained_population.{name}" for name in parent_key)}
    assert {
        tuple(element.target_fullname for element in constraint.elements)
        for constraint in published.foreign_key_constraints
    } == {
        ("kb.data_product.id",),
        tuple(f"ops.data_retained_population.{name}" for name in (*parent_key, "product_id")),
    }
    assert (*parent_key, "address_key") in {
        tuple(constraint.columns.keys())
        for constraint in items.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert {
        constraint.name
        for constraint in retained.constraints
        if isinstance(constraint, CheckConstraint)
    } == {
        "ck_retained_population_output_position",
        "ck_retained_population_ordinal",
        "ck_retained_population_item_count",
    }
    assert not items.c.canonical_text.nullable and not items.c.address_key.nullable
