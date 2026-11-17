"""Current captured PDF calls retain native transport and materialization contracts."""

from dataclasses import replace
from functools import lru_cache

import pytest
import yaml
from pydantic import ValidationError

from corpus_structure.semantic import _pdf_native_calls as calls
from corpus_structure.semantic.operation_value_types import NativeResultViolation
from corpus_structure.semantic.pdf_domain import pdf_call_bindings, pdf_domain_sources


@lru_cache(maxsize=1)
def current_calls():
    return pdf_call_bindings()


def test_prepared_stream_call_binds_and_validates_without_executing_or_collecting():
    from corpus_structure.semantic.identifiers import ContentDigest, ProductKey, TaskId

    statement = calls.prepare_read_pdf_record_rows(
        task_id=TaskId(17),
        product_key=ProductKey("native"),
        content_digest=ContentDigest("a" * 64),
        family="native",
        filters={"record_id": "one"},
        after=None,
        limit=32,
    )
    assert statement.compile().params == {
        "task_id": 17,
        "product_key": "native",
        "content_digest": "a" * 64,
        "family": "native",
        "filters": {"record_id": "one"},
        "after": None,
        "limit": 32,
    }
    row = calls.materialize_read_pdf_record_rows(('{"_cursor":[],"x":null}',))
    assert row.body == '{"_cursor":[],"x":null}'
    assert row.decoded_json_fields(operation="read_native_source")["body"] == {
        "_cursor": [],
        "x": None,
    }
    materialize = vars(calls)["materialize_read_pdf_record_rows"]
    with pytest.raises(NativeResultViolation) as invalid:
        materialize((None,))
    assert invalid.value.locations == (("body",),)


def test_selected_projection_materializers_preserve_empty_ancestors_and_exact_decimals():
    from decimal import Decimal

    section = calls._read_published_sections_result(
        ("#/groups/1", None, 4, "section", "body", None, [], None, "")
    )
    assert section.model_dump(mode="python") == {
        "pointer": "#/groups/1",
        "parent_pointer": None,
        "ordinal": 4,
        "label": "section",
        "content_layer": "body",
        "name": None,
        "ancestors": (),
        "section_pointer": None,
        "text": "",
    }
    exact = Decimal("0.10000000000000000000000000001")
    region = calls._read_published_region_result(
        (
            "build",
            "revision",
            "#/texts/3",
            0,
            2,
            Decimal("600"),
            Decimal("800"),
            exact,
            Decimal("2"),
            Decimal("3"),
            Decimal("4"),
            "TOPLEFT",
        )
    )
    assert region.left is exact
    assert region.model_dump(mode="python")["left"] == exact
    with pytest.raises(NativeResultViolation) as invalid_role:
        calls._read_published_section_nodes_result(
            (
                "invented-role",
                "build",
                "revision",
                "#/texts/3",
                4,
                "text",
                None,
                None,
                "body",
                "hello",
                '{"self_ref":"#/texts/3"}',
            )
        )

    assert isinstance(invalid_role.value.original, ValidationError)
    assert invalid_role.value.locations == (("role",),)


def test_declared_json_text_result_preserves_sql_null_and_json_values():
    from corpus_structure.semantic.operation_value_types import SQL_NULL, decode_json_text

    assert decode_json_text(None) is SQL_NULL
    assert decode_json_text("null") is None
    assert decode_json_text("[]") == []
    assert decode_json_text("{}") == {}
    materialize = vars(calls)["_read_published_section_reports_result"]
    for encoded, expected in (("null", None), ("[]", []), ("{}", {})):
        row = materialize(("report", 3, encoded))
        assert row.body == encoded
        assert row.decoded_json_fields(operation="read_native_source")["body"] == expected
    with pytest.raises(NativeResultViolation) as absent:
        materialize(("report", 3, None))
    assert absent.value.field == "body"
    row = materialize(("report", 3, "malformed"))
    with pytest.raises(NativeResultViolation) as malformed:
        row.decoded_json_fields(operation="read_native_source")
    assert malformed.value.field == "body"


def test_json_text_result_uses_text_cast_without_changing_source_json_contract():
    from sqlalchemy.dialects import postgresql

    call = next(
        call
        for owner, call in current_calls()
        if owner == "read_native_source"
        if call.id == "read_published_section_reports"
    )
    assert call.json_read == "json-text-v1"
    body = next(field for field in call.result_fields if field.name == "body")
    assert body.resolved is not None and body.resolved.kind == "json_payload"
    statement = vars(calls)["_read_published_section_reports_statement"]
    assert "CAST(" in str(statement.compile(dialect=postgresql.dialect()))


def test_projected_requiredness_refines_nullable_source_without_losing_native_diagnostic(
    monkeypatch,
):
    import sys
    from types import ModuleType

    from corpus_structure.semantic.metadata import metadata
    from corpus_structure.semantic.native_call_generation import render_call_bindings
    from corpus_structure.semantic.native_call_sources import resolve_call_bindings

    _, *sources = pdf_domain_sources()
    logical = {
        s.name.removeprefix("pdf-domain/logical/"): s.content
        for s in sources
        if s.name.startswith("pdf-domain/logical/")
    }
    physical = {
        s.name.removeprefix("pdf-domain/physical/"): s.content
        for s in sources
        if s.name.startswith("pdf-domain/physical/")
    }
    body = yaml.safe_load(logical["companion_projections"])
    body["classes"]["PublishedItemIndexRow"]["attributes"]["text"]["required"] = True
    logical["companion_projections"] = yaml.safe_dump(body, sort_keys=False).encode()
    call = next(c for _, c in current_calls() if c.id == "read_published_item_page")
    resolved = resolve_call_bindings(
        (("read_native_source", replace(call, result_fields=(), source_digest=None)),),
        logical_sources=logical,
        physical_sources=physical,
    )
    _, call = resolved[0]
    field = next(f for f in call.result_fields if f.name == "text")
    assert not field.nullable and field.resolved is not None and field.resolved.nullable
    module = ModuleType("corpus_structure.semantic._projection_requiredness_control")
    module.__package__ = "corpus_structure.semantic"
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(
        compile(
            render_call_bindings(
                resolved,
                metadata,
                identifiers_module="._pdf_native_ids",
                canonical_identifiers=True,
                context_validator=(".pdf_domain", "require_pdf_call_context"),
            ),
            "<generated-call-control>",
            "exec",
        ),
        vars(module),
    )
    materialize = vars(module)["_read_published_item_page_result"]
    with pytest.raises(NativeResultViolation) as invalid:
        materialize(("build", "revision", "#/texts/1", 0, "text", None, None, "body", None))
    assert invalid.value.field == "text"
    assert (
        materialize(("build", "revision", "#/texts/1", 0, "text", None, None, "body", "kept")).text
        == "kept"
    )


def test_published_validation_reader_preserves_producer_and_oracle_receipt():
    statement = calls.prepare_read_pdf_published_validation(
        task_id=calls.TaskId(10),
        product_key=calls.ProductKey("integrated"),
        content_digest=calls.ContentDigest("logical-book-digest"),
    )
    assert statement.compile().params == {
        "task_id": 10,
        "product_key": "integrated",
        "content_digest": "logical-book-digest",
    }
    call = next(c for owner, c in current_calls() if c.id == "read_pdf_published_validation")
    assert [f.native_parameter for f in call.parameters] == ["p_task", "p_key", "p_digest"]
    assert call.cardinality == "optional" and not call.requires_context
    result = calls.materialize_read_pdf_published_validation(
        (
            "retained-build",
            "frozen-digest",
            "logical-book-digest",
            "projection-contract",
            True,
            "original-v4-native-contract",
            "round-trip-verified",
            "released-lowering",
            "attested-logical",
            "original-document",
            "actual-oracle",
        )
    )
    assert result.model_dump() == {
        "build_id": "retained-build",
        "frozen_digest": "frozen-digest",
        "logical_digest": "logical-book-digest",
        "contract_digest": "projection-contract",
        "native_callbacks": True,
        "native_contract_digest": "original-v4-native-contract",
        "certification_basis": "round-trip-verified",
        "lowering_identity": "released-lowering",
        "attested_logical_digest": "attested-logical",
        "native_document_digest": "original-document",
        "oracle_receipt_id": "actual-oracle",
    }
    materialize = vars(calls)["materialize_read_pdf_published_validation"]
    with pytest.raises(NativeResultViolation) as refused:
        materialize(
            (
                "b",
                "f",
                "l",
                "contract",
                "true",
                "original-native",
                "round-trip-verified",
                "lowering",
                "logical",
                "native",
                "oracle",
            )
        )
    assert refused.value.locations == (("native_callbacks",),)


def test_current_native_integer_widths_refuse_inputs_outside_the_actual_abi():
    from sqlalchemy import BigInteger, Integer

    function = calls._read_pdf_frozen_rows_function
    types = {parameter.key: type(parameter.type) for parameter in function.clauses}
    assert types["task_id"] is BigInteger
    assert types["limit"] is Integer
    request = {
        "build_id": "build",
        "task_id": 1,
        "attempt": 1,
        "holder": "worker",
        "frozen_digest": "digest",
        "family": "native",
        "after": None,
        "filters": {},
        "limit": 1,
    }
    for field, bits in (("task_id", 64), ("limit", 32)):
        for edge in (-(1 << (bits - 1)), (1 << (bits - 1)) - 1):
            actual = calls._read_pdf_frozen_rowsRequest.model_validate({**request, field: edge})
            assert getattr(actual, field) == edge
        for outside in (-(1 << (bits - 1)) - 1, 1 << (bits - 1)):
            with pytest.raises(ValidationError) as invalid:
                calls._read_pdf_frozen_rowsRequest.model_validate({**request, field: outside})
            assert not isinstance(invalid.value, NativeResultViolation)
            assert invalid.value.errors()[0]["loc"] == (field,)


def test_observation_publication_requires_an_explicit_actual_runtime():
    from corpus_structure.semantic.identifiers import RuntimeId, TaskAttempt, TaskId

    with pytest.raises(TypeError, match="runtime_id"):
        vars(calls)["prepare_publish_pdf_observation"](
            task_id=TaskId(2),
            attempt=TaskAttempt(3),
            holder="actual-holder",
            contract_digest="a" * 64,
            payload=b"{}",
            artifacts=(),
        )
    prepared = calls.prepare_publish_pdf_observation(
        task_id=TaskId(2),
        attempt=TaskAttempt(3),
        holder="actual-holder",
        runtime_id=RuntimeId("actual-runtime"),
        contract_digest="a" * 64,
        payload=b"{}",
        artifacts=(),
    )
    assert prepared.compile().params["runtime_id"] == "actual-runtime"
