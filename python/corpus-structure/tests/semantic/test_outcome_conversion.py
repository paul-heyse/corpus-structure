"""Independent expectations for the source-to-semantic coverage boundary."""
import pytest
from corpus_structure.semantic.outcomes import lower_source_coverage

@pytest.mark.parametrize(('source', 'semantic'), [
    ('complete', 'complete'), ('partial', 'partial'), ('failed', 'failed'),
    ('unknown', 'unanalysed'), ('unsupported', 'unanalysed'),
])
def test_source_coverage_preserves_original_domain(source, semantic):
    result = lower_source_coverage(source, 'source diagnostic', 'parser.math')
    assert result.outcome == semantic
    assert result.source_outcome == source
    assert result.reason == 'source diagnostic'
    assert result.required_capability == 'parser.math'

@pytest.mark.parametrize('value', ['done', 'unanalysed', 'absent', '', None])
def test_unknown_source_outcomes_refuse(value):
    with pytest.raises(ValueError, match='unknown source coverage'):
        lower_source_coverage(value)


def test_composed_coverage_consumes_exact_compiled_translation():
    from types import SimpleNamespace
    from corpus_structure.semantic.contracts import compile_execution_model, trusted_execution_inputs
    from corpus_structure.semantic.types import RegistryRow
    from corpus_structure.semantic.outcomes import PreparedCoverageLowerer
    product = compile_execution_model(trusted_execution_inputs())
    prepared = SimpleNamespace(execution_model_id=product.model_id, registry_rows=(
        RegistryRow('execution_model', product.model_id, product.content),))
    lowerer = PreparedCoverageLowerer.from_release(prepared)
    unknown = lowerer.lower('unknown', 'not inspected', 'parser.symbolic')
    assert unknown.outcome == 'unanalysed'
    assert unknown.source_outcome == 'unknown'
    assert unknown.reason == 'not inspected'
    assert unknown.required_capability == 'parser.symbolic'
    with pytest.raises(ValueError, match='exact execution products'):
        PreparedCoverageLowerer.from_release(SimpleNamespace(execution_model_id=product.model_id, registry_rows=()))
