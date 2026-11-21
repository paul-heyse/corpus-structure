"""Available producer facts stay behind the existing authenticated binding reader."""

from typing import cast

import pytest
from pglast import ast
from psycopg.errors import CheckViolation, InsufficientPrivilege
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._data_operation_wire import WireRevokeDataSupportRequest
from corpus_structure.semantic.data_operation_json import json_bytes, native_json_loads
from corpus_structure.semantic.data_operation_storage import (
    DataOperationStorage,
    admitted_data_read,
)
from corpus_structure.semantic.demand_results import read_demand_result
from corpus_structure.semantic.metadata import get_metadata, table
from corpus_structure.semantic.native_objects import native_owner
from corpus_structure.semantic.prepared_sql import prepare_sql
from semantic.declared_scenarios import declared_serving_case as declared_serving_case
from semantic.declared_scenarios import declared_serving_seed as declared_serving_seed


def test_authorized_binding_observes_producer_without_disclosing_protected_support(
    declared_serving_case,
):
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.data_operation_read_native import read_native_sql
    from corpus_structure.semantic.producer_requirements import SelectedProducerContract

    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    # Install the changed internal query on this owned clone, preserving the
    # existing public frontdoor and purpose grants.
    statements = prepare_sql(read_native_sql(get_metadata()), source="producer-observation-test")
    with clone.admin.begin() as connection, native_owner(connection, "corpus_sem_publisher"):
        for index, statement in enumerate(statements.statements):
            node = statement.stmt
            if (
                isinstance(node, ast.CreateFunctionStmt)
                and node.funcname
                and node.funcname[-1].sval == "ddo_binding_rows"
            ):
                connection.exec_driver_sql(
                    statements.excerpt(index), execution_options={"no_parameters": True}
                )
    model = bound_data_operation_model(stage.prepared)
    with clone.reader.begin() as connection:
        page = read_demand_result(
            connection, stage.demand_id, project_id=stage.project_id, view="frontier"
        )
        pins = page.cut.record
        read = admitted_data_read(
            connection,
            stage.demand_id,
            "urn:ddo-test:source",
            pins["trust_snapshot"],
            model,
            read_id=pins["read_id"],
        )
        evidence = connection.execute(select(read.relation.c.support_evidence)).scalars().all()
    assert len(evidence) == 2
    observations = [
        SelectedProducerContract.model_validate_json(json_bytes(value["producer_contract"]))
        for value in evidence
    ]
    expected = native_json_loads(stage.source_receipt)["derivation_id"]
    assert {item.derivation_id for item in observations} == {expected}
    assert {item.release_id for item in observations} == {stage.prepared.release_id}
    assert all(item.publication_receipt for item in observations)
    assert all(item.cpu_receipt is False for item in observations)
    assert all(
        set(value["producer_contract"])
        == {
            "version",
            "derivation_id",
            "release_id",
            "runtime_id",
            "publication_receipt",
            "cpu_receipt",
            "admitted_effects",
            "validity_families",
        }
        for value in evidence
    )
    with pytest.raises(DBAPIError) as denied, clone.reader.begin() as connection:
        connection.execute(select(table("ops.data_completion_intent")))
    assert isinstance(denied.value.orig, InsufficientPrivilege)
    with clone.writer.begin() as connection:
        DataOperationStorage(connection).revoke_data_support(
            cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": stage.project_id,
                    "original_source": stage.original_source,
                    "selector_kind": "derivation",
                    "selector": expected,
                    "reason": "independent producer observation authority refusal",
                },
            )
        )
    with pytest.raises(DBAPIError) as stale, clone.reader.begin() as connection:
        read = admitted_data_read(
            connection,
            stage.demand_id,
            "urn:ddo-test:source",
            pins["trust_snapshot"],
            model,
            read_id=pins["read_id"],
        )
        connection.execute(select(read.relation.c.support_evidence)).all()

    assert isinstance(stale.value.orig, CheckViolation)
