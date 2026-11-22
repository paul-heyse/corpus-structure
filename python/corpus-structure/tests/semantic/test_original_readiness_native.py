"""Exact late original receipts wake only their own native source-only waiter."""

from pathlib import Path
from typing import cast

from sqlalchemy import text

from corpus_structure.schema.model_change import native_model_inputs
from corpus_structure.semantic import migrations
from corpus_structure.semantic._data_operation_wire import (
    WireAdmitOriginalDocumentAssetRequest,
    WireReadDemandResultRequest,
    WireRegisterDataDemandRequest,
    WireRevokeDataSupportRequest,
)
from corpus_structure.semantic.data_operation_demands import DemandPlanner, freeze_demand
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_operation_support import OriginalSourceSupportReference
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.target_installation import capture_target_installation
from semantic.data_operation_kernel_support import ORIGINAL_DOCUMENT, admit_kernel, prepare_kernel
from semantic.test_data_operation_original_native import _register_document
from semantic.test_target_installation_native import install_target_root

ROOT = Path(__file__).resolve().parents[4]
TARGET = "urn:original-fact-test:consume"


def test_native_original_readiness_tracks_exact_committed_admission_without_watermark(
    semantic_bare_engine, tmp_path, monkeypatch
):
    admin = semantic_bare_engine
    epoch = capture_target_installation(get_metadata(), logical_sources=native_model_inputs(ROOT))
    *_, revision_path = install_target_root(admin, epoch, tmp_path)
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", revision_path)
    preparation = prepare_kernel(ORIGINAL_DOCUMENT, directory=tmp_path / "original-kernel")
    with admin.begin() as connection:
        kernel = admit_kernel(connection, ORIGINAL_DOCUMENT, engine=admin, preparation=preparation)
        original = _register_document(connection, kernel, tmp_path)

    def register(inference):
        intent = freeze_demand(
            kernel.model,
            roots=(original.root,),
            targets=(TARGET,),
            inference=inference,
            execution_profile=kernel.recipe.execution_profile,
            original_sources=(original.selection(),),
        )
        # Registration owns the durable frozen waiter. Intentionally admit its
        # already registered original through the independent native owner later.
        with admin.begin() as connection:
            return DataOperationStorage(connection).register_data_demand(
                cast(
                    WireRegisterDataDemandRequest,
                    {
                        "project_id": original.reference.project_id,
                        "release_id": kernel.prepared.release_id,
                        "runtime_id": preparation.runtime.runtime_id,
                        "root": intent.record["roots"],
                        "selection": intent.record,
                        "strength": "value",
                    },
                )
            )

    def admit(storage, demand):
        return storage.admit_original_document_asset(
            cast(
                WireAdmitOriginalDocumentAssetRequest,
                {
                    "demand_id": demand["demand_id"],
                    "selection_name": original.name,
                    **original.selection().record(),
                },
            )
        )

    def read(demand, **pins):
        with admin.begin() as connection:
            return DataOperationStorage(connection).read_demand_result(
                cast(WireReadDemandResultRequest, {"demand_id": demand["demand_id"], **pins})
            )

    def obligation(page):
        (value,) = [row for row in page["obligations"] if row["operation_id"] == TARGET]
        return value

    demand = register("late-selected-original")
    first = read(demand)
    waiting = obligation(first)
    assert waiting["original_readiness"] == {
        "ready": False,
        "state": "missing",
        "input_role": "source",
        "identity": None,
    }
    assert waiting["fate"] == "awaiting-inputs"
    assert "inputs_watermark" not in waiting
    with admin.begin() as connection:
        assert (
            DemandPlanner(kernel.model, DataOperationStorage(connection)).ready(
                first, authorization=b"{}"
            )
            == ()
        )
        assert connection.scalar(text("SELECT count(*) FROM ops.demand_use")) == 0

    other = register("another-exact-demand")
    with admin.begin() as connection:
        other_admission = admit(DataOperationStorage(connection), other)
    assert obligation(read(other))["original_readiness"]["ready"] is True
    # An equal, physically present product with another admission cannot wake
    # this waiter's exact frozen source. No eligibility is inferred from value.
    assert obligation(read(demand))["original_readiness"] == waiting["original_readiness"]

    with admin.connect() as connection:
        transaction = connection.begin()
        rolled_back = admit(DataOperationStorage(connection), demand)
        assert rolled_back["product_id"] == other_admission["product_id"]
        transaction.rollback()
    assert obligation(read(demand))["original_readiness"] == waiting["original_readiness"]

    with admin.begin() as connection:
        admitted = admit(DataOperationStorage(connection), demand)
    with admin.begin() as connection:
        assert admit(DataOperationStorage(connection), demand) == admitted
    assert admitted["product_id"] == other_admission["product_id"]
    assert admitted["admission_id"] != other_admission["admission_id"]

    historical = read(
        demand,
        read_id=first["read_id"],
        selection=first["selection"],
        trust_snapshot=first["trust_snapshot"],
    )
    assert obligation(historical)["original_readiness"] == waiting["original_readiness"]
    current = read(demand)
    ready = obligation(current)
    assert ready["original_readiness"] == {
        "ready": True,
        "state": "ready",
        "input_role": "source",
        "identity": {
            "product_id": admitted["product_id"],
            "admission_ids": [admitted["admission_id"]],
        },
    }
    assert "inputs_watermark" not in ready
    with admin.begin() as connection:
        planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
        assert planner.ready(historical, authorization=b"{}") == ()
        (scheduled,) = planner.ready(current, authorization=b"{}")
        assert scheduled.operation == TARGET
        (support,) = scheduled.resolved.roles[0].members[0].support_references
        assert isinstance(support, OriginalSourceSupportReference)
        assert support.admission_id == admitted["admission_id"]

    with admin.begin() as connection:
        DataOperationStorage(connection).revoke_data_support(
            cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": original.reference.project_id,
                    "original_source": original.root.original_source,
                    "selector_kind": "original-admission",
                    "selector": admitted["admission_id"],
                    "reason": "selected original support withdrawn",
                },
            )
        )
    revoked = read(demand)
    assert obligation(revoked)["original_readiness"] == waiting["original_readiness"]
    with admin.begin() as connection:
        assert (
            DemandPlanner(kernel.model, DataOperationStorage(connection)).ready(
                revoked, authorization=b"{}"
            )
            == ()
        )
