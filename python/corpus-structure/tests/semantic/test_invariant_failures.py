"""Native identity mapping is release-bound and never inferred from shared prose/SQLSTATE."""

import json
from dataclasses import replace
from functools import lru_cache
from types import SimpleNamespace

import pytest

from corpus_structure.core.db.store import (
    DatabaseOperationFailure,
    DatabasePhase,
    EffectKnowledge,
    classify_error,
    record_operation_failure,
)
from corpus_structure.semantic.invariant_failures import (
    NativeDiagnosticBinding,
    NativeInvariant,
    classify_invariant_failure,
)


@lru_cache(maxsize=1)
def current_model():
    # A finite classifier input, not an admitted release or an execution receipt.
    return SimpleNamespace(
        model_id="definition:diagnostic-example",
        invariants=(
            NativeInvariant(
                "attempt_fence",
                "lifecycle",
                "execution.attempt_fence",
                True,
                (
                    NativeDiagnosticBinding(
                        "claim", "guard", "23514", guard="execution_task", guard_version="2"
                    ),
                ),
            ),
        ),
    )


class NativeError(Exception):
    sqlstate = "23514"

    def __init__(self, detail=None, **diagnostic):
        super().__init__("any wording, including attempt fence")
        self.diag = SimpleNamespace(message_detail=detail, constraint_name=None, **diagnostic)


def envelope(**changes):
    return json.dumps(
        {
            "protocol": "corpus-invariant-1",
            "guard": "execution_task",
            "version": "2",
            "invariant": "attempt_fence",
            **changes,
        }
    )


def test_observable_native_failure_preserves_owned_phase_effect_and_exact_binding():
    model = current_model()
    error = NativeError(envelope())
    context = DatabaseOperationFailure(
        classify_error(error, phase=DatabasePhase.EXECUTING, effects=EffectKnowledge.NONE),
        operation_id="claim",
        release_id="release:owned",
    )
    record_operation_failure(error, context)
    failure = classify_invariant_failure(model.invariants, "claim", error, model_id=model.model_id)
    assert failure is not None
    assert (failure.code, failure.invariant, failure.operation, failure.scope) == (
        "execution.attempt_fence",
        "attempt_fence",
        "claim",
        "lifecycle",
    )
    assert failure.model_id == model.model_id
    assert failure.native is context
    assert failure.native.failure.effects is EffectKnowledge.NONE
    assert error.args == ("any wording, including attempt fence",)


@pytest.mark.parametrize(
    "detail",
    [
        None,
        "attempt_fence",
        envelope(version="1"),
        envelope(guard="another_guard"),
        envelope(invariant="terminal_result"),
        envelope(extra="value"),
    ],
)
def test_shared_sqlstate_prose_or_wrong_native_identity_stays_unmapped(detail):
    assert (
        classify_invariant_failure(
            current_model().invariants,
            "claim",
            NativeError(detail),
            model_id=current_model().model_id,
        )
        is None
    )


def test_diagnostic_from_another_operation_stays_unmapped():
    assert (
        classify_invariant_failure(
            current_model().invariants,
            "complete",
            NativeError(envelope()),
            model_id=current_model().model_id,
        )
        is None
    )


def test_constraint_identity_includes_schema_and_relation():
    model = current_model()
    binding = NativeDiagnosticBinding(
        "claim", "constraint", "23514", "ops", "task", "task_claim_check"
    )
    invariants = tuple(
        replace(i, diagnostics=(binding,)) if i.id == "attempt_fence" else i
        for i in model.invariants
    )
    model = SimpleNamespace(model_id=model.model_id, invariants=invariants)
    error = NativeError(schema_name="ops", table_name="task")
    error.diag.constraint_name = "task_claim_check"
    failure = classify_invariant_failure(model.invariants, "claim", error, model_id=model.model_id)
    assert failure is not None and failure.invariant == "attempt_fence"
    error.diag.table_name = "other_task"
    assert (
        classify_invariant_failure(model.invariants, "claim", error, model_id=model.model_id)
        is None
    )
