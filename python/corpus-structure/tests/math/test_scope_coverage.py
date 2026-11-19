"""Unknown scope prerequisites stay explicit in producer and actual packet boundaries."""

from dataclasses import replace

import pytest

from corpus_structure.core.evidence import RenditionContent, Segment
from corpus_structure.methods.math.scope import BindingSite, Scope, scope_coverage
from corpus_structure.methods.math.spans import SpanValue, SymbolMention
from corpus_structure.semantic.source_types import ParseOutcome, ScopeExtent, SegmentKind


def source(math=True):
    node = Segment(kind=SegmentKind.MATH_INLINE, start=4, end=5)
    sentence = Segment(kind=SegmentKind.SENTENCE, start=0, end=6, children=(node,) if math else ())
    paragraph = Segment(kind=SegmentKind.PARAGRAPH, start=0, end=6, children=(sentence,))
    unit = Segment(kind=SegmentKind.UNIT, start=0, end=6, attrs={"id": "u"}, children=(paragraph,))
    content = RenditionContent(
        canonical_text="Let x.",
        document=Segment(kind=SegmentKind.DOCUMENT, start=0, end=6, children=(unit,)),
    )
    mention = SymbolMention(node, 4, 5, "x", "x", None, None, False, None)
    value = SpanValue(
        node,
        ParseOutcome.OK,
        frozenset({"x"}),
        "formula",
        None,
    )
    site = BindingSite(
        mention, "x", sentence, ScopeExtent.STATEMENT, unit, 0, 6, ("initial",), False
    )
    return content, unit, mention, value, Scope(mention, "x", site)


@pytest.mark.parametrize(
    "parse,outcome",
    [
        (ParseOutcome.AMBIGUOUS, "partial"),
        (ParseOutcome.PARTIAL, "partial"),
        (ParseOutcome.FAILED, "unknown"),
    ],
)
def test_unavailable_or_ambiguous_interpretation_cannot_be_complete_scope(parse, outcome):
    content, _, mention, value, scope = source()
    value = replace(value, parse=parse)
    (coverage,) = scope_coverage(content, [value], [mention], [scope])
    assert coverage.outcome == outcome
    assert coverage.reason


def test_required_unresolved_binding_and_missing_values_are_not_empty_absence():
    content, _, mention, value, scope = source()
    assert (
        scope_coverage(content, [value], [mention], [replace(scope, site=None)])[0].outcome
        == "partial"
    )
    assert scope_coverage(content, [], [mention], [scope])[0].outcome == "unknown"
    assert scope_coverage(content, [value], [], [])[0].outcome == "unknown"
    assert scope_coverage(content, [value], [mention], [scope])[0].outcome == "complete"
    unsupported = replace(
        value,
        parse_error="unknown-command",
        parse=ParseOutcome.FAILED,
    )
    assert scope_coverage(content, [unsupported], [mention], [])[0].outcome == "unsupported"
