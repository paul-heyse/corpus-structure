"""Authored policies govern live preparation and refuse unsupported mechanisms."""

from dataclasses import replace

import pytest
import yaml

from corpus_structure.semantic.contracts import compile_execution_model, trusted_execution_inputs
from corpus_structure.semantic.types import PreparationError, SourceArtifact


def candidate(**policy):
    inputs = trusted_execution_inputs()
    catalog = yaml.safe_load(inputs.catalog.content)
    catalog["analysis_profiles"][0].update(policy)
    return replace(
        inputs, catalog=SourceArtifact(inputs.catalog.name, yaml.safe_dump(catalog).encode())
    )


def test_alignment_mechanism_cannot_silently_change():
    inputs = trusted_execution_inputs()
    policy = yaml.safe_load(inputs.catalog.content)["analysis_profiles"][0]["alignment_policy"]
    with pytest.raises(PreparationError, match="implement text/alignment recipes"):
        compile_execution_model(candidate(alignment_policy={**policy, "solver": "greedy"}))


def test_placement_parameters_are_release_inputs():
    inputs = trusted_execution_inputs()
    baseline = compile_execution_model(inputs)
    policy = yaml.safe_load(inputs.catalog.content)["analysis_profiles"][0]["placement_policy"]
    changed = compile_execution_model(candidate(placement_policy={**policy, "token_cutoff": 91}))
    assert changed.model_id != baseline.model_id
    admitted = changed.analysis_profiles[0].placement_policy
    assert admitted is not None
    assert admitted.token_cutoff == 91
    with pytest.raises(PreparationError, match="invalid cutoff/window/timeout"):
        compile_execution_model(candidate(placement_policy={**policy, "regex_timeout": "NaN"}))
