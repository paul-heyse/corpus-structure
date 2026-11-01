"""Frozen PG boundary and current forward admission, without retained-data compatibility."""

from __future__ import annotations

import ast as python_ast
import json
from hashlib import sha256
from pathlib import Path

import pytest
from alembic.script import ScriptDirectory
from pglast import ast, parse_sql
from sqlalchemy import text

from corpus_structure.semantic import execution_admission
from corpus_structure.semantic.migrations import (
    ALEMBIC_DIR,
    alembic_config,
    current_revision,
    head_revision,
    upgrade,
)
from corpus_structure.semantic.native_objects import (
    NativeAuthoringError,
    NativeObject,
    admit_native,
    native_owner,
)

REVISION = "semantic_pg_20261101"
PROJECTIONS = (
    "ops.read_published_input_batch(text,bigint,text,bigint,text,text)",
    "ops.read_published_relation_batch(text,bigint,text,bigint,text,text)",
    "ops.read_published_coverage_batch(text,bigint,text,bigint,text,text)",
    "ops.read_published_mapping_report_batch(text,bigint,text,bigint,text,text)",
)


def revision_module():
    return ScriptDirectory.from_config(alembic_config()).get_revision(REVISION).module


def frozen_state():
    revision = revision_module()
    return json.loads(
        revision._read_artifact(revision.NATIVE_STATE_FILE, revision.NATIVE_STATE_SHA256)
    )


def sql_bodies(sql):
    result = {}
    for raw in parse_sql(sql):
        statement = raw.stmt
        if isinstance(statement, ast.CreateFunctionStmt):
            options = {option.defname: option.arg for option in statement.options or ()}
            if "as" in options:
                name = ".".join(part.sval for part in statement.funcname or ())
                result[name] = options["as"][0].sval
    return result


def test_single_current_head_and_frozen_source_hashes():
    revision = revision_module()
    scripts = ScriptDirectory.from_config(alembic_config())
    head = head_revision()
    assert head is not None
    assert scripts.get_heads() == [head]
    assert REVISION in {r.revision for r in scripts.iterate_revisions(head, "base")}
    assert revision.down_revision == "semantic_0065"
    assert len(REVISION) <= 32
    state = frozen_state()
    assert state["version"] == 1
    assert state["predecessor"] == "semantic_0065"
    assert {item["identity"]["name"] for item in state["desired"]} == {
        "pdf_native_record_shape",
        "pdf_record_context_rows",
        "require_published_companion_pin",
        "read_published_input_batch",
        "read_published_relation_batch",
        "read_published_coverage_batch",
        "read_published_mapping_report_batch",
        "read_pdf_selected_source_events",
        "execution_contract_descriptor",
        "require_execution_release",
    }
    assert {item["after"]["identity"]["name"] for item in state["operations"]} == {
        item["identity"]["name"] for item in state["desired"]
    }
    admission = revision._read_artifact(
        revision.NATIVE_ADMISSION_FILE, revision.NATIVE_ADMISSION_SHA256
    )
    bodies = sql_bodies(admission.decode())
    assert (
        sha256(bodies["data.execution_contract_descriptor"].encode()).hexdigest()
        == sha256(
            next(
                item["catalog"]["body"]
                for item in state["desired"]
                if item["identity"]["name"] == "execution_contract_descriptor"
            ).encode()
        ).hexdigest()
    )
    assert (
        sha256(bodies["data.require_execution_release"].encode()).hexdigest()
        == execution_admission._REQUIRE_SHA256
    )
    enforcing = sql_bodies((ALEMBIC_DIR / "versions/semantic_0026_admission.sql").read_text())
    assert (
        sha256(enforcing["data.guard_execution_admission"].encode()).hexdigest()
        == execution_admission._GUARD_SHA256
    )
    source = python_ast.parse((ALEMBIC_DIR / "versions/0022_execution_admission.py").read_text())
    execute = next(
        node
        for node in python_ast.walk(source)
        if isinstance(node, python_ast.Call)
        and isinstance(node.func, python_ast.Attribute)
        and node.func.attr == "execute"
    )
    argument = execute.args[0]
    assert isinstance(argument, python_ast.Constant) and isinstance(argument.value, str)
    refusal = argument.value
    assert (
        sha256(sql_bodies(refusal)["data.guard_execution_admission"].encode()).hexdigest()
        == execution_admission._REFUSAL_SHA256
    )
    # Frozen deployment code registers the stable operation, never today's authoring generators.
    assert revision.__file__ is not None
    source = Path(revision.__file__).read_text()
    assert "native_candidate" not in source and "native_products" not in source
    assert "prepare_series_candidate" not in source
    guard = next(
        item for item in state["desired"] if item["identity"]["name"] == "require_execution_release"
    )
    assert guard["role_bindings"] == {"$migration_owner": "sem_namespace_owner"}
    assert ["$migration_owner", "EXECUTE", False] in guard["catalog"]["acl"]


def test_frozen_bytes_refuse_before_database_effects(tmp_path, monkeypatch):
    revision = revision_module()
    monkeypatch.setattr(revision, "__file__", str(tmp_path / "revision.py"))
    (tmp_path / revision.NATIVE_STATE_FILE).write_bytes(b"{}")
    with pytest.raises(RuntimeError, match="frozen PostgreSQL capability artifact differs"):
        revision.upgrade()


def test_fresh_head_admits_exact_native_properties(semantic_db_engine, semantic_admitter_engine):
    from corpus_structure.semantic.contracts import EXECUTION_COMPILER_VERSION
    from corpus_structure.semantic.native_candidate import current_native_state

    with semantic_db_engine.connect() as conn:
        assert current_revision(conn) == head_revision()
        desired = current_native_state(conn)
        assert desired is not None
        admit_native(conn, desired)
        execution_admission._verify_deployment_functions(conn)
        with semantic_admitter_engine.connect() as admitted:
            descriptor = admitted.scalar(text("SELECT data.execution_contract_descriptor()"))
        assert descriptor["execution_abi"] == EXECUTION_COMPILER_VERSION
        for signature in PROJECTIONS:
            row = conn.execute(
                text("""SELECT p.prosecdef, l.lanname,
                pg_get_userbyid(p.proowner), p.proconfig,
                pg_get_function_result(p.oid),
                has_function_privilege('corpus_sem_reader',p.oid,'EXECUTE'),
                EXISTS(SELECT FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a
                       WHERE a.grantee=0 AND a.privilege_type='EXECUTE')
                FROM pg_proc p JOIN pg_language l ON l.oid=p.prolang
                WHERE p.oid=to_regprocedure(:signature)"""),
                {"signature": signature},
            ).one()
            assert row[:4] == (
                True,
                "plpgsql",
                "corpus_sem_publisher",
                ["search_path=pg_catalog, pg_temp"],
            )
            assert row[4].startswith("TABLE(") and row[5:] == (True, False)
        with native_owner(conn, "corpus_sem_publisher"):
            conn.exec_driver_sql("ALTER FUNCTION " + PROJECTIONS[0] + " SECURITY INVOKER")
        with pytest.raises(NativeAuthoringError, match="native admission failed"):
            admit_native(conn, desired)
        conn.rollback()


def test_forward_objects_and_revision_share_caller_rollback(semantic_bare_engine):
    with semantic_bare_engine.begin() as conn:
        upgrade(conn, "semantic_0065")
        conn.exec_driver_sql(
            "CREATE FUNCTION public.pg_capability_unowned() RETURNS integer "
            "LANGUAGE sql AS $$ SELECT 41 $$"
        )
        before = conn.scalar(
            text(
                "SELECT prosrc FROM pg_proc "
                "WHERE oid='data.execution_contract_descriptor()'::regprocedure"
            )
        )
    with semantic_bare_engine.connect() as conn:
        transaction = conn.begin()
        upgrade(conn, REVISION)
        assert current_revision(conn) == REVISION
        assert conn.scalar(
            text("SELECT to_regprocedure(:signature) IS NOT NULL"), {"signature": PROJECTIONS[0]}
        )
        assert conn.scalar(text("SELECT public.pg_capability_unowned()")) == 41
        transaction.rollback()
    with semantic_bare_engine.begin() as conn:
        assert current_revision(conn) == "semantic_0065"
        assert conn.scalar(
            text("SELECT to_regprocedure(:signature) IS NULL"), {"signature": PROJECTIONS[0]}
        )
        assert (
            conn.scalar(
                text(
                    "SELECT prosrc FROM pg_proc "
                    "WHERE oid='data.execution_contract_descriptor()'::regprocedure"
                )
            )
            == before
        )
        assert conn.scalar(text("SELECT public.pg_capability_unowned()")) == 41
        upgrade(conn, REVISION)
        admit_native(
            conn, tuple(NativeObject.from_payload(item) for item in frozen_state()["desired"])
        )


def test_wrong_native_predecessor_refuses_fresh_forward_construction(semantic_bare_engine):
    with semantic_bare_engine.begin() as conn:
        upgrade(conn, "semantic_0065")
    with semantic_bare_engine.connect() as conn, conn.begin():
        with native_owner(conn, "corpus_sem_publisher"):
            conn.exec_driver_sql(
                "ALTER FUNCTION ops.pdf_native_record_shape(text,jsonb,jsonb) STRICT"
            )
        with pytest.raises(NativeAuthoringError, match="stale native before-state"):
            upgrade(conn, REVISION)
        conn.rollback()
    with semantic_bare_engine.connect() as conn:
        assert current_revision(conn) == "semantic_0065"
        assert conn.scalar(
            text("SELECT to_regprocedure(:signature) IS NULL"), {"signature": PROJECTIONS[0]}
        )


def test_regenerated_current_release_activates_and_writes(
    semantic_db_engine, semantic_writer_engine, semantic_admitter_engine
):
    from corpus_structure.semantic.contracts import (
        EXECUTION_COMPILER_VERSION,
        bound_execution_model,
        execution_payload,
    )
    from corpus_structure.semantic.publication import publish_batch
    from corpus_structure.semantic.releases import activate_release

    from .test_publication import batch, seed

    prepared = seed(semantic_db_engine, composed=True)
    model = bound_execution_model(prepared)
    payload = execution_payload(prepared)
    assert payload is not None
    assert json.loads(payload)["inputs"]["compiler_version"] == EXECUTION_COMPILER_VERSION
    model.require_operation("publish_arrow")
    with semantic_admitter_engine.begin() as conn:
        token = activate_release(
            conn, "p", prepared.release_id, expected_parent=None, expected_generation=0
        )
        assert token.release_id == prepared.release_id and token.generation == 1
    receipt = publish_batch(semantic_writer_engine, batch(release_id=prepared.release_id))
    assert receipt.data_revision == 1
    with semantic_db_engine.connect() as conn:
        assert conn.execute(
            text("SELECT text_value FROM data.typed_value WHERE kind='string'")
        ).scalars().all() == ["Straße"]
        assert conn.scalar(text("SELECT count(*) FROM data.fact")) == 1
        assert conn.scalar(text("SELECT count(*) FROM data.occurrence")) == 2


def test_current_head_reauthoring_is_stable_and_tracks_controlled_change(
    semantic_db_engine, monkeypatch
):
    from dataclasses import replace

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    from corpus_structure.semantic import native_candidate
    from corpus_structure.semantic.alembic_native import NativeTransitionOp

    with semantic_db_engine.connect() as conn:
        script, authoring = native_candidate.prepare_series_candidate(conn, owned_authoring=True)
        assert script.upgrade_ops is not None
        assert script.upgrade_ops.is_empty()
        admit_native(conn, authoring.desired)
        original = native_candidate.series_native_definitions

        def changed(connection, **kwargs):
            definitions = original(connection, **kwargs)
            return tuple(
                replace(
                    definition,
                    sql=definition.sql.replace("LANGUAGE plpgsql", "LANGUAGE plpgsql STRICT", 1),
                    source="controlled-strict-property",
                )
                if definition.identity.name == "pdf_native_record_shape"
                else definition
                for definition in definitions
            )

        monkeypatch.setattr(native_candidate, "series_native_definitions", changed)
        script, authoring = native_candidate.prepare_series_candidate(conn, owned_authoring=True)
        assert script.upgrade_ops is not None
        native = [
            operation
            for operation in script.upgrade_ops.ops
            if isinstance(operation, NativeTransitionOp)
        ]
        assert len(native) == len(script.upgrade_ops.ops)
        assert {operation.identity.name for operation in native} == {
            "pdf_native_record_shape",
            "execution_contract_descriptor",
        }
        operations = Operations(MigrationContext.configure(conn))
        for operation in script.upgrade_ops.ops:
            assert isinstance(operation, NativeTransitionOp)
            operations.invoke(operation)
        assert conn.scalar(
            text("""SELECT proisstrict FROM pg_proc
            WHERE oid='ops.pdf_native_record_shape(text,jsonb,jsonb)'::regprocedure""")
        )
        admit_native(conn, authoring.desired)
        conn.rollback()
        assert not conn.scalar(
            text("""SELECT proisstrict FROM pg_proc
            WHERE oid='ops.pdf_native_record_shape(text,jsonb,jsonb)'::regprocedure""")
        )
