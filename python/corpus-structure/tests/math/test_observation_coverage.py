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
    from corpus_structure.core.evidence import RenditionContent, Segment
    from corpus_structure.core.vocab import SegmentKind
    from corpus_structure.semantic.parsing_products import (
        ProductReference,
        SelectedParsingProduct,
        prepare_layered_product,
    )

    latex = {
        ParseOutcome.FAILED: r"\unknown",
        ParseOutcome.AMBIGUOUS: "(0,1)",
        ParseOutcome.PARTIAL: "1,",
    }[status]
    segment = Segment(kind=SegmentKind.MATH_INLINE, start=0, end=len(latex))
    content = RenditionContent(
        canonical_text=latex,
        document=Segment(kind=SegmentKind.DOCUMENT, start=0, end=len(latex), children=(segment,)),
    )
    ren = methods._Rendition(1, "page", "digest", content, {})
    selected = SelectedParsingProduct(
        ProductReference(7, "text", "b" * 64),
        ProductReference(7, "source", "a" * 64),
        "text",
        "available",
        "ok",
        "complete",
    )
    reader = SimpleNamespace(
        layered_products=lambda *a, **kw: (selected,),
        prepare_layered_product=prepare_layered_product,
    )
    monkeypatch.setattr(methods, "_rendition", lambda reader, identifier: ren)
    unit = UnitView(UnitRef(TaskUnitType.RENDITION, 1, "page"), SimpleNamespace())
    (result,) = methods.ExtractMath().run(
        [unit],
        methods.ExtractMathConfig(),
        MethodContext(
            unit.run,
            reader,
            MethodSettings(data_dir=tmp_path, model_cache=tmp_path / "models"),
            logging.getLogger(__name__),
        ),
    )
    assert result.outcome == ObservationOutcome.EMPTY
    assert not result.observations
    assert result.coverage == (
        CoverageDraft(
            family=methods.M09, scope=ren.key_of(segment), outcome="partial", reason=status.value
        ),
    )


def test_incomplete_coverage_requires_a_reason():
    with pytest.raises(ValueError, match="reason"):
        CoverageDraft(family="math", scope="page", outcome="unknown")
