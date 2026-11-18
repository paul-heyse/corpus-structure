"""Shared authored scenarios and fixtures for declared rich native journey test support."""

from copy import deepcopy

import pytest
from evaluate.declared_rich_native_support import (
    run_rich_admission,
)
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


def refuse_rich_completion_substitution(fitted, authorization, source, monkeypatch, *, attack):
    """Neither a body alone nor a substituted decision acquires native authority."""
    from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError
    from corpus_structure.semantic.data_operation_identity import (
        decode_semantic_value,
        semantic_value,
    )
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.rich_knowledge_contracts import DdoRichAdmission
    from corpus_structure.semantic.rich_policy_binding import rich_policy_value

    journey = fitted.journey
    current_policy = rich_policy_value(journey.kernel.prepared, journey.kernel.model)
    size = 1 if attack == "decision" else 2
    allowed = current_policy.allowed_domain_contracts[:size]
    assert len(current_policy.allowed_domain_contracts) > 2
    actual_retain = DataOperationStorage.retain_data_completion_intent
    refused = []
    requests = []

    def substitute(storage, payload):
        outputs = payload["completion"]["outputs"]
        if outputs and outputs[0]["role"] == "admission":
            altered = deepcopy(payload)
            if attack == "missing-cpu":
                # Preserve the genuinely computed complete graph and actual
                # native task fence, but omit computation authority. This is the
                # current counterpart of a plain graph append without admission.
                altered["completion"]["execution_evidence"]["cpu_receipts"] = []
                altered["completion"]["execution_evidence"]["cpu_replies"] = []
                assert altered["completion"]["outputs"] == payload["completion"]["outputs"]
            else:
                body = decode_semantic_value(outputs[0]["product"]["body"])
                accepted = next(
                    row for row in body["reading_decisions"] if row["outcome"] == "accepted"
                )
                removed = accepted["assertion_member_id"]
                accepted.update(
                    outcome="below-threshold",
                    reason_code="below-threshold",
                    assertion_member_id=None,
                    probability_hex=(0.0).hex(),
                )
                body["selected_reading_ids"] = [
                    identifier
                    for identifier in body["selected_reading_ids"]
                    if identifier != removed
                ]
                DdoRichAdmission.model_validate(body)
                altered["completion"]["outputs"][0]["product"]["body"] = semantic_value(body)
                assert (
                    altered["completion"]["execution_evidence"]
                    == payload["completion"]["execution_evidence"]
                )
            requests.append(payload["request_id"])
            try:
                return actual_retain(storage, altered)
            except DBAPIError as error:
                refused.append(error)
                raise
        return actual_retain(storage, payload)

    with monkeypatch.context() as patch:
        patch.setattr(DataOperationStorage, "retain_data_completion_intent", substitute)
        with pytest.raises(NativeDemandExecutionError):
            run_rich_admission(
                journey,
                fitted.calibration_readings,
                authorization,
                selected_source=source,
                inference="actual-rich-completion-" + attack + "-refusal",
                policy_contracts=allowed,
            )
    assert len(refused) == 1
    assert getattr(refused[0].orig, "sqlstate", None) == "23514"
    assert "CPU" in str(refused[0].orig)
    assert len(requests) == 1
    with journey.kernel.engine.begin() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM ops.data_derivation WHERE request_id=:request"),
                {"request": requests[0]},
            )
            == 0
        )
