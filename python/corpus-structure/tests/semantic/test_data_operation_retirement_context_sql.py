"""Physical attempt and contextual product constraints use their declared owners."""

import json
from typing import cast as typing_cast

import pytest
from sqlalchemy import MetaData, UniqueConstraint, insert, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.data_operation_identity import (
    body_identity,
    contextual_product_identity,
)
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.metadata import table
from semantic.data_operation_kernel_support import STORAGE


@pytest.mark.db
@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_retired_attempt_preserves_holder_until_a_new_claim_fence(ddo_kernel):
    from native_refusals import native_refusal

    from corpus_structure.semantic._data_operation_wire import WireReleaseDataAttemptRequest
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.native_objects import native_owner
    from semantic.data_operation_demand_support import attach, claim

    _, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached, holder="original-holder")
    with ddo_kernel["engine"].begin() as connection:
        released = DataOperationStorage(connection).release_data_attempt(
            typing_cast(
                WireReleaseDataAttemptRequest,
                {
                    **fence,
                    "physical_retirement": "confirmed",
                    "failure": {"code": "compute-error", "message": "retired control"},
                },
            )
        )
        assert released["state"] == "released"
        row = connection.execute(
            text("SELECT status,attempt,claimed_by,lease_until FROM ops.task WHERE id=:id"),
            {"id": fence["task_id"]},
        ).one()
        assert tuple(row) == ("pending", 1, "original-holder", None)
        with native_owner(connection, "corpus_sem_publisher"):
            for update, reason in (
                ("claimed_by=NULL", "data holder requires new attempt"),
                (
                    "status='running',lease_until=clock_timestamp()+interval '1 hour'",
                    "invalid data task transition",
                ),
                (
                    "lease_until=clock_timestamp()+interval '1 hour'",
                    "data terminal task retains lease",
                ),
            ):
                with connection.begin_nested() as savepoint:
                    with native_refusal("P0001", message=reason):
                        connection.execute(
                            text("UPDATE ops.task SET " + update + " WHERE id=:id"),
                            {"id": fence["task_id"]},
                        )
                    savepoint.rollback()
    replacement = claim(ddo_kernel, attached, holder="replacement")
    assert replacement["attempt"] == 2
    with (
        ddo_kernel["engine"].begin() as connection,
        native_owner(connection, "corpus_sem_publisher"),
        connection.begin_nested() as savepoint,
    ):
        with native_refusal("P0001", message="invalid data claim fence"):
            connection.execute(
                text(
                    "UPDATE ops.task SET attempt=1,status='pending',lease_until=NULL WHERE id=:id"
                ),
                {"id": fence["task_id"]},
            )
        savepoint.rollback()


@pytest.mark.db
def test_declared_product_primary_identity_allows_equal_body_in_distinct_scopes(
    infrastructure_rollback,
):
    product = table("kb.data_product").to_metadata(MetaData(), schema="pg_temp")
    assert not any(isinstance(constraint, UniqueConstraint) for constraint in product.constraints)
    body = body_identity(7)
    contexts = [
        SubjectContext("project", "local", "original", scope, subject_definition="document")
        for scope in (b'{"page":1}', b'{"page":2}')
    ]
    rows = [
        {
            "id": contextual_product_identity(
                kind="kind:integer", context=context, body=body.key
            ).key,
            "kind_contract": "kind:integer",
            "project_id": "project",
            "subject": "local",
            "subject_definition": context.record["subject_definition"],
            "original_source": "original",
            "analyzed_scope": context.record["analyzed_scope"],
            "canonical_body": ["integer", "7"],
            "body_digest": body.key,
        }
        for context in contexts
    ]
    assert rows[0]["id"] != rows[1]["id"]
    connection = infrastructure_rollback
    transaction = connection.begin_nested()
    try:
        connection.execute(CreateTable(product, include_foreign_key_constraints=[]))
        connection.execute(insert(product), rows)
        assert set(connection.scalars(select(product.c.id))) == {row["id"] for row in rows}
        with connection.begin_nested() as savepoint:
            with pytest.raises(IntegrityError):
                connection.execute(insert(product), rows[0])
            savepoint.rollback()
    finally:
        transaction.rollback()


@pytest.mark.db
def test_qualified_population_preserves_distinct_subject_definitions(infrastructure_rollback):
    from corpus_structure.semantic.binding_recursive_native import binding_population_native_sql

    source = binding_population_native_sql()
    start = source.index("CREATE OR REPLACE FUNCTION ops.ddo_project_population(")
    helpers = (
        source[start:]
        .replace("ops.ddo_project_population", "pg_temp.ddo_project_population")
        .replace("ops.ddo_binding_population_meaning", "pg_temp.ddo_binding_population_meaning")
    )
    members = [
        {
            "member_id": name,
            "subject": "same-address",
            "subject_definition": name,
            "original_source": "same-document",
            "analyzed_scope": {"page": 3},
        }
        for name in ("document-subject", "view-subject")
    ]
    expected = [
        {
            "project_id": "project",
            **{key: value for key, value in member.items() if key != "member_id"},
        }
        for member in members
    ]
    connection = infrastructure_rollback
    transaction = connection.begin_nested()
    try:
        connection.exec_driver_sql(helpers)
        witness = connection.execute(
            text(
                "SELECT pg_temp.ddo_project_population('population:one',true,CAST(:members AS jsonb),'{}','project','qualified-context')"
            ),
            {"members": json.dumps(members)},
        ).scalar_one()
        assert witness["members"] == expected
        assert len({member["subject_definition"] for member in witness["members"]}) == 2
        meaning = connection.execute(
            text("SELECT pg_temp.ddo_binding_population_meaning(CAST(:witness AS jsonb),false)"),
            {"witness": json.dumps(witness)},
        ).scalar_one()
        assert meaning == {
            "identity": "population:one",
            "complete": True,
            "members": expected,
            "projection": "qualified-context",
        }
        del witness["members"][0]["subject_definition"]
        with connection.begin_nested() as savepoint:
            with pytest.raises(DBAPIError, match="invalid structured native population witness"):
                connection.execute(
                    text(
                        "SELECT pg_temp.ddo_binding_population_meaning(CAST(:witness AS jsonb),false)"
                    ),
                    {"witness": json.dumps(witness)},
                )
            savepoint.rollback()
    finally:
        transaction.rollback()
