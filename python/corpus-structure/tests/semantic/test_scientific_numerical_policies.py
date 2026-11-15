"""Selected scientific arithmetic is typed, finite and an exact recipe determinant."""

import json
from dataclasses import replace

import pytest

from corpus_structure.semantic import record_interpretation as finite
from corpus_structure.semantic import record_policy as readings
from corpus_structure.semantic import source_profile_numerics as ratios
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.finite_interpretation_products import (
    finite_interpretation_assets,
    finite_interpretation_declarations,
    finite_interpretation_inputs,
    finite_interpretation_operation_sources,
)
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


def test_closed_scientific_policy_versions_refuse_an_incompatible_runtime():
    for policy in (finite.FINITE_NUMERICS, readings.READING_NUMERICS):
        policy.require_runtime()
        with pytest.raises(ValueError, match="selected numerical libraries"):
            policy.model_copy(update={"scipy_version": "unavailable-version"}).require_runtime()


def test_source_ratio_policy_uses_actual_kernel_rounding_constants():
    from corpus_structure.semantic.source_profiles import (
        SOURCE_RATIO_DECIMAL_PLACES,
        SOURCE_RATIO_EMPTY_FRACTION,
    )

    policy = ratios.source_ratio_numerical_policy()
    assert policy.decimal_places == SOURCE_RATIO_DECIMAL_PLACES == 6
    assert policy.empty_denominator == SOURCE_RATIO_EMPTY_FRACTION == 0.0
    assert policy.rounding == "python-round-nearest-ties-even-binary-input"
    assert policy.equality == "canonical-exact"


def test_actual_finite_selected_library_policy_reaches_recipe_and_has_no_label_fallback():
    from pathlib import Path

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = finite_interpretation_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    sources = finite_interpretation_operation_sources()
    declarations = (finite_interpretation_declarations(),)
    actual = compile_data_operations(bundle, declarations, sources)
    operation = actual.operation("interpret.finite_candidates")
    assert operation.precision_description is None
    assert operation.numerical_policy is not None
    assert operation.numerical_policy.kind == "urn:corpus:kind:finite:NumericalPolicy"
    assert json.loads(operation.numerical_policy.body)["normalization"] == "centered-logsumexp"
    asset = finite_interpretation_assets()
    body = json.loads(asset.content)
    body["numerical_policy"]["scipy_version"] = "different-selected-version"
    changed = SourceArtifact(asset.name, json.dumps(body).encode())
    changed_model = compile_data_operations(
        bundle, declarations, replace(sources, boundary_contracts=(changed,))
    )
    assert operation.recipe != changed_model.operation(operation.semantic_id).recipe
    with pytest.raises(ValueError):
        compile_data_operations(bundle, (), sources)
