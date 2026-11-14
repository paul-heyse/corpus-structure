"""Independent expectations for frozen privilege policy, authoring and custody."""
import json
from uuid import uuid4

import pytest
from alembic.autogenerate import render_python_code
from alembic.migration import MigrationContext
from alembic.operations import Operations, ops
from sqlalchemy import Column, Integer, MetaData, Table, text

from corpus_structure.semantic.alembic_privileges import (
    OwnedOperationsOp, PrivilegeTransitionOp, admit_privileges,
    native_operation_payloads, operation_record, privilege_operations, table_policy,
)
from corpus_structure.semantic.native_objects import NativeAuthoringError
from corpus_structure.schema.model_explanation import explain_native_operations, explanation_from_native


def test_unchanged_policy_and_legacy_normalization_remain_distinct():
    md = MetaData()
    relation = Table("sample", md, Column("id", Integer), schema="ops", info={"read_roles": ["corpus_sem_reader"]})
    expected = {"kind": "table", "name": "ops.sample", "owner": "corpus_sem_publisher", "acl": [("corpus_sem_reader", "SELECT", False)], "columns": []}
    assert table_policy(relation) == expected
    assert privilege_operations([expected], [expected], []) == []
    transition, = privilege_operations([], [expected], [{"relation": "ops.sample", "owner": "corpus_sem_publisher", "read_roles": ["corpus_sem_reader"]}])
    assert transition.before is not None
    assert "unrecorded" in transition.before
    assert transition.before["unrecorded"] == ["acl", "columns"]
    with pytest.raises(NativeAuthoringError, match="cannot be reversed"):
        transition.reverse()
    changed = dict(expected, acl=[])
    forward, = privilege_operations([expected], [changed], [])
    assert forward.reverse().payload()["after"] == expected


def test_tagged_artifact_inspection_includes_normalization_and_unknown_before():
    policy = {"kind": "schema", "name": "ops", "owner": None, "acl": [], "columns": []}
    operation = PrivilegeTransitionOp(None, policy, normalization=True)
    state = {"version": 2, "operations": [operation_record(operation)], "desired": [], "privileges": [policy]}
    raw = json.dumps(state).encode()
    assert native_operation_payloads(state) == ()
    page = explain_native_operations(raw, "candidate")
    assert page.total == 1 and page.items[0].action == "normalize"
    assert page.items[0].before_acl is None and page.items[0].after_acl == []
    assert explanation_from_native(raw).diagnostics[0]["code"] == "declared-privilege-transition"
    state["operations"][0]["kind"] = "unknown"
    with pytest.raises(NativeAuthoringError):
        native_operation_payloads(state)


def test_owned_ddl_rendering_preserves_upgrade_caller_without_ast_repair():
    operations = ops.UpgradeOps([OwnedOperationsOp("corpus_sem_publisher", [ops.AddColumnOp("sample", Column("n", Integer), schema="ops")])])
    rendered = render_python_code(operations)
    assert "with alembic_privileges.owned_operation(op.get_bind(), 'corpus_sem_publisher'):" in rendered
    assert "op.add_column('sample'" in rendered
    assert "SET LOCAL ROLE" not in rendered
    compile("def upgrade():\n" + rendered, "candidate.py", "exec")


def test_named_data_steps_compile_explicit_columns_and_refuse_unknown():
    from corpus_structure.semantic.metadata import metadata
    from corpus_structure.semantic.native_data_steps import build_data_step
    from sqlalchemy.dialects.postgresql import dialect
    sql = str(build_data_step("characterization-source-scope", metadata).compile(dialect=dialect(), compile_kwargs={"literal_binds": True}))
    assert "INSERT INTO kb.characterization_source_scope (task_id, product_key, content_digest, source_view_id, body)" in sql
    assert "ON CONFLICT DO NOTHING" in sql
    from pydantic import ValidationError
    from corpus_structure.schema.model_change import ChangeRequest
    with pytest.raises(ValidationError):
        ChangeRequest.model_validate({"data_steps": ["arbitrary.module.function"]})


def test_live_normalization_exact_transition_stale_before_and_role_restore(semantic_bare_engine):
    schema = "privilege_" + uuid4().hex[:12]
    with semantic_bare_engine.begin() as conn:
        original = conn.scalar(text("SELECT current_user"))
        conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        conn.exec_driver_sql(f'GRANT USAGE,CREATE ON SCHEMA "{schema}" TO corpus_sem_publisher')
        conn.exec_driver_sql(f'CREATE TABLE "{schema}".sample (id integer)')
        conn.exec_driver_sql(f'ALTER TABLE "{schema}".sample OWNER TO corpus_sem_publisher')
        conn.exec_driver_sql(f'GRANT SELECT (id) ON "{schema}".sample TO PUBLIC')
        policy = {"kind": "table", "name": schema + ".sample", "owner": "corpus_sem_publisher", "acl": [("corpus_sem_reader", "SELECT", False)], "columns": []}
        operations = Operations(MigrationContext.configure(conn))
        operations.invoke(PrivilegeTransitionOp(None, policy, normalization=True))
        admit_privileges(conn, [policy])
        assert conn.scalar(text("SELECT current_user")) == original
        assert conn.scalar(text("SELECT has_table_privilege('corpus_sem_reader',:relation,'SELECT')"), {"relation": policy["name"]})
        changed = dict(policy, acl=[])
        operations.invoke(PrivilegeTransitionOp(policy, changed))
        admit_privileges(conn, [changed])
        from corpus_structure.semantic.alembic_privileges import admission_comparison_sql
        from corpus_structure.semantic.identity import canonical_bytes
        expected = canonical_bytes({"privileges": [changed]}).decode().replace("'", "''")
        conn.exec_driver_sql("DO $test$ DECLARE expected jsonb := '" + expected + "'::jsonb; BEGIN " + admission_comparison_sql() + " END $test$;")
        with pytest.raises(NativeAuthoringError, match="stale privilege before-state"):
            operations.invoke(PrivilegeTransitionOp(policy, changed))
        conn.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')


def test_live_schema_normalization_and_frozen_guard_reject_grant_options(semantic_bare_engine):
    from sqlalchemy.exc import DBAPIError
    from corpus_structure.semantic.alembic_privileges import admission_comparison_sql
    from corpus_structure.semantic.identity import canonical_bytes
    schema = "schema_acl_" + uuid4().hex[:10]
    with semantic_bare_engine.begin() as conn:
        conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        conn.exec_driver_sql(f'GRANT USAGE ON SCHEMA "{schema}" TO PUBLIC')
        conn.exec_driver_sql(f'GRANT CREATE ON SCHEMA "{schema}" TO corpus_sem_reader')
        policy = {"kind": "schema", "name": schema, "owner": None,
                  "acl": [["corpus_sem_publisher", "CREATE", False], ["corpus_sem_publisher", "USAGE", False], ["corpus_sem_reader", "USAGE", False]], "columns": []}
        Operations(MigrationContext.configure(conn)).invoke(PrivilegeTransitionOp(None, policy, normalization=True))
        admit_privileges(conn, [policy])
        expected = canonical_bytes({"privileges": [policy]}).decode().replace("'", "''")
        guard = "DO $test$ DECLARE expected jsonb := '" + expected + "'::jsonb; BEGIN " + admission_comparison_sql() + " END $test$;"
        conn.exec_driver_sql(guard)
        with conn.begin_nested():
            conn.exec_driver_sql(f'GRANT USAGE ON SCHEMA "{schema}" TO corpus_sem_reader WITH GRANT OPTION')
            with pytest.raises(DBAPIError, match="privilege policy differs"), conn.begin_nested():
                conn.exec_driver_sql(guard)
        conn.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')


@pytest.mark.parametrize("drift", ["reader-owner", "fitter-create"])
def test_schema_policy_refuses_effective_create_despite_owner_acl_filter(semantic_bare_engine, drift):
    from sqlalchemy.exc import DBAPIError
    from corpus_structure.semantic.alembic_privileges import admission_comparison_sql
    from corpus_structure.semantic.identity import canonical_bytes
    schema = "schema_owner_" + uuid4().hex[:10]
    policy = {"kind": "schema", "name": schema, "owner": None,
              "acl": [["corpus_sem_publisher", "CREATE", False], ["corpus_sem_publisher", "USAGE", False], ["corpus_sem_reader", "USAGE", False]], "columns": []}
    with semantic_bare_engine.begin() as conn:
        conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        Operations(MigrationContext.configure(conn)).invoke(PrivilegeTransitionOp(None, policy, normalization=True))
        expected = canonical_bytes({"privileges": [policy]}).decode().replace("'", "''")
        guard = "DO $test$ DECLARE expected jsonb := '" + expected + "'::jsonb; BEGIN " + admission_comparison_sql() + " END $test$;"
        conn.exec_driver_sql(guard)
        with conn.begin_nested() as drift_scope:
            if drift == "reader-owner":
                conn.exec_driver_sql(f'ALTER SCHEMA "{schema}" OWNER TO corpus_sem_reader')
            else:
                conn.exec_driver_sql(f'GRANT CREATE ON SCHEMA "{schema}" TO corpus_sem_fitter')
            with pytest.raises(NativeAuthoringError, match="effective schema CREATE"):
                admit_privileges(conn, [policy])
            with pytest.raises(DBAPIError, match="effective schema CREATE"), conn.begin_nested():
                conn.exec_driver_sql(guard)
            drift_scope.rollback()
        admit_privileges(conn, [policy])
        conn.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')


def test_rendered_candidate_executes_exact_upgrade_before_admission_and_rolls_back(semantic_bare_engine, monkeypatch):
    from types import SimpleNamespace
    from corpus_structure.semantic import native_candidate, native_objects
    from corpus_structure.semantic.alembic_privileges import admit_privileges as real_admit
    name = "rendered_" + uuid4().hex[:10]
    source = "from alembic import op\ndef upgrade():\n    op.execute('CREATE TABLE public." + name + " (id integer)')\n"
    observed = []
    def native_check(connection, desired):
        assert desired == ()
        assert connection.scalar(text("SELECT to_regclass(:name)"), {"name": "public." + name}) is not None
        observed.append("native")
    def catalog_check(connection, admission):
        assert admission == "frozen"
        assert observed == ["native"]
        assert connection.scalar(text("SELECT to_regclass(:name)"), {"name": "public." + name}) is not None
        real_admit(connection, [])
        observed.append("catalog")
    monkeypatch.setattr(native_objects, "admit_native", native_check)
    monkeypatch.setattr(native_candidate, "verify_frozen_catalog", catalog_check)
    with semantic_bare_engine.begin() as conn:
        role = conn.scalar(text("SELECT current_user"))
        native_candidate.verify_rendered_candidate(conn, source, SimpleNamespace(desired=()), (), "frozen")
        assert observed == ["native", "catalog"]
        assert conn.scalar(text("SELECT to_regclass(:name)"), {"name": "public." + name}) is None
        assert conn.scalar(text("SELECT current_user")) == role


def test_schema_normalization_orders_explicit_delegation_leaves_without_cascade(semantic_bare_engine):
    from corpus_structure.semantic.native_objects import native_owner
    schema = "acl_delegated_" + uuid4().hex[:10]
    policy = {"kind": "schema", "name": schema, "owner": None,
              "acl": [("corpus_sem_publisher", "CREATE", False), ("corpus_sem_publisher", "USAGE", False), ("corpus_sem_reader", "USAGE", False)], "columns": []}
    with semantic_bare_engine.begin() as conn:
        conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        conn.exec_driver_sql(f'GRANT USAGE,CREATE ON SCHEMA "{schema}" TO corpus_sem_publisher WITH GRANT OPTION')
        with native_owner(conn, "corpus_sem_publisher"):
            conn.exec_driver_sql(f'GRANT USAGE ON SCHEMA "{schema}" TO corpus_sem_reader')
        Operations(MigrationContext.configure(conn)).invoke(PrivilegeTransitionOp(None, policy, normalization=True))
        admit_privileges(conn, [policy])
        conn.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')


def test_rendered_candidate_failure_exposes_safe_site_without_sql_or_payload(semantic_bare_engine):
    from types import SimpleNamespace
    from corpus_structure.semantic.native_candidate import verify_rendered_candidate
    source = "from alembic import op\ndef upgrade():\n    op.execute(\"SELECT 'private-payload-sentinel'::integer\")\n"
    with semantic_bare_engine.begin() as conn:
        with pytest.raises(NativeAuthoringError, match="SQLSTATE 22P02") as failure:
            verify_rendered_candidate(conn, source, SimpleNamespace(desired=()), (), "unreachable")
        assert failure.value.authoring_context == {"operation_kind": "execute", "sqlstate": "22P02", "source_line": 3}
        assert "private-payload-sentinel" not in str(failure.value)
        assert conn.scalar(text("SELECT 1")) == 1
