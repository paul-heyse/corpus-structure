"""Explicit finite text policies refuse unsupported mechanisms and retain parameter meaning."""

from dataclasses import replace

import pytest
import yaml

from corpus_structure.semantic.analysis_policies import analysis_policy_sources, compile_analysis_policies
from corpus_structure.semantic.types import PreparationError


def candidate(**policy):
    sources = tuple(source for source in analysis_policy_sources() if source.name.startswith("analysis/"))
    original = next(source for source in sources if source.name == "analysis/policy.yaml")
    record = yaml.safe_load(original.content)
    for name, changes in policy.items():
        record[name].update(changes)
    return tuple(replace(source, content=yaml.safe_dump(record).encode()) if source == original else source for source in sources)


def test_alignment_mechanism_cannot_silently_change():
    with pytest.raises(PreparationError, match="implement changed text/alignment recipes"):
        compile_analysis_policies(candidate(alignment={"solver": "greedy"}))


def test_placement_parameters_are_explicit_policy_inputs():
    baseline = compile_analysis_policies(candidate())
    changed = compile_analysis_policies(candidate(placement={"token_cutoff": 91}))
    assert changed != baseline and changed.placement.token_cutoff == 91
    with pytest.raises(PreparationError, match="invalid cutoff/window/timeout"):
        compile_analysis_policies(candidate(placement={"regex_timeout": "NaN"}))
