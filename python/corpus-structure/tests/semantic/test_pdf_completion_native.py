"""Completion proof declaration includes independent semantic outcome and producer custody."""

from pglast import ast

from corpus_structure.semantic.pdf_completion_native import pdf_completion_native_sql
from corpus_structure.semantic.prepared_sql import prepare_sql


def test_pdf_completion_proof_is_closed_private_and_preserves_semantic_non_success():
    sql = pdf_completion_native_sql()
    prepared = prepare_sql(sql, source="PDF completion proof")
    function = prepared.statements[2].stmt
    assert isinstance(function, ast.CreateFunctionStmt)
    assert function.funcname is not None
    assert tuple(part.sval for part in function.funcname) == ("ops", "ddo_require_pdf_completion")
    assert len(prepared.statements) == 4
    assert "ops.ddo_completion_state(definition,p_completion->>'outcome')" in sql
    assert "ops.pdf_publication_projection(receipts->0,p_task,p_attempt,p_holder)" in sql
    assert "data.ddo_json(output->'product'->'body') IS DISTINCT FROM expected" in sql
    assert "jsonb_array_length(receipts) IS DISTINCT FROM 1" in sql
    assert "output->>'member_id' IS NOT NULL" in sql
    assert "FROM PUBLIC" in sql
    assert "GRANT" not in sql


def test_native_pdf_command_eligibility_refuses_changed_effect_or_uncaptured_factory(
    native_rollback,
):
    """Pure eligibility is necessary; actual sealed receipt inspection remains separate."""
    from copy import deepcopy
    from typing import Any

    from sqlalchemy import text

    from corpus_structure.semantic.data_operation_json import json_bytes

    definition: dict[str, Any] = {
        "profile": "command",
        "implementation_revision": "implementation-slice:captured",
        "support_contract": {
            "effects": [
                {
                    "name": "publish_pdf_capture",
                    "authorization": ["original-source", "owned-request-attempt"],
                    "idempotency": "request-generation/source-digest/recipe-digest",
                    "fulfillment": "sealed-native-pdf-receipt",
                }
            ],
            "capabilities": {
                "preparation": "pdf-native",
                "forms": ["scalar"],
                "prepared_factory": {
                    "entrypoint": "corpus_structure.ingest.pdf_capture.PdfCaptureOperation.acquire_port",
                    "source_digest": "a" * 64,
                },
            },
        },
    }
    query = text(
        "SELECT coalesce(ops.ddo_pdf_command_eligible(jsonb_populate_record(NULL::sem.data_operation_definition,CAST(:value AS jsonb))),false)"
    )
    connection = native_rollback.connection
    assert connection.scalar(query, {"value": json_bytes(definition).decode()}) is True
    for change in ("factory", "fulfillment", "authorization", "implementation"):
        invalid = deepcopy(definition)
        if change == "factory":
            invalid["support_contract"]["capabilities"]["prepared_factory"]["entrypoint"] = (
                "other.acquire_port"
            )
        elif change == "implementation":
            invalid["implementation_revision"] = "unauthenticated-behavior-string"
        else:
            invalid["support_contract"]["effects"][0][change] = (
                [] if change == "authorization" else "invented-receipt"
            )
        assert connection.scalar(query, {"value": json_bytes(invalid).decode()}) is False
