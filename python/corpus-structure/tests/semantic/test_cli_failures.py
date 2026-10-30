"""Actual registered command dispatch preserves semantic, database and defect outcomes."""

from __future__ import annotations

import json
from contextlib import contextmanager
from types import SimpleNamespace

import psycopg
import pytest
from sqlalchemy.exc import DBAPIError

from corpus_structure.evaluate.semantic import ReferenceError
from corpus_structure.semantic.refusals import SemanticRefusal


@pytest.mark.parametrize("command", ["golden", "eval", "regenerate"])
@pytest.mark.parametrize("kind", ["refusal", "retry", "fencing", "defect", "bug", "cancel"])
def test_actual_command_failure_classification(cli, monkeypatch, tmp_path, command, kind):
    from corpus_structure.core.db.store import FENCING_CONSTRAINT
    from corpus_structure.semantic import regeneration, runtime

    if kind == "refusal":
        failure = (
            ReferenceError("reference selection refused")
            if command != "regenerate"
            else SemanticRefusal("pack refused")
        )
    elif kind == "retry":
        failure = DBAPIError(None, None, psycopg.errors.SerializationFailure("retry"))
    elif kind == "fencing":

        class Fenced(Exception):
            sqlstate = "23505"
            diag = SimpleNamespace(constraint_name=FENCING_CONSTRAINT)

        failure = DBAPIError(None, None, Fenced("fenced"))
    elif kind == "defect":
        failure = DBAPIError(None, None, psycopg.errors.UndefinedColumn("broken SQL"))
    elif kind == "bug":
        failure = ValueError("implementation defect")
    else:
        failure = KeyboardInterrupt()

    @contextmanager
    def unavailable(*args, **kwargs):
        raise failure
        yield

    def bad_pack(*args, **kwargs):
        raise failure

    monkeypatch.setattr(runtime, "open_runtime_engine", unavailable)
    monkeypatch.setattr(regeneration, "prepare_pack", bad_pack)
    args = {
        "golden": ("golden", "status", "--json"),
        "eval": ("eval", "run", "--run", "1", "--set-id", "1", "--json"),
        "regenerate": ("regenerate", "--domain", "toy", "--corpus", str(tmp_path), "--json"),
    }[command]
    result = cli(*args)
    assert result.exit_code != 0
    if kind in {"bug", "cancel"}:
        assert "refused:" not in result.output
        assert '"error"' not in result.output
        if kind == "bug":
            assert result.exception is failure
        return
    error = json.loads(result.stdout)["error"]
    expected = type(failure).__name__ if kind == "refusal" else "database_" + kind
    assert error["code"] == expected


def test_invalid_pack_is_a_typed_actual_regenerate_refusal(cli, tmp_path):
    result = cli(
        "regenerate", "--domain", "absent-fixture-pack", "--corpus", str(tmp_path), "--json"
    )
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["code"] == "PackInputError"


@pytest.mark.parametrize("route", ["schema", "db_check"])
@pytest.mark.parametrize("kind", ["refusal", "retry", "fencing", "defect", "bug", "cancel"])
def test_schema_and_database_check_keep_failure_taxonomy(cli, monkeypatch, route, kind):
    from corpus_structure.core.db.store import FENCING_CONSTRAINT
    from corpus_structure.semantic import regeneration, runtime
    from corpus_structure.semantic.execution_admission import ExecutionAdmissionError

    if kind == "refusal":
        failure = ExecutionAdmissionError("required effect profile is unsupported")
    elif kind == "retry":
        failure = DBAPIError(None, None, psycopg.errors.SerializationFailure("retry"))
    elif kind == "fencing":

        class Fenced(Exception):
            sqlstate = "23505"
            diag = SimpleNamespace(constraint_name=FENCING_CONSTRAINT)

        failure = DBAPIError(None, None, Fenced("fenced"))
    elif kind == "defect":
        failure = DBAPIError(None, None, psycopg.errors.UndefinedColumn("broken SQL"))
    elif kind == "bug":
        failure = ValueError("unexpected program failure")
    else:
        failure = KeyboardInterrupt()

    def unavailable(*args, **kwargs):
        raise failure

    @contextmanager
    def no_database(*args, **kwargs):
        raise failure
        yield

    monkeypatch.setattr(regeneration, "prepare_packs", unavailable)
    monkeypatch.setattr(runtime, "open_runtime_engine", no_database)
    args = (
        ("schema", "compile", "--json")
        if route == "schema"
        else ("db", "check", "--release", "release:fixture", "--json")
    )
    result = cli(*args)
    assert result.exit_code != 0
    if kind in {"bug", "cancel"}:
        assert '"error"' not in result.stdout
        assert "refused:" not in result.output
        if kind == "bug":
            assert result.exception is failure
    else:
        code = "ExecutionAdmissionError" if kind == "refusal" else "database_" + kind
        assert json.loads(result.stdout)["error"]["code"] == code


@pytest.mark.parametrize(
    "arguments",
    [
        ("compile", "--domain", "../outside"),
        ("check", "--domain", "toy", "--release", "release:fixture"),
    ],
)
def test_schema_owned_selection_errors_are_typed(cli, arguments):
    result = cli("schema", *arguments, "--json")
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["code"] == "SemanticRefusal"


def test_schema_derive_existing_directory_refuses_before_prepare(cli, tmp_path):
    result = cli("schema", "derive", "--out", str(tmp_path), "--json")
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["code"] == "SemanticRefusal"


def test_actual_database_check_preserves_native_admission_diagnostic(
    cli, semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    from corpus_structure.settings import Settings

    from .test_agent_resubmission import source_task

    prepared, _, _, _ = source_task(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", composed=True
    )
    settings = Settings(
        database={
            "url": semantic_reader_engine.url.set(drivername="postgresql").render_as_string(
                hide_password=False
            )
        }
    )
    args = ("db", "check", "--release", prepared.release_id, "--json")
    checked = cli(*args, settings=lambda: settings)
    assert checked.exit_code == 0, checked.output
    assert json.loads(checked.stdout)["execution_model_id"] == prepared.execution_model_id
    # Deliberately change an actual owned clone's posture; the native diagnostic must survive
    # the complete CLI route instead of becoming a generic SQLAlchemy or ValueError refusal.
    try:
        with semantic_db_engine.begin() as conn:
            conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
            conn.exec_driver_sql(
                "GRANT EXECUTE ON FUNCTION data.require_execution_release(text) TO PUBLIC"
            )
        refused = cli(*args, settings=lambda: settings)
        assert refused.exit_code == 1, refused.output
        error = json.loads(refused.stdout)["error"]
        assert error["code"] == "ExecutionAdmissionError"
        assert "native execution deployment differs" in error["message"]
    finally:
        with semantic_db_engine.begin() as conn:
            conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
            conn.exec_driver_sql(
                "REVOKE EXECUTE ON FUNCTION data.require_execution_release(text) FROM PUBLIC"
            )
