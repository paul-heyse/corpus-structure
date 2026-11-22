"""Fixed protocol compilation and genuine installed native demand/publication controls."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from threading import Barrier
from typing import Any
from typing import cast as typing_cast

import pytest
from sqlalchemy import insert, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._data_operation_wire import (
    WireAdoptDataCompletionIntentRequest,
    WireAttachDataRequestRequest,
    WireAttachDataRequestsRequest,
    WireClaimDataRequestsRequest,
    WireInspectDataCompletionRequest,
    WireOperationId,
    WirePublishDataDerivationRequest,
    WireReadDemandResultRequest,
    WireRecordDataFateRequest,
    WireRegisterDataDemandRequest,
    WireReleaseDataAttemptRequest,
    WireRenewDataRequestRequest,
    WireRetainDataCompletionIntentRequest,
    WireRevokeDataSupportRequest,
    WireSelectDataPopulationRequest,
)
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_identity import SemanticRequestKey, canonical_identity
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.native_protocol_authoring import (
    native_operation_calls,
    native_operation_declarations,
    native_protocol_sources,
    native_source_digest,
)
from semantic.data_operation_binding_support import BINDING_RANGE_CASES, BindingEvidenceCase
from semantic.data_operation_demand_support import (
    attach,
    cancel_demand,
    claim,
    expire_lease,
    publish,
    retain,
)
from semantic.data_operation_kernel_support import POPULATION, STORAGE
from test_preparation import preparation_fixture


def test_kernel_protocol_is_captured_effective_meaning_not_an_ambient_catalog():
    captured = native_protocol_sources()
    declaration = native_operation_declarations(captured)
    model = compile_data_operations(declarations=(declaration,), captured_contracts=captured)
    calls = native_operation_calls(model, sources=captured)
    assert {owner for owner, _ in calls} == {
        operation.semantic_id for operation in model.operations
    }
    assert all(call.parameters[0].native_parameter == "p_payload" for _, call in calls)
    assert all(call.result_fields[0].native_field == "payload" for _, call in calls)
    from corpus_structure.semantic.native_protocol_authoring import native_program_closures

    closures = native_program_closures(captured)
    assert all(
        call.source_digest == closures.operations[owner.removeprefix("data.")]
        for owner, call in calls
    )
    altered = tuple(
        replace(source, content=source.content + b"\n-- changed native behavior\n")
        if source.name.endswith(".sql")
        else source
        for source in captured
    )
    changed = compile_data_operations(
        declarations=(native_operation_declarations(altered),), captured_contracts=altered
    )
    original = {(i.owner, i.domain): i.key for i in model.identities}
    revised = {(i.owner, i.domain): i.key for i in changed.identities}
    assert (
        original["data.publish_data_derivation", "recipe"]
        != revised["data.publish_data_derivation", "recipe"]
    )
    assert native_operation_declarations(captured).content == declaration.content
    with pytest.raises(ValueError, match="captured"):
        native_operation_calls(model, sources=())


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_atomic_publication_and_exact_receipt_replay(ddo_kernel):
    demand, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence, outputs=(1, 2))
    first = publish(ddo_kernel, fence, intent)
    assert first["replayed"] is False
    second = publish(ddo_kernel, fence, intent)
    assert second == {**first, "replayed": True}
    with ddo_kernel["engine"].connect() as connection:
        result = DataOperationStorage(connection).read_demand_result(
            typing_cast(WireReadDemandResultRequest, {**demand, "view": "products"})
        )
        assert result["intent"]["root_operations"] == ["urn:ddo-test:source"]
        assert result["uses"][0]["fate"] == "fulfilled"
        assert [p["body"] for p in result["uses"][0]["products"]] == [
            ["integer", "1"],
            ["integer", "2"],
        ]
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 1
        assert connection.scalar(text("SELECT count(*) FROM ops.data_publication_receipt")) == 1


def _undetermined_storage_recipe():
    assert STORAGE.declaration_content is not None
    declaration = json.loads(STORAGE.declaration_content)
    (source,) = [
        operation
        for operation in declaration["operations"]
        if operation["id"] == "urn:ddo-test:source"
    ]
    source["validity_family"] = ["undetermined"]
    return replace(
        STORAGE, name="undetermined-storage", declaration_content=json.dumps(declaration).encode()
    )


@pytest.mark.parametrize(
    "ddo_kernel", [_undetermined_storage_recipe()], indirect=True, ids=["undetermined"]
)
def test_native_undetermined_source_publishes_with_conservative_validity(ddo_kernel):
    from corpus_structure.semantic.data_operation_admission import inspect_data_operation_release

    operation = "urn:ddo-test:source"
    prepared = ddo_kernel["prepared"]
    assert any(
        diagnostic.code == "validity_undetermined"
        and diagnostic.location == operation
        and diagnostic.outcome == "advisory"
        for diagnostic in prepared.diagnostics
    )
    demand, _, _, attached = attach(ddo_kernel, operation=operation)
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence, outputs=(17,))
    receipt = publish(ddo_kernel, fence, intent)
    with ddo_kernel["engine"].connect() as connection:
        _, admission = inspect_data_operation_release(connection, prepared, validity_only=True)
        result = DataOperationStorage(connection).read_demand_result(
            typing_cast(WireReadDemandResultRequest, {**demand, "view": "products"})
        )
    assert operation in admission["conservative_operations"]
    (use,) = result["uses"]
    assert use["fate"] == "fulfilled"
    assert use["derivation_id"] == receipt["derivation_id"]
    assert [product["body"] for product in use["products"]] == [["integer", "17"]]


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_zero_output_has_authentic_fulfillment(ddo_kernel):
    demand, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence, outputs=(), outcome="empty")
    publish(ddo_kernel, fence, intent)
    with ddo_kernel["engine"].connect() as connection:
        result = DataOperationStorage(connection).read_demand_result(
            typing_cast(WireReadDemandResultRequest, demand)
        )
        assert result["uses"][0]["fate"] == "fulfilled"
        assert result["uses"][0]["products"] == []
        assert result["uses"][0]["derivation_id"]


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_precise_fractional_context_survives_native_attach_publish_and_read(ddo_kernel):
    scope = b'{"coordinate":0.12345678901234567890123456789}'
    demand, _, wire, attached = attach(ddo_kernel, analyzed_scope=json_loads(scope))
    fence = claim(ddo_kernel, attached)
    publish(ddo_kernel, fence, retain(ddo_kernel, fence))
    with ddo_kernel["engine"].begin() as connection:
        result = DataOperationStorage(connection).read_demand_result(
            typing_cast(WireReadDemandResultRequest, {**demand, "view": "products"})
        )
        assert json_bytes(result["root"][0]["analyzed_scope"]) == scope
        assert json_bytes(result["obligations"][0]["analyzed_scope"]) == scope
        assert json_bytes(result["uses"][0]["products"][0]["analyzed_scope"]) == scope
        assert result["uses"][0]["fate"] == "fulfilled"
        assert attached["request_id"] == wire["request_key"]


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_concurrent_attach_uses_one_visible_request_and_existing_task(ddo_kernel):
    _, _, wire, original = attach(ddo_kernel)
    barrier = Barrier(2)

    def once():
        with ddo_kernel["engine"].begin() as connection:
            barrier.wait(timeout=10)
            item_result = DataOperationStorage(connection).attach_data_requests(
                typing_cast(
                    WireAttachDataRequestsRequest,
                    {
                        "read_id": wire["binding"]["read_id"],
                        "items": [typing_cast(WireAttachDataRequestRequest, wire)],
                    },
                )
            )["items"][0]
            assert item_result["state"] != "refused", item_result
            return item_result["result"]

    with ThreadPoolExecutor(max_workers=2) as workers:
        a, b = list(workers.map(lambda _: once(), range(2)))
    assert a["request_id"] == b["request_id"] == original["request_id"]
    assert a["task_id"] == b["task_id"] == original["task_id"]
    with ddo_kernel["engine"].connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM ops.data_request")) == 1
        assert (
            connection.scalar(
                text("SELECT count(*) FROM ops.task WHERE data_request_id IS NOT NULL")
            )
            == 1
        )


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_conflicting_same_attempt_intent_is_rejected(ddo_kernel):
    _, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    original = retain(ddo_kernel, fence)
    assert retain(ddo_kernel, fence) == original
    with pytest.raises(DBAPIError, match="immutable"):
        retain(ddo_kernel, fence, outputs=(2,))


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_expired_owner_cannot_publish_but_exact_intent_can_be_adopted(ddo_kernel):
    _, _, wire, attached = attach(ddo_kernel)
    first = claim(ddo_kernel, attached, seconds=1)
    intent = retain(ddo_kernel, first)
    with ddo_kernel["engine"].begin() as connection:
        item_result = DataOperationStorage(connection).attach_data_requests(
            typing_cast(
                WireAttachDataRequestsRequest,
                {
                    "read_id": wire["binding"]["read_id"],
                    "items": [typing_cast(WireAttachDataRequestRequest, wire)],
                },
            )
        )["items"][0]
        assert item_result["state"] != "refused", item_result
        reconciliation = item_result["result"]
        assert reconciliation["action"] == "reconcile"
        assert reconciliation["retained_intent_id"] == intent["intent_id"]
    expire_lease(ddo_kernel, first)
    second = claim(ddo_kernel, attached, holder="successor")
    assert second["attempt"] == first["attempt"] + 1
    with pytest.raises(DBAPIError, match="adopted"):
        retain(ddo_kernel, second, outputs=(2,))
    with pytest.raises(DBAPIError, match="stale"):
        publish(ddo_kernel, first, intent)
    with ddo_kernel["engine"].begin() as connection:
        adopted = DataOperationStorage(connection).adopt_data_completion_intent(
            typing_cast(
                WireAdoptDataCompletionIntentRequest,
                {
                    **second,
                    "intent_id": intent["intent_id"],
                },
            )
        )
        assert adopted["producer_attempt"] == first["attempt"]
    receipt = publish(ddo_kernel, second, intent)
    with ddo_kernel["engine"].connect() as connection:
        assert connection.execute(
            text("SELECT producer_attempt,producer_task_id FROM ops.data_derivation")
        ).one() == (first["attempt"], first["task_id"])
        assert (
            connection.scalar(text("SELECT publishing_attempt FROM ops.data_publication_receipt"))
            == second["attempt"]
        )
        inspected = DataOperationStorage(connection).inspect_data_completion(
            typing_cast(
                WireInspectDataCompletionRequest,
                {
                    "request_id": first["request_id"],
                    "generation": first["generation"],
                    "intent_id": intent["intent_id"],
                },
            )
        )
        assert inspected["state"] == "committed"
        assert inspected["receipt_id"] == receipt["receipt_id"]


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
@pytest.mark.parametrize("active", [False, True])
def test_invalid_retained_runtime_rebinds_generation_only_after_lease_expiry(ddo_kernel, active):
    from corpus_structure.semantic.data_operation_runtime import prepare_data_operation_runtime
    from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding

    # Revocation has a real scoped producing episode; the unresolved intent is
    # another execution under that same runtime, rather than forged test state.
    _, _, _, prior = attach(ddo_kernel, subject="subject:published")
    prior_fence = claim(ddo_kernel, prior)
    publish(ddo_kernel, prior_fence, retain(ddo_kernel, prior_fence))
    demand, _, wire, attached = attach(ddo_kernel)
    first = claim(ddo_kernel, attached, seconds=30 if active else 1)
    intent = retain(ddo_kernel, first)
    replacement = prepare_data_operation_runtime(
        ddo_kernel["prepared"],
        ddo_kernel["runtime_inputs"],
        execution_profile="execution:test",
        observed={"host": "replacement"},
    )
    with ddo_kernel["engine"].begin() as connection:
        persist_runtime_binding(connection, ddo_kernel["prepared"], replacement)
        DataOperationStorage(connection).revoke_data_support(
            typing_cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": "ddo-test",
                    "original_source": "source:test",
                    "selector_kind": "runtime",
                    "selector": ddo_kernel["runtime"],
                    "reason": "producer runtime defect",
                },
            )
        )
    updated = {**ddo_kernel, "runtime": replacement.runtime_id}
    selected = demand["selection"]
    with ddo_kernel["engine"].begin() as connection:
        replacement_demand = DataOperationStorage(connection).register_data_demand(
            typing_cast(
                WireRegisterDataDemandRequest,
                {
                    "project_id": "ddo-test",
                    "release_id": ddo_kernel["prepared"].release_id,
                    "runtime_id": replacement.runtime_id,
                    "root": selected["roots"],
                    "selection": selected,
                    "strength": "value",
                },
            )
        )
        replacement_read = DataOperationStorage(connection).read_demand_result(
            {"demand_id": replacement_demand["demand_id"]}
        )
    replacement_wire = {
        **wire,
        "obligation_id": replacement_read["obligations"][0]["obligation_id"],
        "binding": {**wire["binding"], "read_id": replacement_read["read_id"]},
    }
    if active:
        with ddo_kernel["engine"].begin() as connection:
            refused = DataOperationStorage(connection).attach_data_requests(
                typing_cast(
                    WireAttachDataRequestsRequest,
                    {
                        "read_id": replacement_read["read_id"],
                        "items": [replacement_wire],
                    },
                )
            )["items"][0]
            assert refused["state"] == "refused" and "active producer lease" in refused["reason"]
            assert (
                connection.scalar(
                    text("SELECT generation FROM ops.data_request WHERE id=:r"),
                    {"r": first["request_id"]},
                )
                == first["generation"]
            )
        return
    expire_lease(ddo_kernel, first)
    with ddo_kernel["engine"].begin() as connection:
        revoked_read = DataOperationStorage(connection).read_demand_result(
            {"demand_id": demand["demand_id"]}
        )
    with ddo_kernel["engine"].begin() as connection:
        refused = DataOperationStorage(connection).attach_data_requests(
            typing_cast(
                WireAttachDataRequestsRequest,
                {
                    "read_id": revoked_read["read_id"],
                    "items": [
                        {**wire, "binding": {**wire["binding"], "read_id": revoked_read["read_id"]}}
                    ],
                },
            )
        )["items"][0]
        assert (
            refused["state"] == "refused" and "replacement runtime or recipe" in refused["reason"]
        )
    _, _, _, current = attach(updated)
    assert current["request_id"] == first["request_id"]
    assert current["generation"] == first["generation"] + 1
    assert current["task_id"] != first["task_id"]
    assert current["action"] == "compute"
    assert current["retained_intent_id"] is None
    with ddo_kernel["engine"].connect() as connection:
        storage = DataOperationStorage(connection)
        historical = storage.inspect_data_completion(
            typing_cast(
                WireInspectDataCompletionRequest,
                {
                    "demand_id": demand["demand_id"],
                    "request_id": first["request_id"],
                    "generation": first["generation"],
                    "intent_id": intent["intent_id"],
                },
            )
        )
        assert historical["state"] == "known-uncommitted"
        assert historical["intent_retained"] is True
        # Publication authority was replaced; physical retirement was not asserted.
        assert (
            connection.scalar(
                text("SELECT status FROM ops.task WHERE id=:t"), {"t": first["task_id"]}
            )
            == "running"
        )
        assert (
            connection.scalar(
                text("SELECT count(*) FROM ops.data_request_generation WHERE request_id=:r"),
                {"r": first["request_id"]},
            )
            == 2
        )
    successor = claim(updated, current, holder="replacement")
    with pytest.raises(DBAPIError, match="stale"):
        publish(ddo_kernel, first, intent)
    next_intent = retain(updated, successor, outputs=(2,))
    receipt = publish(updated, successor, next_intent)
    assert receipt["replayed"] is False
    with ddo_kernel["engine"].begin() as connection:
        observed = DataOperationStorage(connection).read_demand_result(
            typing_cast(WireReadDemandResultRequest, demand)
        )
    wire = {**wire, "binding": {**wire["binding"], "read_id": observed["read_id"]}}
    with ddo_kernel["engine"].begin() as connection:
        response = DataOperationStorage(connection).attach_data_requests(
            typing_cast(
                WireAttachDataRequestsRequest,
                {
                    "read_id": observed["read_id"],
                    "items": [wire],
                },
            )
        )["items"][0]
        assert response["state"] == "fulfilled"
        again = response["result"]
        assert again["generation"] == current["generation"]
        assert again["fate"] == "fulfilled"


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
@pytest.mark.parametrize("bad", ["body", "kind", "role", "member"])
def test_deliberate_invalid_native_output_rolls_back_every_row(ddo_kernel, bad):
    _, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)

    def change(payload):
        output = payload["outputs"][0]
        if bad == "body":
            output["product"]["body"] = ["string", "not integer"]
        elif bad == "kind":
            output["product"]["kind_contract"] = "kind:missing"
        elif bad == "role":
            output["role"] = "undeclared"
        else:
            output["member_id"] = "missing-local-member"

    if bad == "kind":
        # The retention guard resolves the nominal kind before accepting an intent.
        with pytest.raises(DBAPIError) as missing:
            retain(ddo_kernel, fence, mutate=change)
        assert getattr(missing.value.orig, "sqlstate", None) == "P0002"
    else:
        intent = retain(ddo_kernel, fence, mutate=change)
        with pytest.raises(DBAPIError):
            publish(ddo_kernel, fence, intent)
    with ddo_kernel["engine"].connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM kb.data_product")) == 0
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 0
        assert connection.scalar(text("SELECT count(*) FROM ops.data_publication_receipt")) == 0
        assert (
            connection.scalar(text("SELECT status FROM ops.task WHERE data_request_id IS NOT NULL"))
            == "running"
        )


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_revoked_receipt_stays_inspectable_while_current_admission_changes_generation(ddo_kernel):
    demand, _, wire, attached = attach(ddo_kernel)
    first = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, first)
    receipt = publish(ddo_kernel, first, intent)
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        revoked = storage.revoke_data_support(
            typing_cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": "ddo-test",
                    "original_source": "source:test",
                    "selector_kind": "derivation",
                    "selector": receipt["derivation_id"],
                    "reason": "independent producer defect",
                },
            )
        )
        assert revoked["epoch"] == 1
        inspected = storage.inspect_data_completion(
            typing_cast(
                WireInspectDataCompletionRequest,
                {
                    "request_id": first["request_id"],
                    "generation": first["generation"],
                    "intent_id": intent["intent_id"],
                },
            )
        )
        assert inspected["state"] == "committed"
        result = storage.read_demand_result(typing_cast(WireReadDemandResultRequest, demand))
        assert result["uses"][0]["fate"] == "unavailable"
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        item_result = storage.attach_data_requests(
            typing_cast(
                WireAttachDataRequestsRequest,
                {
                    "read_id": result["read_id"],
                    "items": [
                        typing_cast(
                            WireAttachDataRequestRequest,
                            {**wire, "binding": {**wire["binding"], "read_id": result["read_id"]}},
                        )
                    ],
                },
            )
        )["items"][0]
        assert item_result["state"] != "refused", item_result
        current = item_result["result"]
        assert current["generation"] == first["generation"] + 1
        assert current["task_id"] != first["task_id"]
    assert publish(ddo_kernel, first, intent)["receipt_id"] == receipt["receipt_id"]


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_discovery_refuses_arbitrary_member_and_completeness_injection(ddo_kernel):
    demand, _, _, _ = attach(ddo_kernel)
    with ddo_kernel["engine"].begin() as connection, pytest.raises(DBAPIError, match="wire"):
        connection.execute(
            text("SELECT ops.close_data_population(CAST(:p AS jsonb))"),
            {
                "p": json.dumps(
                    {
                        "demand_id": demand["demand_id"],
                        "name": "sentences",
                        "members": ["invented"],
                        "complete": True,
                        "evidence": {"trust": "me"},
                    }
                )
            },
        )


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_atomic_registration_materializes_only_its_frozen_root_context(ddo_kernel):
    demand, _, _, _ = attach(ddo_kernel)
    with ddo_kernel["engine"].begin() as connection:
        result = DataOperationStorage(connection).read_demand_result(
            {"demand_id": demand["demand_id"]}
        )
        assert {
            (row["subject"], row["original_source"], json_bytes(row["analyzed_scope"]))
            for row in result["obligations"]
        } == {
            (root["subject"], root["original_source"], json_bytes(root["analyzed_scope"]))
            for root in demand["selection"]["roots"]
        }
        assert all(row["subject"] != "invented" for row in result["obligations"])


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_global_independent_strength_refuses_without_a_group_contract(ddo_kernel):
    from corpus_structure.semantic.data_operation_demands import RootSubject, freeze_demand

    selected = freeze_demand(
        ddo_kernel["model"],
        roots=(RootSubject("subject:independent", "source:test", b"{}"),),
        targets=("urn:ddo-test:source",),
        inference="inference:test",
        execution_profile="execution:test",
    ).record
    with (
        ddo_kernel["engine"].begin() as connection,
        pytest.raises(DBAPIError, match="distinct-episode"),
    ):
        DataOperationStorage(connection).register_data_demand(
            typing_cast(
                WireRegisterDataDemandRequest,
                {
                    "project_id": "ddo-test",
                    "release_id": ddo_kernel["prepared"].release_id,
                    "runtime_id": ddo_kernel["runtime"],
                    "root": selected["roots"],
                    "selection": selected,
                    "strength": "independent",
                },
            )
        )


@pytest.mark.parametrize("native_read", [None], indirect=True, ids=["storage"])
def test_native_normalized_values_match_independent_exact_vectors(native_read):
    vectors = [
        ('["integer","+001"]', '["integer","1"]'),
        ('["decimal","-0.000"]', '["decimal","0"]'),
        ('["decimal","1.200e+1"]', '["decimal","12"]'),
        ('["float","-0x0.0p+0"]', '["float","-0x0.0p+0"]'),
        ('["float","0x0.0000000000001p-1022"]', '["float","0x0.0000000000001p-1022"]'),
        ('["float","0x1.fffffffffffffp+1023"]', '["float","0x1.fffffffffffffp+1023"]'),
        (
            '["datetime","2026-11-13T12:34:56.123456+00:00"]',
            '["datetime","2026-11-13T12:34:56.123456+00:00"]',
        ),
    ]
    # Keep the existing storage-vector identity; no kernel admission is needed.
    connection = native_read
    for supplied, expected in vectors:
        actual = connection.scalar(
            text("SELECT data.ddo_normalize(CAST(:v AS jsonb))"), {"v": supplied}
        )
        assert actual == json.loads(expected)
    for malformed in (
        '["float","0x1.0p+0"]',
        '["float","0x1.0000000000000p-0"]',
        '["float","0x1.0000000000000p+1024"]',
        '["datetime","invalid+00:00"]',
        '["datetime","2026-02-30T00:00:00+00:00"]',
        '["datetime","2026-11-13T12:34:56.000000+00:00"]',
    ):
        with connection.begin_nested() as savepoint:
            with pytest.raises(DBAPIError):
                connection.execute(
                    text("SELECT data.ddo_normalize(CAST(:v AS jsonb))"), {"v": malformed}
                )
            savepoint.rollback()


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_integer_kind_rejects_equivalent_json_number_with_wrong_meaning_tag(ddo_kernel):
    _, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    intent = retain(
        ddo_kernel,
        fence,
        mutate=lambda completion: completion["outputs"][0]["product"].update(body=["decimal", "1"]),
    )
    with pytest.raises(DBAPIError, match="body violates"):
        publish(ddo_kernel, fence, intent)


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_directly_revoked_producer_cannot_be_rehabilitated_by_rebinding(ddo_kernel):
    demand, _, wire, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence)
    receipt = publish(ddo_kernel, fence, intent)
    with ddo_kernel["engine"].begin() as connection:
        DataOperationStorage(connection).revoke_data_support(
            typing_cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": "ddo-test",
                    "original_source": "source:test",
                    "selector_kind": "derivation",
                    "selector": receipt["derivation_id"],
                    "reason": "producer behavior is defective",
                },
            )
        )
    with ddo_kernel["engine"].begin() as connection:
        fresh = DataOperationStorage(connection).read_demand_result(
            typing_cast(WireReadDemandResultRequest, demand)
        )
    wire = {**wire, "binding": {**wire["binding"], "read_id": fresh["read_id"]}}
    with ddo_kernel["engine"].begin() as connection:
        response = DataOperationStorage(connection).attach_data_requests(
            typing_cast(
                WireAttachDataRequestsRequest,
                {
                    "read_id": fresh["read_id"],
                    "items": [{**wire, "rebind_derivation": receipt["derivation_id"]}],
                },
            )
        )["items"][0]
        assert response["state"] == "refused" and "rehabilitate" in response["reason"]


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_failed_completion_is_historical_but_never_reusable_fulfillment(ddo_kernel):
    demand, _, wire, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence, outputs=(), outcome="failed")
    receipt = publish(ddo_kernel, fence, intent)
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        observed = storage.read_demand_result(typing_cast(WireReadDemandResultRequest, demand))
        assert observed["uses"][0]["fate"] == "failed"
        assert observed["uses"][0]["completion_state"] == "failed"
        assert observed["uses"][0]["products"] == []
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        item_result = storage.attach_data_requests(
            typing_cast(
                WireAttachDataRequestsRequest,
                {
                    "read_id": wire["binding"]["read_id"],
                    "items": [typing_cast(WireAttachDataRequestRequest, wire)],
                },
            )
        )["items"][0]
        assert item_result["state"] != "refused", item_result
        current = item_result["result"]
        assert current["fate"] == "attached"
        assert current["derivation_id"] is None
        assert current["generation"] == attached["generation"] + 1
        historical = storage.inspect_data_completion(
            typing_cast(
                WireInspectDataCompletionRequest,
                {
                    "demand_id": demand["demand_id"],
                    "intent_id": intent["intent_id"],
                },
            )
        )
        assert historical["state"] == "committed"
        assert historical["receipt_id"] == receipt["receipt_id"]


def _protected_binding_case(
    ddo_kernel, case: BindingEvidenceCase, *, prepare_only=False
) -> tuple[dict[str, Any], SemanticRequestKey]:
    from decimal import Decimal

    from corpus_structure.semantic.data_operation_identity import SemanticRequestKey
    from corpus_structure.semantic.data_operation_values import OptionalValue

    sample_value = case.sample_value
    assert sample_value is not None
    targets = ("urn:ddo-test:sample", "urn:ddo-test:consumer")
    demand, _, _, attached = attach(ddo_kernel, operation="urn:ddo-test:sample", targets=targets)
    fence = claim(ddo_kernel, attached)
    sample_kind = next(
        i.key
        for i in ddo_kernel["model"].identities
        if i.domain == "kind"
        and any(k.semantic_id == i.owner and k.name == "Sample" for k in ddo_kernel["model"].kinds)
    )
    completion = {
        "outcome": "success",
        "inputs": [],
        "support": [],
        "implementation_revision": "native-test-source-v1",
        "outputs": [
            {
                "role": "result",
                "position": 0,
                "multiplicity": 1,
                "product": {
                    "kind_contract": sample_kind,
                    "body": semantic_value({"value": sample_value}),
                    "members": [],
                },
            }
        ],
    }
    with ddo_kernel["engine"].begin() as connection:
        intent = DataOperationStorage(connection).retain_data_completion_intent(
            typing_cast(
                WireRetainDataCompletionIntentRequest,
                {**fence, "runtime_id": ddo_kernel["runtime"], "completion": completion},
            )
        )
    receipt = publish(ddo_kernel, fence, intent)
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        result = storage.read_demand_result(typing_cast(WireReadDemandResultRequest, demand))
        use = result["uses"][0]
        product = use["products"][0]["product_id"]
        # The same authored range case drives the PostgreSQL full-result check
        # and this real admitted-product/protected-writer observation.
        native_row = connection.execute(
            text(
                "SELECT body FROM ops.data_binding_rows(:d,:o,CAST(:t AS jsonb),"
                ":read,:subject,CAST(:source AS jsonb),CAST(:scope AS jsonb))"
            ),
            {
                "d": demand["demand_id"],
                "o": "urn:ddo-test:consumer",
                "t": json.dumps(result["trust_snapshot"]),
                "read": result["read_id"],
                "subject": result["root"][0]["subject"],
                "source": json.dumps(result["root"][0]["original_source"]),
                "scope": json.dumps(result["root"][0]["analyzed_scope"]),
            },
        ).scalar_one()
        assert native_row == {"value": sample_value}
        obligation = next(
            row for row in result["obligations"] if row["operation_id"] == "urn:ddo-test:consumer"
        )
        # Authored scalar-input meaning, independent of the compiled binder and
        # project_operation_binding. Only opaque identities come from real custody.
        member = {
            "product": product,
            "kind": sample_kind,
            "subject": "subject:one",
            "subject_definition": "original-occurrence",
            "member": None,
            "original_source": "source:test",
            "analyzed_scope": {"page": Decimal(1)},
            "coverage": [],
            "position": None,
            "multiplicity": 1,
            "support_episodes": (receipt["derivation_id"],),
        }
        request = SemanticRequestKey(
            ddo_kernel["identities"]["urn:ddo-test:consumer", "recipe"],
            "subject:one",
            {
                "source": {
                    "value": OptionalValue("present", (member,)),
                    "population_witness": None,
                    "selected_alternative": None,
                }
            },
            {"parameters": {}, "replicate": None},
            "inference:test",
            subject_context=SubjectContext(
                "ddo-test",
                "subject:one",
                "source:test",
                b'{"page":1}',
                subject_definition="original-occurrence",
            ),
        )
        payload: dict[str, Any] = {
            "obligation_id": obligation["obligation_id"],
            "replicate": None,
            "request_key": request.identity.key,
            "request_meaning": json.loads(request.identity.canonical_input),
            "binding": {
                "inputs": [
                    {
                        "role": "source",
                        "position": 0,
                        "multiplicity": 1,
                        "product_id": product,
                        "member_id": None,
                        "producer_output": {
                            "member_id": None,
                            "multiplicity": 1,
                            "position": 0,
                            "role": "result",
                        },
                        "support_derivation_ids": [receipt["derivation_id"]],
                    }
                ],
                "support": [
                    {
                        "role": "source",
                        "position": 0,
                        "derivation_id": receipt["derivation_id"],
                        "admission_use_id": use["use_id"],
                    }
                ],
                "parameters": semantic_value(request.parameters),
                "request_inputs": semantic_value(request.inputs),
                "inference": "inference:test",
                "populations": [],
                "read_id": result["read_id"],
            },
        }
    if prepare_only:
        return payload, request

    with ddo_kernel.purpose("write").begin() as writer:
        item = writer.scalar(
            text("SELECT ops.attach_data_requests(CAST(:p AS jsonb))"),
            {"p": json.dumps({"read_id": payload["binding"]["read_id"], "items": [payload]})},
        )["payload"]["items"][0]
        if case.native_refusal is not None:
            sqlstate, message = case.native_refusal
            assert item["state"] == "refused"
            assert item["sqlstate"] == sqlstate and message in item["reason"]
        else:
            assert item["state"] == "attached"
            assert item["result"]["request_id"] == request.identity.key
    with ddo_kernel["engine"].connect() as connection:
        retained = (
            connection.execute(
                text(
                    "SELECT binding FROM ops.data_request WHERE operation_id='urn:ddo-test:consumer'"
                )
            )
            .scalars()
            .all()
        )
        if case.native_refusal is not None:
            assert retained == []
        else:
            assert retained == [{**payload["binding"], "execution_profile": "execution:test"}]
    return payload, request


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_direct_writer_cannot_bypass_admitted_binding_predicate_with_real_inputs(ddo_kernel):
    _protected_binding_case(ddo_kernel, BINDING_RANGE_CASES["range-outside"])


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_actual_writer_admits_exact_authored_binding_and_retains_every_input(ddo_kernel):
    _protected_binding_case(ddo_kernel, BINDING_RANGE_CASES["range-ready"])


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_actual_writer_rejects_independently_authored_binding_substitutions(ddo_kernel):
    from copy import deepcopy

    from corpus_structure.semantic.data_operation_identity import SemanticRequestKey
    from corpus_structure.semantic.data_operation_values import OptionalValue

    baseline, authored = _protected_binding_case(
        ddo_kernel, BINDING_RANGE_CASES["range-ready"], prepare_only=True
    )
    # These are protected-admission obligations, not expression-only comparisons.
    reasons = (
        ("role-too-few", "23514", "native binding role cardinality differs"),
        ("extra-role", "23514", "request input roles differ from admitted definition"),
        ("missing-role", "23514", "missing request role"),
        ("unknown-input", "23514", "incomplete input cannot attach runnable request"),
        ("known-absent-required", "23514", "incomplete input cannot attach runnable request"),
        (
            "wrong-source-meaning",
            "23514",
            "semantic request member differs from native product/member",
        ),
        (
            "wrong-context-meaning",
            "23514",
            "semantic request member differs from native product/member",
        ),
        (
            "member-removed",
            "23514",
            "semantic binding has no exact native manifest member for role source",
        ),
        (
            "position-substitution",
            "23514",
            "selected input support set has no exact native binding row",
        ),
        (
            "support-episode-substitution",
            "23514",
            "semantic binding has no exact native manifest member for role source",
        ),
        (
            "unrequested-original-source-identity",
            "23514",
            "unrequested support identity cannot salt semantic input",
        ),
        (
            "unselected-alternative",
            "23514",
            "population meaning lacks exact native receipt locator",
        ),
    )
    statement = text("SELECT ops.attach_data_requests(CAST(:p AS jsonb))")

    with ddo_kernel.purpose("write").begin() as writer, ddo_kernel["engine"].connect() as observer:

        def effects():
            return tuple(
                observer.execute(
                    text(
                        "SELECT (SELECT count(*) FROM ops.data_request WHERE operation_id='urn:ddo-test:consumer'),"
                        "(SELECT count(*) FROM ops.task), (SELECT count(*) FROM ops.demand_use)"
                    )
                ).one()
            )

        before = effects()
        assert before[0] == 0 and before[1] > 0 and before[2] > 0
        for name, sqlstate, message, *_ in reasons:
            # The same admitted product and acquired read succeed under the writer
            # before each one-field semantic/manifest substitution; rollback it.
            with writer.begin_nested() as reach:
                accepted = writer.scalar(
                    statement,
                    {
                        "p": json.dumps(
                            {"read_id": baseline["binding"]["read_id"], "items": [baseline]}
                        )
                    },
                )["payload"]["items"][0]
                assert accepted["state"] == "attached"
                accepted = accepted["result"]
                assert accepted["request_id"] == authored.identity.key
                reach.rollback()
            assert effects() == before, name
            payload = deepcopy(baseline)
            role = dict(authored.inputs["source"])
            role["value"] = OptionalValue(
                "present", tuple(dict(member) for member in role["value"].value)
            )
            meaning = {"source": role}
            member = role["value"].value[0]
            if name == "role-too-few":
                role["value"] = OptionalValue("present", ())
                payload["binding"].update(inputs=[], support=[])
            elif name == "extra-role":
                meaning["unexpected"] = {
                    "value": OptionalValue("present", ()),
                    "population_witness": None,
                    "selected_alternative": None,
                }
            elif name == "missing-role":
                meaning = {}
                payload["binding"].update(inputs=[], support=[])
            elif name in {"unknown-input", "known-absent-required"}:
                role["value"] = OptionalValue(
                    "unknown" if name == "unknown-input" else "known-absent"
                )
                payload["binding"].update(inputs=[], support=[])
            elif name == "wrong-source-meaning":
                member["original_source"] = "other-original"
            elif name == "wrong-context-meaning":
                member["analyzed_scope"] = {"page": 2}
            elif name == "member-removed":
                member["member"] = "not-a-member"
                payload["binding"]["inputs"][0]["member_id"] = "not-a-member"
            elif name == "support-episode-substitution":
                member["support_episodes"] = ("unselected-episode",)
            elif name == "unrequested-original-source-identity":
                member["original_sources"] = ("unrequested-original",)
            elif name == "position-substitution":
                payload["binding"]["inputs"][0]["position"] = 1
                payload["binding"]["support"][0]["position"] = 1
            else:
                role["population_witness"] = {
                    "complete": True,
                    "members": [],
                    "selection": {},
                    "reason": "unselected-declared-branch",
                }
            request = SemanticRequestKey(
                authored.recipe,
                authored.subject,
                meaning,
                authored.parameters,
                authored.inference,
                subject_context=authored.subject_context,
            )
            payload.update(
                request_key=request.identity.key,
                request_meaning=json.loads(request.identity.canonical_input),
            )
            payload["binding"]["request_inputs"] = semantic_value(meaning)
            refused = writer.scalar(
                statement,
                {
                    "p": json.dumps(
                        {
                            "read_id": payload["binding"]["read_id"],
                            "items": [payload],
                        }
                    )
                },
            )["payload"]["items"][0]
            assert refused["state"] == "refused", name
            assert refused["sqlstate"] == sqlstate and message in refused["reason"], name
            assert effects() == before, name


@pytest.mark.parametrize("ddo_kernel", [POPULATION], indirect=True, ids=["population"])
def test_actual_writer_requires_exact_authored_closed_population_binding(ddo_kernel):
    from copy import deepcopy
    from decimal import Decimal

    from corpus_structure.semantic.data_operation_identity import SemanticRequestKey
    from corpus_structure.semantic.data_operation_values import CollectionValue, OptionalValue
    from semantic.data_operation_binding_support import discover

    demand, obligation, parent = discover(ddo_kernel, values=(15, 16))
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        read = storage.read_demand_result(typing_cast(WireReadDemandResultRequest, demand))
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        selected = storage.select_data_population(
            typing_cast(
                WireSelectDataPopulationRequest,
                {
                    **obligation,
                    "population_name": "selected-items",
                    "parent_population_id": parent["population_id"],
                    "read_id": read["read_id"],
                },
            )
        )
        assert [member["member_id"] for member in selected["members"]] == ["m15", "m16"]
        assert selected["complete"] is True
        current = storage.read_demand_result(typing_cast(WireReadDemandResultRequest, demand))
        rows = connection.execute(
            text(
                'SELECT member,subject,"position",multiplicity,body FROM ops.data_binding_rows('
                ":d,:o,CAST(:trust AS jsonb),:read,:subject,CAST(:source AS jsonb),CAST(:scope AS jsonb)) "
                'ORDER BY "position",member'
            ),
            {
                "d": demand["demand_id"],
                "o": "urn:consumer",
                "trust": json.dumps(current["trust_snapshot"]),
                "read": current["read_id"],
                "subject": "doc",
                "source": json.dumps("source:test"),
                "scope": '{"page":1}',
            },
        ).all()
        assert [tuple(row) for row in rows] == [
            ("m15", "item:15", 0, 1, {"value": 15, "document_subject": "doc"}),
            ("m16", "item:16", 0, 1, {"value": 16, "document_subject": "doc"}),
        ]
    product = parent["evidence"]["product_id"]
    episode = parent["evidence"]["derivation_id"]
    use = parent["evidence"]["admission_use_id"]
    sample_kind = ddo_kernel["identities"][
        next(kind.semantic_id for kind in ddo_kernel["model"].kinds if kind.name == "Sample"),
        "kind",
    ]
    # Both members belong to the producer's one output slot (position 0),
    # rather than acquiring an ordinal from their packet-array order.
    # Literal expected members and selected witness; no compiled binder, planner,
    # or project_operation_binding supplies the admission envelope.
    members = (
        {
            "product": canonical_identity("body", {"value": 15, "document_subject": "doc"}).key,
            "kind": sample_kind,
            "subject": "item:15",
            "subject_definition": "original-occurrence",
            "member": "m15",
            "original_source": "source:test",
            "analyzed_scope": {"page": Decimal(1)},
            "coverage": [],
            "position": None,
            "multiplicity": 1,
            "support_episodes": (episode,),
        },
        {
            "product": canonical_identity("body", {"value": 16, "document_subject": "doc"}).key,
            "kind": sample_kind,
            "subject": "item:16",
            "subject_definition": "original-occurrence",
            "member": "m16",
            "original_source": "source:test",
            "analyzed_scope": {"page": Decimal(1)},
            "coverage": [],
            "position": None,
            "multiplicity": 1,
            "support_episodes": (episode,),
        },
    )
    witness = {
        "identity": selected["semantic_key"],
        "complete": True,
        "members": ["m15", "m16"],
        "support_episodes": [episode],
    }
    meaning = {
        "items": {
            "value": OptionalValue("present", CollectionValue("set", members)),
            "population_witness": witness,
            "selected_alternative": None,
        }
    }
    binding = {
        "inputs": [
            {
                "role": "items",
                "position": 0,
                "multiplicity": 1,
                "product_id": product,
                "member_id": "m15",
                "producer_output": {
                    "member_id": None,
                    "multiplicity": 1,
                    "position": 0,
                    "role": "result",
                },
                "support_derivation_ids": [episode],
            },
            {
                "role": "items",
                "position": 0,
                "multiplicity": 1,
                "product_id": product,
                "member_id": "m16",
                "producer_output": {
                    "member_id": None,
                    "multiplicity": 1,
                    "position": 0,
                    "role": "result",
                },
                "support_derivation_ids": [episode],
            },
        ],
        "support": [
            {
                "role": "population:selected-items",
                "position": 0,
                "derivation_id": episode,
                "admission_use_id": use,
            },
            {"role": "items", "position": 0, "derivation_id": episode, "admission_use_id": use},
        ],
        "parameters": semantic_value({"parameters": {}, "replicate": None}),
        "request_inputs": semantic_value(meaning),
        "inference": "inference:test",
        "populations": [
            {"role": "items", "name": "selected-items", "population_id": selected["population_id"]}
        ],
        "read_id": current["read_id"],
    }

    def envelope(inputs, selected_binding):
        request = SemanticRequestKey(
            ddo_kernel["identities"]["urn:consumer", "recipe"],
            "doc",
            inputs,
            {"parameters": {}, "replicate": None},
            "inference:test",
            subject_context=SubjectContext(
                "ddo-test",
                "doc",
                "source:test",
                b'{"page":1}',
                subject_definition="original-occurrence",
            ),
        )
        return {
            "obligation_id": obligation["obligation_id"],
            "replicate": None,
            "request_key": request.identity.key,
            "request_meaning": json.loads(request.identity.canonical_input),
            "binding": {**selected_binding, "request_inputs": semantic_value(inputs)},
        }

    baseline = envelope(meaning, binding)
    statement = text("SELECT ops.attach_data_requests(CAST(:p AS jsonb))")
    reasons = (
        ("member-removed", "23514", "selected native input bundles violate frozen binding"),
        (
            "witness-member-removed",
            "23514",
            "population semantic witness differs from native closure value",
        ),
        (
            "witness-member-added",
            "23514",
            "population semantic witness differs from native closure value",
        ),
        (
            "witness-incomplete",
            "23514",
            "population semantic witness differs from native closure value",
        ),
        (
            "witness-receipt-missing",
            "23514",
            "population meaning lacks exact native receipt locator",
        ),
    )
    with ddo_kernel.purpose("write").begin() as writer, ddo_kernel["engine"].connect() as observer:
        before = tuple(
            observer.execute(
                text(
                    "SELECT (SELECT count(*) FROM ops.data_request WHERE operation_id='urn:consumer'), (SELECT count(*) FROM ops.task), (SELECT count(*) FROM ops.demand_use)"
                )
            ).one()
        )
        assert before[0] == 0 and before[1] > 0 and before[2] > 0
        for name, sqlstate, message in reasons:
            with writer.begin_nested() as reach:
                accepted = writer.scalar(
                    statement,
                    {
                        "p": json.dumps(
                            {"read_id": baseline["binding"]["read_id"], "items": [baseline]}
                        )
                    },
                )["payload"]["items"][0]
                assert accepted["state"] == "attached"
                accepted = accepted["result"]
                assert accepted["request_id"] == baseline["request_key"]
                reach.rollback()
            selected_meaning, selected_binding = deepcopy(meaning), deepcopy(binding)
            if name == "member-removed":
                selected_meaning["items"]["value"] = OptionalValue(
                    "present", CollectionValue("set", members[:1])
                )
                selected_binding["inputs"] = selected_binding["inputs"][:1]
                selected_binding["support"] = selected_binding["support"][:2]
            elif name == "witness-member-removed":
                selected_meaning["items"]["population_witness"]["members"] = ["m15"]
            elif name == "witness-member-added":
                selected_meaning["items"]["population_witness"]["members"] = [
                    "m15",
                    "m16",
                    "not-materialized",
                ]
            elif name == "witness-incomplete":
                selected_meaning["items"]["population_witness"]["complete"] = False
            else:
                selected_binding["populations"] = []
            payload = envelope(selected_meaning, selected_binding)
            refused = writer.scalar(
                statement,
                {
                    "p": json.dumps(
                        {
                            "read_id": payload["binding"]["read_id"],
                            "items": [payload],
                        }
                    )
                },
            )["payload"]["items"][0]
            assert refused["state"] == "refused", name
            assert refused["sqlstate"] == sqlstate and message in refused["reason"], name
            after = tuple(
                observer.execute(
                    text(
                        "SELECT (SELECT count(*) FROM ops.data_request WHERE operation_id='urn:consumer'), (SELECT count(*) FROM ops.task), (SELECT count(*) FROM ops.demand_use)"
                    )
                ).one()
            )
            assert after == before, name
        writer.scalar(
            statement,
            {"p": json.dumps({"read_id": baseline["binding"]["read_id"], "items": [baseline]})},
        )
    with ddo_kernel["engine"].connect() as connection:
        retained = connection.scalar(
            text("SELECT binding FROM ops.data_request WHERE operation_id='urn:consumer'")
        )
        assert retained == {**binding, "execution_profile": "execution:test"}
        assert retained["inputs"] == binding["inputs"]
        assert retained["support"] == binding["support"]
        assert retained["populations"] == binding["populations"]


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_registration_exposes_all_frozen_obligations_atomically(ddo_kernel):
    from corpus_structure.semantic.data_operation_demands import RootSubject, freeze_demand

    roots = tuple(RootSubject("subject:" + name, "source:test", b"{}") for name in ("a", "b", "c"))
    selected = freeze_demand(
        ddo_kernel["model"],
        roots=roots,
        targets=("urn:ddo-test:source",),
        inference="inference:test",
        execution_profile="execution:test",
    ).record
    with ddo_kernel["engine"].connect() as writer:
        transaction = writer.begin()
        registered = DataOperationStorage(writer).register_data_demand(
            typing_cast(
                WireRegisterDataDemandRequest,
                {
                    "project_id": "ddo-test",
                    "release_id": ddo_kernel["prepared"].release_id,
                    "runtime_id": ddo_kernel["runtime"],
                    "root": selected["roots"],
                    "selection": selected,
                    "strength": "value",
                },
            )
        )
        assert registered["inserted_obligations"] == 3
        with ddo_kernel["engine"].connect() as observer:
            assert observer.scalar(text("SELECT count(*) FROM ops.data_demand")) == 0
            assert observer.scalar(text("SELECT count(*) FROM ops.data_obligation")) == 0
        transaction.commit()
    with ddo_kernel["engine"].begin() as reader:
        page = DataOperationStorage(reader).read_demand_result(
            {"demand_id": registered["demand_id"], "limit": 1}
        )
    collected = list(page["obligations"])
    while page["continuation"]:
        with ddo_kernel["engine"].begin() as reader:
            following = DataOperationStorage(reader).read_demand_result({**page["continuation"]})
        assert following["read_id"] == page["read_id"]
        collected.extend(following["obligations"])
        page = following
    assert {row["subject"] for row in collected} == {"subject:a", "subject:b", "subject:c"}
    assert len({row["obligation_id"] for row in collected}) == 3


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_read_receipt_refuses_frontier_writes_in_acquiring_transaction(ddo_kernel):
    demand, obligation, _, _ = attach(ddo_kernel)
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        first = storage.read_demand_result(typing_cast(WireReadDemandResultRequest, demand))
        with pytest.raises(DBAPIError, match="fresh transaction"), connection.begin_nested():
            storage.record_data_fate(
                typing_cast(
                    WireRecordDataFateRequest,
                    {
                        "obligation_id": obligation["obligation_id"],
                        "fate": "awaiting-inputs",
                        "selection": {},
                    },
                )
            )
    with ddo_kernel["engine"].begin() as connection:
        DataOperationStorage(connection).record_data_fate(
            typing_cast(
                WireRecordDataFateRequest,
                {
                    "obligation_id": obligation["obligation_id"],
                    "fate": "awaiting-inputs",
                    "selection": {},
                },
            )
        )
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        pinned = storage.read_demand_result(
            {"demand_id": demand["demand_id"], "read_id": first["read_id"]}
        )
        assert pinned["obligations"] == first["obligations"]
        current = storage.read_demand_result({"demand_id": demand["demand_id"]})
        assert current["obligations"][0]["fate"] == "awaiting-inputs"


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_frontier_view_defers_bodies_and_same_receipt_can_read_products(ddo_kernel):
    demand, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence)
    publish(ddo_kernel, fence, intent)
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        frontier = storage.read_demand_result(typing_cast(WireReadDemandResultRequest, demand))
        assert frontier["view"] == "frontier"
        compact = storage.acquire_data_read_context(
            frontier["demand_id"], frontier["read_id"], frontier["trust_snapshot"]
        )
        assert compact == {
            name: frontier[name]
            for name in (
                "demand_id",
                "selection",
                "trust_snapshot",
                "read_id",
                "read_snapshot",
                "frontier_at",
            )
        }
        product = frontier["uses"][0]["products"][0]
        assert product["body_state"] == "not_requested" and "body" not in product
        hydrated = storage.read_demand_result(
            typing_cast(
                WireReadDemandResultRequest,
                {**demand, "read_id": frontier["read_id"], "view": "products"},
            )
        )
        assert hydrated["read_id"] == frontier["read_id"]
        assert hydrated["uses"][0]["products"][0]["body_state"] == "present"
        assert hydrated["uses"][0]["products"][0]["body"] == ["integer", "1"]


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_set_output_rejects_duplicate_values_atomically(ddo_kernel):
    _, _, _, attached = attach(ddo_kernel, operation="urn:ddo-test:set")
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence, outputs=(1, 1))
    with pytest.raises(DBAPIError, match="set output"):
        publish(ddo_kernel, fence, intent)
    with ddo_kernel["engine"].connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM kb.data_product")) == 0
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation_output")) == 0


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_immutability_is_an_installed_enforcement_not_only_metadata(ddo_kernel):
    _, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence)
    publish(ddo_kernel, fence, intent)
    with (
        ddo_kernel["engine"].begin() as connection,
        pytest.raises(DBAPIError, match="immutable semantic content"),
    ):
        connection.execute(text("UPDATE kb.data_product SET body_digest='forged'"))


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_unbacked_artifact_hash_is_explicitly_refused(ddo_kernel):
    _, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    intent = retain(
        ddo_kernel,
        fence,
        mutate=lambda completion: completion["outputs"][0]["product"].update(
            artifact_digest="f" * 64
        ),
    )
    with pytest.raises(DBAPIError, match="authenticated staged receipt"):
        publish(ddo_kernel, fence, intent)


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_real_purpose_principals_cannot_cross_evaluator_kind_boundary(ddo_kernel):

    writer = ddo_kernel.purpose("write")
    evaluator = ddo_kernel.purpose("evaluate")
    reader = ddo_kernel.purpose("read")
    try:
        with pytest.raises(DBAPIError, match="evaluator"):
            attach(ddo_kernel, operation="urn:ddo-test:evaluator", engine=writer)
        demand, _, _, attached = attach(
            ddo_kernel, operation="urn:ddo-test:evaluator", engine=evaluator
        )
        with evaluator.begin() as connection:
            storage = DataOperationStorage(connection)
            item_result = storage.claim_data_requests(
                typing_cast(
                    WireClaimDataRequestsRequest,
                    {
                        "holder": "evaluator",
                        "lease_seconds": 30,
                        "items": [
                            {
                                "request_id": attached["request_id"],
                                "generation": attached["generation"],
                            }
                        ],
                    },
                )
            )["items"][0]
            assert item_result["state"] == "claimed", item_result
            owned = item_result["result"]
            assert owned["state"] == "claimed"
            fence = {
                name: owned[name]
                for name in ("request_id", "generation", "task_id", "attempt", "holder")
            }
            kind = ddo_kernel["identities"]["urn:ddo-test:evaluator-integer", "kind"]
            intent = storage.retain_data_completion_intent(
                typing_cast(
                    WireRetainDataCompletionIntentRequest,
                    {
                        **fence,
                        "runtime_id": ddo_kernel["runtime"],
                        "completion": {
                            "outcome": "success",
                            "implementation_revision": "native-test-source-v1",
                            "inputs": [],
                            "support": [],
                            "outputs": [
                                {
                                    "role": "result",
                                    "position": 0,
                                    "multiplicity": 1,
                                    "product": {
                                        "kind_contract": kind,
                                        "body": ["integer", "1"],
                                        "members": [],
                                    },
                                }
                            ],
                        },
                    },
                )
            )
            storage.publish_data_derivation(
                typing_cast(
                    WirePublishDataDerivationRequest, {**fence, "intent_id": intent["intent_id"]}
                )
            )
        with reader.begin() as connection, pytest.raises(DBAPIError, match="evaluator"):
            DataOperationStorage(connection).read_demand_result(
                typing_cast(WireReadDemandResultRequest, demand)
            )
        with reader.begin() as connection, pytest.raises(DBAPIError, match="evaluator"):
            DataOperationStorage(connection).inspect_data_completion(
                typing_cast(
                    WireInspectDataCompletionRequest,
                    {
                        "request_id": fence["request_id"],
                        "generation": fence["generation"],
                        "intent_id": intent["intent_id"],
                    },
                )
            )
        with writer.begin() as connection, pytest.raises(DBAPIError, match="permission denied"):
            connection.execute(text("SELECT * FROM kb.data_product"))
    finally:
        writer.dispose()
        evaluator.dispose()
        reader.dispose()


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_evaluator_retires_own_failed_attempt_without_granting_writer_private_access(ddo_kernel):
    writer = ddo_kernel.purpose("write")
    evaluator = ddo_kernel.purpose("evaluate")
    try:
        _, _, _, attached = attach(ddo_kernel, operation="urn:ddo-test:evaluator", engine=evaluator)
        with evaluator.begin() as connection:
            item_result = DataOperationStorage(connection).claim_data_requests(
                typing_cast(
                    WireClaimDataRequestsRequest,
                    {
                        "holder": "evaluator-failure",
                        "lease_seconds": 30,
                        "items": [
                            {
                                "request_id": attached["request_id"],
                                "generation": attached["generation"],
                            }
                        ],
                    },
                )
            )["items"][0]
            assert item_result["state"] == "claimed", item_result
            owned = item_result["result"]
        assert owned["state"] == "claimed"
        payload = {
            **{
                name: owned[name]
                for name in ("request_id", "generation", "task_id", "attempt", "holder")
            },
            "physical_retirement": "confirmed",
            "failure": {
                "code": "known-test-failure",
                "message": "owned finite computation retired",
            },
        }
        with writer.begin() as connection, pytest.raises(DBAPIError, match="evaluator"):
            DataOperationStorage(connection).release_data_attempt(
                typing_cast(WireReleaseDataAttemptRequest, payload)
            )
        with evaluator.begin() as connection:
            storage = DataOperationStorage(connection)
            released = storage.release_data_attempt(
                typing_cast(WireReleaseDataAttemptRequest, payload)
            )
            assert released["state"] == "released" and released["replayed"] is False
            repeated = storage.release_data_attempt(
                typing_cast(WireReleaseDataAttemptRequest, payload)
            )
            assert repeated["state"] == "released"
            assert repeated["failure_id"] == released["failure_id"] and repeated["replayed"] is True
    finally:
        writer.dispose()
        evaluator.dispose()


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_request_renewal_uses_exact_runless_fence_and_does_not_shorten_lease(ddo_kernel):
    _, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    with ddo_kernel["engine"].begin() as connection:
        before = connection.execute(
            text("SELECT data_request_id,data_generation,lease_until FROM ops.task WHERE id=:task"),
            {"task": fence["task_id"]},
        ).one()
        assert before.data_request_id == fence["request_id"]
        assert before.data_generation == fence["generation"]
        renewed = DataOperationStorage(connection).renew_data_request(
            typing_cast(WireRenewDataRequestRequest, {**fence, "lease_seconds": 1})
        )
        after = connection.scalar(
            text("SELECT lease_until FROM ops.task WHERE id=:task"),
            {"task": fence["task_id"]},
        )
        assert renewed["state"] == "renewed"
        assert {name: dict(renewed)[name] for name in fence} == fence
        assert after >= before.lease_until
    publish(ddo_kernel, fence, retain(ddo_kernel, fence))
    with ddo_kernel["engine"].begin() as connection:
        lost = DataOperationStorage(connection).renew_data_request(
            typing_cast(WireRenewDataRequestRequest, {**fence, "lease_seconds": 30})
        )
        assert lost == {**fence, "state": "lost", "reason": "fence"}


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
@pytest.mark.parametrize("field", ["generation", "task_id", "attempt", "holder"])
def test_native_request_renewal_refuses_a_different_fence(ddo_kernel, field):
    _, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    altered = {**fence, field: "different" if field == "holder" else fence[field] + 1}
    with ddo_kernel["engine"].begin() as connection:
        lost = DataOperationStorage(connection).renew_data_request(
            typing_cast(WireRenewDataRequestRequest, {**altered, "lease_seconds": 30})
        )
        assert lost == {**altered, "state": "lost", "reason": "fence"}


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_request_renewal_cannot_revive_an_expired_attempt(ddo_kernel):
    _, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached, seconds=1)
    time.sleep(1.05)
    with ddo_kernel["engine"].begin() as connection:
        lost = DataOperationStorage(connection).renew_data_request(
            typing_cast(WireRenewDataRequestRequest, {**fence, "lease_seconds": 30})
        )
        assert lost == {**fence, "state": "lost", "reason": "fence"}


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_request_renewal_preserves_a_shared_demand_after_one_detaches(ddo_kernel):
    _, first, _, attached = attach(ddo_kernel)
    _, second, _, shared = attach(
        ddo_kernel, targets=("urn:ddo-test:source", "urn:ddo-test:sample")
    )
    assert shared["request_id"] == attached["request_id"]
    assert second["obligation_id"] != first["obligation_id"]
    fence = claim(ddo_kernel, attached)
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        storage.record_data_fate(
            typing_cast(
                WireRecordDataFateRequest,
                {
                    "obligation_id": first["obligation_id"],
                    "fate": "cancelled",
                    "selection": {},
                },
            )
        )
        assert (
            storage.renew_data_request(
                typing_cast(WireRenewDataRequestRequest, {**fence, "lease_seconds": 30})
            )["state"]
            == "renewed"
        )
        storage.record_data_fate(
            typing_cast(
                WireRecordDataFateRequest,
                {
                    "obligation_id": second["obligation_id"],
                    "fate": "cancelled",
                    "selection": {},
                },
            )
        )
    with ddo_kernel["engine"].begin() as connection:
        lost = DataOperationStorage(connection).renew_data_request(
            typing_cast(WireRenewDataRequestRequest, {**fence, "lease_seconds": 30})
        )
        assert lost == {**fence, "state": "lost", "reason": "cancelled"}


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_cancellation_fences_orphan_without_claiming_physical_retirement(ddo_kernel):
    demand, obligation, wire, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence)
    with ddo_kernel["engine"].begin() as connection:
        before = DataOperationStorage(connection).read_demand_result(
            typing_cast(WireReadDemandResultRequest, demand)
        )
    cancelled = cancel_demand(ddo_kernel, demand)
    assert cancelled["state"] == "cancelled"
    assert cancelled["requests"] == [
        {
            "request_id": fence["request_id"],
            "generation": fence["generation"],
            "task_id": fence["task_id"],
            "interest": "orphaned",
            "physical_retirement": "unconfirmed",
        }
    ]
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        assert (
            storage.read_demand_result(typing_cast(WireReadDemandResultRequest, demand))["state"]
            == "cancelled"
        )
        historical = storage.read_demand_result(
            typing_cast(
                WireReadDemandResultRequest,
                {
                    **demand,
                    "read_id": before["read_id"],
                    "trust_snapshot": before["trust_snapshot"],
                },
            )
        )
        assert historical["state"] == "active"
        assert (
            connection.scalar(
                text("SELECT status FROM ops.task WHERE id=:id"), {"id": fence["task_id"]}
            )
            == "running"
        )
        assert storage.claim_data_requests(
            typing_cast(
                WireClaimDataRequestsRequest,
                {
                    "holder": "late",
                    "lease_seconds": 30,
                    "items": [
                        {"request_id": fence["request_id"], "generation": fence["generation"]}
                    ],
                },
            )
        )["items"][0] == {"state": "no-work"}
    with ddo_kernel["engine"].begin() as connection:
        response = DataOperationStorage(connection).attach_data_requests(
            typing_cast(
                WireAttachDataRequestsRequest,
                {
                    "read_id": wire["binding"]["read_id"],
                    "items": [wire],
                },
            )
        )["items"][0]
        assert response["state"] == "refused" and "cancelled" in response["reason"]
    for name, payload in [
        ("publish_data_derivation", {**fence, "intent_id": intent["intent_id"]}),
        (
            "record_data_fate",
            {
                "obligation_id": obligation["obligation_id"],
                "fate": "partial",
                "selection": {},
            },
        ),
    ]:
        with (
            ddo_kernel["engine"].begin() as connection,
            pytest.raises(DBAPIError, match=r"cancelled|no attached demand"),
        ):
            getattr(DataOperationStorage(connection), name)(payload)
    repeated = cancel_demand(ddo_kernel, demand, "retry must not rewrite original reason")
    assert repeated["reason"] == cancelled["reason"]
    # Resume/re-registration cannot silently undo terminal intent.
    selected = demand["selection"]
    with ddo_kernel["engine"].begin() as connection:
        replay = DataOperationStorage(connection).register_data_demand(
            typing_cast(
                WireRegisterDataDemandRequest,
                {
                    "project_id": "ddo-test",
                    "release_id": ddo_kernel["prepared"].release_id,
                    "runtime_id": ddo_kernel["runtime"],
                    "root": selected["roots"],
                    "selection": selected,
                    "strength": "value",
                },
            )
        )
        assert replay["demand_id"] == demand["demand_id"]
        assert replay["state"] == "cancelled"


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_cancellation_preserves_shared_producer_and_committed_receipt(ddo_kernel):
    first, _, _, attached = attach(ddo_kernel)
    second, _, _, shared = attach(
        ddo_kernel, targets=("urn:ddo-test:source", "urn:ddo-test:sample")
    )
    assert shared["request_id"] == attached["request_id"]
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence)
    cancelled = cancel_demand(ddo_kernel, first)
    assert cancelled["requests"][0]["interest"] == "shared"
    with ddo_kernel["engine"].begin() as connection:
        renewed = DataOperationStorage(connection).renew_data_request(
            typing_cast(WireRenewDataRequestRequest, {**fence, "lease_seconds": 30})
        )
        assert renewed["state"] == "renewed"
    receipt = publish(ddo_kernel, fence, intent)
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        first_result = storage.read_demand_result(typing_cast(WireReadDemandResultRequest, first))
        assert first_result["state"] == "cancelled"
        assert {item["fate"] for item in first_result["obligations"]} == {"cancelled"}
        assert (
            storage.read_demand_result(typing_cast(WireReadDemandResultRequest, second))["uses"][0][
                "fate"
            ]
            == "fulfilled"
        )
    cancel_demand(ddo_kernel, second)
    assert publish(ddo_kernel, fence, intent)["receipt_id"] == receipt["receipt_id"]
    with ddo_kernel["engine"].begin() as connection:
        inspected = DataOperationStorage(connection).inspect_data_completion(
            typing_cast(
                WireInspectDataCompletionRequest,
                {
                    "request_id": fence["request_id"],
                    "generation": fence["generation"],
                    "intent_id": intent["intent_id"],
                },
            )
        )
        assert inspected["state"] == "committed"


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_concurrent_cancel_and_attach_never_resurrects_demand(ddo_kernel):
    demand, _, wire, attached = attach(ddo_kernel)
    barrier = Barrier(2)

    def attaching():
        barrier.wait()
        with ddo_kernel["engine"].begin() as connection:
            result = DataOperationStorage(connection).attach_data_requests(
                typing_cast(
                    WireAttachDataRequestsRequest,
                    {
                        "read_id": wire["binding"]["read_id"],
                        "items": [wire],
                    },
                )
            )["items"][0]
            assert result["state"] == "attached" or (
                result["state"] == "refused" and "cancelled" in result["reason"]
            )
            return result

    def cancelling():
        barrier.wait()
        return cancel_demand(ddo_kernel, demand)

    with ThreadPoolExecutor(max_workers=2) as pool:
        joining = pool.submit(attaching)
        stopping = pool.submit(cancelling)
        joining.result(timeout=30)
        assert stopping.result(timeout=30)["state"] == "cancelled"
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        assert (
            storage.read_demand_result(typing_cast(WireReadDemandResultRequest, demand))["state"]
            == "cancelled"
        )
        assert (
            storage.claim_data_requests(
                typing_cast(
                    WireClaimDataRequestsRequest,
                    {
                        "holder": "late",
                        "lease_seconds": 30,
                        "items": [
                            {
                                "request_id": attached["request_id"],
                                "generation": attached["generation"],
                            }
                        ],
                    },
                )
            )["items"][0]["state"]
            == "no-work"
        )


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_new_demand_cannot_restore_a_cancelled_producer_fence(ddo_kernel):
    from corpus_structure.semantic.data_operation_runtime import prepare_data_operation_runtime
    from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding

    first, _, _, attached = attach(ddo_kernel)
    old_claim = claim(ddo_kernel, attached)
    old_intent = retain(ddo_kernel, old_claim)
    cancel_demand(ddo_kernel, first)
    replacement = prepare_data_operation_runtime(
        ddo_kernel["prepared"],
        ddo_kernel["runtime_inputs"],
        execution_profile="execution:test",
        observed={"host": "new-demand-owner"},
    )
    with ddo_kernel["engine"].begin() as connection:
        persist_runtime_binding(connection, ddo_kernel["prepared"], replacement)
    updated = {**ddo_kernel, "runtime": replacement.runtime_id}
    _, _, current_binding, current = attach(
        updated, targets=("urn:ddo-test:source", "urn:ddo-test:sample")
    )
    assert current["request_id"] == old_claim["request_id"]
    assert current["generation"] == old_claim["generation"] + 1
    assert current["task_id"] != old_claim["task_id"]
    current_claim = claim(ddo_kernel, current, holder="new-demand-owner")
    with pytest.raises(DBAPIError, match="stale"):
        publish(ddo_kernel, old_claim, old_intent)
    with ddo_kernel["engine"].begin() as connection:
        assert (
            connection.scalar(
                text("SELECT status FROM ops.task WHERE id=:id"), {"id": old_claim["task_id"]}
            )
            == "running"
        )
        current_request = connection.execute(
            text("SELECT runtime_id,release_id,binding FROM ops.data_request WHERE id=:id"),
            {"id": current["request_id"]},
        ).one()
        assert current_request.runtime_id == replacement.runtime_id
        assert current_request.release_id == ddo_kernel["prepared"].release_id
        assert current_request.binding["read_id"] == current_binding["binding"]["read_id"]
        assert (
            connection.scalar(
                text("SELECT release_id FROM ops.task WHERE id=:id"), {"id": current["task_id"]}
            )
            == current_request.release_id
        )
    receipt = publish(updated, current_claim, retain(updated, current_claim, outputs=(2,)))
    assert receipt["replayed"] is False
    with ddo_kernel["engine"].connect() as connection:
        assert (
            connection.scalar(
                text("SELECT runtime_id FROM ops.data_derivation WHERE id=:id"),
                {"id": receipt["derivation_id"]},
            )
            == replacement.runtime_id
        )


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
@pytest.mark.parametrize("retained", [False, True])
def test_native_release_retired_failed_attempt_preserves_intent_and_physical_history(
    ddo_kernel,
    retained,
):
    demand, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence) if retained else None
    payload = {
        **fence,
        "physical_retirement": "confirmed",
        "failure": {"code": "compute-error", "message": "known retired computation"},
    }
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        before = storage.read_demand_result(typing_cast(WireReadDemandResultRequest, demand))
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        released = storage.release_data_attempt(typing_cast(WireReleaseDataAttemptRequest, payload))
        assert released["state"] == "released" and released["replayed"] is False
        assert released["retained_intent_id"] == (intent["intent_id"] if intent else None)
        physical = connection.execute(
            text("SELECT status,claimed_by,lease_until,error FROM ops.task WHERE id=:id"),
            {"id": fence["task_id"]},
        ).one()
        assert physical.status == "pending"
        assert physical.claimed_by == fence["holder"] and physical.lease_until is None
        assert physical.error["data_attempt_failure"] == released["failure_id"]
        current = storage.read_demand_result(typing_cast(WireReadDemandResultRequest, demand))
        assert current["uses"][0]["fate"] == "attached"
        assert current["attempt_failures"] == [
            {
                **fence,
                "failure_id": released["failure_id"],
                "failure": payload["failure"],
            }
        ]
        pinned = storage.read_demand_result(
            typing_cast(
                WireReadDemandResultRequest,
                {
                    "demand_id": demand["demand_id"],
                    "read_id": before["read_id"],
                },
            )
        )
        assert pinned["attempt_failures"] == []
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        item_result = storage.claim_data_requests(
            typing_cast(
                WireClaimDataRequestsRequest,
                {
                    "holder": "replacement",
                    "lease_seconds": 30,
                    "items": [
                        {"request_id": fence["request_id"], "generation": fence["generation"]}
                    ],
                },
            )
        )["items"][0]
        assert item_result["state"] == "claimed", item_result
        replacement = item_result["result"]
        assert replacement["state"] == "claimed"
        assert replacement["action"] == ("reconcile" if retained else "compute")
        assert replacement["attempt"] == fence["attempt"] + 1
        replay = storage.release_data_attempt(typing_cast(WireReleaseDataAttemptRequest, payload))
        assert replay == {**released, "replayed": True}
        assert connection.scalar(text("SELECT count(*) FROM ops.data_attempt_failure")) == 1
        assert (
            connection.scalar(
                text("SELECT status FROM ops.task WHERE id=:id"), {"id": fence["task_id"]}
            )
            == "running"
        )
        lost = storage.renew_data_request(
            typing_cast(WireRenewDataRequestRequest, {**fence, "lease_seconds": 30})
        )
        assert lost == {**fence, "state": "lost", "reason": "fence"}


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_claim_owner_isolates_cancelled_request_renewal_and_preserves_sibling(ddo_kernel):
    from datetime import datetime
    from threading import Event

    from corpus_structure.orchestrate.data_operations import NativeRequestClaim
    from corpus_structure.semantic.claim_lifetime import ClaimFenceLost, maintained_claims

    first, _, _, first_request = attach(ddo_kernel, subject="subject:first")
    _, _, _, second_request = attach(ddo_kernel, subject="subject:second")
    claims = []
    with ddo_kernel["engine"].begin() as connection:
        for request in (first_request, second_request):
            item_result = DataOperationStorage(connection).claim_data_requests(
                typing_cast(
                    WireClaimDataRequestsRequest,
                    {
                        "holder": "owner",
                        "lease_seconds": 30,
                        "items": [
                            {
                                "request_id": request["request_id"],
                                "generation": request["generation"],
                            }
                        ],
                    },
                )
            )["items"][0]
            assert item_result["state"] == "claimed", item_result
            response = item_result["result"]
            assert response["state"] == "claimed"
            claims.append(
                NativeRequestClaim(
                    response["request_id"],
                    response["generation"],
                    response["task_id"],
                    response["attempt"],
                    response["holder"],
                    response["release_id"],
                    datetime.fromisoformat(response["lease_until"].replace("Z", "+00:00")),
                    runtime_id=response["runtime_id"],
                )
            )
    sibling_renewed = Event()

    def renew(connection, claim):
        response = DataOperationStorage(connection).renew_data_request(
            typing_cast(
                WireRenewDataRequestRequest,
                {
                    **claim.fence,
                    "lease_seconds": 30,
                },
            )
        )
        if response["state"] == "lost":
            raise ClaimFenceLost(claim, response["reason"])
        if claim == claims[1]:
            sibling_renewed.set()

    cancel_demand(ddo_kernel, first)
    with (
        pytest.raises(ClaimFenceLost),
        maintained_claims(
            ddo_kernel["engine"],
            tuple(claims),
            "owner",
            interval=0.01,
            renew=renew,
        ) as owner,
    ):
        assert sibling_renewed.wait(10)
        owner()
        owner.check_claim(claims[1])
        with pytest.raises(ClaimFenceLost) as loss:
            owner.check_claim(claims[0])
        assert loss.value.reason == "cancelled"
        intent = retain(ddo_kernel, claims[1].fence)
        receipt = owner.settle(
            claims[1],
            lambda connection: DataOperationStorage(connection).publish_data_derivation(
                typing_cast(
                    WirePublishDataDerivationRequest,
                    {**claims[1].fence, "intent_id": intent["intent_id"]},
                )
            ),
        )
        assert isinstance(receipt, dict)
        assert receipt["derivation_id"]
        assert not owner.active


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
@pytest.mark.parametrize("state", ["pending", "active", "expired"])
def test_revoked_runtime_without_retained_intent_refreshes_only_unleased_generation(
    ddo_kernel, state
):
    from corpus_structure.semantic.data_operation_runtime import prepare_data_operation_runtime
    from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding

    # Establish native authority for this scoped runtime revocation through a
    # genuine earlier episode, not direct mutation of request/task custody.
    _, _, _, produced = attach(ddo_kernel, subject="subject:runtime-proof")
    proof = claim(ddo_kernel, produced)
    publish(ddo_kernel, proof, retain(ddo_kernel, proof))
    demand, _, wire, old = attach(ddo_kernel)
    fence = (
        None
        if state == "pending"
        else claim(ddo_kernel, old, seconds=30 if state == "active" else 1)
    )
    replacement = prepare_data_operation_runtime(
        ddo_kernel["prepared"],
        ddo_kernel["runtime_inputs"],
        execution_profile="execution:test",
        observed={"host": "unretained-replacement"},
    )
    with ddo_kernel["engine"].begin() as connection:
        persist_runtime_binding(connection, ddo_kernel["prepared"], replacement)
        DataOperationStorage(connection).revoke_data_support(
            typing_cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": "ddo-test",
                    "original_source": "source:test",
                    "selector_kind": "runtime",
                    "selector": ddo_kernel["runtime"],
                    "reason": "runtime invalidated before completion intent",
                },
            )
        )
    updated = {**ddo_kernel, "runtime": replacement.runtime_id}
    selected = demand["selection"]
    with ddo_kernel["engine"].begin() as connection:
        replacement_demand = DataOperationStorage(connection).register_data_demand(
            typing_cast(
                WireRegisterDataDemandRequest,
                {
                    "project_id": "ddo-test",
                    "release_id": ddo_kernel["prepared"].release_id,
                    "runtime_id": replacement.runtime_id,
                    "root": selected["roots"],
                    "selection": selected,
                    "strength": "value",
                },
            )
        )
        replacement_read = DataOperationStorage(connection).read_demand_result(
            {"demand_id": replacement_demand["demand_id"]}
        )
    replacement_wire = {
        **wire,
        "obligation_id": replacement_read["obligations"][0]["obligation_id"],
        "binding": {**wire["binding"], "read_id": replacement_read["read_id"]},
    }
    if state == "active":
        with ddo_kernel["engine"].begin() as connection:
            refused = DataOperationStorage(connection).attach_data_requests(
                typing_cast(
                    WireAttachDataRequestsRequest,
                    {
                        "read_id": replacement_read["read_id"],
                        "items": [replacement_wire],
                    },
                )
            )["items"][0]
            assert refused["state"] == "refused" and "active producer lease" in refused["reason"]
        return
    if state == "expired":
        expire_lease(ddo_kernel, fence)
    with ddo_kernel["engine"].begin() as connection:
        revoked_read = DataOperationStorage(connection).read_demand_result(
            {"demand_id": demand["demand_id"]}
        )
    with ddo_kernel["engine"].begin() as connection:
        refused = DataOperationStorage(connection).attach_data_requests(
            typing_cast(
                WireAttachDataRequestsRequest,
                {
                    "read_id": revoked_read["read_id"],
                    "items": [
                        {**wire, "binding": {**wire["binding"], "read_id": revoked_read["read_id"]}}
                    ],
                },
            )
        )["items"][0]
        assert (
            refused["state"] == "refused" and "replacement runtime or recipe" in refused["reason"]
        )
    _, _, binding, current = attach(updated)
    assert current["request_id"] == old["request_id"]
    assert current["generation"] == old["generation"] + 1
    assert current["task_id"] != old["task_id"]
    assert current["action"] == "compute" and current["retained_intent_id"] is None
    with ddo_kernel["engine"].connect() as connection:
        row = connection.execute(
            text("SELECT runtime_id,binding FROM ops.data_request WHERE id=:id"),
            {"id": current["request_id"]},
        ).one()
        assert row.runtime_id == replacement.runtime_id
        assert row.binding["read_id"] == binding["binding"]["read_id"]
        assert (
            connection.scalar(
                text("SELECT count(*) FROM ops.data_completion_intent WHERE request_id=:id"),
                {"id": old["request_id"]},
            )
            == 0
        )
        # Fencing publication is distinct from claiming physical retirement.
        assert connection.scalar(
            text("SELECT status FROM ops.task WHERE id=:id"), {"id": old["task_id"]}
        ) == ("pending" if fence is None else "running")
    successor = claim(updated, current, holder="unretained-successor")
    assert publish(updated, successor, retain(updated, successor))["derivation_id"]


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
@pytest.mark.parametrize("changed", ["scope", "source", "project"])
def test_distinct_root_contexts_attach_and_publish_equal_bodies(ddo_kernel, changed):
    kwargs = (
        {"analyzed_scope": {"page": 2}}
        if changed == "scope"
        else (
            {"original_source": "source:other"}
            if changed == "source"
            else {"project_id": "ddo-other"}
        )
    )
    if changed == "project":
        with ddo_kernel["engine"].begin() as connection:
            connection.execute(insert(table("data.project")).values(project_id="ddo-other"))
    _, _, original_wire, original = attach(ddo_kernel)
    _, _, changed_wire, changed_request = attach(ddo_kernel, **kwargs)
    assert original["request_id"] != changed_request["request_id"]
    assert original_wire["request_key"] != changed_wire["request_key"]
    products = []
    for attached in (original, changed_request):
        fence = claim(ddo_kernel, attached)
        intent = retain(ddo_kernel, fence, outputs=(1,))
        receipt = publish(ddo_kernel, fence, intent)
        with ddo_kernel["engine"].connect() as connection:
            products.append(
                connection.execute(
                    text(
                        "SELECT product_id FROM ops.data_derivation_output WHERE derivation_id=:id"
                    ),
                    {"id": receipt["derivation_id"]},
                ).scalar_one()
            )
            from corpus_structure.semantic.data_operation_identity import (
                body_identity,
                contextual_product_identity,
            )

            context_row = (
                connection.execute(
                    text(
                        "SELECT project_id,subject,original_source,analyzed_scope "
                        "FROM ops.data_request WHERE id=:id"
                    ),
                    {"id": attached["request_id"]},
                )
                .mappings()
                .one()
            )
            context = SubjectContext(
                context_row["project_id"],
                context_row["subject"],
                context_row["original_source"],
                canonical_bytes(context_row["analyzed_scope"]),
                subject_definition="original-occurrence",
            )
            assert (
                products[-1]
                == contextual_product_identity(
                    kind=ddo_kernel["kind"], context=context, body=body_identity(1).key
                ).key
            )
    assert products[0] != products[1]
    assert attach(ddo_kernel)[3]["request_id"] == original["request_id"]


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_overlapping_publication_returns_committed_exact_receipt(ddo_kernel):
    from queue import Queue

    _, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence)
    payload = {**fence, "intent_id": intent["intent_id"]}
    backend = Queue()

    def retry():
        with ddo_kernel["engine"].begin() as connection:
            backend.put(connection.execute(text("SELECT pg_backend_pid()")).scalar_one())
            return DataOperationStorage(connection).publish_data_derivation(
                typing_cast(WirePublishDataDerivationRequest, payload)
            )

    with ThreadPoolExecutor(max_workers=1) as pool:
        with ddo_kernel["engine"].begin() as first_connection:
            first = DataOperationStorage(first_connection).publish_data_derivation(
                typing_cast(WirePublishDataDerivationRequest, payload)
            )
            future = pool.submit(retry)
            pid = backend.get(timeout=10)
            deadline = time.monotonic() + 10
            while not first_connection.execute(
                text("SELECT cardinality(pg_blocking_pids(:pid))>0"), {"pid": pid}
            ).scalar_one():
                if time.monotonic() >= deadline:
                    pytest.fail("retry did not reach the held publication lock")
                time.sleep(0.01)
        second = future.result(timeout=10)
    assert second == {**first, "replayed": True}
    with ddo_kernel["engine"].connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM ops.data_derivation WHERE intent_id=:id"),
                {"id": intent["intent_id"]},
            ).scalar_one()
            == 1
        )


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_writer_cannot_mutate_or_read_pending_evaluator_obligations(ddo_kernel):

    writer = ddo_kernel.purpose("write")
    evaluator = ddo_kernel.purpose("evaluate")
    try:
        demand, obligation, _, attached = attach(
            ddo_kernel, operation="urn:ddo-test:evaluator", engine=evaluator
        )
        calls = [
            ("read_demand_result", {"demand_id": demand["demand_id"]}),
            (
                "record_data_fate",
                {
                    "obligation_id": obligation["obligation_id"],
                    "fate": "closed",
                    "selection": {},
                },
            ),
        ]
        for name, payload in calls:
            with writer.begin() as connection, pytest.raises(DBAPIError, match="evaluator"):
                getattr(DataOperationStorage(connection), name)(payload)
        with evaluator.begin() as connection:
            result = DataOperationStorage(connection).read_demand_result(
                typing_cast(WireReadDemandResultRequest, demand)
            )
            assert result["obligations"][0]["fate"] == "attached"
            assert result["obligations"][0]["request_id"] == attached["request_id"]
    finally:
        writer.dispose()
        evaluator.dispose()


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_writer_cannot_revoke_runtime_with_ordinary_and_evaluator_targets(ddo_kernel):

    writer = ddo_kernel.purpose("write")
    try:
        ordinary_demand, _, _, ordinary = attach(ddo_kernel)
        ordinary_fence = claim(ddo_kernel, ordinary)
        publish(ddo_kernel, ordinary_fence, retain(ddo_kernel, ordinary_fence))
        protected_demand, _, _, protected = attach(ddo_kernel, operation="urn:ddo-test:evaluator")
        protected_fence = claim(ddo_kernel, protected)

        def protected_kind(completion):
            completion["outputs"][0]["product"]["kind_contract"] = ddo_kernel["identities"][
                "urn:ddo-test:evaluator-integer", "kind"
            ]

        publish(
            ddo_kernel, protected_fence, retain(ddo_kernel, protected_fence, mutate=protected_kind)
        )
        with ddo_kernel["engine"].connect() as connection:
            before = (
                connection.execute(
                    text("SELECT epoch FROM ops.data_trust_scope WHERE project_id='ddo-test'")
                )
                .scalars()
                .all()
            )
        with writer.begin() as connection, pytest.raises(DBAPIError, match="evaluator"):
            DataOperationStorage(connection).revoke_data_support(
                typing_cast(
                    WireRevokeDataSupportRequest,
                    {
                        "project_id": "ddo-test",
                        "original_source": "source:test",
                        "selector_kind": "runtime",
                        "selector": ddo_kernel["runtime"],
                        "reason": "unauthorized broad revoke",
                    },
                )
            )
        with ddo_kernel["engine"].connect() as connection:
            assert (
                connection.execute(
                    text("SELECT epoch FROM ops.data_trust_scope WHERE project_id='ddo-test'")
                )
                .scalars()
                .all()
                == before
            )
            for demand in (ordinary_demand, protected_demand):
                result = DataOperationStorage(connection).read_demand_result(
                    typing_cast(WireReadDemandResultRequest, demand)
                )
                assert result["uses"][0]["fate"] == "fulfilled"
    finally:
        writer.dispose()


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_competing_first_attachments_coalesce_one_request_and_task(ddo_kernel):
    gate = Barrier(2)

    def first_attach():
        gate.wait(timeout=10)
        return attach(ddo_kernel)[3]

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(first_attach) for _ in range(2)]
        attached = [future.result(timeout=30) for future in futures]
    assert attached[0]["request_id"] == attached[1]["request_id"]
    assert attached[0]["task_id"] == attached[1]["task_id"]
    with ddo_kernel["engine"].connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM ops.data_request")).scalar_one() == 1
        assert (
            connection.execute(
                text("SELECT count(*) FROM ops.task WHERE data_request_id IS NOT NULL")
            ).scalar_one()
            == 1
        )


@preparation_fixture("ddo_selected_graph")
def selected_graph_case(request, scenario_seeds):
    with scenario_seeds.rollback_family(request.param) as case:
        yield case


@pytest.mark.parametrize("selected_graph_case", [STORAGE], indirect=True, ids=["storage"])
@pytest.mark.parametrize("mutation", ["dependency", "roots", "discovery", "duplicate"])
def test_registration_rejects_forged_selected_graph_with_authentic_node_identities(
    selected_graph_case, mutation
):
    from copy import deepcopy

    from native_refusals import native_refusal

    from corpus_structure.semantic.data_operation_demands import freeze_demand
    from semantic.data_operation_declaration_support import root_subject

    case = selected_graph_case
    preparation = case.stage.preparation
    connection = case.connection
    selected = freeze_demand(
        preparation.model,
        roots=(root_subject(subject="subject:one", source="source:test", scope={"page": 1}),),
        targets=("urn:ddo-test:source",),
        inference="inference:test",
        execution_profile="execution:test",
    ).record
    payload = {
        "project_id": "ddo-test",
        "release_id": preparation.prepared.release_id,
        "runtime_id": preparation.runtime.runtime_id,
        "root": selected["roots"],
        "selection": selected,
        "strength": "value",
    }

    def effects():
        return connection.execute(
            text(
                "SELECT (SELECT count(*) FROM ops.data_demand),"
                "(SELECT count(*) FROM ops.data_request),(SELECT count(*) FROM ops.task)"
            )
        ).one()

    assert effects() == (0, 0, 0)
    with connection.begin_nested() as positive:
        admitted = DataOperationStorage(connection).register_data_demand(
            typing_cast(WireRegisterDataDemandRequest, payload)
        )
        assert admitted["demand_id"]
        assert effects() == (1, 0, 0)
        positive.rollback()
    assert effects() == (0, 0, 0)
    frozen = deepcopy(selected)
    if mutation == "dependency":
        frozen["operations"][0]["dependencies"] = [frozen["operations"][0]["operation"]]
    elif mutation == "roots":
        # Use an authentic admitted operation, but forge its membership in this
        # selected graph. Empty roots would fail wire admission before this guard.
        frozen["root_operations"] = [preparation.model.operation("urn:ddo-test:sample").semantic_id]
    elif mutation == "discovery":
        frozen["discovery"] = [
            {
                "producer": WireOperationId("urn:ddo-test:source"),
                "output_role": "result",
                "target": WireOperationId("urn:ddo-test:source"),
                "population": "forged",
            }
        ]
    else:
        frozen["operations"].append(deepcopy(frozen["operations"][0]))
    expected = {
        "dependency": "selected dependencies differ from the authenticated declared graph",
        "roots": "root operations differ from selected dependency closure",
        "discovery": "discovery relation differs from declared producer output",
        "duplicate": "selected dependencies differ from the authenticated declared graph",
    }
    with native_refusal("P0001", message=expected[mutation]), connection.begin_nested():
        DataOperationStorage(connection).register_data_demand(
            typing_cast(WireRegisterDataDemandRequest, {**payload, "selection": frozen})
        )
    assert effects() == (0, 0, 0)


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
@pytest.mark.parametrize("uncommitted_intent", [False, True])
def test_native_planner_rebinds_equal_support_or_replaces_invalid_retained_generation(
    ddo_kernel, uncommitted_intent
):
    from corpus_structure.semantic.data_operation_demands import DemandPlanner

    targets = ("urn:ddo-test:value-consumer",)
    demand, _, _, source_request = attach(
        ddo_kernel, operation="urn:ddo-test:sample", targets=targets
    )
    sample_kind = next(
        identity.key
        for identity in ddo_kernel["model"].identities
        if identity.domain == "kind"
        and any(
            kind.semantic_id == identity.owner and kind.name == "Sample"
            for kind in ddo_kernel["model"].kinds
        )
    )

    def sample_output(completion):
        completion["outputs"][0]["product"].update(
            kind_contract=sample_kind, body=semantic_value({"value": 15})
        )

    source_fence = claim(ddo_kernel, source_request)
    original_source = publish(
        ddo_kernel, source_fence, retain(ddo_kernel, source_fence, mutate=sample_output)
    )
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        snapshot = planner.resume(demand["demand_id"])
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        ready = planner.ready(snapshot, authorization=b"{}")
        assert len(ready) == 1 and ready[0].operation == "urn:ddo-test:value-consumer"
        consumer = ready[0]
        consumer_native = json.loads(consumer.native)
        consumer_binding = json.loads(consumer.binding)
    consumer_fence = claim(ddo_kernel, consumer_native)

    def consumer_inputs(completion):
        completion.update(inputs=consumer_binding["inputs"], support=consumer_binding["support"])

    original_intent = retain(ddo_kernel, consumer_fence, mutate=consumer_inputs)
    original_receipt = (
        None if uncommitted_intent else publish(ddo_kernel, consumer_fence, original_intent)
    )
    with ddo_kernel["engine"].begin() as connection:
        DataOperationStorage(connection).revoke_data_support(
            typing_cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": "ddo-test",
                    "original_source": "source:test",
                    "selector_kind": "derivation",
                    "selector": original_source["derivation_id"],
                    "reason": "replace an invalid upstream observation",
                },
            )
        )
    # A new authentic upstream episode produces the exact same semantic value.
    _, _, _, replacement_source = attach(
        ddo_kernel, operation="urn:ddo-test:sample", targets=targets
    )
    assert replacement_source["generation"] == source_request["generation"] + 1
    replacement_fence = claim(ddo_kernel, replacement_source)
    replacement_receipt = publish(
        ddo_kernel, replacement_fence, retain(ddo_kernel, replacement_fence, mutate=sample_output)
    )
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        snapshot = planner.resume(demand["demand_id"])
    if uncommitted_intent:
        with ddo_kernel["engine"].begin() as connection:
            planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
            assert planner.ready(snapshot, authorization=b"{}") == ()
            assert len(planner.refusals) == 1
            assert any(word in str(planner.refusals[0]) for word in ("active", "lease", "invalid"))
            released = planner.storage.release_data_attempt(
                typing_cast(
                    WireReleaseDataAttemptRequest,
                    {
                        **consumer_fence,
                        "physical_retirement": "confirmed",
                        "failure": {
                            "code": "invalidated-support",
                            "message": "computation retired",
                        },
                    },
                )
            )
            assert released["state"] == "released"
            updated_snapshot = planner.resume(demand["demand_id"])
        with ddo_kernel["engine"].begin() as connection:
            planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
            updated = planner.ready(updated_snapshot, authorization=b"{}")
            assert len(updated) == 1
            new_request = json.loads(updated[0].native)
            assert new_request["request_id"] == consumer_native["request_id"]
            assert new_request["generation"] == consumer_native["generation"] + 1
            assert new_request["action"] == "compute"
            old = planner.storage.inspect_data_completion(
                typing_cast(
                    WireInspectDataCompletionRequest,
                    {
                        "request_id": consumer_native["request_id"],
                        "generation": consumer_native["generation"],
                        "intent_id": original_intent["intent_id"],
                    },
                )
            )
            assert old["state"] == "known-uncommitted" and old["intent_retained"]
    else:
        with ddo_kernel["engine"].begin() as connection:
            planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
            assert original_receipt is not None
            previous = next(
                use
                for use in snapshot["uses"]
                if use["request_id"] == consumer_native["request_id"]
            )
            assert previous["rebind_derivation"] == original_receipt["derivation_id"]
            assert planner.ready(snapshot, authorization=b"{}") == ()
            assert consumer_native["request_id"] in planner.fulfilled_request_ids
            after = planner.resume(demand["demand_id"])
            use = next(
                use for use in after["uses"] if use["request_id"] == consumer_native["request_id"]
            )
            assert (
                use["fate"] == "fulfilled"
                and use["derivation_id"] == original_receipt["derivation_id"]
            )
            support = use["selection"].get("support")
            assert isinstance(support, list)
            assert any(
                isinstance(item, dict)
                and item.get("derivation_id") == replacement_receipt["derivation_id"]
                for item in support
            )
            assert (
                connection.execute(
                    text("SELECT count(*) FROM ops.data_derivation WHERE request_id=:id"),
                    {"id": consumer_native["request_id"]},
                ).scalar_one()
                == 1
            )
    if uncommitted_intent:
        with pytest.raises(DBAPIError, match=r"stale|fence"):
            publish(ddo_kernel, consumer_fence, original_intent)


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_overlapping_differing_intents_preserve_one_answer_and_its_publication(ddo_kernel):
    from queue import Queue

    _, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    payload = {
        **fence,
        "runtime_id": ddo_kernel["runtime"],
        "completion": {
            "outcome": "success",
            "inputs": [],
            "support": [],
            "implementation_revision": "native-test-source-v1",
            "outputs": [
                {
                    "role": "result",
                    "position": 0,
                    "multiplicity": 1,
                    "product": {
                        "kind_contract": ddo_kernel["kind"],
                        "body": ["integer", "1"],
                        "members": [],
                    },
                }
            ],
        },
    }
    changed = json.loads(json.dumps(payload))
    changed["completion"]["outputs"][0]["product"]["body"] = ["integer", "2"]
    backend = Queue()

    def conflicting():
        with ddo_kernel["engine"].begin() as connection:
            backend.put(connection.execute(text("SELECT pg_backend_pid()")).scalar_one())
            return DataOperationStorage(connection).retain_data_completion_intent(
                typing_cast(WireRetainDataCompletionIntentRequest, changed)
            )

    with ThreadPoolExecutor(max_workers=1) as pool:
        with ddo_kernel["engine"].begin() as connection:
            original = DataOperationStorage(connection).retain_data_completion_intent(
                typing_cast(WireRetainDataCompletionIntentRequest, payload)
            )
            future = pool.submit(conflicting)
            pid = backend.get(timeout=10)
            deadline = time.monotonic() + 10
            while not connection.execute(
                text("SELECT cardinality(pg_blocking_pids(:pid))>0"), {"pid": pid}
            ).scalar_one():
                if time.monotonic() >= deadline:
                    pytest.fail("conflicting intent did not reach the retained-answer lock")
                time.sleep(0.01)
        with pytest.raises(DBAPIError, match="immutable"):
            future.result(timeout=10)
    receipt = publish(ddo_kernel, fence, original)
    assert publish(ddo_kernel, fence, original) == {**receipt, "replayed": True}
    with ddo_kernel["engine"].connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM ops.data_completion_intent")) == 1
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 1


def test_native_nominal_topology_capture_requires_the_execution_declaration():
    name = "native/data-operation-graph-execution.json"
    sources = native_protocol_sources()
    assert name in {source.name for source in sources}
    with pytest.raises(ValueError, match="captured"):
        native_source_digest(tuple(source for source in sources if source.name != name))
    altered = tuple(
        replace(source, content=source.content + b"\n") if source.name == name else source
        for source in sources
    )
    assert native_source_digest(altered) == native_source_digest(sources)


@pytest.mark.parametrize(
    "name",
    [
        "native/data-operation-kind-refinements.py",
        "native/data-operation-graph-topology.py",
        "native/data-operation-graph-runtime.py",
    ],
)
def test_native_program_manifest_keeps_topology_provenance_out_of_program_identity(name):
    sources = native_protocol_sources()
    initial = native_source_digest(sources)
    altered = tuple(
        replace(source, content=source.content + b"\n") if source.name == name else source
        for source in sources
    )
    assert native_source_digest(altered) == initial
    assert (
        native_source_digest(tuple(source for source in sources if source.name != name)) == initial
    )


def test_native_graph_execution_capture_names_selected_engine_and_library():
    import json
    from pathlib import Path

    from corpus_structure.semantic import graph_runtime, graph_topology

    captured = {source.name: source.content for source in native_protocol_sources()}
    assert (
        captured["native/data-operation-graph-topology.py"]
        == Path(graph_topology.__file__).read_bytes()
    )
    assert (
        captured["native/data-operation-graph-runtime.py"]
        == Path(graph_runtime.__file__).read_bytes()
    )
    assert json.loads(captured["native/data-operation-graph-execution.json"]) == {
        "version": "data-operation-graph-execution-v1",
        "networkx": "3.7",
        "backend": "networkx",
    }


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_set_validity_deduplicates_and_refuses_cyclic_support(ddo_kernel):
    _, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    receipt = publish(ddo_kernel, fence, retain(ddo_kernel, fence))
    episode = receipt["derivation_id"]
    with ddo_kernel["engine"].begin() as connection:
        rows = connection.execute(
            text("SELECT kind,id,valid FROM ops.ddo_valid_closure('{}',ARRAY[:episode,:episode])"),
            {"episode": episode},
        ).all()
        assert len(rows) == len({(row.kind, row.id) for row in rows})
        assert next(row.valid for row in rows if row.kind == "episode" and row.id == episode)
        connection.execute(
            text(
                "INSERT INTO ops.data_derivation_support "
                "SELECT :episode,'deliberate-cycle',0,:episode,ops.ddo_scope('ddo-test','source:test'),0,NULL,999999"
            ),
            {"episode": episode},
        )
        assert (
            connection.scalar(
                text("SELECT ops.ddo_node_valid('episode',:episode)"), {"episode": episode}
            )
            is False
        )


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_read_acquisition_forbids_later_frontier_writes(ddo_kernel):
    demand, _, _, _ = attach(ddo_kernel)
    with ddo_kernel["engine"].begin() as connection:
        DataOperationStorage(connection).read_demand_result(
            typing_cast(WireReadDemandResultRequest, demand)
        )
        with pytest.raises(DBAPIError, match="fresh transaction"):
            connection.execute(
                text(
                    "INSERT INTO ops.data_obligation SELECT * FROM ops.data_obligation LIMIT 1 ON CONFLICT DO NOTHING"
                )
            )


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_completion_receipt_records_actual_validator_not_release_expectation(ddo_kernel):
    _, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence)
    with ddo_kernel["engine"].begin() as connection:
        payload, payload_digest, seal = connection.execute(
            text(
                "SELECT CAST(payload AS text), payload_digest, validation_seal "
                "FROM ops.data_completion_intent WHERE id=:id"
            ),
            {"id": intent["intent_id"]},
        ).one()
        completion = json_loads(payload)
        assert payload_digest == sha256(canonical_bytes(completion)).hexdigest()
        intent_frame = [
            fence["request_id"],
            fence["generation"],
            fence["task_id"],
            fence["attempt"],
            fence["holder"],
            ddo_kernel["runtime"],
            completion,
        ]
        assert intent["intent_id"] == "intent:" + sha256(canonical_bytes(intent_frame)).hexdigest()
        assert seal["payload"] == intent["payload_digest"] == payload_digest
        assert seal["request"] == fence["request_id"]
        assert seal["generation"] == fence["generation"]
        assert seal["runtime"] == ddo_kernel["runtime"]
        assert seal["trust"] and all(epoch == 0 for epoch in seal["trust"].values())
        source_digest = connection.scalar(
            text("SELECT sem.data_operation_native_descriptor()->>'source_digest'")
        )
        validators = connection.scalar(
            text(
                "SELECT ops.ddo_current_validation_identities(release_id, operation_id) "
                "FROM ops.data_request WHERE id=:id"
            ),
            {"id": fence["request_id"]},
        )
        assert seal["validators"] == validators
    receipt = publish(ddo_kernel, fence, intent)
    with ddo_kernel["engine"].begin() as connection:
        actual = connection.execute(
            text(
                "SELECT validating_kernel_digest, validation_identities "
                "FROM ops.data_publication_receipt WHERE id=:id"
            ),
            {"id": receipt["receipt_id"]},
        ).one()
        assert tuple(actual) == (source_digest, validators)


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_read_records_zero_epochs_and_refuses_unrecorded_old_reads(ddo_kernel):
    demand, _, _, _ = attach(ddo_kernel)
    with ddo_kernel["engine"].begin() as connection:
        read = DataOperationStorage(connection).read_demand_result(
            typing_cast(WireReadDemandResultRequest, demand)
        )
        scopes = connection.execute(
            text(
                "SELECT scope,epoch,ordinary,domain FROM ops.data_demand_read_scope WHERE read_id=:read ORDER BY scope"
            ),
            {"read": read["read_id"]},
        ).all()
        assert scopes and {row.scope: row.epoch for row in scopes} == read["trust_snapshot"]
        assert all(row.epoch == 0 and row.ordinary and not row.domain for row in scopes)
        eligibility = connection.execute(
            text(
                "SELECT grade_census_eligible,fit_census_eligible FROM ops.data_demand_read WHERE id=:read"
            ),
            {"read": read["read_id"]},
        ).one()
        assert eligibility.grade_census_eligible and eligibility.fit_census_eligible
    with ddo_kernel["engine"].begin() as connection:
        old_id = read["read_id"] + ":unrecorded"
        connection.execute(
            text(
                "INSERT INTO ops.data_demand_read(id,demand_id,read_snapshot,frontier_at,owner_xid,trust_snapshot,scope) "
                "SELECT :old,demand_id,read_snapshot,frontier_at,owner_xid,trust_snapshot,scope FROM ops.data_demand_read WHERE id=:read"
            ),
            {"old": old_id, "read": read["read_id"]},
        )
    with (
        ddo_kernel["engine"].begin() as connection,
        pytest.raises(DBAPIError, match="reacquisition"),
    ):
        DataOperationStorage(connection).read_demand_result(
            typing_cast(WireReadDemandResultRequest, {**demand, "read_id": old_id})
        )


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_cancellation_locks_recorded_support_scopes_outside_its_roots(ddo_kernel):
    from psycopg.errors import LockNotAvailable

    demand, _, _, attached = attach(ddo_kernel)
    attach(ddo_kernel, original_source="source:other")
    with ddo_kernel["engine"].begin() as connection:
        # A retained settlement scope remains relevant even after a later use
        # becomes current. It carries no extra value or permission authority.
        connection.execute(
            text(
                "INSERT INTO ops.demand_use "
                "SELECT 'use:historical-scope',demand_id,obligation_id,fate,request_id,generation,derivation_id,selection,"
                "jsonb_build_object(ops.ddo_scope('ddo-test','source:other'),0),clock_timestamp()-interval '1 day',pg_current_xact_id()::text "
                "FROM ops.demand_use WHERE id=:use"
            ),
            {"use": attached["use_id"]},
        )
        DataOperationStorage(connection).cancel_data_demand(
            {"demand_id": demand["demand_id"], "reason": "test exact historical barrier"}
        )
        with ddo_kernel["engine"].begin() as contender, pytest.raises(DBAPIError) as blocked:
            contender.execute(
                text(
                    "SELECT epoch FROM ops.data_trust_scope WHERE scope=ops.ddo_scope('ddo-test','source:other') FOR UPDATE NOWAIT"
                )
            )
        assert isinstance(blocked.value.orig, LockNotAvailable)
        assert blocked.value.orig.sqlstate == "55P03"


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
@pytest.mark.parametrize(
    "shape", ["shared-descendant", "mixed-validity", "two-node-cycle", "superseded-population"]
)
def test_installed_validity_closure_matches_authored_reference_graph(ddo_kernel, shape):
    from datetime import timedelta

    from corpus_structure.semantic.metadata import table

    episodes: dict[str, str] = {}
    demands: dict[str, str] = {}
    expected: dict[tuple[str, str], bool]
    seeds: list[str]
    producers = ("shared",) if shape == "superseded-population" else ("left", "right", "shared")
    for name in producers:
        demand, _, _, attached = attach(ddo_kernel, subject="reference:" + name)
        fence = claim(ddo_kernel, attached)
        receipt = publish(ddo_kernel, fence, retain(ddo_kernel, fence))
        episodes[name] = receipt["derivation_id"]
        demands[name] = demand["demand_id"]

    with ddo_kernel["engine"].begin() as connection:
        if shape == "superseded-population":
            use = connection.scalar(
                text(
                    "SELECT id FROM ops.demand_use WHERE demand_id=:demand AND derivation_id=:episode"
                ),
                {"demand": demands["shared"], "episode": episodes["shared"]},
            )
            assert use is not None
            now, xid = connection.execute(
                text("SELECT clock_timestamp(),pg_current_xact_id()::text")
            ).one()
            for name, created in (("old", now), ("new", now + timedelta(seconds=1))):
                connection.execute(
                    table("ops.data_population").insert(),
                    {
                        "id": "reference-population:" + name,
                        "demand_id": demands["shared"],
                        "semantic_key": "reference-population-key:" + name,
                        "name": "reference-population",
                        "context_key": "reference-context",
                        "members": [],
                        "complete": True,
                        "evidence": {"admission_use_id": use, "derivation_id": episodes["shared"]},
                        "created_at": created,
                        "created_xid": xid,
                    },
                )
            expected = {
                ("population", "reference-population:old"): False,
                ("population", "reference-population:new"): True,
                ("use", use): True,
                ("episode", episodes["shared"]): True,
                ("producer", episodes["shared"]): True,
            }
            seeds = ["reference-population:old", "reference-population:new"]
            kind = "population"
            query = text(
                "SELECT kind,id,valid FROM ops.ddo_valid_closure('{}','{}',NULL,CAST(:seeds AS text[]))"
            )
        else:
            links = [("left", "shared"), ("right", "shared")]
            if shape == "two-node-cycle":
                links.append(("shared", "left"))
            source_scope = connection.scalar(text("SELECT ops.ddo_scope('ddo-test','source:test')"))
            for parent, child in links:
                connection.execute(
                    table("ops.data_derivation_support").insert(),
                    {
                        "derivation_id": episodes[parent],
                        "role": "authored-reference-edge",
                        "position": 0,
                        "support_derivation_id": episodes[child],
                        "scope": source_scope,
                        "epoch": 0,
                        "admission_use_id": None,
                        "occurrence": 0,
                    },
                )
            expected = {
                (kind, episode): kind == "producer" or shape != "two-node-cycle"
                for kind in ("episode", "producer")
                for episode in episodes.values()
            }
            seeds = [episodes["left"], episodes["right"]]
            if shape == "mixed-validity":
                seeds.append("reference:absent-episode")
                expected.update(
                    {
                        ("episode", "reference:absent-episode"): False,
                        ("producer", "reference:absent-episode"): False,
                    }
                )
            kind = "episode"
            query = text(
                "SELECT kind,id,valid FROM ops.ddo_valid_closure('{}',CAST(:seeds AS text[]))"
            )
        actual = {
            (row.kind, row.id): row.valid for row in connection.execute(query, {"seeds": seeds})
        }
        assert actual == expected
        for seed in seeds:
            alone = {
                (row.kind, row.id): row.valid
                for row in connection.execute(query, {"seeds": [seed]})
            }
            assert alone[kind, seed] is expected[kind, seed]
            assert all(valid is expected[node] for node, valid in alone.items())


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
@pytest.mark.parametrize("seal", ["current", "other", "absent", "invariant"])
def test_historical_completion_always_checks_retained_intent_integrity(ddo_kernel, seal):
    from native_refusals import native_refusal

    _, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence)
    receipt = publish(ddo_kernel, fence, intent)
    check = text(
        "SELECT (ops.ddo_require_episode_correspondence(d,i)).id "
        "FROM ops.data_derivation d JOIN ops.data_completion_intent i ON i.id=d.intent_id "
        "WHERE d.id=:episode"
    )
    params = {"episode": receipt["derivation_id"]}
    with ddo_kernel["engine"].connect() as connection:
        transaction = connection.begin()
        try:
            assert connection.scalar(check, params) == fence["request_id"]
            # This owned rollback-only DATA fixture bypasses the intrinsic write guard
            # so the validator's reuse decision receives deliberately inconsistent data.
            for relation in ("ops.data_completion_intent", "ops.data_publication_receipt"):
                connection.exec_driver_sql(
                    "ALTER TABLE " + relation + " DISABLE TRIGGER semantic_immutable"
                )
            if seal in {"other", "absent"}:
                connection.execute(
                    text(
                        "UPDATE ops.data_publication_receipt "
                        "SET validation_identities=CAST(:identities AS jsonb) WHERE id=:id"
                    ),
                    {
                        "id": receipt["receipt_id"],
                        "identities": None
                        if seal == "absent"
                        else json.dumps({"conservative": "other-validator"}),
                    },
                )
            if seal == "invariant":
                connection.execute(
                    text(
                        "UPDATE ops.data_completion_intent SET payload=jsonb_set(payload,'{execution_evidence}',"
                        "CAST(:evidence AS jsonb)) WHERE id=:id"
                    ),
                    {
                        "id": intent["intent_id"],
                        "evidence": json.dumps(
                            {"pdf_receipts": [{"controlled": "foreign-PDF-event"}]}
                        ),
                    },
                )
                connection.execute(
                    text(
                        "UPDATE ops.data_completion_intent SET payload_digest=ops.ddo_digest(payload) WHERE id=:id"
                    ),
                    {"id": intent["intent_id"]},
                )
                reason = "non-PDF computation cannot acquire a PDF execution event"
            else:
                connection.execute(
                    text(
                        "UPDATE ops.data_completion_intent SET payload=payload||CAST(:corruption AS jsonb) WHERE id=:id"
                    ),
                    {
                        "id": intent["intent_id"],
                        "corruption": json.dumps({"controlled_corruption": True}),
                    },
                )
                reason = "historical intent payload digest differs"
            with native_refusal("23514", message=reason):
                connection.execute(check, params)
        finally:
            transaction.rollback()
