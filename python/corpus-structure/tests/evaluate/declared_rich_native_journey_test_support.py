"""Independent native refusal controls applied to actual in-flight completions."""

from contextlib import contextmanager
from copy import deepcopy

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError


def _completion_counts(connection, request_id):
    from corpus_structure.semantic.metadata import table

    intent = table("ops.data_completion_intent")
    derivation = table("ops.data_derivation")
    receipt = table("ops.data_publication_receipt")
    return tuple(
        connection.scalar(statement)
        for statement in (
            select(func.count()).select_from(intent).where(intent.c.request_id == request_id),
            select(func.count())
            .select_from(derivation)
            .where(derivation.c.request_id == request_id),
            select(func.count())
            .select_from(receipt.join(intent, intent.c.id == receipt.c.intent_id))
            .where(intent.c.request_id == request_id),
        )
    )


def verify_mixed_producer_requirements(connection, episode, admission, assertions):
    """Compare actual native consumers with independent requirements and receipts."""
    from sqlalchemy import text

    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_support import ComputationalSupportReference

    selected = (
        ("consolidation", admission.consolidation, "rich", True, None),
        ("records", assertions[0].original, "none", True, None),
        ("readings", assertions[0].resolution, "none", True, None),
        (
            "policy_authorizations",
            admission.policy_authorizations[0],
            "none",
            False,
            "native-evaluator-policy-authorization",
        ),
    )
    consumer = connection.execute(
        text(
            "SELECT definition.input_roles FROM ops.data_derivation episode "
            "JOIN ops.data_request request ON request.id=episode.request_id "
            "JOIN sem.data_operation_definition definition "
            "ON definition.release_id=request.release_id "
            "AND definition.operation_id=request.operation_id WHERE episode.id=:episode"
        ),
        {"episode": episode},
    ).scalar_one()
    roles = {role["name"]: role["producer_requirement"] for role in consumer}
    for role, reference, family, requires_cpu, effect in selected:
        requirement = roles[role]
        assert requirement["required_family"] == family
        assert requirement["requires_cpu"] is requires_cpu
        assert requirement["required_effect"] == effect
        producer = connection.execute(
            text(
                "SELECT producer.id FROM ops.data_derivation episode "
                "JOIN ops.data_request request ON request.id=episode.request_id "
                "CROSS JOIN LATERAL ops.ddo_rich_producing_request("
                "request,CAST(:selected AS jsonb),:role) producer "
                "WHERE episode.id=:episode"
            ),
            {
                "episode": episode,
                "selected": json_bytes(reference.model_dump(mode="python")).decode(),
                "role": role,
            },
        ).scalar_one()
        observed = connection.execute(
            text(
                "SELECT definition.profile,definition.validity_families,intent.payload,"
                "receipt.derivation_id FROM ops.data_request request "
                "JOIN sem.data_operation_definition definition "
                "ON definition.release_id=request.release_id "
                "AND definition.operation_id=request.operation_id "
                "JOIN ops.data_derivation episode ON episode.request_id=request.id "
                "JOIN ops.data_completion_intent intent ON intent.id=episode.intent_id "
                "JOIN ops.data_publication_receipt receipt "
                "ON receipt.derivation_id=episode.id AND receipt.intent_id=intent.id "
                "WHERE request.id=:producer"
            ),
            {"producer": producer},
        ).one()
        support = reference.support_references[0]
        assert isinstance(support, ComputationalSupportReference)
        assert observed.derivation_id == support.derivation_id
        if requires_cpu:
            assert observed.profile == "derivation"
            assert len(observed.payload["execution_evidence"]["cpu_receipts"]) == 1
        if family == "rich":
            assert "rich" in observed.validity_families
        if role == "policy_authorizations":
            assert observed.profile == "command"
            assert "rich" not in observed.validity_families


def _unretained_completion(journey, request_id):
    with journey.kernel.engine.begin() as connection:
        assert _completion_counts(connection, request_id) == (0, 0, 0)


def _refuse_completion(storage, altered, actual_retain, *, message):
    # Keep the real caller, task, holder and transaction. The nested rollback
    # releases every rejected effect before the untouched positive completion.
    with pytest.raises(DBAPIError) as refused, storage.connection.begin_nested():
        actual_retain(storage, altered)
    assert getattr(refused.value.orig, "sqlstate", None) == "23514"
    assert message in str(refused.value.orig)


def _grade_label_substitution(payload):
    from corpus_structure.evaluate.declared_record_policy import DdoRecordGrade
    from corpus_structure.semantic.data_operation_values import (
        decode_semantic_value,
        semantic_value,
    )

    altered = deepcopy(payload)
    original = payload["completion"]
    grade = DdoRecordGrade.from_selected_body(
        decode_semantic_value(original["outputs"][0]["product"]["body"])
    )
    assert grade.frame.events
    first, *rest = grade.frame.events
    frame = grade.frame.model_copy(
        update={"events": (first.model_copy(update={"correct": not first.correct}), *rest)}
    )
    changed = DdoRecordGrade.from_frame(frame)
    altered["completion"]["outputs"][0]["product"]["body"] = semantic_value(
        changed.model_dump(mode="python")
    )
    assert altered["completion"]["execution_evidence"] == original["execution_evidence"]
    assert (
        len(original["execution_evidence"]["cpu_receipts"])
        == len(original["execution_evidence"]["cpu_replies"])
        == 1
    )
    return altered


def _rich_substitution(payload, attack):
    from corpus_structure.semantic.data_operation_values import (
        decode_semantic_value,
        semantic_value,
    )
    from corpus_structure.semantic.rich_knowledge_contracts import DdoRichAdmission

    altered = deepcopy(payload)
    if attack == "missing-cpu":
        altered["completion"]["execution_evidence"]["cpu_receipts"] = []
        altered["completion"]["execution_evidence"]["cpu_replies"] = []
        assert altered["completion"]["outputs"] == payload["completion"]["outputs"]
    else:
        body = decode_semantic_value(altered["completion"]["outputs"][0]["product"]["body"])
        accepted = next(row for row in body["reading_decisions"] if row["outcome"] == "accepted")
        removed = accepted["assertion_member_id"]
        accepted.update(
            outcome="below-threshold",
            reason_code="below-threshold",
            assertion_member_id=None,
            probability_hex=(0.0).hex(),
        )
        body["selected_reading_ids"] = [
            identifier for identifier in body["selected_reading_ids"] if identifier != removed
        ]
        DdoRichAdmission.model_validate(body)
        altered["completion"]["outputs"][0]["product"]["body"] = semantic_value(body)
        assert (
            altered["completion"]["execution_evidence"]
            == payload["completion"]["execution_evidence"]
        )
    return altered


@contextmanager
def verify_completion_refusals(journey, monkeypatch):
    """Check mutations before the same actual grade and rich result are retained."""
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage

    actual_retain = DataOperationStorage.retain_data_completion_intent
    checked = {"grade": [], "decision": [], "missing-cpu": []}

    def retain_with_refusals(storage, payload):
        outputs = payload["completion"]["outputs"]
        role = outputs[0]["role"] if outputs else None
        if role == "grade" and not checked["grade"]:
            request_id = payload["request_id"]
            _unretained_completion(journey, request_id)
            _refuse_completion(
                storage,
                _grade_label_substitution(payload),
                actual_retain,
                message="actual CPU result and reference basis",
            )
            _unretained_completion(journey, request_id)
            checked["grade"].append(request_id)
        if role == "admission":
            request_id = payload["request_id"]
            _unretained_completion(journey, request_id)
            for attack in ("decision", "missing-cpu"):
                _refuse_completion(
                    storage, _rich_substitution(payload, attack), actual_retain, message="CPU"
                )
                _unretained_completion(journey, request_id)
                checked[attack].append(request_id)
        return actual_retain(storage, payload)

    with monkeypatch.context() as patch:
        patch.setattr(DataOperationStorage, "retain_data_completion_intent", retain_with_refusals)
        yield
    assert {name: len(requests) for name, requests in checked.items()} == {
        "grade": 1,
        "decision": 1,
        "missing-cpu": 1,
    }
    assert checked["decision"] == checked["missing-cpu"]
    with journey.kernel.engine.begin() as connection:
        for request_id in {requests[0] for requests in checked.values()}:
            assert _completion_counts(connection, request_id) == (1, 1, 1)
