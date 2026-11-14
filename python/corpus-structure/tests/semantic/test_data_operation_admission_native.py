"""Restricted acquisition reads exact immutable facts through its owned native port."""

from hashlib import sha256

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from semantic.data_operation_kernel_support import STORAGE, source_declaration


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["admission-read"])
def test_native_admission_read_authenticates_selected_contract_and_runtime_without_table_access(
    ddo_kernel,
):
    payload = {
        "release_id": ddo_kernel.prepared.release_id,
        "operation_id": source_declaration()["id"],
        "runtime_id": ddo_kernel.runtime,
    }
    with ddo_kernel.purpose("admit").begin() as connection:
        retained = DataOperationStorage(connection).invoke("inspect_data_execution", payload)
        assert retained["recipe"] == ddo_kernel.identities[payload["operation_id"], "recipe"]
        assert retained["runtime"] == {
            "manifest_sha256": sha256(ddo_kernel.preparation.runtime.manifest).hexdigest(),
            "archive_sha256": sha256(ddo_kernel.preparation.runtime.archive).hexdigest(),
        }
        # Admission receives selected identities, not a broad protected-table grant.
        with pytest.raises(DBAPIError, match="permission denied"), connection.begin_nested():
            connection.execute(text("SELECT * FROM sem.data_operation_definition"))
        with pytest.raises(DBAPIError, match="no rows"), connection.begin_nested():
            DataOperationStorage(connection).invoke(
                "inspect_data_execution", {**payload, "runtime_id": "runtime:absent"}
            )
