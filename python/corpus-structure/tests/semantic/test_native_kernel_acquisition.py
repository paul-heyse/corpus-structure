"""Execution checks the release's recorded kernel without regenerating it."""

from dataclasses import replace
from unittest.mock import Mock

import pytest
from sqlalchemy import Connection

from corpus_structure.semantic import (
    data_operation_storage,
    execution_admission,
    native_protocol_authoring,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.types import PreparedArtifact, PreparedRelease

NATIVE_DIGEST = "a" * 64


def _release() -> PreparedRelease:
    return PreparedRelease(
        release_id="release:recorded",
        manifest=b"{}",
        definitions=(),
        vocabularies=(),
        registry_rows=(),
        queries=(),
        artifacts=(
            PreparedArtifact(
                "data_operation_native_definitions.json",
                canonical_bytes({"native_digest": NATIVE_DIGEST}),
            ),
        ),
        required_capabilities=(),
        diagnostics=(),
        _adapters=(),
    )


def test_acquisition_checks_recorded_digest_without_generation(monkeypatch):
    admission = Mock(return_value="frozen-physical-identity")
    generate = Mock(side_effect=AssertionError("execution must not generate native sources"))
    monkeypatch.setattr(execution_admission, "require_native_execution", admission)
    monkeypatch.setattr(native_protocol_authoring, "native_protocol_sources", generate)
    connection = Mock(spec=Connection)
    connection.scalar.return_value = {
        "version": "data-operation-native-v1",
        "source_digest": NATIVE_DIGEST,
    }
    prepared = _release()
    assert (
        data_operation_storage.require_data_operation_native(connection, prepared) == NATIVE_DIGEST
    )
    admission.assert_called_once_with(connection, prepared)

    connection.scalar.return_value["source_digest"] = "b" * 64
    with pytest.raises(ValueError, match="different native kernel"):
        data_operation_storage.require_data_operation_native(connection, prepared)
    generate.assert_not_called()


def test_acquisition_does_not_infer_a_missing_release_basis(monkeypatch):
    monkeypatch.setattr(execution_admission, "require_native_execution", Mock())
    connection = Mock(spec=Connection)
    prepared = replace(_release(), artifacts=())
    with pytest.raises(ValueError, match="exactly one native definition projection"):
        data_operation_storage.require_data_operation_native(connection, prepared)
    connection.scalar.assert_not_called()
