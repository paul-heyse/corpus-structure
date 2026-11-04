"""Native identity mapping is release-bound and never inferred from shared prose/SQLSTATE."""

import json
from dataclasses import replace
from functools import lru_cache
from hashlib import sha256
from types import SimpleNamespace

import pytest

from corpus_structure.core.db.store import (
    DatabaseOperationFailure,
    DatabasePhase,
    EffectKnowledge,
    classify_error,
    record_operation_failure,
)
from corpus_structure.semantic.contracts import (
    NativeDiagnosticBinding,
    _bound_execution_model,
    compile_execution_model,
    trusted_execution_inputs,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.invariant_failures import (
    classify_invariant_failure,
    validate_invariant_diagnostics,
)
from corpus_structure.semantic.types import PreparationError


@lru_cache(maxsize=1)
def current_model():
    return compile_execution_model(trusted_execution_inputs())


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
    failure = classify_invariant_failure(model, "claim", error)
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
    assert classify_invariant_failure(current_model(), "claim", NativeError(detail)) is None


def test_diagnostic_from_another_operation_stays_unmapped():
    assert classify_invariant_failure(current_model(), "complete", NativeError(envelope())) is None


def test_constraint_identity_includes_schema_and_relation():
    model = current_model()
    binding = NativeDiagnosticBinding(
        "claim", "constraint", "23514", "ops", "task", "task_claim_check"
    )
    invariants = tuple(
        replace(i, diagnostics=(binding,)) if i.id == "attempt_fence" else i
        for i in model.invariants
    )
    model = replace(model, invariants=invariants)
    validate_invariant_diagnostics(model)
    error = NativeError(schema_name="ops", table_name="task")
    error.diag.constraint_name = "task_claim_check"
    failure = classify_invariant_failure(model, "claim", error)
    assert failure is not None and failure.invariant == "attempt_fence"
    error.diag.table_name = "other_task"
    assert classify_invariant_failure(model, "claim", error) is None


@pytest.mark.parametrize("change", ["missing", "version", "operation", "ambiguous"])
def test_unsupported_observable_declarations_refuse(change):
    model = current_model()
    attempt = next(i for i in model.invariants if i.id == "attempt_fence")
    binding = attempt.diagnostics[0]
    if change == "missing":
        attempt = replace(attempt, diagnostics=())
    elif change == "version":
        attempt = replace(attempt, diagnostics=(replace(binding, guard_version="unimplemented"),))
    elif change == "operation":
        attempt = replace(attempt, diagnostics=(replace(binding, operation="unknown"),))
    else:
        attempt = replace(attempt, diagnostics=(binding, binding))
    model = replace(
        model, invariants=tuple(attempt if i.id == attempt.id else i for i in model.invariants)
    )
    with pytest.raises(PreparationError):
        validate_invariant_diagnostics(model)


def legacy20_product():
    """Build the independent pre-extension normalized shape, not current model defaults."""
    body = json.loads(current_model().content)
    for invariant in body["invariants"]:
        invariant.pop("observable")
        invariant.pop("diagnostics")
    for operation in body["operations"]:
        operation.pop("calls")
    next(g for g in body["native_guards"] if g["id"] == "execution_task")["version"] = "1"
    body["inputs"]["compiler_version"] = "20"
    body["model_id"] = "execution:" + sha256(canonical_bytes(body["inputs"])).hexdigest()
    return body


def test_compiler20_product_refuses_without_current_admission(monkeypatch):
    from corpus_structure.semantic import contracts

    body = legacy20_product()
    encoded = canonical_bytes(body)

    def no_current_admission(*args):
        raise AssertionError("archived20 read cannot re-admit against current guard versions")

    monkeypatch.setattr(contracts, "_validate", no_current_admission)
    with pytest.raises(
        PreparationError, match="requires current compiler 24; regenerate"
    ) as refusal:
        _bound_execution_model(encoded, body["model_id"])
    assert refusal.value.diagnostics[0].code == "unsupported_execution_abi"


def test_compiler20_cannot_claim_new_observable_contracts():
    body = legacy20_product()
    body["invariants"][0]["observable"] = True
    with pytest.raises(PreparationError, match="requires current compiler 24; regenerate"):
        _bound_execution_model(canonical_bytes(body), body["model_id"])


def test_compiler21_product_with_retired_bindings_refuses_without_current_admission(monkeypatch):
    from corpus_structure.semantic import contracts

    body = json.loads(current_model().content)
    body["inputs"]["compiler_version"] = "21"
    body["model_id"] = "execution:" + sha256(canonical_bytes(body["inputs"])).hexdigest()
    for operation in body["operations"]:
        operation["calls"] = [c for c in operation["calls"] if c["backend"] == "native"]
        for call in operation["calls"]:
            call.pop("json_read")
            call.pop("backend")
    legacy = next(op for op in body["operations"] if op["id"] == "publish_pdf_observation")
    legacy["id"] = "publish_integrated_pdf"
    encoded = canonical_bytes(body)

    def no_current_admission(*args):
        raise AssertionError("archived21 read cannot re-admit the current implementation catalog")

    monkeypatch.setattr(contracts, "_normalize", no_current_admission)
    with pytest.raises(
        PreparationError, match="requires current compiler 24; regenerate"
    ) as refusal:
        _bound_execution_model(encoded, body["model_id"])
    assert refusal.value.diagnostics[0].code == "unsupported_execution_abi"


def test_current_archived_product_read_is_independent_of_growing_current_capabilities(monkeypatch):
    from corpus_structure.semantic import contracts, effect_support

    original = current_model()
    encoded = original.content
    implementations = dict(contracts.approved_implementations())
    implementations["future_owned_capability"] = object()
    monkeypatch.setattr(contracts, "approved_implementations", lambda: implementations)
    monkeypatch.setitem(
        effect_support.SUPPORTED_EFFECTS,
        "future_owned_capability",
        {"effects": (), "implementation": "future_owned_capability", "transitions": {}},
    )

    def no_current_ingress(*args):
        raise AssertionError("a static archived read cannot repeat current source admission")

    monkeypatch.setattr(contracts, "_normalize", no_current_ingress)
    _bound_execution_model.cache_clear()
    archived = _bound_execution_model(encoded, original.model_id)
    assert archived.content == encoded and archived.operations == original.operations
    assert archived.operation("claim") == original.operation("claim")
    changed = replace(
        archived,
        operations=tuple(
            replace(op, effects=(*op.effects, "unadmitted_effect")) if op.id == "claim" else op
            for op in archived.operations
        ),
    )
    assert "unadmitted_effect" in changed.operation("claim").effects
    with pytest.raises(PreparationError):
        changed.require_operation("claim")


@pytest.mark.parametrize("mutation", ["future", "malformed", "unknown_field"])
def test_archived_execution_decoder_refuses_unknown_abi_or_malformed_shape(mutation):
    body = json.loads(current_model().content)
    if mutation == "future":
        body["inputs"]["compiler_version"] = "999"
    elif mutation == "malformed":
        body["operations"][0]["calls"] = 17
    else:
        body["operations"][0]["unmodeled_fact"] = "not a known field"
    with pytest.raises(PreparationError):
        _bound_execution_model(canonical_bytes(body), body["model_id"])


def test_published_address_constraint_is_qualified_and_operation_bound():
    model = current_model()
    error = NativeError(schema_name="kb", table_name="source_view")
    error.sqlstate = "23503"
    error.diag.constraint_name = "fk_source_view_native_build_id_native_revision_id_secti_79ff"
    failure = classify_invariant_failure(model, "publish_source_view", error)
    assert failure is not None
    assert (failure.code, failure.invariant) == (
        "pdf.published_document_address",
        "published_document_address",
    )
    assert classify_invariant_failure(model, "publish_pdf_region_artifact", error) is None
    error.diag.constraint_name = "fk_source_view_native_task_key_section"
    assert classify_invariant_failure(model, "publish_source_view", error) is None


def test_compiler22_native_only_product_refuses_without_current_admission(monkeypatch):
    from corpus_structure.semantic import contracts

    body = json.loads(current_model().content)
    body["inputs"]["compiler_version"] = "22"
    body["model_id"] = "execution:" + sha256(canonical_bytes(body["inputs"])).hexdigest()
    for operation in body["operations"]:
        operation["calls"] = [c for c in operation["calls"] if c["backend"] == "native"]
        for call in operation["calls"]:
            call.pop("backend")
    encoded = canonical_bytes(body)

    def no_current_ingress(*args):
        raise AssertionError("a retained22 reader cannot reinterpret current capabilities")

    monkeypatch.setattr(contracts, "_normalize", no_current_ingress)
    with pytest.raises(
        PreparationError, match="requires current compiler 24; regenerate"
    ) as refusal:
        _bound_execution_model(encoded, body["model_id"])
    assert refusal.value.diagnostics[0].code == "unsupported_execution_abi"


@pytest.mark.parametrize("compiler", ["20", "21", "22"])
def test_pre23_archive_cannot_assert_core_backend_even_if_native(compiler):
    body = json.loads(current_model().content)
    body["inputs"]["compiler_version"] = compiler
    with pytest.raises(PreparationError, match="requires current compiler 24; regenerate"):
        _bound_execution_model(canonical_bytes(body), body["model_id"])
