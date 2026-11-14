"""Actual child failures remain visible with the retained partial demand result."""

import json
import sys

from corpus_structure.cli.exception_observations import transform_exception
from corpus_structure.orchestrate.data_operations import DemandAdvance, NativeDemandExecutionError


def test_demand_error_preserves_original_failures_in_existing_exception_projection():
    try:
        raise ValueError("original arithmetic boundary failed")
    except ValueError as error:
        original = error
    result = DemandAdvance("demand:partial", b"{}", (b"{}",), 1)
    try:
        raise NativeDemandExecutionError(result, (original, TypeError("independent typed failure")))
    except NativeDemandExecutionError as error:
        trace = transform_exception(sys.exc_info())
        value = json.dumps(trace.model_dump(mode="json"))
        assert "original arithmetic boundary failed" in value
        assert "independent typed failure" in value
        selected, rest = error.split(ValueError)
        assert selected.result is result and rest.result is result
        assert selected.failures == (original,)
        assert len(rest.failures) == 1 and isinstance(rest.failures[0], TypeError)
