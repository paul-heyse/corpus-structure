"""Model-admitted source batching preserves configuration and task boundaries."""

from types import SimpleNamespace

from corpus_structure.methods.math.methods import ExtractMathConfig, NormalizeFormulaConfig
from corpus_structure.orchestrate.semantic import _source_step_groups

from .domain_scenarios import fixture_model


def steps(*names):
    return [SimpleNamespace(config=name) for name in names]


def configurations(seconds=2.0):
    return {
        "normalize.formula": SimpleNamespace(config=NormalizeFormulaConfig()),
        "extract.math": SimpleNamespace(config=ExtractMathConfig(parse_seconds=seconds)),
    }


def test_model_bound_compatible_consumers_share_one_group():
    prepared = fixture_model(composed=True)[1]
    selected = steps("normalize.formula/default", "extract.math/default")
    assert list(_source_step_groups(selected, configurations(), prepared)) == [selected]
    assert list(_source_step_groups(selected, configurations(1), prepared)) == [
        [selected[0]],
        [selected[1]],
    ]
    assert list(_source_step_groups(selected[:1], configurations(), prepared)) == [selected[:1]]


def test_base_release_does_not_claim_model_bound_grouping():
    prepared = fixture_model(composed=False)[1]
    selected = steps("normalize.formula/default", "extract.math/default")
    assert list(_source_step_groups(selected, configurations(), prepared)) == [
        [selected[0]],
        [selected[1]],
    ]
