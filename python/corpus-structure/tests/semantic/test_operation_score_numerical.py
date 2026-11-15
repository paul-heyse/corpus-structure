"""Actual finite score policy, captured library determinants and exact result values."""

import json
from dataclasses import replace
from math import exp

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import read_effective_data_operations
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operation_policy import (
    DEFAULT_OPERATION_EVENT,
    OperationEventAlgorithm,
    OperationEventParameters,
    operation_score_numerical_policy,
    score_operation_event,
)
from corpus_structure.semantic.operation_score_sources import (
    operation_score_inputs,
    operation_score_sources,
)
from corpus_structure.semantic.types import PreparationError, SourceArtifact


def parameters():
    return OperationEventParameters(
        numerical=operation_score_numerical_policy(),
        algorithm=OperationEventAlgorithm(),
        event=DEFAULT_OPERATION_EVENT,
        event_version="event-1",
        producer_version="producer-1",
        feature_names=("x",),
        frame_digest="a" * 64,
        corpus_id="corpus",
        rubric_digest="b" * 64,
        reference_digest="c" * 64,
        means=(0.0,),
        scales=(1.0,),
        coefficients=(1.0,),
        intercept=0.0,
    )


def score(parameters, features):
    return score_operation_event(
        parameters,
        features,
        corpus_id="corpus",
        event_version="event-1",
        producer_version="producer-1",
    )


def test_actual_score_uses_selected_float64_policy_and_finite_probability():
    fitted = parameters()
    assert score(fitted, (0.0,)) == 0.5
    assert score(fitted, (1.0,)) == pytest.approx(1 / (1 + exp(-1)))
    assert score(fitted, (1e6,)) == 1.0
    assert score(fitted, (-1e6,)) == 0.0
    with pytest.raises(ValueError, match="finite"):
        score(fitted, (float("nan"),))
    with pytest.raises(ValueError, match="numerical policy"):
        score(
            fitted.model_copy(
                update={
                    "numerical": fitted.numerical.model_copy(
                        update={"numpy_version": "different-build"}
                    )
                }
            ),
            (1.0,),
        )
    missing = fitted.model_dump(mode="python")
    del missing["numerical"]
    with pytest.raises(ValidationError, match="numerical"):
        OperationEventParameters.model_validate(missing)


def test_score_policy_is_a_checked_nominal_body_and_current_archive_fact():
    model = compile_data_operations(
        declarations=operation_score_inputs(), python_sources=operation_score_sources()
    )
    operation = model.operation("urn:corpus:operation:score-operation-event")
    assert operation.precision_description is None
    assert operation.numerical_policy is not None
    assert json.loads(
        operation.numerical_policy.body
    ) == operation_score_numerical_policy().model_dump(mode="json")
    field = next(
        kind
        for kind in model.kinds
        if kind.semantic_id == "urn:corpus:kind:operation-event:parameters/property/numerical"
    )
    assert (
        json.loads(field.facts)["range"]
        == "urn:corpus:kind:operation-event:OperationScoreNumericalPolicy"
    )
    assert read_effective_data_operations(model.content).content == model.content
    assert any(
        identity.owner == operation.semantic_id and identity.domain == "recipe"
        for identity in model.identities
    )


def changed_policy(sources, **changes):
    artifacts = []
    for artifact in sources.boundary_contracts:
        if artifact.name == "operation-score/numerical-policy":
            body = json.loads(artifact.content)
            body["policy"].update(changes)
            artifact = SourceArtifact(artifact.name, canonical_bytes(body))
        artifacts.append(artifact)
    return replace(sources, boundary_contracts=tuple(artifacts))


def test_library_selection_changes_recipe_and_invalid_policy_body_refuses():
    sources = operation_score_sources()
    before = compile_data_operations(declarations=operation_score_inputs(), python_sources=sources)
    after = compile_data_operations(
        declarations=operation_score_inputs(),
        python_sources=changed_policy(sources, numpy_version="selected-other-version"),
    )

    def recipe(model):
        return next(identity.key for identity in model.identities if identity.domain == "recipe")

    assert recipe(before) != recipe(after)
    with pytest.raises(PreparationError, match="numerical policy differs"):
        compile_data_operations(
            declarations=operation_score_inputs(),
            python_sources=changed_policy(sources, dtype="float32"),
        )
