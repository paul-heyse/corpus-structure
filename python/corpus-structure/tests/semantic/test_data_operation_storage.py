"""Fixed protocol compilation and genuine installed native demand/publication controls."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier
from typing import Any

import pytest
from sqlalchemy import insert, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_identity import SemanticRequestKey, semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_storage import (
    DataOperationStorage,
    native_operation_calls,
    native_operation_declarations,
    native_protocol_sources,
    native_source_digest,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
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


def test_kernel_protocol_is_captured_effective_meaning_not_an_ambient_catalog():
    captured = native_protocol_sources()
    declaration = native_operation_declarations(captured)
    model = compile_data_operations(declarations=(declaration,))
    calls = native_operation_calls(model, sources=captured)
    assert {owner for owner, _ in calls} == {
        operation.semantic_id for operation in model.operations
    }
    assert all(call.parameters[0].native_parameter == "p_payload" for _, call in calls)
    assert all(call.result_fields[0].native_field == "payload" for _, call in calls)
    assert all(call.source_digest == native_source_digest(captured) for _, call in calls)
    altered = tuple(
        replace(source, content=source.content + b"\n-- changed native behavior\n")
        if source.name.endswith(".sql")
        else source
        for source in captured
    )
    changed = compile_data_operations(declarations=(native_operation_declarations(altered),))
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
        result = DataOperationStorage(connection).invoke(
            "read_demand_result", {**demand, "view": "products"}
        )
        assert result["intent"]["root_operations"] == ["urn:ddo-test:source"]
        assert result["uses"][0]["fate"] == "fulfilled"
        assert [p["body"] for p in result["uses"][0]["products"]] == [
            ["integer", "1"],
            ["integer", "2"],
        ]
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 1
        assert connection.scalar(text("SELECT count(*) FROM ops.data_publication_receipt")) == 1


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_zero_output_has_authentic_fulfillment(ddo_kernel):
    demand, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence, outputs=(), outcome="empty")
    publish(ddo_kernel, fence, intent)
    with ddo_kernel["engine"].connect() as connection:
        result = DataOperationStorage(connection).invoke("read_demand_result", demand)
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
        result = DataOperationStorage(connection).invoke(
            "read_demand_result",
            {**demand, "view": "products"},
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
            return DataOperationStorage(connection).invoke("attach_data_request", wire)

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
        assert connection.scalar(text("SELECT count(*) FROM ops.run")) == 0


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
        reconciliation = DataOperationStorage(connection).invoke("attach_data_request", wire)
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
        adopted = DataOperationStorage(connection).invoke(
            "adopt_data_completion_intent",
            {
                **second,
                "intent_id": intent["intent_id"],
            },
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
        inspected = DataOperationStorage(connection).invoke(
            "inspect_data_completion",
            {
                "request_id": first["request_id"],
                "generation": first["generation"],
                "intent_id": intent["intent_id"],
            },
        )
        assert inspected["receipt_id"] == receipt["receipt_id"]
        assert inspected["state"] == "committed"


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
        DataOperationStorage(connection).invoke(
            "revoke_data_support",
            {
                "project_id": "ddo-test",
                "original_source": "source:test",
                "selector_kind": "runtime",
                "selector": ddo_kernel["runtime"],
                "reason": "producer runtime defect",
            },
        )
    updated = {**ddo_kernel, "runtime": replacement.runtime_id}
    if active:
        with pytest.raises(DBAPIError, match="active producer lease"):
            attach(updated)
        with ddo_kernel["engine"].connect() as connection:
            assert (
                connection.scalar(
                    text("SELECT generation FROM ops.data_request WHERE id=:r"),
                    {"r": first["request_id"]},
                )
                == first["generation"]
            )
        return
    expire_lease(ddo_kernel, first)
    # A directly revoked runtime cannot rescue its own immutable answer.
    with pytest.raises(DBAPIError, match="replacement runtime or recipe"):
        attach(ddo_kernel)
    _, _, _, current = attach(updated)
    assert current["request_id"] == first["request_id"]
    assert current["generation"] == first["generation"] + 1
    assert current["task_id"] != first["task_id"]
    assert current["action"] == "compute"
    assert current["retained_intent_id"] is None
    with ddo_kernel["engine"].connect() as connection:
        storage = DataOperationStorage(connection)
        historical = storage.invoke(
            "inspect_data_completion",
            {
                "demand_id": demand["demand_id"],
                "request_id": first["request_id"],
                "generation": first["generation"],
                "intent_id": intent["intent_id"],
            },
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
        again = DataOperationStorage(connection).invoke(
            "attach_data_request",
            {
                **wire,
                "binding": {
                    **wire["binding"],
                    "read_id": DataOperationStorage(connection).invoke(
                        "read_demand_result", demand
                    )["read_id"],
                },
            },
        )
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
        revoked = storage.invoke(
            "revoke_data_support",
            {
                "project_id": "ddo-test",
                "original_source": "source:test",
                "selector_kind": "derivation",
                "selector": receipt["derivation_id"],
                "reason": "independent producer defect",
            },
        )
        assert revoked["epoch"] == 1
        inspected = storage.invoke(
            "inspect_data_completion",
            {
                "request_id": first["request_id"],
                "generation": first["generation"],
                "intent_id": intent["intent_id"],
            },
        )
        assert inspected["state"] == "committed"
        result = storage.invoke("read_demand_result", demand)
        assert result["uses"][0]["fate"] == "unavailable"
        current = storage.invoke(
            "attach_data_request",
            {**wire, "binding": {**wire["binding"], "read_id": result["read_id"]}},
        )
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
def test_native_frozen_scope_refuses_unrelated_subject(ddo_kernel):
    demand, _, _, _ = attach(ddo_kernel)
    with ddo_kernel["engine"].begin() as connection, pytest.raises(DBAPIError, match="scope"):
        DataOperationStorage(connection).invoke(
            "expand_data_obligation",
            {
                "demand_id": demand["demand_id"],
                "operation_id": "urn:ddo-test:source",
                "subject": "invented",
                "original_source": "source:test",
                "analyzed_scope": {"page": 99},
                "parameters": {},
            },
        )


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
        DataOperationStorage(connection).invoke(
            "register_data_demand",
            {
                "project_id": "ddo-test",
                "release_id": ddo_kernel["prepared"].release_id,
                "runtime_id": ddo_kernel["runtime"],
                "root": selected["roots"],
                "selection": selected,
                "strength": "independent",
            },
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
        DataOperationStorage(connection).invoke(
            "revoke_data_support",
            {
                "project_id": "ddo-test",
                "original_source": "source:test",
                "selector_kind": "derivation",
                "selector": receipt["derivation_id"],
                "reason": "producer behavior is defective",
            },
        )
    with ddo_kernel["engine"].begin() as connection:
        fresh = DataOperationStorage(connection).invoke("read_demand_result", demand)
    wire = {**wire, "binding": {**wire["binding"], "read_id": fresh["read_id"]}}
    with (
        ddo_kernel["engine"].begin() as connection,
        pytest.raises(DBAPIError, match="rehabilitate"),
    ):
        DataOperationStorage(connection).invoke(
            "attach_data_request",
            {
                **wire,
                "rebind_derivation": receipt["derivation_id"],
            },
        )


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_failed_completion_is_historical_but_never_reusable_fulfillment(ddo_kernel):
    demand, _, wire, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence, outputs=(), outcome="failed")
    receipt = publish(ddo_kernel, fence, intent)
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        observed = storage.invoke("read_demand_result", demand)
        assert observed["uses"][0]["fate"] == "failed"
        assert observed["uses"][0]["completion_state"] == "failed"
        assert observed["uses"][0]["products"] == []
        current = storage.invoke("attach_data_request", wire)
        assert current["fate"] == "attached"
        assert current["derivation_id"] is None
        assert current["generation"] == attached["generation"] + 1
        historical = storage.invoke(
            "inspect_data_completion",
            {
                "demand_id": demand["demand_id"],
                "intent_id": intent["intent_id"],
            },
        )
        assert historical["state"] == "committed"
        assert historical["receipt_id"] == receipt["receipt_id"]


def _protected_binding_case(
    ddo_kernel, case: BindingEvidenceCase, *, prepare_only=False
) -> tuple[dict[str, Any], SemanticRequestKey]:
    from decimal import Decimal

    from corpus_structure.semantic.data_operation_identity import OptionalValue, SemanticRequestKey

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
        intent = DataOperationStorage(connection).invoke(
            "retain_data_completion_intent",
            {**fence, "runtime_id": ddo_kernel["runtime"], "completion": completion},
        )
    receipt = publish(ddo_kernel, fence, intent)
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        result = storage.invoke("read_demand_result", demand)
        use = result["uses"][0]
        product = use["products"][0]["product_id"]
        # The same authored range case drives the PostgreSQL full-result check
        # and this real admitted-product/protected-writer observation.
        native_row = connection.execute(
            text(
                "SELECT body FROM ops.data_binding_rows(:d,:o,CAST(:t AS jsonb),"
                ":read,:subject,:source,CAST(:scope AS jsonb))"
            ),
            {
                "d": demand["demand_id"],
                "o": "urn:ddo-test:consumer",
                "t": json.dumps(result["trust_snapshot"]),
                "read": result["read_id"],
                "subject": result["root"][0]["subject"],
                "source": result["root"][0]["original_source"],
                "scope": json.dumps(result["root"][0]["analyzed_scope"]),
            },
        ).scalar_one()
        assert native_row == {"value": sample_value}
        obligation = storage.invoke(
            "expand_data_obligation",
            {
                "demand_id": demand["demand_id"],
                "operation_id": "urn:ddo-test:consumer",
                "subject": "subject:one",
                "original_source": "source:test",
                "analyzed_scope": {"page": 1},
                "parameters": {},
            },
        )
        # Authored scalar-input meaning, independent of the compiled binder and
        # project_operation_binding. Only opaque identities come from real custody.
        member = {
            "product": product,
            "kind": sample_kind,
            "subject": "subject:one",
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
            subject_context=SubjectContext("ddo-test", "subject:one", "source:test", b'{"page":1}'),
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
                        "support_derivation_id": receipt["derivation_id"],
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

    from native_refusals import native_refusal

    with ddo_kernel.purpose("write").begin() as writer:
        if case.native_refusal is not None:
            sqlstate, message = case.native_refusal
            with native_refusal(sqlstate, message=message), writer.begin_nested():
                writer.scalar(
                    text("SELECT ops.attach_data_request(CAST(:p AS jsonb))"),
                    {"p": json.dumps(payload)},
                )
        else:
            attached = writer.scalar(
                text("SELECT ops.attach_data_request(CAST(:p AS jsonb))"),
                {"p": json.dumps(payload)},
            )
            assert attached["payload"]["request_id"] == request.identity.key
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

    from native_refusals import native_refusal

    from corpus_structure.semantic.data_operation_identity import OptionalValue, SemanticRequestKey

    baseline, authored = _protected_binding_case(
        ddo_kernel, BINDING_RANGE_CASES["range-ready"], prepare_only=True
    )
    # These are protected-admission obligations, not expression-only comparisons.
    reasons = (
        ("role-too-few", "P0001", "native binding role cardinality differs"),
        ("extra-role", "P0001", "request input roles differ from admitted definition"),
        ("missing-role", "P0001", "missing request role"),
        ("unknown-input", "P0001", "incomplete input cannot attach runnable request"),
        ("known-absent-required", "P0001", "incomplete input cannot attach runnable request"),
        (
            "wrong-source-meaning",
            "P0001",
            "semantic request member differs from native product/member",
        ),
        (
            "wrong-context-meaning",
            "P0001",
            "semantic request member differs from native product/member",
        ),
        ("member-removed", "23514", "selected binding row is outside current admitted universe"),
        (
            "position-substitution",
            "23514",
            "selected binding row is outside current admitted universe",
        ),
        ("support-episode-substitution", "P0002", "query returned no rows", "ddo_validate_binding"),
        (
            "unselected-alternative",
            "P0001",
            "population meaning lacks exact native receipt locator",
        ),
    )
    statement = text("SELECT ops.attach_data_request(CAST(:p AS jsonb))")

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
        for name, sqlstate, message, *diagnostic_context in reasons:
            # The same admitted product and acquired read succeed under the writer
            # before each one-field semantic/manifest substitution; rollback it.
            with writer.begin_nested() as reach:
                accepted = writer.scalar(statement, {"p": json.dumps(baseline)})["payload"]
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
            try:
                with (
                    native_refusal(
                        sqlstate,
                        message=message,
                        context=diagnostic_context[0] if diagnostic_context else None,
                    ),
                    writer.begin_nested(),
                ):
                    writer.scalar(statement, {"p": json.dumps(payload)})
            except AssertionError as error:
                raise AssertionError(f"{name}: {error}") from error
            assert effects() == before, name


@pytest.mark.parametrize("ddo_kernel", [POPULATION], indirect=True, ids=["population"])
def test_actual_writer_requires_exact_authored_closed_population_binding(ddo_kernel):
    from copy import deepcopy
    from decimal import Decimal

    from native_refusals import native_refusal

    from corpus_structure.semantic.data_operation_identity import (
        CollectionValue,
        OptionalValue,
        SemanticRequestKey,
    )
    from semantic.data_operation_binding_support import discover

    demand, obligation, parent = discover(ddo_kernel, values=(15, 16))
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        read = storage.invoke("read_demand_result", demand)
        selected = storage.invoke(
            "select_data_population",
            {
                **obligation,
                "population_name": "selected-items",
                "parent_population_id": parent["population_id"],
                "read_id": read["read_id"],
            },
        )
        assert [member["member_id"] for member in selected["members"]] == ["m15", "m16"]
        assert selected["complete"] is True
        current = storage.invoke("read_demand_result", demand)
        rows = connection.execute(
            text(
                'SELECT member,subject,"position",multiplicity,body FROM ops.data_binding_rows('
                ':d,:o,CAST(:trust AS jsonb),:read,:subject,:source,CAST(:scope AS jsonb)) ORDER BY "position",member'
            ),
            {
                "d": demand["demand_id"],
                "o": "urn:consumer",
                "trust": json.dumps(current["trust_snapshot"]),
                "read": current["read_id"],
                "subject": "doc",
                "source": "source:test",
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
            "product": product,
            "kind": sample_kind,
            "subject": "item:15",
            "member": "m15",
            "original_source": "source:test",
            "analyzed_scope": {"page": Decimal(1)},
            "coverage": [],
            "position": None,
            "multiplicity": 1,
            "support_episodes": (episode,),
        },
        {
            "product": product,
            "kind": sample_kind,
            "subject": "item:16",
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
                "support_derivation_id": episode,
            },
            {
                "role": "items",
                "position": 0,
                "multiplicity": 1,
                "product_id": product,
                "member_id": "m16",
                "support_derivation_id": episode,
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
            subject_context=SubjectContext("ddo-test", "doc", "source:test", b'{"page":1}'),
        )
        return {
            "obligation_id": obligation["obligation_id"],
            "replicate": None,
            "request_key": request.identity.key,
            "request_meaning": json.loads(request.identity.canonical_input),
            "binding": {**selected_binding, "request_inputs": semantic_value(inputs)},
        }

    baseline = envelope(meaning, binding)
    statement = text("SELECT ops.attach_data_request(CAST(:p AS jsonb))")
    reasons = (
        ("member-removed", "23514", "selected native input bundles violate frozen binding"),
        (
            "witness-member-removed",
            "P0001",
            "population semantic witness differs from native closure value",
        ),
        (
            "witness-member-added",
            "P0001",
            "population semantic witness differs from native closure value",
        ),
        (
            "witness-incomplete",
            "P0001",
            "population semantic witness differs from native closure value",
        ),
        (
            "witness-receipt-missing",
            "P0001",
            "population witness lacks authenticated native receipt reference",
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
                accepted = writer.scalar(statement, {"p": json.dumps(baseline)})["payload"]
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
            try:
                with native_refusal(sqlstate, message=message), writer.begin_nested():
                    writer.scalar(
                        statement, {"p": json.dumps(envelope(selected_meaning, selected_binding))}
                    )
            except AssertionError as error:
                raise AssertionError(f"{name}: {error}") from error
            after = tuple(
                observer.execute(
                    text(
                        "SELECT (SELECT count(*) FROM ops.data_request WHERE operation_id='urn:consumer'), (SELECT count(*) FROM ops.task), (SELECT count(*) FROM ops.demand_use)"
                    )
                ).one()
            )
            assert after == before, name
        writer.scalar(statement, {"p": json.dumps(baseline)})
    with ddo_kernel["engine"].connect() as connection:
        retained = connection.scalar(
            text("SELECT binding FROM ops.data_request WHERE operation_id='urn:consumer'")
        )
        assert retained == {**binding, "execution_profile": "execution:test"}
        assert retained["inputs"] == binding["inputs"]
        assert retained["support"] == binding["support"]
        assert retained["populations"] == binding["populations"]


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_read_receipt_excludes_pre_cut_uncommitted_insert_after_it_commits(ddo_kernel):
    from corpus_structure.semantic.data_operation_demands import RootSubject, freeze_demand

    roots = tuple(RootSubject("subject:" + name, "source:test", b"{}") for name in ("a", "b", "c"))
    selected = freeze_demand(
        ddo_kernel["model"],
        roots=roots,
        targets=("urn:ddo-test:source",),
        inference="inference:test",
        execution_profile="execution:test",
    ).record
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        demand = storage.invoke(
            "register_data_demand",
            {
                "project_id": "ddo-test",
                "release_id": ddo_kernel["prepared"].release_id,
                "runtime_id": ddo_kernel["runtime"],
                "root": selected["roots"],
                "selection": selected,
                "strength": "value",
            },
        )
        baseline = [
            storage.invoke(
                "expand_data_obligation",
                {
                    "demand_id": demand["demand_id"],
                    "operation_id": "urn:ddo-test:source",
                    **root,
                    "parameters": {},
                },
            )["obligation_id"]
            for root in selected["roots"][:2]
        ]
    with ddo_kernel["engine"].connect() as unpublished:
        pending = unpublished.begin()
        later = DataOperationStorage(unpublished).invoke(
            "expand_data_obligation",
            {
                "demand_id": demand["demand_id"],
                "operation_id": "urn:ddo-test:source",
                **selected["roots"][2],
                "parameters": {},
            },
        )["obligation_id"]
        with ddo_kernel["engine"].begin() as reader:
            first = DataOperationStorage(reader).invoke(
                "read_demand_result", {**demand, "limit": 1}
            )
        assert first["continuation"] is not None
        pending.commit()
    with ddo_kernel["engine"].connect() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT created_at<=CAST(:cut AS timestamptz) "
                    "FROM ops.data_obligation WHERE id=:id"
                ),
                {"cut": first["frontier_at"], "id": later},
            )
            is True
        )
    collected = [row["obligation_id"] for row in first["obligations"]]
    continuation = first["continuation"]
    while continuation:
        with ddo_kernel["engine"].begin() as reader:
            page = DataOperationStorage(reader).invoke("read_demand_result", continuation)
        assert page["read_id"] == first["read_id"]
        collected.extend(row["obligation_id"] for row in page["obligations"])
        continuation = page["continuation"]
    assert collected == sorted(baseline)
    with ddo_kernel["engine"].begin() as reader:
        fresh = DataOperationStorage(reader).invoke("read_demand_result", demand)
    assert {row["obligation_id"] for row in fresh["obligations"]} == {*baseline, later}


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_read_receipt_excludes_future_writes_in_its_own_transaction(ddo_kernel):
    from corpus_structure.semantic.data_operation_demands import RootSubject, freeze_demand

    selected = freeze_demand(
        ddo_kernel["model"],
        roots=(
            RootSubject("subject:before", "source:test", b"{}"),
            RootSubject("subject:after", "source:test", b"{}"),
        ),
        targets=("urn:ddo-test:source",),
        inference="inference:test",
        execution_profile="execution:test",
    ).record
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        demand = storage.invoke(
            "register_data_demand",
            {
                "project_id": "ddo-test",
                "release_id": ddo_kernel["prepared"].release_id,
                "runtime_id": ddo_kernel["runtime"],
                "root": selected["roots"],
                "selection": selected,
                "strength": "value",
            },
        )
        before = storage.invoke(
            "expand_data_obligation",
            {
                "demand_id": demand["demand_id"],
                "operation_id": "urn:ddo-test:source",
                **selected["roots"][0],
                "parameters": {},
            },
        )
        first = storage.invoke("read_demand_result", demand)
        after = storage.invoke(
            "expand_data_obligation",
            {
                "demand_id": demand["demand_id"],
                "operation_id": "urn:ddo-test:source",
                **selected["roots"][1],
                "parameters": {},
            },
        )
        pinned = storage.invoke("read_demand_result", {**demand, "read_id": first["read_id"]})
        assert [row["obligation_id"] for row in pinned["obligations"]] == [before["obligation_id"]]
        fresh = storage.invoke("read_demand_result", demand)
        assert {row["obligation_id"] for row in fresh["obligations"]} == {
            before["obligation_id"],
            after["obligation_id"],
        }


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_frontier_view_defers_bodies_and_same_receipt_can_read_products(ddo_kernel):
    demand, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence)
    publish(ddo_kernel, fence, intent)
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        frontier = storage.invoke("read_demand_result", demand)
        assert frontier["view"] == "frontier"
        product = frontier["uses"][0]["products"][0]
        assert product["body_state"] == "not_requested" and "body" not in product
        hydrated = storage.invoke(
            "read_demand_result", {**demand, "read_id": frontier["read_id"], "view": "products"}
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
            owned = storage.invoke(
                "claim_data_request",
                {"request_id": attached["request_id"], "holder": "evaluator", "lease_seconds": 30},
            )
            fence = {
                name: owned[name]
                for name in ("request_id", "generation", "task_id", "attempt", "holder")
            }
            kind = ddo_kernel["identities"]["urn:ddo-test:evaluator-integer", "kind"]
            intent = storage.invoke(
                "retain_data_completion_intent",
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
            storage.invoke("publish_data_derivation", {**fence, "intent_id": intent["intent_id"]})
        with reader.begin() as connection, pytest.raises(DBAPIError, match="evaluator"):
            DataOperationStorage(connection).invoke("read_demand_result", demand)
        with reader.begin() as connection, pytest.raises(DBAPIError, match="evaluator"):
            DataOperationStorage(connection).invoke(
                "inspect_data_completion",
                {
                    "request_id": fence["request_id"],
                    "generation": fence["generation"],
                    "intent_id": intent["intent_id"],
                },
            )
        with writer.begin() as connection, pytest.raises(DBAPIError, match="permission denied"):
            connection.execute(text("SELECT * FROM kb.data_product"))
    finally:
        writer.dispose()
        evaluator.dispose()
        reader.dispose()


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_request_renewal_uses_exact_runless_fence_and_does_not_shorten_lease(ddo_kernel):
    _, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    with ddo_kernel["engine"].begin() as connection:
        before = connection.execute(
            text("SELECT run_id,lease_until FROM ops.task WHERE id=:task"),
            {"task": fence["task_id"]},
        ).one()
        assert before.run_id is None
        renewed = DataOperationStorage(connection).invoke(
            "renew_data_request", {**fence, "lease_seconds": 1}
        )
        after = connection.scalar(
            text("SELECT lease_until FROM ops.task WHERE id=:task"),
            {"task": fence["task_id"]},
        )
        assert renewed["state"] == "renewed"
        assert {name: renewed[name] for name in fence} == fence
        assert after >= before.lease_until
    publish(ddo_kernel, fence, retain(ddo_kernel, fence))
    with ddo_kernel["engine"].begin() as connection:
        lost = DataOperationStorage(connection).invoke(
            "renew_data_request", {**fence, "lease_seconds": 30}
        )
        assert lost == {**fence, "state": "lost", "reason": "fence"}


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
@pytest.mark.parametrize("field", ["generation", "task_id", "attempt", "holder"])
def test_native_request_renewal_refuses_a_different_fence(ddo_kernel, field):
    _, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    altered = {**fence, field: "different" if field == "holder" else fence[field] + 1}
    with ddo_kernel["engine"].begin() as connection:
        lost = DataOperationStorage(connection).invoke(
            "renew_data_request", {**altered, "lease_seconds": 30}
        )
        assert lost == {**altered, "state": "lost", "reason": "fence"}


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_request_renewal_cannot_revive_an_expired_attempt(ddo_kernel):
    _, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached, seconds=1)
    time.sleep(1.05)
    with ddo_kernel["engine"].begin() as connection:
        lost = DataOperationStorage(connection).invoke(
            "renew_data_request", {**fence, "lease_seconds": 30}
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
        storage.invoke(
            "record_data_fate",
            {
                "obligation_id": first["obligation_id"],
                "fate": "cancelled",
                "selection": {},
            },
        )
        assert (
            storage.invoke("renew_data_request", {**fence, "lease_seconds": 30})["state"]
            == "renewed"
        )
        storage.invoke(
            "record_data_fate",
            {
                "obligation_id": second["obligation_id"],
                "fate": "cancelled",
                "selection": {},
            },
        )
    with ddo_kernel["engine"].begin() as connection:
        lost = DataOperationStorage(connection).invoke(
            "renew_data_request", {**fence, "lease_seconds": 30}
        )
        assert lost == {**fence, "state": "lost", "reason": "cancelled"}


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_cancellation_fences_orphan_without_claiming_physical_retirement(ddo_kernel):
    demand, obligation, wire, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence)
    with ddo_kernel["engine"].begin() as connection:
        before = DataOperationStorage(connection).invoke("read_demand_result", demand)
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
        assert storage.invoke("read_demand_result", demand)["state"] == "cancelled"
        historical = storage.invoke(
            "read_demand_result",
            {
                **demand,
                "read_id": before["read_id"],
                "trust_snapshot": before["trust_snapshot"],
            },
        )
        assert historical["state"] == "active"
        assert (
            connection.scalar(
                text("SELECT status FROM ops.task WHERE id=:id"), {"id": fence["task_id"]}
            )
            == "running"
        )
        assert storage.invoke(
            "claim_data_request",
            {
                "request_id": fence["request_id"],
                "holder": "late",
                "lease_seconds": 30,
            },
        ) == {"state": "no-work"}
    for name, payload in [
        ("publish_data_derivation", {**fence, "intent_id": intent["intent_id"]}),
        ("attach_data_request", wire),
        (
            "expand_data_obligation",
            {
                "demand_id": demand["demand_id"],
                "operation_id": "urn:ddo-test:source",
                **demand["selection"]["roots"][0],
                "parameters": {},
            },
        ),
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
            DataOperationStorage(connection).invoke(name, payload)
    repeated = cancel_demand(ddo_kernel, demand, "retry must not rewrite original reason")
    assert repeated["reason"] == cancelled["reason"]
    # Resume/re-registration cannot silently undo terminal intent.
    selected = demand["selection"]
    with ddo_kernel["engine"].begin() as connection:
        replay = DataOperationStorage(connection).invoke(
            "register_data_demand",
            {
                "project_id": "ddo-test",
                "release_id": ddo_kernel["prepared"].release_id,
                "runtime_id": ddo_kernel["runtime"],
                "root": selected["roots"],
                "selection": selected,
                "strength": "value",
            },
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
        renewed = DataOperationStorage(connection).invoke(
            "renew_data_request", {**fence, "lease_seconds": 30}
        )
        assert renewed["state"] == "renewed"
    receipt = publish(ddo_kernel, fence, intent)
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        first_result = storage.invoke("read_demand_result", first)
        assert first_result["state"] == "cancelled"
        assert {item["fate"] for item in first_result["obligations"]} == {"cancelled"}
        assert storage.invoke("read_demand_result", second)["uses"][0]["fate"] == "fulfilled"
    cancel_demand(ddo_kernel, second)
    assert publish(ddo_kernel, fence, intent)["receipt_id"] == receipt["receipt_id"]
    with ddo_kernel["engine"].begin() as connection:
        inspected = DataOperationStorage(connection).invoke(
            "inspect_data_completion",
            {
                "request_id": fence["request_id"],
                "generation": fence["generation"],
                "intent_id": intent["intent_id"],
            },
        )
        assert inspected["state"] == "committed"


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_concurrent_cancel_and_attach_never_resurrects_demand(ddo_kernel):
    demand, _, wire, attached = attach(ddo_kernel)
    barrier = Barrier(2)

    def attaching():
        barrier.wait()
        try:
            with ddo_kernel["engine"].begin() as connection:
                return DataOperationStorage(connection).invoke("attach_data_request", wire)
        except DBAPIError as error:
            assert "cancelled" in str(error)
            return None

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
        assert storage.invoke("read_demand_result", demand)["state"] == "cancelled"
        assert (
            storage.invoke(
                "claim_data_request",
                {
                    "request_id": attached["request_id"],
                    "holder": "late",
                    "lease_seconds": 30,
                },
            )["state"]
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
        before = storage.invoke("read_demand_result", demand)
        released = storage.invoke("release_data_attempt", payload)
        assert released["state"] == "released" and released["replayed"] is False
        assert released["retained_intent_id"] == (intent["intent_id"] if intent else None)
        physical = connection.execute(
            text("SELECT status,claimed_by,lease_until,error FROM ops.task WHERE id=:id"),
            {"id": fence["task_id"]},
        ).one()
        assert physical.status == "pending"
        assert physical.claimed_by == fence["holder"] and physical.lease_until is None
        assert physical.error["data_attempt_failure"] == released["failure_id"]
        current = storage.invoke("read_demand_result", demand)
        assert current["uses"][0]["fate"] == "attached"
        assert current["attempt_failures"] == [
            {
                **fence,
                "failure_id": released["failure_id"],
                "failure": payload["failure"],
            }
        ]
        pinned = storage.invoke(
            "read_demand_result",
            {
                "demand_id": demand["demand_id"],
                "read_id": before["read_id"],
            },
        )
        assert pinned["attempt_failures"] == []
        replacement = storage.invoke(
            "claim_data_request",
            {
                "request_id": fence["request_id"],
                "holder": "replacement",
                "lease_seconds": 30,
            },
        )
        assert replacement["action"] == ("reconcile" if retained else "compute")
        assert replacement["attempt"] == fence["attempt"] + 1
        replay = storage.invoke("release_data_attempt", payload)
        assert replay == {**released, "replayed": True}
        assert connection.scalar(text("SELECT count(*) FROM ops.data_attempt_failure")) == 1
        assert (
            connection.scalar(
                text("SELECT status FROM ops.task WHERE id=:id"), {"id": fence["task_id"]}
            )
            == "running"
        )
        lost = storage.invoke("renew_data_request", {**fence, "lease_seconds": 30})
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
            response = DataOperationStorage(connection).invoke(
                "claim_data_request",
                {
                    "request_id": request["request_id"],
                    "holder": "owner",
                    "lease_seconds": 30,
                },
            )
            claims.append(
                NativeRequestClaim(
                    response["request_id"],
                    response["generation"],
                    response["task_id"],
                    response["attempt"],
                    response["holder"],
                    ddo_kernel["prepared"].release_id,
                    datetime.fromisoformat(response["lease_until"].replace("Z", "+00:00")),
                )
            )
    sibling_renewed = Event()

    def renew(connection, claim):
        response = DataOperationStorage(connection).invoke(
            "renew_data_request",
            {
                **claim.fence,
                "lease_seconds": 30,
            },
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
            lambda connection: DataOperationStorage(connection).invoke(
                "publish_data_derivation",
                {**claims[1].fence, "intent_id": intent["intent_id"]},
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
    _, _, _, old = attach(ddo_kernel)
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
        DataOperationStorage(connection).invoke(
            "revoke_data_support",
            {
                "project_id": "ddo-test",
                "original_source": "source:test",
                "selector_kind": "runtime",
                "selector": ddo_kernel["runtime"],
                "reason": "runtime invalidated before completion intent",
            },
        )
    updated = {**ddo_kernel, "runtime": replacement.runtime_id}
    if state == "active":
        with pytest.raises(DBAPIError, match="active producer lease"):
            attach(updated)
        return
    if state == "expired":
        expire_lease(ddo_kernel, fence)
    with pytest.raises(DBAPIError, match="replacement runtime or recipe"):
        attach(ddo_kernel)
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
            return DataOperationStorage(connection).invoke("publish_data_derivation", payload)

    with ThreadPoolExecutor(max_workers=1) as pool:
        with ddo_kernel["engine"].begin() as first_connection:
            first = DataOperationStorage(first_connection).invoke(
                "publish_data_derivation", payload
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
            (
                "expand_data_obligation",
                {
                    "demand_id": demand["demand_id"],
                    "operation_id": "urn:ddo-test:evaluator",
                    "subject": "subject:one",
                    "original_source": "source:test",
                    "analyzed_scope": {"page": 1},
                    "parameters": {},
                },
            ),
        ]
        for name, payload in calls:
            with writer.begin() as connection, pytest.raises(DBAPIError, match="evaluator"):
                DataOperationStorage(connection).invoke(name, payload)
        with evaluator.begin() as connection:
            result = DataOperationStorage(connection).invoke("read_demand_result", demand)
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
            DataOperationStorage(connection).invoke(
                "revoke_data_support",
                {
                    "project_id": "ddo-test",
                    "original_source": "source:test",
                    "selector_kind": "runtime",
                    "selector": ddo_kernel["runtime"],
                    "reason": "unauthorized broad revoke",
                },
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
                result = DataOperationStorage(connection).invoke("read_demand_result", demand)
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


@pytest.fixture
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
        admitted = DataOperationStorage(connection).invoke("register_data_demand", payload)
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
                "producer": "urn:ddo-test:source",
                "output_role": "result",
                "target": "urn:ddo-test:source",
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
        DataOperationStorage(connection).invoke(
            "register_data_demand", {**payload, "selection": frozen}
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
        # Register the declared target obligation through the ordinary planner.
        planner.storage.invoke(
            "expand_data_obligation",
            {
                "demand_id": demand["demand_id"],
                "operation_id": "urn:ddo-test:value-consumer",
                "subject": "subject:one",
                "original_source": "source:test",
                "analyzed_scope": {"page": 1},
                "parameters": {},
            },
        )
        ready = planner.ready(planner.resume(demand["demand_id"]), authorization=b"{}")
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
        DataOperationStorage(connection).invoke(
            "revoke_data_support",
            {
                "project_id": "ddo-test",
                "original_source": "source:test",
                "selector_kind": "derivation",
                "selector": original_source["derivation_id"],
                "reason": "replace an invalid upstream observation",
            },
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
            with connection.begin_nested() as savepoint:
                with pytest.raises(DBAPIError, match=r"active|lease|invalid"):
                    planner.ready(snapshot, authorization=b"{}")
                savepoint.rollback()
            released = planner.storage.invoke(
                "release_data_attempt",
                {
                    **consumer_fence,
                    "physical_retirement": "confirmed",
                    "failure": {"code": "invalidated-support", "message": "computation retired"},
                },
            )
            assert released["state"] == "released"
            updated = planner.ready(planner.resume(demand["demand_id"]), authorization=b"{}")
            assert len(updated) == 1
            new_request = json.loads(updated[0].native)
            assert new_request["request_id"] == consumer_native["request_id"]
            assert new_request["generation"] == consumer_native["generation"] + 1
            assert new_request["action"] == "compute"
            old = planner.storage.invoke(
                "inspect_data_completion",
                {
                    "request_id": consumer_native["request_id"],
                    "generation": consumer_native["generation"],
                    "intent_id": original_intent["intent_id"],
                },
            )
            assert old["state"] == "known-uncommitted" and old["intent_retained"]
        else:
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
            assert any(
                item.get("derivation_id") == replacement_receipt["derivation_id"]
                for item in use["selection"]["support"]
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
