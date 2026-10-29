"""The standing context of a unit (ingest and math §3.10; D4 §4.1; D7 §3.2).

`standing_context(content, page, scopes, unit)` is a pure function of recorded inputs, as packet
assembly requires. It is the port of the spike's `s0r2_sample.context_for`:

1. **Symbols.** For each symbol the unit uses (its non-constant, non-subscript mentions inside the
   unit), the scope of its first mention inside the unit that is not `unresolved`.
2. **Context sentences.** That binding site's sentence when it lies outside the unit, and the
   reopened site's sentence the same way.
3. **Filter.** A sentence whose text equals one of the unit's sentences is dropped (the page may
   restate a unit's own supposition); a sentence chosen twice is kept once.
4. **Cap.** The six latest in page order are kept, then numbered `c1`... in page order.

Each `ContextSentence` holds its `cN` id, the sentence segment, its generated locator and its text,
which are what the citation frame records for `cN` (D1 §10.3). Without M13 output the function
returns nothing.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from corpus_structure.core.evidence import RenditionContent, Segment
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.core.vocab import SegmentKind
from corpus_structure.methods.math.scope import Scope

MAX_CONTEXT = 6


@dataclass(frozen=True, slots=True)
class ContextSentence:
    id: str  # c1, c2, ...
    segment: Segment
    locator: str
    text: str


def standing_context(
    content: RenditionContent,
    page: str,
    scopes: Sequence[Scope],
    unit: Sequence[Segment],
    *,
    cap: int = MAX_CONTEXT,
) -> list[ContextSentence]:
    """The unit's standing context; `unit` is its segments (one annotation unit, or the parts a
    sample unit joins)."""

    def inside(pos: int) -> bool:
        return any(part.start <= pos < part.end for part in unit)

    used = sorted(
        (s for s in scopes if inside(s.mention.start) and s.mention.in_subscript_of is None),
        key=lambda s: s.mention.start,
    )
    first: dict[str, Scope] = {}
    for scope in used:
        if scope.site is not None and scope.symbol not in first:
            first[scope.symbol] = scope
    chosen: dict[tuple[int, int], Segment] = {}
    for scope in first.values():
        site = scope.site
        if site is None:
            continue
        for sentence in (site.sentence, site.reopens.sentence if site.reopens else None):
            if sentence is not None and not inside(sentence.start):
                chosen[(sentence.start, sentence.end)] = sentence
    own = {
        content.text(s)
        for s in content.document.walk()
        if s.kind is SegmentKind.SENTENCE
        and any(p.start <= s.start and s.end <= p.end for p in unit)
    }
    kept = [s for _, s in sorted(chosen.items()) if content.text(s) not in own]
    kept = kept[-cap:] if cap else []
    index = LocatorIndex(content, page) if kept else None
    return [
        ContextSentence(f"c{i + 1}", s, str(index.generate(s)) if index else "", content.text(s))
        for i, s in enumerate(kept)
    ]
