"""Independent physical relationships, exact projections and legacy compiler compatibility."""

from __future__ import annotations

from decimal import Decimal

import pytest
from linkml_runtime.utils.schemaview import SchemaView
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from corpus_structure.schema.model import ModelError
from corpus_structure.schema.relational import compile_metadata
from corpus_structure.semantic.metadata import (
    PHYSICAL_MODEL,
    PHYSICAL_MODEL_ID,
    decimal_projection,
    metadata,
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
    ('name', 'local', 'target'),
    [
        ('data.typed_value', ('realization_id', 'release_id', 'entity_id'),
         ('data.entity.realization_id', 'data.entity.release_id', 'data.entity.entity_id')),
        ('data.value_role', ('realization_id', 'release_id', 'child_value_id'),
         ('data.typed_value.realization_id', 'data.typed_value.release_id', 'data.typed_value.value_id')),
        ('data.fact', ('release_id', 'property_id'),
         ('sem.property_definition.release_id', 'sem.property_definition.property_id')),
        ('data.membership', ('release_id', 'class_id'),
         ('sem.class_definition.release_id', 'sem.class_definition.class_id')),
        ('data.support', ('realization_id', 'release_id', 'occurrence_id', 'fact_id'),
         ('data.occurrence.realization_id', 'data.occurrence.release_id',
          'data.occurrence.occurrence_id', 'data.occurrence.fact_id')),
    ],
)
def test_required_scoped_relationships(name: str, local: tuple[str, ...], target: tuple[str, ...]) -> None:
    assert (local, target) in _foreign_keys(name)


def test_all_data_children_are_pinned_to_the_realization_release() -> None:
    for name, item in metadata.tables.items():
        if item.schema == 'data' and item.name not in {'project', 'realization'}:
            assert (
                ('realization_id', 'release_id'),
                ('data.realization.realization_id', 'data.realization.release_id'),
            ) in _foreign_keys(name)


def test_metadata_deterministic_and_fixed() -> None:
    again = compile_metadata(SchemaView(str(PHYSICAL_MODEL)), target='semantic')
    dialect = postgresql.dialect()
    for name, item in metadata.tables.items():
        assert str(CreateTable(item).compile(dialect=dialect)) == str(CreateTable(again.tables[name]).compile(dialect=dialect))
    assert set(t.schema for t in metadata.tables.values()) == {'sem', 'data'}
    assert table('sem.release') is metadata.tables['sem.release']
    assert PHYSICAL_MODEL_ID.startswith('physical:')
    assert head_revision() == 'semantic_0002'


def test_candidate_schema_is_not_a_physical_model() -> None:
    with pytest.raises(ModelError, match='trusted physical'):
        compile_metadata(SchemaView(str(PHYSICAL_MODEL.with_name('core.yaml'))), target='semantic')


def test_exact_decimal_projection_preserves_lexical_semantics() -> None:
    assert decimal_projection('1.2300') == Decimal('1.2300')
    assert decimal_projection('-0.000') is not None
    assert decimal_projection('1e131071') == Decimal('1e131071')
    assert decimal_projection('1e131072') is None
    assert decimal_projection('1e-16384') is None
    for lexical in ('NaN', 'Infinity', '1_000', ' 1', ''):
        with pytest.raises(ValueError):
            decimal_projection(lexical)
