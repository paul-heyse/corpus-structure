"""Generated closure guards retain native replay, mutation refusal and activation CAS."""

import pytest
from pglast import ast, parse_sql
from pglast.stream import RawStream
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.closure_native import closure_native_sql
from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.native_objects import (
    definition_from_sql,
    execute_native_sql,
    prepare_native_authoring,
)
from semantic.releases_support import stage


def test_generated_closure_receipts_bind_and_keep_mutation_guards(commit_db_engine):
    with commit_db_engine.begin() as connection:
        _, _, _, prepared = stage(connection)
        release = prepared.release_id
        definitions = tuple(definition_from_sql(
            connection, RawStream()(item), source="generated-closure", owner="corpus_sem_publisher",
        ) for item in parse_sql(closure_native_sql(metadata)))
        ordinary = frozenset(item.identity for item in definitions if item.identity.name not in {
            "refuse_immutable_mutation", "guard_finalized_insert",
        })
        assert len(prepare_native_authoring(
            connection, tuple(item for item in definitions if item.identity in ordinary),
            owned_authoring=True, check_plpgsql=ordinary,
        ).desired) == 3
        for definition in definitions:
            execute_native_sql(connection, definition.sql)
        for name, parameters in (
            ("record_deployment_admission", {"r": release, "p": "physical:test", "d": "deployment:test", "k": "native", "c": b"exact control"}),
            ("record_sql_admission", {"r": release, "ik": "dependency", "n": "opaque", "p": "physical:test", "c": b"exact control"}),
        ):
            placeholders = ",".join(":" + key for key in parameters)
            statement = text("SELECT sem." + name + "(" + placeholders + ")")
            connection.execute(statement, parameters)
            connection.execute(statement, parameters)
            with pytest.raises(DBAPIError) as replay, connection.begin_nested():
                connection.execute(statement, {**parameters, "c": b"changed control"})
            assert getattr(replay.value.orig, "sqlstate", None) == "23505"
            with pytest.raises(DBAPIError) as missing, connection.begin_nested():
                connection.execute(statement, {**parameters, "r": "release:absent"})
            assert getattr(missing.value.orig, "sqlstate", None) == "P0001"
        with pytest.raises(DBAPIError) as immutable, connection.begin_nested():
            connection.execute(text("UPDATE sem.release SET profile=profile WHERE release_id=:r"), {"r": release})
        assert getattr(immutable.value.orig, "sqlstate", None) == "23514"
        assert "immutable semantic content: sem.release UPDATE" in str(immutable.value)
        with pytest.raises(DBAPIError) as intrinsic, connection.begin_nested():
            connection.execute(text("INSERT INTO sem.input VALUES(:r,'extra','extra','x'::bytea,'wrong')"), {"r": release})
        assert getattr(intrinsic.value.orig, "sqlstate", None) == "23514"
        assert "finalized release cannot acquire intrinsic meaning: " + release in str(intrinsic.value)


def test_closure_capture_includes_exact_compiler_and_generated_effect():
    from corpus_structure.semantic.target_installation import capture_target_installation

    captured = capture_target_installation(metadata)
    sources = {source.name: source.content for source in captured.authoring_inputs.sources}
    assert sources["authoring/closure-native.sql"] == closure_native_sql(captured.metadata).encode()
    assert b"def closure_native_sql" in sources["authoring/closure-native.py"]
    declarations = parse_sql(sources["authoring/closure-native.sql"].decode())
    assert len(declarations) == 5
    assert all(isinstance(item.stmt, ast.CreateFunctionStmt) for item in declarations)
