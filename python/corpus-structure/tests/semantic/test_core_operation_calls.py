"""Current Core source boundaries preserve physical meaning and actual algorithm ownership."""

from dataclasses import replace

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from corpus_structure.semantic import _source_admission_calls as calls
from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.native_call_sources import resolve_call_bindings
from corpus_structure.semantic.operation_value_types import NativeResultViolation
from corpus_structure.semantic.original_document_contracts import OPERATION, source_call_bindings
from corpus_structure.semantic.types import PreparationError
from semantic.original_document_support import prepared_source_admission


def test_core_registration_request_and_selected_result_are_independently_typed():
    prepared = prepared_source_admission()
    request = calls.prepare_source_document_registration(
        project_id=calls.ProjectId("project"),
        key="document",
        source_uri="uri",
        content_hash="hash",
        original_path="/retained",
        mime="text/plain",
        title=None,
        meta={"omitted-is-different": None, "empty": []},
        projection_context=prepared,
    )
    values = calls.values_source_document_registration_kb_document(request)
    assert values["title"] is None
    assert values["meta"] == {"omitted-is-different": None, "empty": []}
    result = calls.materialize_source_document_registration(
        (
            17,
            "project",
            "document",
            "uri",
            "hash",
            "/retained",
            "text/plain",
            None,
            '{"omitted-is-different":null,"empty":[]}',
        )
    )
    assert result.id == 17 and result.title is None
    assert result.decoded_json_fields(operation=OPERATION)["meta"] == values["meta"]
    with pytest.raises(ValidationError):
        vars(calls)["prepare_source_document_registration"](
            **{**values, "title": 17}, projection_context=prepared
        )
    with pytest.raises(NativeResultViolation):
        vars(calls)["materialize_source_document_registration"](
            (None, "project", "document", "uri", "hash", "/retained", "text/plain", None, "{}")
        )


def test_core_projections_resolve_actual_physical_columns_without_native_dispatch():
    statement = select(*calls.projection_source_document_registration)
    assert statement.get_final_froms() == [metadata.tables["kb.document"]]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "CAST(kb.document.meta AS TEXT) AS meta" in sql
    assert "kb.document.project_id" in sql
    assert "ops." not in sql


@pytest.mark.parametrize("mutation", ["wrong_owner", "native_parameter", "batch"])
def test_core_boundaries_refuse_native_identity_or_unowned_executor(mutation):
    original = next(
        call for _, call in source_call_bindings() if call.id == "source_document_registration"
    )
    if mutation == "wrong_owner":
        changed = replace(
            original, symbol="semantic.original_documents.read_original_document_bytes"
        )
    elif mutation == "native_parameter":
        changed = replace(
            original,
            parameters=(
                replace(original.parameters[0], native_parameter="p"),
                *original.parameters[1:],
            ),
        )
    else:
        changed = replace(original, batch=True)
    with pytest.raises(PreparationError):
        resolve_call_bindings(
            ((OPERATION, changed),),
            logical_sources={"linkml:types": metadata.info["physical_linkml_types"]},
            physical_sources=metadata.info["physical_sources"],
            core_owners={(OPERATION, original.id): original.symbol},
        )
