"""Independent physical relationships, exact projections and trusted compiler boundaries."""

from __future__ import annotations

from decimal import Decimal

import pytest
from linkml_runtime.utils.schemaview import SchemaView
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from corpus_structure.schema.declarations import ModelError
from corpus_structure.schema.physical import compile_physical, physical_source_closure
from corpus_structure.schema.relational import compile_metadata
from corpus_structure.semantic.metadata import (
    PHYSICAL_MODEL,
    decimal_projection,
    get_metadata,
    get_physical_model_id,
    table,
)
from corpus_structure.semantic.migrations import head_revision


def _foreign_keys(name: str) -> set[tuple[tuple[str, ...], tuple[str, ...]]]:
    return {
        (tuple(c.columns.keys()), tuple(e.target_fullname for e in c.elements))
        for c in table(name).constraints
        if isinstance(c, ForeignKeyConstraint)
    }


@pytest.mark.parametrize(
    ("name", "local", "target"),
    [
        (
            "ops.data_request",
            ("release_id", "operation_id"),
            (
                "sem.data_operation_definition.release_id",
                "sem.data_operation_definition.operation_id",
            ),
        ),
        ("ops.task", ("data_request_id",), ("ops.data_request.id",)),
        ("kb.data_product", ("kind_contract",), ("sem.data_kind_contract.kind_contract",)),
        ("ops.data_derivation", ("intent_id",), ("ops.data_completion_intent.id",)),
    ],
)
def test_required_scoped_relationships(name, local, target):
    assert (local, target) in _foreign_keys(name)


@pytest.mark.parametrize("name", ["ops.data_completion_intent", "ops.data_derivation"])
def test_request_children_keep_exact_generation(name):
    assert (
        ("request_id", "generation"),
        ("ops.data_request_generation.request_id", "ops.data_request_generation.generation"),
    ) in _foreign_keys(name)


def test_metadata_deterministic_and_fixed() -> None:
    again = compile_physical(
        physical_source_closure(
            PHYSICAL_MODEL.name, lambda name: PHYSICAL_MODEL.with_name(name).read_bytes()
        )
    )
    dialect = postgresql.dialect()
    for name, item in get_metadata().tables.items():
        assert str(CreateTable(item).compile(dialect=dialect)) == str(
            CreateTable(again.tables[name]).compile(dialect=dialect)
        )
    assert set(t.schema for t in get_metadata().tables.values()) == {"sem", "data", "ops", "kb"}
    assert table("sem.release") is get_metadata().tables["sem.release"]
    assert get_physical_model_id().startswith("physical:")
    assert head_revision() is not None


def test_candidate_schema_is_not_a_physical_model() -> None:
    with pytest.raises(ModelError, match="trusted physical"):
        compile_metadata(SchemaView(str(PHYSICAL_MODEL.with_name("core.yaml"))), target="semantic")


def test_exact_decimal_projection_preserves_lexical_semantics() -> None:
    assert decimal_projection("1.2300") == Decimal("1.2300")
    assert decimal_projection("-0.000") is not None
    assert decimal_projection("1e131071") == Decimal("1e131071")
    assert decimal_projection("1e131072") is None
    assert decimal_projection("1e-16384") is None
    assert decimal_projection("1e9999999999999999999999") is None
    for lexical in ("NaN", "Infinity", "1_000", " 1", ""):
        with pytest.raises(ValueError):
            decimal_projection(lexical)


def test_product_payloads_are_not_btree_index_entries():
    product = table("kb.data_product")
    assert "canonical_body" in product.c
    for index in product.indexes:
        assert "canonical_body" not in {column.name for column in index.columns}


def test_read_shapes_never_supply_stored_table_ddl():
    from corpus_structure.semantic.metadata import READ_MODEL

    read = compile_physical(
        physical_source_closure(
            READ_MODEL.name, lambda name: READ_MODEL.with_name(name).read_bytes()
        ),
        root=READ_MODEL.name,
        target="semantic-read",
    )
    expected = {
        "ops.pdf_selected_product",
        "ops.pdf_published_item",
        "ops.pdf_published_region",
        "ops.pdf_published_coverage",
        "ops.pdf_published_derivation",
    }
    assert set(read.tables) == expected
    assert expected.isdisjoint(get_metadata().tables)
    assert table("ops.pdf_published_item").c.pointer.type.python_type is str
    assert table("ops.pdf_published_region").c.left.type.python_type is Decimal
    assert table("ops.pdf_selected_product").c.payload.nullable
    for relation in (
        "kb.rendition",
        "kb.segment",
        "kb.span",
        "ops.source_frame",
        "ops.rendition_build",
        "ops.run_rendition",
        "ops.native_document_product",
        "kb.native_document_item",
        "ops.parsing_product",
        "ops.parsing_layer_product",
    ):
        assert relation not in get_metadata().tables
