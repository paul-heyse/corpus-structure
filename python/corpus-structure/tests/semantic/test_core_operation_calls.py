"""Fixed Core boundaries preserve physical meaning and named algorithm ownership."""

from dataclasses import replace
from functools import lru_cache

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from corpus_structure.semantic import _operation_calls as calls
from corpus_structure.semantic.contracts import compile_execution_model, trusted_execution_inputs
from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.operation_call_generation import validate_call_bindings
from corpus_structure.semantic.operation_value_types import NativeResultViolation
from corpus_structure.semantic.types import PreparationError


@lru_cache(maxsize=1)
def model():
    return compile_execution_model(trusted_execution_inputs())


def test_core_registration_request_and_selected_result_are_independently_typed():
    request = calls.prepare_document_registration(
        project_id=calls.ProjectId("project"),
        key="document",
        source_uri="uri",
        content_hash="hash",
        original_path="/retained",
        mime="text/plain",
        title=None,
        meta={"omitted-is-different": None, "empty": []},
    )
    values = calls.values_document_registration_kb_document(request)
    assert values["title"] is None
    assert values["meta"] == {"omitted-is-different": None, "empty": []}
    result = calls.materialize_document_registration(
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
    assert result.decoded_json_fields(operation="register_document")["meta"] == values["meta"]
    # An output corruption is a server contract failure, while bad input stays invalid input.
    prepare = vars(calls)["prepare_document_registration"]
    with pytest.raises(ValidationError):
        prepare(**{**values, "title": 17})
    materialize = vars(calls)["materialize_document_registration"]
    with pytest.raises(NativeResultViolation):
        materialize(
            (None, "project", "document", "uri", "hash", "/retained", "text/plain", None, "{}")
        )


def test_core_projections_resolve_actual_physical_columns_without_native_dispatch():
    statement = select(*calls.projection_document_registration)
    assert statement.get_final_froms() == [metadata.tables["kb.document"]]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "CAST(kb.document.meta AS TEXT) AS meta" in sql
    assert "ops." not in sql
    assert not hasattr(calls, "_document_registration_function")
    assert calls.materialize_original_artifact((b"original",)) == b"original"
    # The generated immutable module owns one reusable scalar adapter.
    adapter = calls._original_artifact_adapter
    assert calls.materialize_original_artifact((b"again",)) == b"again"
    assert calls._original_artifact_adapter is adapter


@pytest.mark.parametrize("mutation", ["wrong_owner", "native_parameter", "batch"])
def test_core_boundaries_refuse_native_identity_or_unowned_executor(mutation):
    original = model()
    operation = original.operation("register_document")
    core = next(c for c in operation.calls if c.backend == "core")
    if mutation == "wrong_owner":
        core = replace(core, symbol="semantic.operations.read_original")
    elif mutation == "native_parameter":
        core = replace(
            core,
            parameters=(replace(core.parameters[0], native_parameter="p"), *core.parameters[1:]),
        )
    else:
        core = replace(core, batch=True)
    operation = replace(
        operation, calls=tuple(core if c.backend == "core" else c for c in operation.calls)
    )
    changed = replace(
        original,
        operations=tuple(operation if o.id == operation.id else o for o in original.operations),
    )
    with pytest.raises(PreparationError):
        validate_call_bindings(changed, trusted_execution_inputs())


def test_core_optional_scalar_materializes_real_result_cardinality():
    from sqlalchemy import create_engine, false, literal, union_all

    engine = create_engine("sqlite://")
    try:
        with engine.connect() as connection:
            selected = select(literal(b"retained"))
            assert calls.collect_original_artifact(connection.execute(selected)) == b"retained"
            assert (
                calls.collect_original_artifact(connection.execute(selected.where(false()))) is None
            )
            with pytest.raises(NativeResultViolation):
                calls.collect_original_artifact(connection.execute(union_all(selected, selected)))
    finally:
        engine.dispose()
