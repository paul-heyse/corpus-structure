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
