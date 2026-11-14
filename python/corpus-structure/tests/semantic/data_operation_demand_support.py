"""Native demand setup actions; expected outcomes stay with their tests."""

from __future__ import annotations

import json

from corpus_structure.semantic.data_operation_identity import SemanticRequestKey, semantic_value
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from semantic.data_operation_declaration_support import root_subject, subject_context


def attach(
    kernel,
    *,
    subject="subject:one",
    inference="inference:test",
    operation="urn:ddo-test:source",
    targets=None,
    engine=None,
    original_source="source:test",
    analyzed_scope=None,
    project_id="ddo-test",
):
    from corpus_structure.semantic.data_operation_demands import freeze_demand

    root = {
        "subject": subject,
        "original_source": original_source,
        "analyzed_scope": {"page": 1} if analyzed_scope is None else analyzed_scope,
    }
    selected = freeze_demand(
        kernel["model"],
        roots=(
            root_subject(subject=subject, source=original_source, scope=root["analyzed_scope"]),
        ),
        targets=targets or (operation,),
        inference=inference,
        execution_profile="execution:test",
    ).record
    with (engine or kernel["engine"]).begin() as connection:
        storage = DataOperationStorage(connection)
        demand = storage.invoke(
            "register_data_demand",
            {
                "project_id": project_id,
                "release_id": kernel["prepared"].release_id,
                "runtime_id": kernel["runtime"],
                "root": [root],
                "selection": selected,
                "strength": "value",
            },
        )
        obligation = storage.invoke(
            "expand_data_obligation",
            {
                "demand_id": demand["demand_id"],
                "operation_id": operation,
                **root,
                "parameters": {},
            },
        )
        acquired = storage.invoke("read_demand_result", {"demand_id": demand["demand_id"]})
        request = SemanticRequestKey(
            kernel["identities"][operation, "recipe"],
            subject,
            {},
            {"parameters": {}, "replicate": None},
            inference,
            subject_context=subject_context(
                project=project_id,
                subject=subject,
                source=original_source,
                scope=root["analyzed_scope"],
            ),
        )
        wire = {
            "obligation_id": obligation["obligation_id"],
            "request_meaning": json.loads(request.identity.canonical_input),
            "request_key": request.identity.key,
            "binding": {
                "inputs": [],
                "support": [],
                "parameters": semantic_value(request.parameters),
                "request_inputs": semantic_value({}),
                "inference": inference,
                "populations": [],
                "read_id": acquired["read_id"],
            },
            "replicate": None,
        }
        attached = storage.invoke("attach_data_request", wire)
    return demand, obligation, wire, attached


def claim(kernel, attached, holder="producer", seconds=30):
    with kernel["engine"].begin() as connection:
        result = DataOperationStorage(connection).invoke(
            "claim_data_request",
            {
                "request_id": attached["request_id"],
                "holder": holder,
                "lease_seconds": seconds,
            },
        )
    return {
        name: result[name] for name in ("request_id", "generation", "task_id", "attempt", "holder")
    }


def retain(kernel, fence, *, outputs=(1,), outcome="success", mutate=None):
    completion = {
        "outcome": outcome,
        "inputs": [],
        "support": [],
        "implementation_revision": "native-test-source-v1",
        "outputs": [
            {
                "role": "result",
                "position": position,
                "multiplicity": 1,
                "product": {
                    "kind_contract": kernel["kind"],
                    "body": semantic_value(value),
                    "members": [],
                },
            }
            for position, value in enumerate(outputs)
        ],
    }
    if mutate:
        mutate(completion)
    with kernel["engine"].begin() as connection:
        intent = DataOperationStorage(connection).invoke(
            "retain_data_completion_intent",
            {
                **fence,
                "runtime_id": kernel["runtime"],
                "completion": completion,
            },
        )
    return intent


def publish(kernel, fence, intent):
    with kernel["engine"].begin() as connection:
        return DataOperationStorage(connection).invoke(
            "publish_data_derivation",
            {
                **fence,
                "intent_id": intent["intent_id"],
            },
        )


def cancel_demand(kernel, demand, reason="operator stopped this demand"):
    with kernel["engine"].begin() as connection:
        return DataOperationStorage(connection).invoke(
            "cancel_data_demand", {"demand_id": demand["demand_id"], "reason": reason}
        )


def expire_lease(kernel, fence):
    """Expiry is clone setup through the publisher, never a worker capability."""
    from sqlalchemy import text

    with kernel["engine"].begin() as connection:
        connection.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        updated = connection.execute(
            text(
                "UPDATE ops.task SET lease_until=clock_timestamp()-interval '1 second' WHERE id=:task"
            ),
            {"task": fence["task_id"]},
        )
        if updated.rowcount != 1:
            raise ValueError("lease expiry requires one existing task")
