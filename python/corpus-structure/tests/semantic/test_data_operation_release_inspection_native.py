"""Actual current read-purpose inspection and bidirectional admitted-rowset refusal.

Requires the combined captured native revision; controlled schemas are not admission evidence.
"""

import pytest
from sqlalchemy import literal, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_definition_projection import read_native_definition_projection
from semantic.data_operation_kernel_support import STORAGE


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True)
def test_reader_inspection_is_read_only_and_attests_no_protected_body_or_admission_grant(
    ddo_kernel,
):
    kernel = ddo_kernel
    expected = read_native_definition_projection(kernel.prepared)
    with kernel.purpose("read").begin() as connection:
        connection.exec_driver_sql("SET TRANSACTION READ ONLY")
        assert (
            connection.scalar(
                text("SELECT has_table_privilege(current_user,'sem.data_kind_contract','SELECT')")
            )
            is False
        )
        assert (
            connection.scalar(
                text(
                    "SELECT has_function_privilege(current_user,'sem.admit_data_operation_definitions(jsonb)','EXECUTE')"
                )
            )
            is False
        )
        report = DataOperationStorage(connection).inspect_data_operation_release(
            {"release_id": kernel.prepared.release_id}
        )
    assert report == {
        "release_id": kernel.prepared.release_id,
        "model_digest": expected["model_digest"],
        "native_digest": expected["native_digest"],
    }
    assert set(report) == {"release_id", "model_digest", "native_digest"}


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True)
@pytest.mark.parametrize("mutation", ["missing-kind", "changed-operation", "extra-operation"])
def test_read_inspection_refuses_actual_missing_changed_and_extra_rows(ddo_kernel, mutation):
    kernel = ddo_kernel
    release = kernel.prepared.release_id
    kind = None
    with kernel.engine.begin() as connection:
        # Only the test's owned isolated clone is tampered. Preserve native trigger
        # posture, so refusal must come from the actual rowset correspondence check.
        connection.exec_driver_sql("SET LOCAL session_replication_role=replica")
        if mutation == "missing-kind":
            kind = connection.scalar(
                text(
                    "SELECT kind_contract FROM sem.data_kind_release WHERE release_id=:release ORDER BY kind_contract LIMIT 1"
                ),
                {"release": release},
            )
            assert isinstance(kind, str)
            connection.execute(
                text(
                    "DELETE FROM sem.data_kind_release WHERE release_id=:release AND kind_contract=:kind"
                ),
                {"release": release, "kind": kind},
            )
        elif mutation == "changed-operation":
            connection.execute(
                text(
                    "UPDATE sem.data_operation_definition SET support_contract=support_contract||CAST(:counterfeit AS jsonb) WHERE release_id=:release"
                ),
                {"release": release, "counterfeit": '{"inspection_counterfeit":true}'},
            )
        else:
            relation = get_metadata().tables["sem.data_operation_definition"]
            original = relation.alias("original")
            fields = {
                field.name: literal("unexpected:inspection")
                if field.name == "operation_id"
                else original.c.recipe + ":unexpected"
                if field.name == "recipe"
                else original.c[field.name]
                for field in relation.c
            }
            connection.execute(
                insert(relation).from_select(
                    tuple(fields),
                    select(*fields.values())
                    .where(original.c.release_id == release)
                    .order_by(original.c.operation_id)
                    .limit(1),
                )
            )
    try:
        with kernel.purpose("read").begin() as connection:
            with pytest.raises(DBAPIError) as caught, connection.begin_nested():
                DataOperationStorage(connection).inspect_data_operation_release(
                    {"release_id": release}
                )
            assert getattr(caught.value.orig, "sqlstate", None) == "23514"
            assert "read-only inspection admitted" in str(caught.value.orig)
    finally:
        with kernel.engine.begin() as connection:
            connection.exec_driver_sql("SET LOCAL session_replication_role=replica")
            if mutation == "missing-kind":
                assert kind is not None
                connection.execute(
                    text("INSERT INTO sem.data_kind_release VALUES(:release,:kind)"),
                    {"release": release, "kind": kind},
                )
            elif mutation == "changed-operation":
                connection.execute(
                    text(
                        "UPDATE sem.data_operation_definition SET support_contract=support_contract-'inspection_counterfeit' WHERE release_id=:release"
                    ),
                    {"release": release},
                )
            else:
                connection.execute(
                    text(
                        "DELETE FROM sem.data_operation_definition WHERE release_id=:release AND operation_id='unexpected:inspection'"
                    ),
                    {"release": release},
                )
