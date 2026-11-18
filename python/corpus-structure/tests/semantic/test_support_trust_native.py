"""Direct PostgreSQL controls for trust meaning, lock union and acquisition barriers."""

import json
from hashlib import sha256

import pytest
from pglast import ast
from sqlalchemy import Text, cast, column, func, select, text
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.metadata import metadata, table
from corpus_structure.semantic.native_objects import execute_native_sql
from corpus_structure.semantic.native_program import Parameter, pg_type, sql_function
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.support_trust_native import support_trust_native_sql
from semantic.data_operation_binding_support import (
    binding_native_connection as binding_native_connection,
)


@pytest.fixture
def support_control(binding_native_connection):
    connection = binding_native_connection
    execute_native_sql(connection, support_trust_native_sql(metadata))
    # These independent providers isolate canonical union/lock orchestration.
    # Their owning census and event implementations retain separate qualification.
    for family, completion_values in (
        ("record_grade", ["completion:z", "completion:a"]),
        ("record_fit", ["completion:a"]),
        ("operation_event", ["completion:z"]),
    ):
        for phase, values in (("dependency", []), ("completion", completion_values)):
            result_type = pg_type("text")
            result_type.setof = True
            rows = (
                func.unnest(array(values, type_=Text()))
                .table_valued(column("value", Text()))
                .render_derived(name="controlled_scope")
            )
            parameter = (
                Parameter("episode", pg_type("text"))
                if phase == "dependency"
                else Parameter("r", pg_type("ops", "data_request"))
            )
            execute_native_sql(
                connection,
                sql_function(
                    "ops",
                    "ddo_" + family + "_" + phase + "_scopes",
                    parameters=(parameter,),
                    returns=result_type,
                    body=select(rows.c.value),
                    volatility="stable",
                    search_path=("pg_catalog", "pg_temp"),
                ),
            )
    return connection


@pytest.mark.parametrize(
    ("project", "source", "expected"),
    [
        ("p", None, "project:" + sha256(b'["p"]').hexdigest()),
        ("p", "s", "source:" + sha256(b'["p","s"]').hexdigest()),
    ],
)
def test_scope_uses_distinct_project_and_source_context(support_control, project, source, expected):
    assert (
        support_control.scalar(
            text("SELECT ops.ddo_scope(:project,:source)"), {"project": project, "source": source}
        )
        == expected
    )


@pytest.mark.parametrize(("project", "source"), [(None, "s"), ("", "s"), ("p", "")])
def test_scope_refuses_missing_project_or_empty_source(support_control, project, source):
    with pytest.raises(DBAPIError, match="trust scope requires"), support_control.begin_nested():
        support_control.execute(
            text("SELECT ops.ddo_scope(:project,:source)"),
            {"project": project, "source": source},
        )


def test_trust_meaning_removes_only_zero_epochs_and_keeps_exact_large_integers(support_control):
    snapshot = '{"absent-equivalent":0,"zero-decimal":0.0,"changed":4.000,"large":9007199254740993}'
    actual = support_control.scalar(
        text("SELECT ops.ddo_trust_snapshot_meaning(CAST(:snapshot AS jsonb))"),
        {"snapshot": snapshot},
    )
    assert actual == {"changed": 4, "large": 9007199254740993}
    assert support_control.scalar(text("SELECT ops.ddo_trust_snapshot_meaning('{}')")) == {}


@pytest.mark.parametrize(
    "snapshot", ["null", "[]", '{"":0}', '{"a":"0"}', '{"a":null}', '{"a":-1}', '{"a":0.5}']
)
def test_trust_meaning_refuses_implicit_or_noninteger_epochs(support_control, snapshot):
    with pytest.raises(DBAPIError, match="trust snapshot requires"), support_control.begin_nested():
        support_control.execute(
            text("SELECT ops.ddo_trust_snapshot_meaning(CAST(:snapshot AS jsonb))"),
            {"snapshot": snapshot},
        )


@pytest.mark.parametrize(
    ("reference", "available", "expected"),
    [
        (
            {"derivation_id": "e1"},
            {"kind": "computation", "derivation_id": "e1", "admission_use_id": "u1"},
            True,
        ),
        (
            {"derivation_id": "e1", "admission_use_id": "u2"},
            {"kind": "computation", "derivation_id": "e1", "admission_use_id": "u1"},
            False,
        ),
        ({"derivation_id": "e2"}, {"kind": "computation", "derivation_id": "e1"}, False),
        (
            {"kind": "authored", "admission_id": "a1", "source_reference": "s1"},
            {"kind": "authored", "admission_id": "a1", "source_reference": "s1"},
            True,
        ),
        (
            {"kind": "original-source", "admission_id": "a1", "source_reference": "s1"},
            {"kind": "authored", "admission_id": "a1", "source_reference": "s1"},
            False,
        ),
        (
            {"kind": "authored", "admission_id": "a1", "source_reference": "s1"},
            {"kind": "authored", "admission_id": "a1", "source_reference": "s2"},
            False,
        ),
        ({"kind": "authored"}, {"kind": "authored"}, False),
    ],
)
def test_support_matches_actual_reference_kind_and_exact_identity(
    support_control, reference, available, expected
):
    assert (
        support_control.scalar(
            text(
                "SELECT ops.ddo_support_reference_matches(CAST(:reference AS jsonb),CAST(:row AS jsonb))"
            ),
            {
                "reference": json.dumps(reference),
                "row": json.dumps({"support_references": [available]}),
            },
        )
        is expected
    )


def test_support_lock_records_zero_then_reacquires_existing_epoch(support_control):
    expected_scope = "source:" + sha256(b'["p","s"]').hexdigest()
    call = text("SELECT ops.ddo_lock_support('p','s','[]')")
    assert support_control.scalar(call) == {expected_scope: 0}
    support_control.execute(table("ops.data_trust_scope").update().values(epoch=7))
    assert support_control.scalar(call) == {expected_scope: 7}


def test_completion_locks_one_sorted_deduplicated_union(support_control):
    support_control.exec_driver_sql(
        "CREATE TEMP TABLE support_scope_order(ordinal bigserial,scope text)"
    )
    support_control.exec_driver_sql(
        "CREATE FUNCTION pg_temp.capture_scope_insert() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$"
        "BEGIN INSERT INTO pg_temp.support_scope_order(scope) VALUES(NEW.scope); RETURN NEW; END$$"
    )
    support_control.exec_driver_sql(
        "CREATE TRIGGER capture_scope_insert AFTER INSERT ON ops.data_trust_scope "
        "FOR EACH ROW EXECUTE FUNCTION pg_temp.capture_scope_insert()"
    )
    expected_scope = "source:" + sha256(b'["p","s"]').hexdigest()
    actual = support_control.scalar(
        text(
            "SELECT ops.ddo_lock_completion_support(jsonb_populate_record(NULL::ops.data_request,"
            '\'{"project_id":"p","original_source":"s"}\'),\'{"support":[]}\')'
        )
    )
    assert actual == {"completion:a": 0, "completion:z": 0, expected_scope: 0}
    assert support_control.scalars(
        text("SELECT scope FROM pg_temp.support_scope_order ORDER BY ordinal")
    ).all() == ["completion:a", "completion:z", expected_scope]


def test_authorization_preserves_caller_purpose_and_rejects_unknown_universe(support_control):
    support_control.execute(
        text("SELECT ops.ddo_authorize('ordinary'),ops.ddo_authorize('source')")
    )
    with pytest.raises(DBAPIError, match="unknown data universe"), support_control.begin_nested():
        support_control.execute(text("SELECT ops.ddo_authorize('unrecognized')"))
    support_control.exec_driver_sql("GRANT USAGE ON SCHEMA ops TO corpus_sem_reader")
    support_control.exec_driver_sql(
        "GRANT EXECUTE ON FUNCTION ops.ddo_authorize(text) TO corpus_sem_reader"
    )
    with support_control.begin_nested():
        support_control.exec_driver_sql("SET LOCAL ROLE corpus_sem_reader")
        with (
            pytest.raises(DBAPIError, match="evaluator data requires evaluator purpose"),
            support_control.begin_nested(),
        ):
            support_control.execute(text("SELECT ops.ddo_authorize('evaluator')"))
        support_control.exec_driver_sql("RESET ROLE")


def test_read_acquisition_barrier_rejects_later_graph_writes_in_same_transaction(
    semantic_bare_engine,
):
    with semantic_bare_engine.begin() as connection:
        connection.exec_driver_sql("CREATE SCHEMA ops")
        connection.execute(
            CreateTable(table("ops.data_demand_read"), include_foreign_key_constraints=[])
        )
        programs = prepare_sql(
            support_trust_native_sql(metadata), source="acquisition-barrier-control"
        )
        for index, raw in enumerate(programs.statements):
            if (
                isinstance(raw.stmt, ast.CreateFunctionStmt)
                and raw.stmt.funcname
                and raw.stmt.funcname[-1].sval == "ddo_refuse_post_acquisition_graph_write"
            ):
                execute_native_sql(connection, programs.excerpt(index))
                break
        else:
            raise AssertionError("acquisition write barrier is absent")
        connection.exec_driver_sql("CREATE TEMP TABLE graph_write_control(value integer)")
        connection.exec_driver_sql(
            "CREATE TRIGGER acquisition_barrier BEFORE INSERT ON graph_write_control FOR EACH STATEMENT EXECUTE FUNCTION ops.ddo_refuse_post_acquisition_graph_write()"
        )
        connection.exec_driver_sql("INSERT INTO graph_write_control VALUES(1)")
        connection.execute(
            table("ops.data_demand_read")
            .insert()
            .values(
                id="read:control",
                demand_id="demand:control",
                read_snapshot="1:1:",
                frontier_at=func.clock_timestamp(),
                owner_xid=cast(func.pg_current_xact_id(), Text()),
                trust_snapshot={},
                scope={},
            )
        )
        with pytest.raises(DBAPIError, match="fresh transaction"), connection.begin_nested():
            connection.exec_driver_sql("INSERT INTO graph_write_control VALUES(2)")
        assert connection.scalars(text("SELECT value FROM graph_write_control")).all() == [1]
