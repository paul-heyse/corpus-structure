"""Original facts enter through authentic published custody, never inference episodes."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from typing import cast as typing_cast

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._data_operation_wire import (
    WireAdmitOriginalDocumentAssetRequest,
    WireClaimDataRequestsRequest,
    WirePublishDataDerivationRequest,
    WireRetainDataCompletionIntentRequest,
    WireRevokeDataSupportRequest,
)
from corpus_structure.semantic.data_operation_admission import (
    bound_data_operation_model,
)
from corpus_structure.semantic.data_operation_demands import DemandPlanner, freeze_demand
from corpus_structure.semantic.data_operation_identity import canonical_identity
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_operation_values import decode_semantic_value, semantic_value
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.original_documents import (
    acquire_original_document_selection,
    register_original_document,
)
from semantic.data_operation_kernel_support import ORIGINAL_DOCUMENT, original_pdf_recipe


def _exact_original_recipe():
    assert ORIGINAL_DOCUMENT.declaration_content is not None
    declaration = json.loads(ORIGINAL_DOCUMENT.declaration_content)
    declaration["operations"][0]["roles"][0]["support"]["identity_requirements"] = [
        "original-source"
    ]
    return replace(
        ORIGINAL_DOCUMENT,
        name="exact-original-identity",
        declaration_content=canonical_bytes(declaration),
    )


EXACT_ORIGINAL = _exact_original_recipe()


def test_original_fact_target_has_explicit_value_based_origin_policy(original_target):
    model = bound_data_operation_model(original_target[3])
    operation = next(
        op for op in model.operations if op.semantic_id == "urn:original-fact-test:consume"
    )
    role = next(role for role in operation.roles if role.direction == "input")
    assert role.support is not None
    assert role.support.origins == ("original-source",)
    assert role.support.identity_requirements == ()


@pytest.mark.parametrize(
    "ddo_kernel",
    [ORIGINAL_DOCUMENT, EXACT_ORIGINAL],
    indirect=True,
    ids=("original-document", "exact-original-identity"),
)
def test_authentic_original_fact_admission_publication_and_revocation(ddo_kernel, tmp_path):
    kernel = ddo_kernel
    prepared, model = kernel.prepared, kernel.model
    with kernel.engine.begin() as connection:
        runtime = kernel.preparation.runtime
        acquired = _register_document(connection, kernel, tmp_path)
        intent = freeze_demand(
            model,
            roots=(acquired.root,),
            targets=("urn:original-fact-test:consume",),
            inference="inference:original-value",
            execution_profile=kernel.recipe.execution_profile,
            original_sources=(acquired.selection(),),
        )
        storage = DataOperationStorage(connection)
        demand = DemandPlanner(model, storage).register(
            intent,
            project=acquired.reference.project_id,
            release=prepared.release_id,
            runtime=runtime.runtime_id,
        )
    with kernel.engine.begin() as connection:
        storage = DataOperationStorage(connection)
        snapshot = storage.read_demand_result({"demand_id": demand["demand_id"]})
        admissions = snapshot["original_source_admissions"]
        assert len(admissions) == 1
        admission = admissions[0]
        assert admission["original_source"] == acquired.root.original_source
        assert isinstance(admission["evidence"], dict)
        assert admission["evidence"]["document_content_hash"] == acquired.reference.content_hash
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 0
        assert connection.scalar(text("SELECT count(*) FROM ops.data_request")) == 0
    with kernel.engine.begin() as connection:
        storage = DataOperationStorage(connection)
        # Repeated authenticated admission neither invents an episode nor a new value.
        repeated = storage.admit_original_document_asset(
            typing_cast(
                WireAdmitOriginalDocumentAssetRequest,
                {
                    "demand_id": demand["demand_id"],
                    "selection_name": acquired.name,
                    **acquired.selection().record(),
                },
            )
        )
        assert repeated["admission_id"] == admission["admission_id"]
        assert repeated["product_id"] == admission["product_id"]
        selected = DemandPlanner(model, storage).ready(snapshot, authorization=b"{}")
        assert len(selected) == 1
        ready = selected[0]
        binding = json.loads(ready.binding)
        assert binding["support"] == [
            {
                "kind": "original-source",
                "admission_id": admission["admission_id"],
                "source_reference": admission["source_reference"],
                "role": "source",
                "position": 0,
            }
        ]
        assert binding["inputs"][0]["support_derivation_ids"] == []
        assert ready.resolved.roles[0].members[0].support_episodes == ()
        bad_reference = deepcopy(binding)
        bad_reference["support"][0]["source_reference"] = "original:never-admitted"
        bad = dict(
            obligation_id=ready.obligation,
            request_key=json.loads(ready.native)["request_id"],
            request_meaning=json.loads(ready.request),
            binding=bad_reference,
            replicate=None,
        )
        refused = connection.scalar(
            text("SELECT ops.attach_data_requests(CAST(:payload AS jsonb))"),
            {
                "payload": json.dumps({"read_id": binding["read_id"], "items": [bad]}),
            },
        )["payload"]["items"][0]
        assert refused["state"] == "refused" and "original support" in refused["reason"]
        source_role = next(
            role for role in model.operation(ready.operation).roles if role.direction == "input"
        )
        assert source_role.support is not None
        if "original-source" in source_role.support.identity_requirements:
            meaning = decode_semantic_value(json.loads(ready.request)[3])
            meaning["inputs"]["source"]["value"].value[0]["original_sources"] = (
                "original:never-admitted",
            )
            forged = canonical_identity("semantic-request", meaning)
            altered = deepcopy(binding)
            altered["request_inputs"] = semantic_value(meaning["inputs"])
            before = connection.scalar(text("SELECT count(*) FROM ops.data_request"))
            bad = dict(
                obligation_id=ready.obligation,
                request_key=forged.key,
                request_meaning=json.loads(forged.canonical_input),
                binding=altered,
                replicate=None,
            )
            refused = connection.scalar(
                text("SELECT ops.attach_data_requests(CAST(:payload AS jsonb))"),
                {
                    "payload": json.dumps({"read_id": binding["read_id"], "items": [bad]}),
                },
            )["payload"]["items"][0]
            assert (
                refused["state"] == "refused"
                and "original source identity differs" in refused["reason"]
            )
            assert connection.scalar(text("SELECT count(*) FROM ops.data_request")) == before
        # An identical subject/source with a different selector scope cannot see this fact.
        wrong_scope = connection.execute(
            text(
                "SELECT count(*) FROM ops.data_binding_rows(:demand,:operation,"
                "CAST(:trust AS jsonb),:read,:subject,CAST(:source AS jsonb),CAST(:scope AS jsonb))"
            ),
            {
                "demand": demand["demand_id"],
                "operation": ready.operation,
                "trust": json.dumps(snapshot["trust_snapshot"]),
                "read": snapshot["read_id"],
                "subject": acquired.root.subject,
                "source": json.dumps(acquired.root.original_source),
                "scope": json.dumps(
                    {"document": acquired.reference.document_key, "scope": "different"}
                ),
            },
        ).scalar_one()
        assert wrong_scope == 0
        native = json.loads(ready.native)
        item_result = storage.claim_data_requests(
            typing_cast(
                WireClaimDataRequestsRequest,
                {
                    "holder": "original-test",
                    "lease_seconds": 30,
                    "items": [
                        {"request_id": native["request_id"], "generation": native["generation"]}
                    ],
                },
            )
        )["items"][0]
        assert item_result["state"] == "claimed", item_result
        claimed = item_result["result"]
        assert claimed["state"] == "claimed"
        fence = {
            key: claimed[key]
            for key in ("request_id", "generation", "task_id", "attempt", "holder")
        }
        output_kind = next(
            role.kind
            for op in model.operations
            if op.semantic_id == ready.operation
            for role in op.roles
            if role.direction == "output"
        )
        kind = next(
            item.key
            for item in model.identities
            if item.owner == output_kind and item.domain == "kind"
        )
        retained = storage.retain_data_completion_intent(
            typing_cast(
                WireRetainDataCompletionIntentRequest,
                {
                    **fence,
                    "runtime_id": runtime.runtime_id,
                    "completion": {
                        "outcome": "success",
                        "inputs": binding["inputs"],
                        "support": binding["support"],
                        "implementation_revision": "source-value-consumer-v1",
                        "outputs": [
                            {
                                "role": "result",
                                "position": 0,
                                "multiplicity": 1,
                                "product": {
                                    "kind_contract": kind,
                                    "body": semantic_value(7),
                                    "members": [],
                                },
                            }
                        ],
                    },
                },
            )
        )
        published = storage.publish_data_derivation(
            typing_cast(
                WirePublishDataDerivationRequest,
                {
                    **fence,
                    "intent_id": retained["intent_id"],
                },
            )
        )
        assert published["derivation_id"]
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation_support")) == 0
        assert (
            connection.scalar(text("SELECT count(*) FROM ops.data_derivation_original_support"))
            == 1
        )
        storage.revoke_data_support(
            typing_cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": acquired.reference.project_id,
                    "original_source": acquired.root.original_source,
                    "selector_kind": "original-admission",
                    "selector": admission["admission_id"],
                    "reason": "original source trust withdrawn",
                },
            )
        )
        current = storage.read_demand_result({"demand_id": demand["demand_id"]})
        assert current["original_source_admissions"] == []
        assert current["uses"][0]["fate"] == "unavailable"
        # Committed content and truthful lineage remain historically readable.
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 1
        assert connection.scalar(text("SELECT count(*) FROM ops.original_source_admission")) == 1
    with kernel.engine.begin() as connection:
        storage = DataOperationStorage(connection)
        with connection.begin_nested() as savepoint:
            with pytest.raises(DBAPIError, match="revoked"):
                storage.admit_original_document_asset(
                    typing_cast(
                        WireAdmitOriginalDocumentAssetRequest,
                        {
                            "demand_id": demand["demand_id"],
                            "selection_name": acquired.name,
                            **acquired.selection().record(),
                        },
                    )
                )
            savepoint.rollback()


@pytest.mark.parametrize(
    "ddo_kernel",
    [original_pdf_recipe],
    indirect=True,
    ids=("original-document",),
)
def test_original_pdf_fact_admission_and_runless_private_stage_use_actual_request_context(
    ddo_kernel,
    tmp_path,
):
    from corpus_structure.semantic.pdf_contracts import store_pdf_original

    kernel = ddo_kernel
    prepared, model = kernel.prepared, kernel.model
    with kernel.engine.begin() as connection:
        runtime = kernel.preparation.runtime
        acquired = _register_document(connection, kernel, tmp_path)
        document = connection.execute(
            text("SELECT id,key,content_hash FROM kb.document WHERE key=:key"),
            {"key": acquired.reference.document_key},
        ).one()
        intent = freeze_demand(
            model,
            roots=(acquired.root,),
            targets=("urn:original-fact-test:consume",),
            inference="inference:original-pdf",
            execution_profile="execution:original-pdf",
            original_sources=(acquired.selection(),),
        )
        storage = DataOperationStorage(connection)
        planner = DemandPlanner(model, storage)
        demand = planner.register(
            intent,
            project=acquired.reference.project_id,
            release=prepared.release_id,
            runtime=runtime.runtime_id,
        )
        snapshot = storage.read_demand_result({"demand_id": demand["demand_id"]})
        assert len(snapshot["original_source_admissions"]) == 1
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 0
        # Source-only selections must retain authentic bytes even before any inference
        # episode exists. Export and verification use the same admitted native cut.
        from corpus_structure.serve.demand_export import export_demand_result, verify_demand_export

        destination = tmp_path / "original-only-export"
        manifest = export_demand_result(
            connection,
            demand["demand_id"],
            project_id=acquired.reference.project_id,
            destination=destination,
            page_rows=1,
        )
        stored_original = connection.scalar(
            text("SELECT content FROM kb.source_artifact WHERE artifact_digest=:digest"),
            {"digest": document.content_hash},
        )
        assert (
            destination / manifest["source_artifacts"][document.content_hash]
        ).read_bytes() == stored_original
        assert (
            verify_demand_export(
                destination,
                manifest_digest=manifest["manifest_digest"],
            )["cut_id"]
            == manifest["cut_id"]
        )
    with kernel.engine.begin() as connection:
        storage = DataOperationStorage(connection)
        planner = DemandPlanner(model, storage)
        (ready,) = planner.ready(snapshot, authorization=b"{}")
        item_result = storage.claim_data_requests(
            typing_cast(
                WireClaimDataRequestsRequest,
                {
                    "holder": "raw-pdf-owner",
                    "lease_seconds": 30,
                    "items": [
                        {
                            "request_id": json.loads(ready.native)["request_id"],
                            "generation": json.loads(ready.native)["generation"],
                        }
                    ],
                },
            )
        )["items"][0]
        assert item_result["state"] == "claimed", item_result
        claim = item_result["result"]
        assert claim["state"] == "claimed"
        original = connection.scalar(
            text("SELECT content FROM kb.source_artifact WHERE artifact_digest=:digest"),
            {"digest": document.content_hash},
        )
        # A claimed request supplies real runless context, but an arbitrary fixture
        # carrying pdf-native preparation is not an admitted PDF implementation.
        # Positive stage/publication custody is covered by the genuine capture test.
        with connection.begin_nested() as savepoint:
            with pytest.raises(DBAPIError, match="owner/capability/support"):
                store_pdf_original(
                    connection,
                    task_id=claim["task_id"],
                    attempt=claim["attempt"],
                    holder=claim["holder"],
                    original=original,
                    recipe_bytes=b'{"recipe":"unadmitted-generic-pdf-capability"}',
                )
            savepoint.rollback()
        context = (
            connection.execute(
                text("SELECT * FROM ops.pdf_task_context(:task)"),
                {
                    "task": claim["task_id"],
                },
            )
            .mappings()
            .one()
        )
        assert "run_id" not in context
        assert context["request_id"] == claim["request_id"]
        assert context["generation"] == claim["generation"]
        assert context["document_id"] == document.id
        assert (
            connection.scalar(
                text("SELECT count(*) FROM ops.pdf_stage_build WHERE task_id=:task"),
                {"task": claim["task_id"]},
            )
            == 0
        )


def _register_document(connection, kernel, tmp_path):
    from corpus_structure.semantic.identifiers import ProjectId, ReleaseId

    project = "original-factual-support"
    DataOperationStorage(connection).initialize_source_project(
        {
            "project_id": ProjectId(project),
            "release_id": ReleaseId(kernel.prepared.release_id),
        }
    )
    original = b"%PDF-1.7\n% retained independent original bytes\n%%EOF\n"
    path = tmp_path / "original.pdf"
    path.write_bytes(original)
    register_original_document(
        connection,
        prepared=kernel.prepared,
        project_id=project,
        source_uri="original.pdf",
        original_path=str(path),
        original=original,
        mime="application/pdf",
    )
    from hashlib import sha256

    from corpus_structure.core.evidence import document_key

    key = document_key(project, "original.pdf", sha256(original).hexdigest())
    path.unlink()
    return acquire_original_document_selection(connection, project_id=project, document_key=key)
