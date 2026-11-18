"""Physical predicates bind modeled fields and preserve independent SQL semantics."""

import json

import pytest
from linkml_runtime.utils.schemaview import SchemaView
from sqlalchemy import CheckConstraint
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import CreateIndex

from corpus_structure.schema.model import ModelError
from corpus_structure.schema.relational import compile_metadata, physical_expression_sql


def compile_checks(checks, indexes=()):
    declaration = {
        "id": "https://corpus-structure.org/model/semantic/physical",
        "name": "physical",
        "prefixes": {"linkml": "https://w3id.org/linkml/"},
        "imports": ["linkml:types"],
        "subsets": {"data": {}},
        "classes": {
            "span": {
                "in_subset": ["data"],
                "attributes": {"start": {"range": "integer"}, "end": {"range": "integer"}},
                "annotations": {"ph:checks": json.dumps(checks), "ph:indexes": json.dumps(indexes)},
            }
        },
    }
    return compile_metadata(SchemaView(json.dumps(declaration)), target="semantic").tables["data.span"]


def test_cross_field_check_and_partial_index_bind_real_columns():
    relation = compile_checks(
        [{"name": "ordered_span", "predicate": {"op": "ge", "args": [{"field": "end"}, {"field": "start"}]}}],
        [{"name": "ix_start", "columns": ["start"], "where": {"op": "is_not_null", "args": [{"field": "start"}]}}],
    )
    (check,) = [constraint for constraint in relation.constraints if isinstance(constraint, CheckConstraint)]
    assert check.name == "ordered_span"
    assert set(check.columns) == {relation.c.start, relation.c.end}
    assert physical_expression_sql(check.sqltext) == '"end" >= start'
    (index,) = relation.indexes
    assert str(CreateIndex(index).compile(dialect=dialect())) == (
        "CREATE INDEX ix_start ON data.span USING btree (start) WHERE start IS NOT NULL"
    )


@pytest.mark.parametrize("predicate", ["end >= start", {"field": "missing"}, {"op": "ge", "args": [{"field": "end"}]}])
def test_unbound_or_unstructured_predicates_refuse_at_compile(predicate):
    with pytest.raises(ModelError):
        compile_checks([{"name": "invalid", "predicate": predicate}])


def test_index_include_requires_a_modeled_field():
    with pytest.raises(ModelError, match="unknown physical index field"):
        compile_checks([], [{"columns": ["start"], "include": ["missing"]}])


def test_search_configuration_changes_both_generated_vector_and_population_check():
    from corpus_structure.schema.physical import compile_physical, physical_source_closure
    from corpus_structure.semantic.metadata import PHYSICAL_MODEL

    sources = physical_source_closure(
        PHYSICAL_MODEL.name, lambda name: PHYSICAL_MODEL.with_name(name).read_bytes()
    )
    sources["physical.yaml"] = sources["physical.yaml"].replace(
        b"ph:search_configuration: english", b"ph:search_configuration: simple"
    )
    selected = compile_physical(sources)
    vector = selected.tables["ops.pdf_source_search_section"].c.search_vector
    assert vector.info["search_configuration"] == "simple"
    assert vector.computed is not None
    assert "'simple'" in physical_expression_sql(vector.computed.sqltext)
    population = selected.tables["ops.pdf_source_search_population"]
    predicates = [physical_expression_sql(item.sqltext) for item in population.constraints
                  if isinstance(item, CheckConstraint)]
    assert "configuration = 'simple'" in predicates
    assert "configuration = 'english'" not in predicates


def test_postgresql_enforces_generated_cross_field_constraint(semantic_bare_engine):
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.schema import CreateSchema

    relation = compile_checks(
        [{"name": "ordered_span", "predicate": {"op": "ge", "args": [{"field": "end"}, {"field": "start"}]}}]
    )
    with semantic_bare_engine.begin() as connection:
        connection.execute(CreateSchema("data"))
        relation.create(connection)
        connection.execute(relation.insert(), [{"start": 1, "end": 2}, {"start": 3, "end": 3}])
        with pytest.raises(IntegrityError, match="ordered_span"), connection.begin_nested():
            connection.execute(relation.insert(), {"start": 4, "end": 3})
        assert connection.execute(relation.select()).all() == [(1, 2), (3, 3)]


def test_postgresql_same_name_check_change_has_ordered_drop_and_create(semantic_bare_engine):
    from alembic.autogenerate import produce_migrations
    from alembic.migration import MigrationContext
    from alembic.operations.ops import CreateCheckConstraintOp, DropConstraintOp, ModifyTableOps
    from sqlalchemy.schema import CreateSchema

    from corpus_structure.semantic.alembic_checks import plugin

    original = compile_checks(
        [{"name": "ordered_span", "predicate": {"op": "ge", "args": [{"field": "end"}, {"field": "start"}]}}]
    )
    proposed = compile_checks(
        [{"name": "ordered_span", "predicate": {"op": "gt", "args": [{"field": "end"}, {"field": "start"}]}}]
    )
    with semantic_bare_engine.begin() as connection:
        connection.execute(CreateSchema("data"))
        original.create(connection)
        context = MigrationContext.configure(connection, opts={
            "include_schemas": True,
            "include_name": lambda name, kind, parents: name == "data" if kind == "schema" else True,
            "autogenerate_plugins": ["alembic.autogenerate.*", "alembic.ext.checkconstraint_byname", plugin.name],
        })
        unchanged = produce_migrations(context, original.metadata)
        assert unchanged.upgrade_ops is not None and unchanged.upgrade_ops.is_empty()
        changed = produce_migrations(context, proposed.metadata)
        assert changed.upgrade_ops is not None
        (table_changes,) = changed.upgrade_ops.ops
        assert isinstance(table_changes, ModifyTableOps)
        assert [type(operation) for operation in table_changes.ops] == [DropConstraintOp, CreateCheckConstraintOp]
        assert [operation.constraint_name for operation in table_changes.ops] == ["ordered_span", "ordered_span"]
