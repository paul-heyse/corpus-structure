"""Current computational policy has an explicit boundary independent of operation catalogs."""

from dataclasses import replace

import pytest
import yaml

from corpus_structure.semantic.analysis_contracts import AnalysisContextProfile, acquire_analysis_context_profile, prepare_interpretation_context, prepare_placement_policy
from corpus_structure.semantic.analysis_policies import analysis_policy_sources, compile_analysis_policies
from corpus_structure.semantic.types import PreparationError


def _policy_sources():
    return tuple(source for source in analysis_policy_sources() if source.name.startswith("analysis/"))


def _changed_sources(change):
    sources = _policy_sources()
    policy = next(source for source in sources if source.name == "analysis/policy.yaml")
    record = yaml.safe_load(policy.content)
    change(record)
    return tuple(replace(source, content=yaml.safe_dump(record).encode()) if source == policy else source for source in sources)


def test_current_context_and_placement_do_not_acquire_the_retired_catalog():
    from corpus_structure.semantic.contracts import IMPLEMENTATION_UNAVAILABLE, implementation_override

    with implementation_override(IMPLEMENTATION_UNAVAILABLE):
        captured = acquire_analysis_context_profile()
        context = prepare_interpretation_context(macros={}, context_profile=captured)
        placement = prepare_placement_policy()
    assert context.profile.grammar_recipe == "extended-lark-3"
    assert context.profile.mathematical_conventions == ("naturals-zero-1", "set-builder-real-domain-1")
    assert placement.recipe == "citation-cascade-2"
    assert placement.candidate_limit == 5


def test_supplied_scientific_parameters_change_current_context_without_ambient_defaults():
    baseline = acquire_analysis_context_profile()
    sources = _changed_sources(lambda record: record["mathematical"]["scientific_profiles"][0].update(minimum_valid_points=7))
    policies = compile_analysis_policies(sources)
    captured = AnalysisContextProfile(policies.mathematical, baseline.implementation_digests)
    assert captured.profile.scientific_profiles[0].minimum_valid_points == 7
    assert baseline.profile.scientific_profiles[0].minimum_valid_points == 6
    assert captured.model_id != baseline.model_id
    context = prepare_interpretation_context(macros={}, context_profile=captured)
    assert context.profile is captured.profile


@pytest.mark.parametrize("minimum", [0, 13])
def test_current_scientific_range_refuses_invalid_population(minimum):
    sources = _changed_sources(lambda record: record["mathematical"]["scientific_profiles"][0].update(minimum_valid_points=minimum))
    with pytest.raises(PreparationError, match="precision/sampling"):
        compile_analysis_policies(sources)


def test_current_profile_boundary_refuses_unknown_fields_and_missing_inputs():
    sources = _changed_sources(lambda record: record["mathematical"].update(legacy_operations=["evaluate"]))
    with pytest.raises(PreparationError):
        compile_analysis_policies(sources)
    with pytest.raises(ValueError, match="exactly its captured boundary and policy"):
        compile_analysis_policies(_policy_sources()[:1])
