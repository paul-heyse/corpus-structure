"""Read-only correspondence and native materialization have distinct failure ownership.

Controlled connections establish Python boundaries; actual role/custody controls are native tests.
"""

from unittest.mock import MagicMock

import pytest
from sqlalchemy import Connection

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.operation_value_types import NativeResultViolation


@pytest.mark.parametrize("encoded", [None, "{", "{}", '{"payload":{}}', '{"payload":{"release_id":"r","model_digest":"wrong","native_digest":"' + 'b'*64 + '"}}'])
def test_only_executed_result_decode_and_schema_failures_become_native_result_violation(encoded):
    connection = MagicMock(spec=Connection)
    connection.scalar.return_value = encoded
    with pytest.raises(NativeResultViolation) as caught:
        DataOperationStorage(connection).inspect_data_operation_release({"release_id": "release:one"})
    assert caught.value.operation == "data.inspect_data_operation_release"
    assert caught.value.result_class == "urn:corpus:data-wire:inspect_data_operation_release_result"
    assert caught.value.original is not None
    connection.scalar.assert_called_once()


@pytest.mark.parametrize("failure", [ValueError("statement defect"), KeyError("implementation lookup")])
def test_native_statement_and_acquisition_defects_retain_their_exact_identity(failure):
    connection = MagicMock(spec=Connection)
    connection.scalar.side_effect = failure
    with pytest.raises(type(failure)) as caught:
        DataOperationStorage(connection).inspect_data_operation_release({"release_id": "release:one"})
    assert caught.value is failure and not isinstance(caught.value, NativeResultViolation)


def test_invalid_request_is_not_misreported_as_an_executed_native_result():
    connection = MagicMock(spec=Connection)
    with pytest.raises(ValueError) as caught:
        DataOperationStorage(connection)._invoke("inspect_data_operation_release", {"release_id": "r", "unknown": True})
    assert not isinstance(caught.value, NativeResultViolation)
    connection.scalar.assert_not_called()


@pytest.fixture(scope="module")
def inspected_prepared(tmp_path_factory):
    from semantic.data_operation_kernel_support import STORAGE, prepare_kernel
    return prepare_kernel(STORAGE, directory=tmp_path_factory.mktemp("inspected-contract")).prepared


@pytest.mark.parametrize("mismatch", [False, True])
def test_inspection_checks_actual_attestation_without_calling_admission(inspected_prepared, monkeypatch, mismatch):
    from corpus_structure.semantic import data_operation_admission, execution_admission
    from corpus_structure.semantic.native_definition_projection import read_native_definition_projection
    projection = read_native_definition_projection(inspected_prepared)
    attestation = dict(release_id=inspected_prepared.release_id,
        model_digest=projection["model_digest"], native_digest=projection["native_digest"])
    connection = MagicMock(spec=Connection)
    connection.scalar.return_value = json_bytes({"payload": {**attestation, **({"model_digest": "0"*64} if mismatch else {})}}).decode()
    acquired = []
    def guard(connection, prepared):
        acquired.append(prepared.release_id)
        return "physical:actual-installed-contract"
    def forbidden(*args, **kwargs):
        pytest.fail("read-only inspection must not admit definitions")
    monkeypatch.setattr(execution_admission, "require_native_execution", guard)
    monkeypatch.setattr(data_operation_admission, "admit_data_operation_release", forbidden)
    if mismatch:
        with pytest.raises(execution_admission.ExecutionAdmissionError, match="another release or contract"):
            data_operation_admission.inspect_data_operation_release(connection, inspected_prepared)
    else:
        physical, result = data_operation_admission.inspect_data_operation_release(connection, inspected_prepared)
        assert physical == "physical:actual-installed-contract" and result == attestation
    assert acquired == [inspected_prepared.release_id]
    assert "ops.inspect_data_operation_release" in str(connection.scalar.call_args.args[0])


def test_malformed_native_inspection_carries_the_real_release_and_model_context(inspected_prepared, monkeypatch):
    from corpus_structure.semantic import data_operation_admission, execution_admission
    from corpus_structure.semantic.refusals import failure_context
    connection = MagicMock(spec=Connection)
    connection.scalar.return_value = '{"payload":{}}'
    monkeypatch.setattr(execution_admission, "require_native_execution", lambda *args: "physical:actual")
    with pytest.raises(NativeResultViolation) as caught:
        data_operation_admission.inspect_data_operation_release(connection, inspected_prepared)
    context = failure_context(caught.value)
    from hashlib import sha256
    assert context.release_id == inspected_prepared.release_id
    assert context.model_id == sha256(data_operation_admission.bound_data_operation_model(inspected_prepared).content).hexdigest()
    assert context.operation == "data.inspect_data_operation_release"


def test_actual_db_check_adapter_uses_read_inspection_and_reports_current_contract_ids(cli, inspected_prepared, monkeypatch):
    from contextlib import contextmanager
    from corpus_structure.semantic import data_operation_admission, execution_admission, query, releases, runtime, storage_target
    from corpus_structure.semantic.native_definition_projection import read_native_definition_projection
    from corpus_structure.semantic.data_operation_json import json_loads

    connection = MagicMock(spec=Connection)
    selected_engine = object()
    received = []
    @contextmanager
    def engine(settings, name, *, purpose):
        assert purpose == "read"
        yield selected_engine
    @contextmanager
    def snapshot(engine):
        assert engine is selected_engine
        yield connection
    def forbidden(*args, **kwargs):
        pytest.fail("db check must not admit an execution release")
    projection = read_native_definition_projection(inspected_prepared)
    attestation = dict(release_id=inspected_prepared.release_id, model_digest=projection["model_digest"], native_digest=projection["native_digest"])
    def inspect(conn, prepared):
        received.append((conn, prepared))
        return "physical:installed", attestation
    target = storage_target.StorageTarget(database="controlled", database_oid=3, system_identifier="actual-target-control",
        host="localhost", port=5434, purpose="read")
    monkeypatch.setattr(runtime, "open_runtime_engine", engine)
    monkeypatch.setattr(query, "read_snapshot", snapshot)
    monkeypatch.setattr(releases, "open_release", lambda conn, release: inspected_prepared)
    monkeypatch.setattr(storage_target, "acquired_target", lambda conn, *, purpose: target)
    monkeypatch.setattr(execution_admission, "admit_execution_release", forbidden)
    monkeypatch.setattr(data_operation_admission, "inspect_data_operation_release", inspect)
    response = cli("db", "check", "--release", inspected_prepared.release_id, "--json")
    assert response.exit_code == 0, (response.output, response.exception)
    assert json_loads(response.stdout) == {**attestation, "physical_id": "physical:installed", "target": "development", "acquired": target.model_dump()}
    assert received == [(connection, inspected_prepared)]


@pytest.mark.parametrize("state", ["23514", "40001", "23505", "42703"])
def test_inspection_translates_only_its_owned_correspondence_constraint(inspected_prepared, monkeypatch, state):
    import psycopg
    from sqlalchemy.exc import DBAPIError
    from corpus_structure.semantic import data_operation_admission, execution_admission
    failures = {"23514": psycopg.errors.CheckViolation, "40001": psycopg.errors.SerializationFailure,
        "23505": psycopg.errors.UniqueViolation, "42703": psycopg.errors.UndefinedColumn}
    failure = DBAPIError(None, None, failures[state]("read-only inspection admitted rowset differs"))
    connection = MagicMock(spec=Connection)
    connection.scalar.side_effect = failure
    monkeypatch.setattr(execution_admission, "require_native_execution", lambda *args: "physical:actual")
    expected = execution_admission.ExecutionAdmissionError if state == "23514" else DBAPIError
    with pytest.raises(expected) as caught:
        data_operation_admission.inspect_data_operation_release(connection, inspected_prepared)
    if state == "23514":
        assert caught.value.__cause__ is failure
    else:
        assert caught.value is failure
