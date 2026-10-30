"""A failed or ambiguous read never establishes covered absence."""

import logging
from types import SimpleNamespace

import pytest

from corpus_structure.core.method import (
    CoverageDraft,
    MethodContext,
    MethodSettings,
    UnitRef,
    UnitView,
)
from corpus_structure.core.vocab import ObservationOutcome, ParseOutcome, TaskUnitType
from corpus_structure.methods.math import methods


@pytest.mark.parametrize(
    "status", [ParseOutcome.FAILED, ParseOutcome.AMBIGUOUS, ParseOutcome.PARTIAL]
)
def test_extract_math_preserves_partial_read_when_no_mentions_are_emitted(
    monkeypatch, status, tmp_path
):
    ren = SimpleNamespace(
        content=SimpleNamespace(canonical_text=""), key_of=lambda segment: "page#math1"
    )
    readings = [
        SimpleNamespace(
            span=SimpleNamespace(segment=object()),
            result=SimpleNamespace(status=status, tree=None, occurrences=()),
        )
    ]
    monkeypatch.setattr(methods, "_rendition", lambda reader, identifier: ren)
    monkeypatch.setattr(methods, "_readings", lambda rendition, config, reader: readings)
    unit = UnitView(UnitRef(TaskUnitType.RENDITION, 1, "page"), SimpleNamespace())
    (result,) = methods.ExtractMath().run(
        [unit],
        methods.ExtractMathConfig(),
        MethodContext(
            unit.run,
            SimpleNamespace(),
            MethodSettings(data_dir=tmp_path, model_cache=tmp_path / "models"),
            logging.getLogger(__name__),
        ),
    )
    assert result.outcome == ObservationOutcome.EMPTY
    assert not result.observations
    assert result.coverage == (
        CoverageDraft(
            family=methods.M09, scope="page#math1", outcome="partial", reason=status.value
        ),
    )


def test_incomplete_coverage_requires_a_reason():
    with pytest.raises(ValueError, match="reason"):
        CoverageDraft(family="math", scope="page", outcome="unknown")
