"""Completion proof declaration includes independent semantic outcome and producer custody."""

import pytest
from pglast import ast

from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.pdf_completion_native import pdf_completion_native_sql
from corpus_structure.semantic.prepared_sql import prepare_sql


def test_pdf_completion_proof_is_closed_private_and_preserves_semantic_non_success():
    sql = pdf_completion_native_sql(metadata)
    prepared = prepare_sql(sql, source="PDF completion proof")
    function = prepared.statements[2].stmt
    assert isinstance(function, ast.CreateFunctionStmt)
    assert function.funcname is not None
    assert tuple(part.sval for part in function.funcname) == ("ops", "ddo_require_pdf_completion")
    assert len(prepared.statements) == 4
    assert "FROM PUBLIC" in sql
    assert "GRANT" not in sql


@pytest.mark.parametrize(
    "factory,effect,authorization",
    [
        (
            "corpus_structure.ingest.pdf_capture.PdfCaptureOperation.acquire_port",
            "publish_pdf_capture",
            ["original-source", "owned-request-attempt"],
        ),
        (
            "corpus_structure.ingest.pdf_enrichment_operation.PdfEnrichmentOperation.acquire_port",
            "publish_pdf_enrichment",
            ["original-source", "exact-selected-pdf", "owned-request-attempt"],
        ),
        (
            "corpus_structure.ingest.pdf_integration_operation.PdfIntegrationOperation.acquire_port",
            "publish_pdf_integration",
            ["original-source", "exact-selected-pdf", "owned-request-attempt"],
        ),
        (
            "corpus_structure.ingest.pdf_organization_operation.PdfOrganizationOperation.acquire_port",
            "publish_pdf_organization",
            ["original-source", "exact-selected-pdf", "owned-request-attempt"],
        ),
    ],
    ids=["capture", "enrichment", "integration", "organization"],
)
def test_native_pdf_command_eligibility_refuses_changed_effect_or_uncaptured_factory(
    native_rollback, factory, effect, authorization
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
                    "name": effect,
                    "authorization": authorization,
                    "idempotency": "request-generation/source-digest/recipe-digest",
                    "fulfillment": "sealed-native-pdf-receipt",
                }
            ],
            "capabilities": {
                "preparation": "pdf-native",
                "forms": ["scalar"],
                "prepared_factory": {
                    "entrypoint": factory,
                    "source_digest": "a" * 64,
                },
            },
        },
    }
    query = text(
        "SELECT coalesce(ops.ddo_pdf_command_eligible(jsonb_populate_record(NULL::sem.data_operation_definition,CAST(:value AS jsonb))),false)"
    )
    connection = native_rollback.connection
    from corpus_structure.semantic.native_objects import execute_native_sql, native_owner

    with native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, pdf_completion_native_sql(metadata))
    assert connection.scalar(query, {"value": json_bytes(definition).decode()}) is True
    for change in (
        "factory",
        "paired_factory",
        "fulfillment",
        "authorization",
        "implementation",
        "profile",
        "effects",
        "preparation",
        "forms",
        "source_digest",
    ):
        invalid = deepcopy(definition)
        if change == "factory":
            invalid["support_contract"]["capabilities"]["prepared_factory"]["entrypoint"] = (
                "other.acquire_port"
            )
        elif change == "paired_factory":
            invalid["support_contract"]["capabilities"]["prepared_factory"]["entrypoint"] = (
                "corpus_structure.ingest.pdf_capture.PdfCaptureOperation.acquire_port"
                if effect != "publish_pdf_capture"
                else "corpus_structure.ingest.pdf_integration_operation.PdfIntegrationOperation.acquire_port"
            )
        elif change == "profile":
            invalid["profile"] = "derivation"
        elif change == "effects":
            invalid["support_contract"]["effects"] = []
        elif change in ("preparation", "forms"):
            invalid["support_contract"]["capabilities"][change] = (
                "none" if change == "preparation" else ["scalar", "batch"]
            )
        elif change == "source_digest":
            invalid["support_contract"]["capabilities"]["prepared_factory"][change] = "uncaptured"
        elif change == "implementation":
            invalid["implementation_revision"] = "unauthenticated-behavior-string"
        else:
            invalid["support_contract"]["effects"][0][change] = (
                [] if change == "authorization" else "invented-receipt"
            )
        assert connection.scalar(query, {"value": json_bytes(invalid).decode()}) is False


def test_generated_pdf_completion_binds_in_native_model_and_retains_strict_lookup(native_rollback):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic.native_objects import execute_native_sql, native_owner

    connection = native_rollback.connection
    execute_native_sql(connection, "CREATE EXTENSION IF NOT EXISTS plpgsql_check VERSION '2.10'")
    with native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, pdf_completion_native_sql(metadata))
        failures = (
            connection.execute(
                text(
                    "SELECT message FROM public.plpgsql_check_function_tb("
                    "'ops.ddo_require_pdf_completion(jsonb,bigint,bigint,text,text,text)'::regprocedure,"
                    "fatal_errors=>false) WHERE level='error'"
                )
            )
            .scalars()
            .all()
        )
        assert failures == []
        with pytest.raises(DBAPIError) as missing, connection.begin_nested():
            connection.execute(
                text("SELECT ops.ddo_require_pdf_completion('{}',-1,-1,'absent','absent','absent')")
            )
        assert getattr(missing.value.orig, "sqlstate", None) == "P0002"
