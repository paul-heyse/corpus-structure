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


def test_model_preview_delivers_preparation_error_when_report_schema_is_unavailable(
    cli, monkeypatch, tmp_path
):
    from corpus_structure.cli import failures
    from corpus_structure.schema import model_change
    from corpus_structure.semantic.types import Diagnostic, PreparationError

    original = PreparationError((Diagnostic("unknown_range", "Example", "range is missing"),))
    fallback = PreparationError((Diagnostic("unknown_range", "Report", "report is invalid"),))

    def refuse_preview(*args, **kwargs):
        raise original

    def refuse_report(*args, **kwargs):
        raise fallback

    monkeypatch.setattr(model_change, "prepare_preview", refuse_preview)
    monkeypatch.setattr(failures, "semantic_refusal_report", refuse_report)
    request = tmp_path / "change.yaml"
    request.write_text("{}\n")
    result = cli("model", "change", "preview", str(request), "--json")
    assert result.exit_code == 1
    error = json.loads(result.stdout)["error"]
    assert error["code"] == "PreparationError"
    assert [d["location"] for d in error["diagnostics"]] == ["Example"]


@pytest.mark.parametrize("command", ["golden", "eval", "regenerate"])
@pytest.mark.parametrize(
    "kind", ["refusal", "serialization", "fencing", "unknown", "bug", "cancel"]
)
def test_actual_command_failure_classification(cli, monkeypatch, tmp_path, command, kind):
    from corpus_structure.core.db.store import FENCING_CONSTRAINT
    from corpus_structure.semantic import regeneration, runtime

    if kind == "refusal":
        failure = (
            ReferenceError("reference selection refused")
            if command != "regenerate"
            else SemanticRefusal("pack refused")
        )
    elif kind == "serialization":
        failure = DBAPIError(None, None, psycopg.errors.SerializationFailure("serialization"))
    elif kind == "fencing":

        class Fenced(Exception):
            sqlstate = "23505"
            diag = SimpleNamespace(constraint_name=FENCING_CONSTRAINT)

        failure = DBAPIError(None, None, Fenced("fenced"))
    elif kind == "unknown":
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
    if kind != "refusal":
        assert error["failure"]["phase"] == "unknown"
        assert error["failure"]["effects"] == "uncertain"
        assert (
            error["failure"]["sqlstate"]
            == {"serialization": "40001", "fencing": "23505", "unknown": "42703"}[kind]
        )
        assert error["remediation"] == "inspect_failure"


def test_invalid_pack_is_a_typed_actual_regenerate_refusal(cli, tmp_path):
    result = cli(
        "regenerate", "--domain", "absent-fixture-pack", "--corpus", str(tmp_path), "--json"
    )
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["code"] == "PackInputError"


@pytest.mark.parametrize("route", ["schema", "db_check"])
@pytest.mark.parametrize(
    "kind", ["refusal", "serialization", "fencing", "unknown", "bug", "cancel"]
)
def test_schema_and_database_check_keep_failure_taxonomy(cli, monkeypatch, route, kind):
    from corpus_structure.core.db.store import FENCING_CONSTRAINT
    from corpus_structure.semantic import regeneration, runtime
    from corpus_structure.semantic.execution_admission import ExecutionAdmissionError
    from corpus_structure.semantic.types import (
        PreparationProfile,
        ResolvedDependencies,
        SourceBundle,
    )

    if kind == "refusal":
        failure = ExecutionAdmissionError("required effect profile is unsupported")
    elif kind == "serialization":
        failure = DBAPIError(None, None, psycopg.errors.SerializationFailure("serialization"))
    elif kind == "fencing":

        class Fenced(Exception):
            sqlstate = "23505"
            diag = SimpleNamespace(constraint_name=FENCING_CONSTRAINT)

        failure = DBAPIError(None, None, Fenced("fenced"))
    elif kind == "unknown":
        failure = DBAPIError(None, None, psycopg.errors.UndefinedColumn("broken SQL"))
    elif kind == "bug":
        failure = ValueError("unexpected program failure")
    else:
        failure = KeyboardInterrupt()

    bundle = SourceBundle("failure-fixture", ())
    dependencies = ResolvedDependencies()
    profile = PreparationProfile()
    calls = []

    def acquired(packs):
        assert [pack.name for pack in packs] == ["statistics"]
        return bundle, dependencies, profile

    def unavailable(source, supplied_dependencies, supplied_profile):
        assert source is bundle
        assert supplied_dependencies is dependencies
        assert supplied_profile is profile
        calls.append("prepare")
        raise failure

    @contextmanager
    def no_database(*args, **kwargs):
        calls.append("database")
        raise failure
        yield

    monkeypatch.setattr(regeneration, "acquire_packs", acquired)
    monkeypatch.setattr(regeneration, "prepare_release", unavailable)
    monkeypatch.setattr(runtime, "open_runtime_engine", no_database)
    args = (
        ("schema", "compile", "--json")
        if route == "schema"
        else ("db", "check", "--release", "release:fixture", "--json")
    )
    result = cli(*args)
    assert calls == ["prepare" if route == "schema" else "database"]
    assert result.exit_code != 0
    if kind in {"bug", "cancel"}:
        assert '"error"' not in result.stdout
        assert "refused:" not in result.output
        if kind == "bug":
            assert result.exception is failure
    else:
        code = "ExecutionAdmissionError" if kind == "refusal" else "database_" + kind
        error = json.loads(result.stdout)["error"]
        assert error["code"] == code
        if kind != "refusal":
            assert error["failure"]["phase"] == "unknown"
            assert error["failure"]["effects"] == "uncertain"
            assert (
                error["failure"]["sqlstate"]
                == {"serialization": "40001", "fencing": "23505", "unknown": "42703"}[kind]
            )
            assert error["remediation"] == "inspect_failure"


def test_schema_pack_name_is_native_grammar_before_acquisition(cli, monkeypatch):
    from corpus_structure.semantic import regeneration

    def forbidden(*args, **kwargs):
        pytest.fail("malformed native pack name acquired settings or pack inputs")

    monkeypatch.setattr(regeneration, "acquire_packs", forbidden)
    result = cli("schema", "compile", "--domain", "../outside", "--json", settings=forbidden)
    assert result.exit_code == 2, result.output
    assert "Invalid value for '--domain'" in result.output
    assert "../outside" in result.output
    assert '"error"' not in result.stdout


def test_schema_owned_selection_errors_are_typed(cli):
    result = cli("schema", "check", "--domain", "toy", "--release", "release:fixture", "--json")
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

    from .agent_scenarios import build_resubmission_case

    prepared, _, _, _ = build_resubmission_case(
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


@pytest.mark.parametrize("route", ["schema", "db_check"])
@pytest.mark.parametrize("kind", ["serialization", "fencing", "unknown", "bug"])
def test_actual_archive_query_failure_reaches_cli_unchanged(
    cli, semantic_db_engine, semantic_reader_engine, route, kind
):
    from sqlalchemy import Engine, event

    from corpus_structure.core.db.store import FENCING_CONSTRAINT
    from corpus_structure.settings import Settings

    from .test_releases import stage

    with semantic_db_engine.begin() as conn:
        _, _, _, prepared = stage(conn)
    settings = Settings(
        database={
            "url": semantic_reader_engine.url.set(drivername="postgresql").render_as_string(
                hide_password=False
            )
        }
    )
    if kind == "serialization":
        failure = DBAPIError(None, None, psycopg.errors.SerializationFailure("serialization"))
    elif kind == "fencing":

        class Fenced(Exception):
            sqlstate = "23505"
            diag = SimpleNamespace(constraint_name=FENCING_CONSTRAINT)

        failure = DBAPIError(None, None, Fenced("fenced"))
    elif kind == "unknown":
        failure = DBAPIError(None, None, psycopg.errors.UndefinedColumn("broken SQL"))
    else:
        failure = RuntimeError("unexpected archive program defect")
    called = []

    def fail_archived_input(conn, cursor, statement, parameters, context, executemany):
        if "FROM sem.input" in statement:
            called.append(statement)
            raise failure

    args = (
        ("schema", "check", "--release", prepared.release_id, "--json")
        if route == "schema"
        else ("db", "check", "--release", prepared.release_id, "--json")
    )
    event.listen(Engine, "before_cursor_execute", fail_archived_input)
    try:
        result = cli(*args, settings=lambda: settings)
    finally:
        event.remove(Engine, "before_cursor_execute", fail_archived_input)
    assert called, result.output
    assert result.exit_code != 0
    if kind == "bug":
        assert result.exception is failure
        assert '"error"' not in result.stdout
    else:
        error = json.loads(result.stdout)["error"]
        assert error["code"] == "database_" + kind
        assert error["failure"]["phase"] == "unknown"
        assert error["failure"]["effects"] == "uncertain"
        assert (
            error["failure"]["sqlstate"]
            == {"serialization": "40001", "fencing": "23505", "unknown": "42703"}[kind]
        )
        assert error["remediation"] == "inspect_failure"
