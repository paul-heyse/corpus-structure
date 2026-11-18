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
    from corpus_structure.semantic.data_operation_identity import (
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
    from corpus_structure.semantic.data_operation_identity import (
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
