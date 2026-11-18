"""Independent PostgreSQL table/reader witnesses for typed catalog admission."""

import json

import psycopg
import pytest
from pglast import parse_plpgsql, parse_sql
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.native_admission_tables import (
    reader_catalog_checks,
    table_catalog_checks,
)
from corpus_structure.semantic.native_objects import execute_native_sql
from corpus_structure.semantic.native_program import Block, Local, Parameter, function, pg_type

_ACTORS = (
    "corpus_sem_writer",
    "corpus_sem_reader",
    "corpus_sem_evaluator",
    "corpus_sem_admitter",
)
_RELATION = "catalog_table_control.items"


@pytest.fixture
def table_catalog_control(infrastructure_rollback):
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA catalog_table_control")
    connection.exec_driver_sql(
        "CREATE TABLE catalog_table_control.parent (num integer,name text,PRIMARY KEY(num,name))"
    )
    connection.exec_driver_sql(
        "CREATE TABLE catalog_table_control.items ("
        "id bigint GENERATED ALWAYS AS IDENTITY,"
        "second integer NOT NULL DEFAULT 7,first text,"
        "computed integer GENERATED ALWAYS AS(second+1) STORED,"
        "PRIMARY KEY(id,second),"
        "CONSTRAINT parent_pair FOREIGN KEY(second,first) "
        "REFERENCES catalog_table_control.parent(num,name) MATCH FULL "
        "ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED)"
    )
    connection.exec_driver_sql(
        "GRANT SELECT ON catalog_table_control.items TO " + ",".join(_ACTORS)
    )
    expected = dict(
        tables=[
            dict(
                relation=_RELATION,
                owner=connection.scalar(text("SELECT current_user")),
                read_roles=list(_ACTORS),
                columns=[
                    dict(
                        name="computed",
                        type="integer",
                        not_null=False,
                        identity="",
                        generated="s",
                        default="(second + 1)",
                    ),
                    dict(
                        name="first",
                        type="text",
                        not_null=False,
                        identity="",
                        generated="",
                        default=None,
                    ),
                    dict(
                        name="id",
                        type="bigint",
                        not_null=True,
                        identity="a",
                        generated="",
                        default=None,
                    ),
                    dict(
                        name="second",
                        type="integer",
                        not_null=True,
                        identity="",
                        generated="",
                        default="7",
                    ),
                ],
                primary_key=["id", "second"],
                foreign_keys=[
                    dict(
                        name="parent_pair",
                        columns=["second", "first"],
                        target="catalog_table_control.parent",
                        remote_columns=["num", "name"],
                        on_update="c",
                        on_delete="r",
                        match="f",
                        deferrable=True,
                        deferred=True,
                        validated=True,
                    )
                ],
            )
        ],
        readers=[dict(relation=_RELATION, roles=["corpus_sem_reader"])],
    )
    for name, statements in (
        ("require_tables", table_catalog_checks()),
        ("require_readers", reader_catalog_checks()),
    ):
        source = function(
            "pg_temp",
            name,
            parameters=(Parameter("expected", pg_type("jsonb")),),
            returns=pg_type("void"),
            body=Block(statements, (Local("spec", pg_type("jsonb")),)),
            search_path=("pg_catalog", "pg_temp"),
        )
        assert parse_sql(source) and parse_plpgsql(source)
        execute_native_sql(connection, source)
    return connection, expected


def _require(connection, expected, *, readers=False):
    query = text(
        "SELECT pg_temp."
        + ("require_readers" if readers else "require_tables")
        + "(CAST(:expected AS jsonb))"
    )
    connection.execute(query, {"expected": json.dumps(expected)})


def _refuses(connection, expected, *, readers=False):
    message = (
        "required native read capability is unavailable"
        if readers
        else "native source frame projection differs"
    )
    with pytest.raises(DBAPIError, match=message) as error, connection.begin_nested():
        _require(connection, expected, readers=readers)
    assert isinstance(error.value.orig, psycopg.Error)
    assert error.value.orig.sqlstate == "23514"
    assert _RELATION in str(error.value)


def test_exact_table_column_key_privilege_and_reader_witnesses(table_catalog_control):
    connection, expected = table_catalog_control
    _require(connection, expected)
    _require(connection, expected, readers=True)
    del expected["tables"][0]["read_roles"]
    _require(connection, expected)


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "renamed"),
        ("type", "bigint"),
        ("not_null", True),
        ("identity", "a"),
        ("generated", "v"),
        ("default", "(second + 2)"),
    ],
)
def test_changed_column_witness_refuses(table_catalog_control, field, value):
    connection, expected = table_catalog_control
    expected["tables"][0]["columns"][0][field] = value
    _refuses(connection, expected)


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "another_key"),
        ("columns", ["first", "second"]),
        ("target", "catalog_table_control.another_parent"),
        ("remote_columns", ["name", "num"]),
        ("on_update", "a"),
        ("on_delete", "c"),
        ("match", "s"),
        ("deferrable", False),
        ("deferred", False),
        ("validated", False),
    ],
)
def test_changed_foreign_key_witness_refuses(table_catalog_control, field, value):
    connection, expected = table_catalog_control
    expected["tables"][0]["foreign_keys"][0][field] = value
    _refuses(connection, expected)


@pytest.mark.parametrize(
    "defect", ["owner", "column-order", "primary-key", "missing-fk", "extra-fk"]
)
def test_changed_table_inventory_refuses(table_catalog_control, defect):
    connection, expected = table_catalog_control
    declared = expected["tables"][0]
    if defect == "owner":
        declared["owner"] = "corpus_sem_publisher"
    elif defect == "column-order":
        declared["columns"].reverse()
    elif defect == "primary-key":
        declared["primary_key"].reverse()
    elif defect == "missing-fk":
        declared["foreign_keys"] = []
    else:
        declared["foreign_keys"].append({**declared["foreign_keys"][0], "name": "extra"})
    _refuses(connection, expected)


@pytest.mark.parametrize(
    "alteration",
    [
        "ALTER TABLE catalog_table_control.items ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE catalog_table_control.items FORCE ROW LEVEL SECURITY",
        "ALTER TABLE catalog_table_control.items SET UNLOGGED",
        "ALTER TABLE catalog_table_control.items ALTER COLUMN second SET DEFAULT 8",
        "GRANT INSERT ON catalog_table_control.items TO corpus_sem_writer",
        "GRANT UPDATE(first) ON catalog_table_control.items TO corpus_sem_reader",
        "REVOKE SELECT ON catalog_table_control.items FROM corpus_sem_evaluator",
        "GRANT SELECT ON catalog_table_control.items TO PUBLIC",
        "ALTER TABLE catalog_table_control.items ADD COLUMN extra integer",
        "ALTER TABLE catalog_table_control.items DROP CONSTRAINT parent_pair",
    ],
)
def test_changed_observed_table_or_privilege_refuses(table_catalog_control, alteration):
    connection, expected = table_catalog_control
    connection.exec_driver_sql(alteration)
    _refuses(connection, expected)


def test_column_select_cannot_replace_table_read_capability(table_catalog_control):
    connection, expected = table_catalog_control
    connection.exec_driver_sql(
        "REVOKE SELECT ON catalog_table_control.items FROM corpus_sem_reader"
    )
    connection.exec_driver_sql(
        "GRANT SELECT(first) ON catalog_table_control.items TO corpus_sem_reader"
    )
    _refuses(connection, expected)
    _refuses(connection, expected, readers=True)


def test_absent_primary_key_stays_null_and_empty_foreign_keys_stay_array(table_catalog_control):
    connection, expected = table_catalog_control
    connection.exec_driver_sql("CREATE TABLE catalog_table_control.unkeyed(value text)")
    declared = expected["tables"][0]
    declared.update(
        relation="catalog_table_control.unkeyed",
        read_roles=[],
        columns=[
            dict(name="value", type="text", not_null=False, identity="", generated="", default=None)
        ],
        foreign_keys=[],
    )
    # The original guard distinguishes a missing property (SQL NULL) from both
    # explicit JSON null and an empty key vector. Preserve that archive contract.
    del declared["primary_key"]
    _require(connection, expected)
    for absent_key in (None, []):
        declared["primary_key"] = absent_key
        with (
            pytest.raises(DBAPIError, match="native source frame projection differs"),
            connection.begin_nested(),
        ):
            _require(connection, expected)


def test_missing_relation_and_required_reader_refuse(table_catalog_control):
    connection, expected = table_catalog_control
    connection.exec_driver_sql("DROP TABLE catalog_table_control.items")
    _refuses(connection, expected)
    _refuses(connection, expected, readers=True)
