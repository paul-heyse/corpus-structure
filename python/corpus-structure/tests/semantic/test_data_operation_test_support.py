"""Behavioral controls for shared DDO preparation and wire-checked routing."""

from dataclasses import replace

import pytest
from scenario_recipes import scenario_builder

from corpus_structure.semantic.contracts import (
    IMPLEMENTATION_UNAVAILABLE,
    implementation_override,
)
from semantic.data_operation_binding_support import WireCheckedStorage
from semantic.data_operation_kernel_support import (
    CLAIM_SOURCE,
    CONSUMERS,
    EXECUTION,
    ORIGINAL_FACT,
    ORIGINAL_PDF,
    POPULATION,
    STORAGE,
    build_kernel,
    prepare_kernel,
)


@pytest.mark.parametrize(
    ("recipe", "operation"),
    [
        (STORAGE, "urn:ddo-test:source"),
        (POPULATION, "urn:discover"),
        (CONSUMERS["document"], "text.native_evidence/selection"),
        (CONSUMERS["projection"], "extract.m1_candidates/selection"),
        (CONSUMERS["structural"], "structure.compare/selection"),
        (CONSUMERS["occurrences"], "retrieve.contextual/selection"),
        (EXECUTION, "urn:ddo-execution:answer"),
        (CLAIM_SOURCE, "urn:corpus:operation:claim-source-item"),
        (ORIGINAL_FACT, "urn:original-fact-test:consume"),
        (ORIGINAL_PDF, "urn:original-fact-test:consume"),
    ],
    ids=lambda value: getattr(value, "name", value),
)
def test_recipe_prepares_its_captured_model_and_reuses_equal_value(recipe, operation):
    prepared = prepare_kernel(recipe)
    assert prepared.model.operation(operation).semantic_id == operation
    assert prepare_kernel(replace(recipe)) is prepared
    assert scenario_builder(recipe) is build_kernel


def test_implementation_override_bypasses_kernel_memo_and_restores_after_exception():
    ordinary = prepare_kernel(STORAGE)
    with (
        pytest.raises(ValueError, match="case interrupted"),
        implementation_override(IMPLEMENTATION_UNAVAILABLE),
    ):
        overridden = prepare_kernel(STORAGE)
        assert overridden is not ordinary
        assert overridden.directory != ordinary.directory
        assert overridden.prepared.release_id == ordinary.prepared.release_id
        raise ValueError("case interrupted")
    assert prepare_kernel(STORAGE) is ordinary


@pytest.mark.parametrize(
    ("payload", "reply", "recorded"),
    [
        (
            {"intent_id": "intent:one", "demand_id": "demand:one", "generation": True},
            {"state": "known-uncommitted", "intent_retained": False},
            False,
        ),
        (
            {"intent_id": "intent:one", "demand_id": "demand:one"},
            {"state": "committed", "intent_retained": True},
            True,
        ),
    ],
    ids=["invalid-input", "invalid-result"],
)
def test_wire_checked_double_refuses_malformed_input_and_reply(payload, reply, recorded):
    storage = WireCheckedStorage({"inspect_data_completion": reply})
    with pytest.raises(ValueError):
        storage.invoke("inspect_data_completion", payload)
    assert bool(storage.calls) is recorded


def test_wire_checked_double_refuses_unconfigured_operation():
    storage = WireCheckedStorage({})
    with pytest.raises(ValueError, match="unknown configured native"):
        storage.invoke(
            "inspect_data_completion", {"intent_id": "intent:one", "demand_id": "demand:one"}
        )
    assert storage.calls == []
