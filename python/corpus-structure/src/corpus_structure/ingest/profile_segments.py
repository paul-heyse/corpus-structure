"""M02 `profile.segments`: the character and math features policies route on (D4 M02; D6 §6;
ingest and math §3.5), as a pure function of a rendition's content.

Per measured segment: `segment.chars` (its length), `segment.inline_math` and
`segment.display_math` (the math segments inside it), and `segment.math_share` (the share of its
characters inside math). Measured segments are the annotation units and the paragraphs that can be
one (member properties `annotation_unit`, `top_level_annotation_unit`) and the search blocks
(`search_block`). Token counts join in phase 1. The statement-kind and `claim_bearing` hints are
segment attributes, not M02 features.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from corpus_structure.core.evidence import RenditionContent, Segment
from corpus_structure.core.method import MeasurementDraft
from corpus_structure.core.vocab import (
    ANNOTATION_UNIT,
    SEARCH_BLOCK,
    TOP_LEVEL_ANNOTATION_UNIT,
    MeasurementScope,
    SegmentKind,
)

MEASURED: frozenset[SegmentKind] = ANNOTATION_UNIT | TOP_LEVEL_ANNOTATION_UNIT | SEARCH_BLOCK
MATH = frozenset({SegmentKind.MATH_INLINE, SegmentKind.MATH_DISPLAY})
METRICS = ("segment.chars", "segment.math_share", "segment.inline_math", "segment.display_math")


@dataclass(frozen=True, slots=True)
class SegmentFeatures:
    segment: Segment
    chars: int
    math_share: float
    inline_math: int
    display_math: int

    def values(self) -> dict[str, float]:
        return dict(
            zip(
                METRICS,
                (self.chars, self.math_share, self.inline_math, self.display_math),
                strict=True,
            )
        )


def _math(segment: Segment) -> list[Segment]:
    """The outermost math segments inside a segment (math does not nest)."""
    out: list[Segment] = []
    for child in segment.children:
        if child.kind in MATH:
            out.append(child)
        elif child.kind is not SegmentKind.SENTENCE:
            out += _math(child)
    return out


def features(content: RenditionContent) -> list[SegmentFeatures]:
    """Features of every measured segment, in document order."""
    out = []
    for segment in content.document.walk():
        if segment.kind not in MEASURED:
            continue
        math = _math(segment)
        length = segment.end - segment.start
        inside = sum(m.end - m.start for m in math)
        out.append(
            SegmentFeatures(
                segment,
                length,
                round(inside / length, 6) if length else 0.0,
                sum(m.kind is SegmentKind.MATH_INLINE for m in math),
                sum(m.kind is SegmentKind.MATH_DISPLAY for m in math),
            )
        )
    return out


def measurements(
    content: RenditionContent,
    segment_key: Callable[[Segment], str],
    segment_ids: Mapping[str, int] | None = None,
) -> list[MeasurementDraft]:
    """The features as `ops.measurement` drafts, each scoped to its segment's key and, given the
    stored segments' ids by key, its id."""
    out = []
    for f in features(content):
        key = segment_key(f.segment)
        for metric, value in f.values().items():
            out.append(
                MeasurementDraft(
                    metric=metric,
                    scope_type=MeasurementScope.SEGMENT,
                    scope_id=segment_ids.get(key) if segment_ids is not None else None,
                    scope_key=key,
                    value=float(value),
                )
            )
    return out
