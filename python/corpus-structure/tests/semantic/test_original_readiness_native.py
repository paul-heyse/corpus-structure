"""Exact late original receipts wake only their own native source-only waiter."""

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import cast

from sqlalchemy import text

from corpus_structure.core.evidence import document_key
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
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.original_documents import (
    acquire_original_document_selection,
    register_original_document,
)
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
    assert waiting["native_readiness"] == {
        "ready": False,
        "roles": [{"input_role": "source", "state": "missing", "identity": None}],
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
    assert obligation(read(other))["native_readiness"]["ready"] is True
    # An equal, physically present product with another admission cannot wake
    # this waiter's exact frozen source. No eligibility is inferred from value.
    assert obligation(read(demand))["native_readiness"] == waiting["native_readiness"]

    with admin.connect() as connection:
        transaction = connection.begin()
        rolled_back = admit(DataOperationStorage(connection), demand)
        assert rolled_back["product_id"] == other_admission["product_id"]
        transaction.rollback()
    assert obligation(read(demand))["native_readiness"] == waiting["native_readiness"]

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
    assert obligation(historical)["native_readiness"] == waiting["native_readiness"]
    current = read(demand)
    ready = obligation(current)
    assert ready["native_readiness"]["ready"] is True
    (ready_role,) = ready["native_readiness"]["roles"]
    assert ready_role["input_role"] == "source"
    assert ready_role["state"] == "ready"
    assert ready_role["identity"]["input"] == {
        "role": "source",
        "position": 0,
        "multiplicity": 1,
        "product_id": admitted["product_id"],
        "member_id": None,
        "producer_output": None,
        "support_derivation_ids": [],
    }
    (ready_support,) = ready_role["identity"]["support"]
    assert ready_support["admission_id"] == admitted["admission_id"]
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
    assert obligation(revoked)["native_readiness"] == waiting["native_readiness"]
    with admin.begin() as connection:
        assert (
            DemandPlanner(kernel.model, DataOperationStorage(connection)).ready(
                revoked, authorization=b"{}"
            )
            == ()
        )


def test_native_original_origin_wakes_only_matching_collection_waiter(
    semantic_bare_engine, tmp_path, monkeypatch
):
    admin = semantic_bare_engine
    epoch = capture_target_installation(get_metadata(), logical_sources=native_model_inputs(ROOT))
    *_, revision_path = install_target_root(admin, epoch, tmp_path)
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", revision_path)

    assert ORIGINAL_DOCUMENT.declaration_content is not None
    declaration = json.loads(ORIGINAL_DOCUMENT.declaration_content)
    (operation,) = declaration["operations"]
    (source_role,) = [role for role in operation["roles"] if role["name"] == "source"]
    source_role.update(collection="set", maximum=None)
    operation["binding"] = {"operator": "collection", "roles": ["source"], "collection": "set"}
    recipe = replace(
        ORIGINAL_DOCUMENT,
        name="original-collection",
        declaration_content=canonical_bytes(declaration),
    )
    preparation = prepare_kernel(recipe, directory=tmp_path / "original-collection")
    with admin.begin() as connection:
        kernel = admit_kernel(connection, recipe, engine=admin, preparation=preparation)
        primary = _register_document(connection, kernel, tmp_path)
        project = primary.reference.project_id
        body = b"%PDF-1.7\n% unrelated second original\n%%EOF\n"
        path = tmp_path / "second.pdf"
        path.write_bytes(body)
        register_original_document(
            connection,
            prepared=kernel.prepared,
            project_id=project,
            source_uri=path.name,
            original_path=str(path),
            original=body,
            mime="application/pdf",
        )
        second = acquire_original_document_selection(
            connection,
            project_id=project,
            document_key=document_key(project, path.name, sha256(body).hexdigest()),
            name="second-original",
        )

    intent = freeze_demand(
        kernel.model,
        roots=(primary.root, second.root),
        targets=(TARGET,),
        inference="source-collection-waiters",
        execution_profile=kernel.recipe.execution_profile,
        original_sources=(primary.selection(), second.selection()),
    )
    with admin.begin() as connection:
        demand = DataOperationStorage(connection).register_data_demand(
            cast(
                WireRegisterDataDemandRequest,
                {
                    "project_id": project,
                    "release_id": kernel.prepared.release_id,
                    "runtime_id": preparation.runtime.runtime_id,
                    "root": intent.record["roots"],
                    "selection": intent.record,
                    "strength": "value",
                },
            )
        )

    def resume():
        with admin.begin() as connection:
            planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
            return planner.resume(demand["demand_id"])

    scheduled_requests: set[tuple[str, int]] = set()

    def ready(page):
        with admin.begin() as connection:
            planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
            return planner.ready(
                page, authorization=b"{}", excluded_requests=frozenset(scheduled_requests)
            )

    def admit(original):
        with admin.begin() as connection:
            return DataOperationStorage(connection).admit_original_document_asset(
                cast(
                    WireAdmitOriginalDocumentAssetRequest,
                    {
                        "demand_id": demand["demand_id"],
                        "selection_name": original.name,
                        **original.selection().record(),
                    },
                )
            )

    before = resume()
    assert ready(before) == ()
    original_watermarks = {
        str(row["subject"]): row["inputs_watermark"] for row in before["obligations"]
    }
    for selected, other in ((second, primary), (primary, second)):
        admission = admit(selected)
        page = resume()
        by_subject = {str(row["subject"]): row for row in page["obligations"]}
        addressed = by_subject[selected.root.subject]
        assert addressed["native_readiness"] is None
        assert addressed["binding_original_changed"] is True
        assert addressed["inputs_watermark"] == original_watermarks[selected.root.subject]
        assert by_subject[other.root.subject].get("binding_original_changed", False) is False
        (scheduled,) = ready(page)
        assert scheduled.subject == selected.root.subject
        request = json.loads(scheduled.native)
        scheduled_requests.add((request["request_id"], request["generation"]))
        (support,) = scheduled.resolved.roles[0].members[0].support_references
        assert isinstance(support, OriginalSourceSupportReference)
        assert support.admission_id == admission["admission_id"]
