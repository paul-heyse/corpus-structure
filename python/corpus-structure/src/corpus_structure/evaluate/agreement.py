"""A/B agreement and the pass-C diff (D7 §3.3, §3.4; evaluation §3.6, P0-E-2a).

`unit_agreement(pass_a, pass_b, view, unit, context)`:

1. derives both passes' stored forms on the unit's current rendition with A0's parse, in memory;
2. aligns A as reference against B, and the reverse;
3. counts items per predicate and tier (an alternative group is one item, matched when any of its
   readings is; context items are not counted);
4. symmetrizes: per tier, the mean of the two directions' F1, flagging an asymmetry.

It returns one `AgreementResult`: the counts and symmetrized F1 per tier and predicate, and the
diff pass C reads (matched, A-only, B-only, and core pairs failing the full tier with their fields),
each entry carrying local refs into both passes. Inputs and outputs are plain data, so the
computation can run in another process; it must run on that process's main thread (the grammar).
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence

from pydantic import BaseModel, ConfigDict

from corpus_structure.core import batch as B
from corpus_structure.core.evidence import RenditionContent, Segment, segment_key
from corpus_structure.core.vocab import SegmentKind
from corpus_structure.evaluate.align import (
    TIERS,
    AlignmentContext,
    AlignmentSide,
    UnitAlignment,
    align,
)
from corpus_structure.methods.llm.parse import RenditionView, parse

type Counts = dict[
    tuple[str, str], list[int]
]  # (predicate, tier) -> [n_ref, n_pred, m_ref, m_pred]


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TierAgreement(_Model):
    a_ref: float | None  # F1 with A as reference
    b_ref: float | None
    agreement: float | None  # their mean
    asymmetric: bool


class DiffEntry(_Model):
    predicate: str
    a: str | None  # local ref in pass A
    b: str | None
    fields: tuple[str, ...] = ()  # full-tier failures of a core pair


class AgreementResult(_Model):
    unit: str
    tiers: dict[str, TierAgreement]
    per_predicate: dict[str, dict[str, TierAgreement]]
    matched: tuple[DiffEntry, ...]
    differing: tuple[DiffEntry, ...]
    a_only: tuple[DiffEntry, ...]
    b_only: tuple[DiffEntry, ...]
    undecided: int  # value comparisons counted unequal for want of a deciding tier


def side_of(
    stored: B.StoredBatch,
    content: RenditionContent,
    unit: Sequence[Segment],
    name: str,
    context: frozenset[str] | None = None,
) -> AlignmentSide:
    """A stored batch as an alignment side: anchor keys as spans, the unit's sentences, and its
    uncounted context items. `context` is the local refs E1 flags `context` on the golden items
    (§3.3, D2 §10.2); without it (a pass not yet derived into items), the claims whose evidence lies
    wholly outside the unit stand in."""
    spans = {
        segment_key(stored.rendition, s.kind, s.start, s.end): (s.start, s.end)
        for s in content.document.walk()
    }
    anchors = {
        st.local_ref: tuple(spans[k] for k in st.anchor if k in spans)
        for st in stored.statements
        if isinstance(st, B.StoredStatement)
    }

    def inside(a: int, b: int) -> bool:
        return any(u.start <= a and b <= u.end for u in unit)

    sentences = tuple(
        (s.start, s.end)
        for s in content.document.walk()
        if s.kind is SegmentKind.SENTENCE and inside(s.start, s.end)
    )
    if context is None:
        context = frozenset(
            c.local_ref
            for c in stored.claims
            if not any(inside(e.start, e.end) for e in c.evidence)
        )
    return AlignmentSide(name, stored, anchors, sentences, context)


def _items(
    claims: Mapping[str, B.StoredClaim], groups: Iterable[tuple[str, ...]], context: frozenset[str]
) -> list[tuple[str, set[str]]]:
    """Scoring items: each alternative group one item (overlapping groups merged), every other
    claim its own; the predicate of the group's first listed reading; context items left out."""
    parent = {r: r for r in claims}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    first: dict[str, str] = {}
    for g in groups:
        members = [r for r in g if r in claims]
        for r in members[1:]:
            ra, rb = find(members[0]), find(r)
            if ra != rb:
                parent[rb] = ra
        if members:
            first.setdefault(find(members[0]), members[0])
    grouped: dict[str, set[str]] = defaultdict(set)
    for r in claims:
        grouped[find(r)].add(r)
    out = []
    for root, ms in grouped.items():
        if ms <= context:
            continue
        head = first.get(root, root) if len(ms) > 1 else next(iter(ms))
        out.append((claims[head].predicate, ms))
    return out


def counts(ua: UnitAlignment) -> Counts:
    out: Counts = defaultdict(lambda: [0, 0, 0, 0])
    ref = _items(ua.ref_claims, [g for g, _ in ua.alternatives_ref], ua.ref_context)
    pred = _items(ua.pred_claims, [g for g, _ in ua.alternatives_pred], ua.pred_context)
    for tier in TIERS:
        mr = {a for a, _ in ua.matches.get(tier, [])}
        mp = {b for _, b in ua.matches.get(tier, [])}
        for p, _ in (*ref, *pred):
            out[(p, tier)]  # every predicate appears at every tier
        for p, ms in ref:
            out[(p, tier)][0] += 1
            out[(p, tier)][2] += bool(ms & mr)
        for p, ms in pred:
            out[(p, tier)][1] += 1
            out[(p, tier)][3] += bool(ms & mp)
    return dict(out)


def f1(units: Iterable[Counts], tier: str, predicate: str | None = None) -> float | None:
    """Micro F1 over units at a tier (one predicate's, when named); None when undefined."""
    total = [0, 0, 0, 0]
    for c in units:
        for (p, t), v in c.items():
            if t == tier and (predicate is None or p == predicate):
                total = [x + y for x, y in zip(total, v, strict=True)]
    n_ref, n_pred, m_ref, m_pred = total
    if not n_ref or not n_pred:
        return None
    precision, recall = m_pred / n_pred, m_ref / n_ref
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _symmetric(x: float | None, y: float | None) -> TierAgreement:
    if x is None or y is None:
        return TierAgreement(a_ref=x, b_ref=y, agreement=None, asymmetric=False)
    return TierAgreement(
        a_ref=x, b_ref=y, agreement=(x + y) / 2, asymmetric=not math.isclose(x, y, abs_tol=1e-12)
    )


def symmetrized(
    ab: Sequence[UnitAlignment], ba: Sequence[UnitAlignment], predicate: str | None = None
) -> dict[str, TierAgreement]:
    """D7 §3.3: per tier, the mean of the two directions' micro F1 over the units."""
    ca, cb = [counts(u) for u in ab], [counts(u) for u in ba]
    return {t: _symmetric(f1(ca, t, predicate), f1(cb, t, predicate)) for t in TIERS}


def diff(ua: UnitAlignment) -> dict[str, tuple[DiffEntry, ...]]:
    """The pass-C diff of an A-as-reference alignment."""
    R, P = ua.ref_claims, ua.pred_claims
    core = ua.matches.get("core", [])
    full = set(ua.matches.get("full", []))
    matched = tuple(
        DiffEntry(predicate=R[a].predicate, a=a, b=b) for a, b in core if (a, b) in full
    )
    differing = tuple(
        DiffEntry(
            predicate=R[a].predicate, a=a, b=b, fields=tuple(ua.field_failures.get((a, b), ()))
        )
        for a, b in core
        if (a, b) not in full
    )
    in_a, in_b = {a for a, _ in core}, {b for _, b in core}
    a_only = tuple(
        DiffEntry(predicate=c.predicate, a=r, b=None) for r, c in R.items() if r not in in_a
    )
    b_only = tuple(
        DiffEntry(predicate=c.predicate, a=None, b=r) for r, c in P.items() if r not in in_b
    )
    return {"matched": matched, "differing": differing, "a_only": a_only, "b_only": b_only}


def agreement_of(
    unit: str, ab: UnitAlignment, ba: UnitAlignment, undecided: int = 0
) -> AgreementResult:
    predicates = sorted({p for p, _ in counts(ab)} | {p for p, _ in counts(ba)})
    return AgreementResult(
        unit=unit,
        tiers=symmetrized([ab], [ba]),
        per_predicate={p: symmetrized([ab], [ba], p) for p in predicates},
        undecided=undecided,
        **diff(ab),
    )


def unit_agreement(
    pass_a: tuple[B.AuthoredBatch, B.CitationFrame],
    pass_b: tuple[B.AuthoredBatch, B.CitationFrame],
    view: RenditionView,
    unit: Sequence[Segment],
    names: Mapping[str, str],
    context: AlignmentContext,
) -> AgreementResult:
    """The agreement of one golden unit's two blind passes on its current rendition."""
    stored_a = parse(view, pass_a[0], pass_a[1], names).stored
    stored_b = parse(view, pass_b[0], pass_b[1], names).stored
    side_a = side_of(stored_a, view.content, unit, "A")
    side_b = side_of(stored_b, view.content, unit, "B")
    before = len(context.comparator.undecided)
    ab, ba = align(side_a, side_b, context), align(side_b, side_a, context)
    undecided = len(context.comparator.undecided) - before
    return agreement_of(stored_a.unit_ref, ab, ba, undecided)
