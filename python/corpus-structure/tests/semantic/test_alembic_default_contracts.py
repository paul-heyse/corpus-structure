"""Default comparison uses PostgreSQL binding without executing volatile values."""

import warnings

import pytest
from alembic.autogenerate import produce_migrations
from alembic.migration import MigrationContext
from alembic.operations.ops import AlterColumnOp, ModifyTableOps
from sqlalchemy import Column, Computed, Integer, MetaData, Table, Text, cast, column, func
from sqlalchemy.schema import CreateSchema

from corpus_structure.semantic.alembic_defaults import compare_default, plugin
from corpus_structure.semantic.native_authoring import _declared_physical_catalog
from corpus_structure.semantic.native_products import relation_descriptor


def declaration(*, increment=1):
    return Table(
        "sample", MetaData(), Column("invocation_key", Text, server_default=cast(func.gen_random_uuid(), Text)),
        Column("input", Integer), Column("computed", Integer, Computed(column("input") + increment, persisted=True)),
        schema="default_control",
    )


def compare(connection, relation, monkeypatch):
    catalog = _declared_physical_catalog(connection, relation.metadata)
    descriptor = relation_descriptor(relation)
    for item in descriptor["columns"]:
        item["default"] = (catalog.generated if item["generated"] else catalog.defaults).get(relation.fullname, {}).get(item["name"])
    context = MigrationContext.configure(connection, opts={
        "include_schemas": True,
        "include_name": lambda name, kind, parents: name == "default_control" if kind == "schema" else True,
        "autogenerate_plugins": ["alembic.autogenerate.*", plugin.name],
        "compare_server_default": compare_default,
        "declared_physical_columns": {relation.fullname: {item["name"]: item for item in descriptor["columns"]}},
    })
    def forbid_evaluation(*args, **kwargs):
        raise AssertionError("volatile defaults must be compared from bound catalog values")
    monkeypatch.setattr(context.impl, "compare_server_default", forbid_evaluation)
    return produce_migrations(context, relation.metadata)


def test_equivalent_volatile_and_computed_defaults_have_no_ddl_or_warning(semantic_bare_engine, monkeypatch):
    selected = declaration()
    with semantic_bare_engine.begin() as connection:
        connection.execute(CreateSchema("default_control"))
        selected.create(connection)
        with warnings.catch_warnings(record=True) as diagnostics:
            result = compare(connection, selected, monkeypatch)
        assert diagnostics == []
        assert result.upgrade_ops is not None and result.upgrade_ops.is_empty()


def test_changed_volatile_default_remains_an_actual_alter(semantic_bare_engine, monkeypatch):
    selected = declaration()
    with semantic_bare_engine.begin() as connection:
        connection.execute(CreateSchema("default_control"))
        selected.create(connection)
        connection.exec_driver_sql("ALTER TABLE default_control.sample ALTER COLUMN invocation_key SET DEFAULT 'changed'::text")
        result = compare(connection, selected, monkeypatch)
        assert result.upgrade_ops is not None
        (table_change,) = result.upgrade_ops.ops
        assert isinstance(table_change, ModifyTableOps)
        (change,) = table_change.ops
        assert isinstance(change, AlterColumnOp) and change.column_name == "invocation_key"
        assert change.modify_server_default is not False


def test_changed_computed_default_retains_unsupported_change_diagnostic(semantic_bare_engine, monkeypatch):
    with semantic_bare_engine.begin() as connection:
        connection.execute(CreateSchema("default_control"))
        declaration().create(connection)
        with pytest.warns(UserWarning, match="Computed default.*cannot be modified"):
            compare(connection, declaration(increment=2), monkeypatch)
