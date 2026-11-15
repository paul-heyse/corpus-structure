"""Actual registered command dispatch preserves semantic, database and defect outcomes."""

from __future__ import annotations

import json
from contextlib import contextmanager
from types import SimpleNamespace

import psycopg
import pytest
from sqlalchemy.exc import DBAPIError

from semantic.data_operation_kernel_support import STORAGE


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


def current_failure_command(command, directory):
    """Use current request DTOs; every taxonomy case must reach engine acquisition."""
    from corpus_structure.evaluate.selected_references import (
        ReferenceApplicability,
        SelectedReferenceEvaluationRequest,
    )
    from corpus_structure.orchestrate.source_request import SourceRunRequest
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_service import DemandRoot, NativeDemandRequest

    if command == "golden":
        request = NativeDemandRequest(
            project_id="project:failure",
            release_id="release:failure",
            runtime_id="runtime:failure",
            roots=(
                DemandRoot(
                    subject="subject:failure", original_source="original:failure", analyzed_scope={}
                ),
            ),
            targets=("reference.snapshot/declared",),
            execution_profile="execution:failure",
        )
        route = ("golden", "author")
    elif command == "eval":
        request = SelectedReferenceEvaluationRequest(
            project_id="project:failure",
            reference_demand_id="demand:reference",
            reference_product_id="product:reference",
            prediction_demand_id="demand:prediction",
            prediction_product_id="product:prediction",
            assignments={},
            applicability=ReferenceApplicability(
                reference_source_release_id="release:source",
                reference_source_cut_id="cut:source",
                prediction_release_id="release:prediction",
                original_source="original:failure",
                projection="projection:failure",
                selectors=(),
                basis="independently selected scope",
            ),
        )
        route = ("eval", "run")
    else:
        request = SourceRunRequest(
            project_id="project:failure",
            release_id="release:failure",
            runtime_id="runtime:failure",
            domain="toy",
            documents=("document:failure",),
        )
        route = ("regenerate", "--source-root", str(directory))
    path = directory / (command + ".json")
    path.write_bytes(json_bytes(request.model_dump(mode="python")))
    return (*route, "--request", str(path), "--json")


@pytest.mark.parametrize("command", ["golden", "eval", "regenerate"])
@pytest.mark.parametrize(
    "kind", ["refusal", "serialization", "fencing", "unknown", "bug", "cancel"]
)
def test_actual_command_failure_classification(cli, monkeypatch, tmp_path, command, kind):
    from corpus_structure.core.db.store import FENCING_CONSTRAINT
    from corpus_structure.evaluate.selected_references import SelectedReferenceRefusal
    from corpus_structure.orchestrate.source_request import SourceRequestError
    from corpus_structure.semantic import runtime

    if kind == "refusal":
        failure = (
            SelectedReferenceRefusal("reference selection refused")
            if command != "regenerate"
            else SourceRequestError("source selection refused")
        )
    elif kind == "conflict":
        from corpus_structure.semantic.refusals import OperationConflict

        failure = OperationConflict("native fence changed")
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
    elif kind == "key_bug":
        failure = KeyError("unexpected implementation lookup")
    else:
        failure = KeyboardInterrupt()

    acquired = []

    @contextmanager
    def unavailable(*args, **kwargs):
        acquired.append(kwargs["purpose"])
        raise failure
        yield

    monkeypatch.setattr(runtime, "open_runtime_engine", unavailable)
    monkeypatch.setenv("CORPUS_CI_RESULTS", str(tmp_path / "managed"))
    args = current_failure_command(command, tmp_path)
    result = cli(*args)
    assert acquired == ["write" if command == "regenerate" else "evaluate"], (
        result.output,
        result.exception,
    )
    assert result.exit_code != 0
    if kind in {"bug", "key_bug", "cancel"}:
        assert "refused:" not in result.output
        assert '"error"' not in result.output
        if kind in {"bug", "key_bug"}:
            assert result.exception is failure
        return
    error = json.loads(result.stdout)["error"]
    expected = type(failure).__name__ if kind in {"refusal", "conflict"} else "database_" + kind
    assert error["code"] == expected
    if kind not in {"refusal", "conflict"}:
        assert error["failure"]["phase"] == "unknown"
        assert error["failure"]["effects"] == "uncertain"
        assert (
            error["failure"]["sqlstate"]
            == {"serialization": "40001", "fencing": "23505", "unknown": "42703"}[kind]
        )
        assert error["remediation"] == "inspect_failure"


def test_regenerate_refuses_another_workflow_before_engine_acquisition(cli, tmp_path, monkeypatch):
    from corpus_structure.orchestrate.source_request import SourceRunRequest
    from corpus_structure.semantic import runtime
    from corpus_structure.semantic.data_operation_json import json_bytes

    def forbidden(*args, **kwargs):
        pytest.fail("incompatible source workflow must not acquire a database")

    monkeypatch.setattr(runtime, "open_runtime_engine", forbidden)
    request = SourceRunRequest(
        project_id="project:failure",
        release_id="release:failure",
        runtime_id="runtime:failure",
        workflow="characterize",
    )
    path = tmp_path / "source.json"
    path.write_bytes(json_bytes(request.model_dump(mode="python")))
    result = cli("regenerate", "--source-root", str(tmp_path), "--request", str(path), "--json")
    assert result.exit_code == 1, result.output
    assert json.loads(result.stdout)["error"]["code"] == "SourceRequestError"


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


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True)
def test_actual_database_check_preserves_native_admission_diagnostic(cli, ddo_kernel):
    """Current reader checks actual admitted contracts; posture tampering still refuses."""
    from hashlib import sha256

    from sqlalchemy import text

    from corpus_structure.semantic.native_definition_projection import (
        read_native_definition_projection,
    )
    from corpus_structure.settings import Settings

    kernel = ddo_kernel
    prepared = kernel.prepared
    settings = Settings(
        database={
            "url": kernel.engine.url.set(drivername="postgresql").render_as_string(
                hide_password=False
            )
        }
    )
    with kernel.purpose("read").begin() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT has_function_privilege(current_user,'sem.admit_data_operation_definitions(jsonb)','EXECUTE')"
                )
            )
            is False
        )
        assert (
            connection.scalar(
                text(
                    "SELECT has_table_privilege(current_user,'sem.data_operation_definition','SELECT')"
                )
            )
            is False
        )
    args = ("db", "check", "--release", prepared.release_id, "--json")
    checked = cli(*args, settings=lambda: settings)
    assert checked.exit_code == 0, checked.output
    report = json.loads(checked.stdout)
    assert report["model_digest"] == sha256(kernel.model.content).hexdigest()
    assert report["native_digest"] == read_native_definition_projection(prepared)["native_digest"]
    assert report["physical_id"] and report["physical_id"] != report["native_digest"]
    assert "execution_model_id" not in report
    try:
        with kernel.engine.begin() as connection:
            connection.exec_driver_sql(
                "GRANT EXECUTE ON FUNCTION ops.inspect_data_operation_release(jsonb) TO PUBLIC"
            )
        refused = cli(*args, settings=lambda: settings)
        assert refused.exit_code == 1, refused.output
        error = json.loads(refused.stdout)["error"]
        assert error["code"] == "ExecutionAdmissionError"
        assert "native execution deployment differs" in error["message"]
    finally:
        with kernel.engine.begin() as connection:
            connection.exec_driver_sql(
                "REVOKE EXECUTE ON FUNCTION ops.inspect_data_operation_release(jsonb) FROM PUBLIC"
            )


@pytest.mark.parametrize("route", ["schema", "db_check"])
@pytest.mark.parametrize("kind", ["serialization", "fencing", "unknown", "bug"])
def test_actual_archive_query_failure_reaches_cli_unchanged(
    cli, commit_db_engine, commit_reader_engine, route, kind
):
    from sqlalchemy import Engine, event

    from corpus_structure.core.db.store import FENCING_CONSTRAINT
    from corpus_structure.settings import Settings
    from semantic.releases_support import stage

    with commit_db_engine.begin() as conn:
        _, _, _, prepared = stage(conn)
    settings = Settings(
        database={
            "url": commit_reader_engine.url.set(drivername="postgresql").render_as_string(
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


def test_current_reference_owner_types_explicit_refusal_without_wrapping_unknown_helper(
    monkeypatch,
):
    from corpus_structure.evaluate import selected_references
    from corpus_structure.semantic.data_operation_service import DemandRoot, NativeDemandRequest

    request = NativeDemandRequest(
        project_id="p",
        release_id="r",
        runtime_id="runtime",
        roots=(DemandRoot(subject="subject", original_source="original", analyzed_scope={}),),
        targets=("unrelated",),
        execution_profile="execution",
    )
    with pytest.raises(selected_references.SelectedReferenceRefusal, match="dedicated snapshot"):
        selected_references.author_selected_references(object(), object(), request=request)
    failure = ValueError("unexpected implementation helper defect")

    def broken(prepared):
        raise failure

    monkeypatch.setattr(selected_references, "read_native_definition_projection", broken)
    with pytest.raises(ValueError) as caught:
        selected_references.author_selected_references(
            object(),
            object(),
            request=request.model_copy(update={"targets": ("reference.snapshot/declared",)}),
        )
    assert caught.value is failure


def test_cli_database_failure_is_not_semantic_refusal():
    import json

    import psycopg
    import typer
    from sqlalchemy.exc import OperationalError
    from typer.testing import CliRunner

    from corpus_structure.cli.failures import failure_boundary

    app = typer.Typer()

    @app.command()
    def command():
        with failure_boundary(True):
            raise OperationalError(None, None, psycopg.errors.SerializationFailure("retry"))

    result = CliRunner().invoke(app, [])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["code"] == "database_serialization"
