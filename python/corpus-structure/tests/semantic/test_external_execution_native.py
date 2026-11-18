"""Native external custody projections retain exact typed receipt identity."""

import json

import pytest
from pglast import ast
from sqlalchemy import text

from corpus_structure.semantic.prepared_sql import prepare_sql
from semantic.data_operation_binding_support import (
    binding_native_connection as binding_native_connection,
)
from semantic.data_operation_binding_support import binding_source_recipe


@pytest.mark.db
@pytest.mark.parametrize("model_assertion", [None, "controlled-model"])
def test_native_external_receipt_keeps_exact_producer_and_assertion_fields(
    binding_native_connection, model_assertion
):
    source = prepare_sql(binding_source_recipe().codecs.decode(), source="external-receipt")
    for index, raw in enumerate(source.statements):
        if (
            isinstance(raw.stmt, ast.CreateFunctionStmt)
            and raw.stmt.funcname
            and raw.stmt.funcname[-1].sval == "ddo_external_receipt_value"
        ):
            binding_native_connection.exec_driver_sql(
                source.excerpt(index), execution_options={"no_parameters": True}
            )
            break
    else:
        raise AssertionError("captured external receipt declaration is absent")
    physical = {
        "id": "external-result:independent",
        "packet_id": "external-packet:independent",
        "packet_digest": "a" * 64,
        "request_id": "request:independent",
        "generation": 7,
        "task_id": 9007199254740993,
        "attempt": 11,
        "holder": "independent-holder",
        "runtime_id": "runtime:independent",
        "admitting_principal": "independent-principal",
        "actor_assertion": "controlled-actor",
        "model_assertion": model_assertion,
        "result_digest": "b" * 64,
        "created_at": "2026-11-18T12:00:00+00:00",
    }
    expected = {
        "version": "external-execution-receipt-v1",
        "receipt_id": "external-result:independent",
        "packet_id": "external-packet:independent",
        "packet_digest": "a" * 64,
        "request_id": "request:independent",
        "generation": 7,
        "task_id": 9007199254740993,
        "attempt": 11,
        "holder": "independent-holder",
        "runtime_id": "runtime:independent",
        "admitting_principal": "independent-principal",
        "actor_assertion": "controlled-actor",
        "model_assertion": model_assertion,
        "result_digest": "b" * 64,
    }
    actual = binding_native_connection.scalar(
        text(
            "SELECT ops.ddo_external_receipt_value(jsonb_populate_record("
            "NULL::ops.data_external_receipt,CAST(:physical AS jsonb)))"
        ),
        {"physical": json.dumps(physical)},
    )
    assert actual == expected
