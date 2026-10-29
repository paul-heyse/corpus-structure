"""Entity and claim alignment of two claim sets of one unit on one rendition (D7 §5.2, §5.3;
evaluation §3.5, P0-E-2a).

`align(ref, pred, context)` aligns a prediction side to a reference side; both are stored-form
batches (F2b's items) with their anchor and sentence spans. Ported from the spike's
`instruments/align.py`, rewritten against the product's models; its known defects are not ported
(thresholds after assignment, fixed lexicographic weights, statistics names in the code).

**Entities.** Types must be equal.
- Statements: anchor overlap, 0.6 + 0.3 x overlap ratio + 0.1 for equal kinds.
- Global entities: an equal label or alias in text form scores 1.0, equal after the pack's alias
  rules (F2b's `normalize_label`) 0.9. A fuzzy match never aligns: `token_sort_ratio` >= 90 is a
  label near miss.
- Identity-dependent classes (whose `ci:identity_keys` name an entity-valued slot): aligned in
  later passes, in the dependency order of those keys; identical when every referenced entity is
  aligned to its counterpart and the other identity keys are equal in text form; aligned
  references with differing names are an identity near miss. A cycle is refused.
- Local entities: the symbol (F2b's symbol rule) scores 0.7, + 0.2 for the same scope segment;
  labels after the article rule when neither side has a symbol.
- + 0.05 when the entities' claim evidence overlaps.

Similarities below 0.5 are set to zero *before* `linear_sum_assignment(maximize=True)`, and
zero-weight pairs are dropped, so a weak pair never displaces a strong one.

**Claims.** Core: predicate, aligned subject, aligned object or equivalent value. Full adds
modality, polarity, statement role, each identity qualifier from the lookup (maps key by key,
entities by alignment, conditions by tree equivalence) and the conditions tree, its leaves matched
one-to-one. Evidence adds primary-span overlap or a shared sentence. The core matching is found by
fixed-point iteration (`claim` leaves judged through the current matching; at most 8 passes) and
prefers more core, then full, then evidence pairs, then evidence overlap, with weights b^3, b^2,
b and the overlap ratio, b = min(|R|, |P|) + 1, so a lower term never outweighs a higher one. A
conclusion failing the full tier only because its premise failed the core tier is `cascaded`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from pydantic import MISSING
from rapidfuzz import fuzz
from scipy.optimize import linear_sum_assignment

from corpus_structure.core import batch as B
from corpus_structure.core import values as V
from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.keys import (
    UNSET,
    LabelRules,
    normalize_label,
    qualifier_value,
    symbol_form,
    text_form,
)
from corpus_structure.core.vocab import BindKind, CaseRule, EntityScope, EvidenceRole
from corpus_structure.evaluate.equivalence import TreeMatch, ValueComparator, trees_equivalent
from corpus_structure.schema.lookup import SchemaLookup

THRESHOLD = 0.5
MAX_ITER = 8
W_SYMBOL, W_SCOPE, W_EVIDENCE = 0.7, 0.2, 0.05
NEAR_MISS = 90
TIERS = ("core", "full", "evidence")
_STORED_VALUE: Any = V.VALUE_ADAPTERS["stored"]
_STORED_CONDITION: Any = V.CONDITION_ADAPTERS["stored"]

type Span = tuple[int, int]
type Pair = tuple[str, str]


@dataclass(frozen=True)
class AlignmentSide:
    """One unit's claim set on one rendition: the stored batch, each statement's anchor spans, the
    unit's sentence spans, and the local refs of uncounted context items."""

    unit: str
    batch: B.StoredBatch
    anchors: Mapping[str, tuple[Span, ...]]
    sentences: tuple[Span, ...] = ()
    context: frozenset[str] = frozenset()


@dataclass(frozen=True)
class AlignmentContext:
    lookup: SchemaLookup
    labels: LabelRules
    macros: Mapping[str, MacroDef]
    comparator: ValueComparator


@dataclass(frozen=True)
class EntityPair:
    ref: str
    pred: str
    sim: float
    basis: str


@dataclass
class UnitAlignment:
    unit: str
    entity_pairs: list[EntityPair] = field(default_factory=list)
    entity_unmatched_ref: list[str] = field(default_factory=list)
    entity_unmatched_pred: list[str] = field(default_factory=list)
    identity_near_misses: list[tuple[str, str, str]] = field(default_factory=list)
    label_near_misses: list[tuple[str, str, str]] = field(default_factory=list)
    ref_claims: dict[str, B.StoredClaim] = field(default_factory=dict)
    pred_claims: dict[str, B.StoredClaim] = field(default_factory=dict)
    ref_context: frozenset[str] = frozenset()
    pred_context: frozenset[str] = frozenset()
    matches: dict[str, list[Pair]] = field(default_factory=dict)
    field_failures: dict[Pair, list[str]] = field(default_factory=dict)
    diagnostics: dict[Pair, list[str]] = field(default_factory=dict)
    alternatives_ref: list[tuple[tuple[str, ...], str]] = field(default_factory=list)
    alternatives_pred: list[tuple[tuple[str, ...], str]] = field(default_factory=list)
    unsupported_pairs: list[Pair] = field(default_factory=list)
    unsupported_n: tuple[int, int] = (0, 0)
    bindings: list[dict[str, Any]] = field(default_factory=list)
    scopes: list[dict[str, Any]] = field(default_factory=list)
    cascaded: list[Pair] = field(default_factory=list)
    iterations: int = 0
    converged: bool = True

    @property
    def emap(self) -> dict[str, str]:
        return {p.ref: p.pred for p in self.entity_pairs}

    def cmap(self, tier: str) -> dict[str, str]:
        return dict(self.matches.get(tier, []))


def _overlap(a: Span, b: Span) -> int:
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def _primary(c: B.StoredClaim) -> list[Span]:
    return [(e.start, e.end) for e in c.evidence if e.role is EvidenceRole.PRIMARY]


def _spans(c: B.StoredClaim) -> list[Span]:
    return [(e.start, e.end) for e in c.evidence]


def assign(sim: np.ndarray, threshold: float = 0.0) -> list[tuple[int, int, float]]:
    """A maximum-weight one-to-one assignment over `sim` masked below `threshold` first; pairs of
    weight zero are dropped."""
    if sim.size == 0:
        return []
    masked = np.where(sim >= threshold, sim, 0.0) if threshold else sim
    rows, cols = linear_sum_assignment(masked, maximize=True)
    return [
        (int(i), int(j), float(masked[i, j]))
        for i, j in zip(rows, cols, strict=True)
        if masked[i, j] > 0
    ]


def _object_ref(c: B.StoredClaim) -> str | None:
    return c.object.ref if isinstance(c.object, V.EntityRef) else None


class _Aligner:
    def __init__(self, ref: AlignmentSide, pred: AlignmentSide, ctx: AlignmentContext) -> None:
        self.r, self.p, self.ctx = ref, pred, ctx
        self.ua = UnitAlignment(ref.unit, ref_context=ref.context, pred_context=pred.context)
        self.ua.ref_claims = {c.local_ref: c for c in ref.batch.claims}
        self.ua.pred_claims = {c.local_ref: c for c in pred.batch.claims}
        self.ref_entities = {e.local_ref: e for e in ref.batch.entities}
        self.pred_entities = {e.local_ref: e for e in pred.batch.entities}
        self.espan_r, self.espan_p = self._entity_spans(ref.batch), self._entity_spans(pred.batch)
        self.emap: dict[str, str] = {}
        self.sentences = sorted(set(ref.sentences) | set(pred.sentences))
        self.classes = {c.prefixed: c for c in ctx.lookup.entity_classes.values()}
        self.predicates = {p.prefixed: p for p in ctx.lookup.predicates.values()}

    @staticmethod
    def _entity_spans(batch: B.StoredBatch) -> dict[str, list[Span]]:
        out: dict[str, list[Span]] = {}
        for c in batch.claims:
            for r in (c.subject, _object_ref(c)):
                if r:
                    out.setdefault(r, []).extend(_primary(c))
        return out

    # -- entities --------------------------------------------------------------------------------

    def _evidence(self, a: str, b: str) -> float:
        hit = any(_overlap(x, y) for x in self.espan_r.get(a, []) for y in self.espan_p.get(b, []))
        return W_EVIDENCE if hit else 0.0

    def _global(self, a: B.StoredEntity, b: B.StoredEntity) -> tuple[float, str]:
        la = {text_form(x) for x in (a.label, *a.aliases) if x}
        lb = {text_form(x) for x in (b.label, *b.aliases) if x}
        if la & lb:
            return 1.0, "label"
        rules = self.ctx.labels
        if {normalize_label(x, a.type, rules) for x in la} & {
            normalize_label(x, b.type, rules) for x in lb
        }:
            return 0.9, "alias_rule"
        best = max(((fuzz.token_sort_ratio(x, y), x, y) for x in la for y in lb), default=None)
        if best is not None and best[0] >= NEAR_MISS:
            self.ua.label_near_misses.append(
                (
                    a.local_ref,
                    b.local_ref,
                    f"token_sort_ratio {best[0]:.1f}: {best[1]!r} / {best[2]!r}",
                )
            )
        return 0.0, ""

    def _identity_refs(self, e: B.StoredEntity) -> dict[str, str]:
        cls = self.classes.get(e.type)
        slots = cls.entity_identity if cls is not None else ()
        return {s: e.identity[s] for s in slots if s in e.identity}

    def _sim(self, a: B.StoredEntity, b: B.StoredEntity) -> tuple[float, str]:
        if a.type != b.type:
            return 0.0, ""
        ev = self._evidence(a.local_ref, b.local_ref)
        if a.scope is EntityScope.LOCAL and b.scope is EntityScope.LOCAL:
            macros = self.ctx.macros
            sa = symbol_form(_present(a.symbol) or a.label, macros)
            sb = symbol_form(_present(b.symbol) or b.label, macros)
            if sa != sb:
                if _present(a.symbol) or _present(b.symbol):
                    return 0.0, ""
                la = normalize_label(a.label, "", self.ctx.labels)
                lb = normalize_label(b.label, "", self.ctx.labels)
                if not la or la != lb:
                    return 0.0, ""
            same = a.scope_segment is not MISSING and a.scope_segment == b.scope_segment
            return W_SYMBOL + (W_SCOPE if same else 0.0) + ev, "symbol" + ("+scope" if same else "")
        if a.scope != b.scope:
            return 0.0, ""
        ra, rb = self._identity_refs(a), self._identity_refs(b)
        if ra and rb:
            if set(ra) != set(rb) or any(self.emap.get(ra[s]) != rb[s] for s in ra):
                return 0.0, ""
            cls = self.classes.get(a.type)
            case = cls.identity_case if cls is not None else {}
            rest = (set(a.identity) | set(b.identity)) - set(ra)
            differ = [
                s
                for s in sorted(rest)
                if text_form(a.identity.get(s, ""), case.get(s, CaseRule.FOLD))
                != text_form(b.identity.get(s, ""), case.get(s, CaseRule.FOLD))
            ]
            if not differ:
                return 1.0 + ev, "identity"
            self.ua.identity_near_misses.append(
                (a.local_ref, b.local_ref, f"identity keys differ: {', '.join(differ)}")
            )
            return 0.0, ""
        s, basis = self._global(a, b)
        return (s + ev, basis) if s else (0.0, "")

    def _statement(self, a: Any, b: Any) -> tuple[float, str]:
        sa = self.r.anchors.get(a.local_ref, ())
        sb = self.p.anchors.get(b.local_ref, ())
        inter = sum(_overlap(x, y) for x in sa for y in sb)
        if not inter:
            return 0.0, ""
        union = sum(e - s for s, e in sa) + sum(e - s for s, e in sb) - inter
        ratio = inter / union if union else 0.0
        kind = 0.1 if getattr(a, "kind", None) == getattr(b, "kind", None) else 0.0
        return 0.6 + 0.3 * ratio + kind, f"anchor:{ratio:.2f}"

    def _passes(self, entities: Sequence[B.StoredEntity]) -> list[list[str]]:
        """Classes in alignment order: independent ones first, then identity-dependent classes in
        the dependency order of their entity-valued identity keys; a cycle is refused."""
        by_ref = {e.local_ref: e for e in entities}
        depends: dict[str, set[str]] = {}
        for e in entities:
            refs = self._identity_refs(e)
            if refs:
                depends.setdefault(e.type, set()).update(
                    by_ref[r].type for r in refs.values() if r in by_ref
                )
        independent = sorted({e.type for e in entities} - set(depends))
        order: list[list[str]] = [independent]
        done = set(independent)
        pending = set(depends)
        while pending:
            ready = sorted(t for t in pending if depends[t] - {t} <= done and t not in depends[t])
            if not ready:
                raise ValueError(f"identity keys depend on each other: {sorted(pending)}")
            order.append(ready)
            done |= set(ready)
            pending -= set(ready)
        return order

    def entities(self) -> None:
        rs = [s for s in self.r.batch.statements if isinstance(s, B.StoredStatement)]
        ps = [s for s in self.p.batch.statements if isinstance(s, B.StoredStatement)]
        if rs and ps:
            m = np.array([[self._statement(a, b)[0] for b in ps] for a in rs])
            for i, j, s in assign(m, THRESHOLD):
                basis = self._statement(rs[i], ps[j])[1]
                self.ua.entity_pairs.append(EntityPair(rs[i].local_ref, ps[j].local_ref, s, basis))
        self.emap = self.ua.emap
        re_, pe = list(self.r.batch.entities), list(self.p.batch.entities)
        for classes in self._passes([*re_, *pe]):
            ra = [e for e in re_ if e.type in classes]
            pa = [e for e in pe if e.type in classes]
            if not ra or not pa:
                continue
            m = np.array([[self._sim(a, b)[0] for b in pa] for a in ra])
            for i, j, s in assign(m, THRESHOLD):
                basis = self._sim(ra[i], pa[j])[1]
                self.ua.entity_pairs.append(EntityPair(ra[i].local_ref, pa[j].local_ref, s, basis))
            self.emap = self.ua.emap
        matched_r, matched_p = set(self.emap), set(self.emap.values())
        self.ua.entity_unmatched_ref = [
            x.local_ref for x in (*re_, *rs) if x.local_ref not in matched_r
        ]
        self.ua.entity_unmatched_pred = [
            x.local_ref for x in (*pe, *ps) if x.local_ref not in matched_p
        ]
        for name in ("identity_near_misses", "label_near_misses"):
            kept = {
                n for n in getattr(self.ua, name) if n[0] not in matched_r and n[1] not in matched_p
            }
            setattr(self.ua, name, sorted(kept))

    # -- claims ----------------------------------------------------------------------------------

    def ref_eq(self, a: str | None, b: str | None) -> bool:
        return a is not None and self.emap.get(a) == b

    def _conds(self, a: B.StoredClaim, b: B.StoredClaim) -> list[V.StoredCondition]:
        return [c for c in (a.qualifiers.conditions, b.qualifiers.conditions) if c is not MISSING]

    def value_eq(self, x: Any, y: Any, conds: list[V.StoredCondition]) -> bool:
        return self.ctx.comparator.compare(x, y, conds, self.ref_eq).equal

    def core(self, a: B.StoredClaim, b: B.StoredClaim) -> bool:
        if a.predicate != b.predicate or not self.ref_eq(a.subject, b.subject):
            return False
        ra, rb = _object_ref(a), _object_ref(b)
        if ra is not None or rb is not None:
            return ra is not None and rb is not None and self.ref_eq(ra, rb)
        return self.value_eq(a.object, b.object, self._conds(a, b))

    @staticmethod
    def span_eq(x: Any, y: Any) -> bool:
        return _overlap((x.start, x.end), (y.start, y.end)) > 0

    def tree_eq(
        self, ta: Any, tb: Any, conds: list[V.StoredCondition], leaf_eq: Callable[[str, str], bool]
    ) -> bool:
        comparator = self.ctx.comparator
        return trees_equivalent(
            ta,
            tb,
            TreeMatch(
                value_eq=lambda x, y: self.value_eq(x, y, conds),
                claim_eq=leaf_eq,
                ref_eq=lambda x, y: self.ref_eq(x, y),
                span_eq=self.span_eq,
                canonical_eq=lambda x, y: comparator.canonical_equal(x, y, self.ref_eq),
            ),
        )

    def full_failures(
        self, a: B.StoredClaim, b: B.StoredClaim, leaf_eq: Callable[[str, str], bool]
    ) -> list[str]:
        fails = []
        qa, qb = a.qualifiers, b.qualifiers
        if qa.modality != qb.modality:
            fails.append("modality")
        if qa.polarity != qb.polarity:
            fails.append("polarity")
        if a.statement_role != b.statement_role:
            fails.append("statement_role")
        conds = self._conds(a, b)
        predicate = self.predicates.get(a.predicate)
        for local in predicate.identity_qualifiers if predicate is not None else ():
            q = self.ctx.lookup.qualifiers[local]
            va, vb = qualifier_value(qa, q.prefixed), qualifier_value(qb, q.prefixed)
            if va is UNSET and vb is UNSET:
                continue
            if (va is UNSET) != (vb is UNSET):
                fails.append(f"{q.prefixed}.present")
                continue
            if not self._qualifier_eq(q.object_kind, q.map_value_kind, va, vb, conds, leaf_eq):
                fails.append(q.prefixed)
        ca = qa.conditions if qa.conditions is not MISSING else None
        cb = qb.conditions if qb.conditions is not MISSING else None
        if (ca is not None or cb is not None) and not self.tree_eq(ca, cb, conds, leaf_eq):
            fails.append("conditions")
        return fails

    def _qualifier_eq(
        self,
        kind: str,
        value_kind: str | None,
        va: Any,
        vb: Any,
        conds: list[V.StoredCondition],
        leaf_eq: Callable[[str, str], bool],
    ) -> bool:
        if kind == "map":
            if not (isinstance(va, dict) and isinstance(vb, dict)) or set(va) != set(vb):
                return False
            return all(
                self._qualifier_eq(value_kind or "", None, va[k], vb[k], conds, leaf_eq)
                for k in sorted(va)
            )
        if kind == "condition":
            return self.tree_eq(_condition(va), _condition(vb), conds, leaf_eq)
        if kind == "entity":
            return self.ref_eq(_ref(va), _ref(vb))
        typed_a, typed_b = _value(va), _value(vb)
        if typed_a is not None and typed_b is not None:
            return self.value_eq(typed_a, typed_b, conds)
        return va == vb

    def evidence_ok(self, a: B.StoredClaim, b: B.StoredClaim) -> bool:
        pa, pb = _primary(a), _primary(b)
        if any(_overlap(x, y) for x in pa for y in pb):
            return True
        return any(
            any(_overlap(x, s) for x in pa) and any(_overlap(y, s) for y in pb)
            for s in self.sentences
        )

    @staticmethod
    def _overlap_ratio(a: B.StoredClaim, b: B.StoredClaim) -> float:
        ov = sum(_overlap(x, y) for x in _spans(a) for y in _spans(b))
        total = sum(e - s for s, e in _spans(a)) + sum(e - s for s, e in _spans(b))
        return ov / total if total else 0.0

    def _match(self, weight: Callable[[Pair], float]) -> list[Pair]:
        rc, pc = list(self.ua.ref_claims), list(self.ua.pred_claims)
        if not rc or not pc:
            return []
        m = np.array([[weight((a, b)) for b in pc] for a in rc])
        return sorted((rc[i], pc[j]) for i, j, _ in assign(m))

    def _tiers(self, core_edges: set[Pair], leaf_eq: Callable[[str, str], bool]) -> Any:
        R, P = self.ua.ref_claims, self.ua.pred_claims
        fails = {e: self.full_failures(R[e[0]], P[e[1]], leaf_eq) for e in core_edges}
        full_e = {e for e, f in fails.items() if not f}
        ev_e = {e for e in full_e if self.evidence_ok(R[e[0]], P[e[1]])}
        return fails, full_e, ev_e

    def claims(self) -> None:
        R, P = self.ua.ref_claims, self.ua.pred_claims
        core_edges = {(a, b) for a in R for b in P if self.core(R[a], P[b])}
        ratio = {e: self._overlap_ratio(R[e[0]], P[e[1]]) for e in core_edges}
        base = min(len(R), len(P)) + 1
        w_core, w_full, w_ev = float(base**3), float(base**2), float(base)

        def leaf0(x: str, y: str) -> bool:
            return (x, y) in core_edges

        leaf_eq: Callable[[str, str], bool] = leaf0
        core: list[Pair] = []
        core_map: dict[str, str] | None = None
        self.ua.converged = False
        for it in range(1, MAX_ITER + 1):
            fails, full_e, ev_e = self._tiers(core_edges, leaf_eq)

            def weight(e: Pair, full_e: set[Pair] = full_e, ev_e: set[Pair] = ev_e) -> float:
                if e not in core_edges:
                    return 0.0
                return w_core + w_full * (e in full_e) + w_ev * (e in ev_e) + ratio[e]

            core = self._match(weight)
            new_map = dict(core)
            self.ua.iterations = it
            stable = new_map == core_map
            core_map = new_map
            leaf_eq = _through(core_map)
            if stable:
                self.ua.converged = True
                break
        assert core_map is not None
        fails, full_e, ev_e = self._tiers(core_edges, leaf_eq)
        core_set = set(core)
        self.ua.matches["core"] = core
        # each tier maximizes its count first (b^2, then b), then agrees with the higher tiers
        self.ua.matches["full"] = self._match(
            lambda e: (w_full + w_ev * (e in core_set) + (e in ev_e)) if e in full_e else 0.0
        )
        full_set = set(self.ua.matches["full"])
        self.ua.matches["evidence"] = self._match(
            lambda e: (w_ev + (e in full_set)) if e in ev_e else 0.0
        )
        for e in core:
            self.ua.field_failures[e] = fails[e]
            self.ua.diagnostics[e] = self.diagnose(R[e[0]], P[e[1]], core_map)
        matched_r, matched_p = set(core_map), set(core_map.values())

        def lenient(x: str, y: str) -> bool:
            if core_map.get(x) == y:
                return True
            return x not in matched_r and y not in matched_p and x in R and y in P

        lfails, _, _ = self._tiers(core_edges, lenient)
        self.ua.cascaded = sorted(e for e in core if fails[e] and not lfails[e])

    # -- diagnostics -----------------------------------------------------------------------------

    def _formula_pairs(self, a: B.StoredClaim, b: B.StoredClaim) -> Iterator[tuple[str, Any, Any]]:
        if isinstance(a.object, V.Formula | V.SetValue) and type(a.object) is type(b.object):
            yield "object", a.object, b.object
        for q in self.ctx.lookup.qualifiers.values():
            va, vb = (
                qualifier_value(a.qualifiers, q.prefixed),
                qualifier_value(b.qualifiers, q.prefixed),
            )
            if va is UNSET or vb is UNSET:
                continue
            if q.object_kind == "map" and isinstance(va, dict) and isinstance(vb, dict):
                for k in sorted(set(va) & set(vb)):
                    xa, xb = _value(va[k]), _value(vb[k])
                    if isinstance(xa, V.Formula | V.SetValue) and isinstance(
                        xb, V.Formula | V.SetValue
                    ):
                        yield f"{q.prefixed}.{k}", xa, xb
            elif q.object_kind in ("formula", "set"):
                xa, xb = _value(va), _value(vb)
                if xa is not None and xb is not None:
                    yield q.prefixed, xa, xb

    def diagnose(
        self, a: B.StoredClaim, b: B.StoredClaim, core_map: Mapping[str, str]
    ) -> list[str]:
        out: list[str] = []
        macros = self.ctx.macros
        for where, fa, fb in self._formula_pairs(a, b):
            sb = {symbol_form(k, macros): v for k, v in fb.symbols.items()}
            for symbol, ba in fa.symbols.items():
                key = symbol_form(symbol, macros)
                bb = sb.get(key)
                ok = bb is not None and ba.bind == bb.bind
                if ok and bb is not None and ba.bind in (BindKind.VARIABLE, BindKind.FAMILY_PARAM):
                    ok = self.ref_eq(_present(ba.entity), _present(bb.entity))
                elif (
                    ok and bb is not None and ba.bind in (BindKind.PARAM_OF, BindKind.PARAM_EXPR_OF)
                ):
                    ok = core_map.get(str(ba.claim)) == bb.claim and ba.param == bb.param
                self.ua.bindings.append(
                    {
                        "ref_claim": a.local_ref,
                        "pred_claim": b.local_ref,
                        "where": where,
                        "symbol": key,
                        "ref_bind": ba.bind.value,
                        "pred_bind": bb.bind.value if bb is not None else None,
                        "correct": ok,
                    }
                )
                if not ok and "bindings" not in out:
                    out.append("bindings")
        for r in (a.subject, _object_ref(a)):
            ea = self.ref_entities.get(r) if r else None
            if ea is not None and ea.scope is EntityScope.LOCAL and r in self.emap:
                eb = self.pred_entities.get(self.emap[r])
                if eb is not None and ea.scope_segment != eb.scope_segment and "extent" not in out:
                    out.append("extent")
        return out

    def scopes(self) -> None:
        for p in self.ua.entity_pairs:
            ea, eb = self.ref_entities.get(p.ref), self.pred_entities.get(p.pred)
            if ea is not None and eb is not None and ea.scope is EntityScope.LOCAL:
                self.ua.scopes.append(
                    {
                        "ref": p.ref,
                        "pred": p.pred,
                        "ref_segment": _present(ea.scope_segment),
                        "pred_segment": _present(eb.scope_segment),
                        "correct": ea.scope_segment == eb.scope_segment,
                    }
                )

    def alternatives(self) -> None:
        core = dict(self.ua.matches["core"])
        inverse = {v: k for k, v in core.items()}
        rg = [a.refs for a in self.r.batch.alternatives]
        pg = [a.refs for a in self.p.batch.alternatives]

        def outcome(
            group: tuple[str, ...], mapping: Mapping[str, str], others: list[tuple[str, ...]]
        ) -> str:
            mapped = {mapping.get(x) for x in group}
            if None not in mapped and any(set(o) == mapped for o in others):
                return "matched"
            return "ambiguity_collapsed" if mapped - {None} else "unmatched"

        self.ua.alternatives_ref = [(g, outcome(g, core, pg)) for g in rg]
        self.ua.alternatives_pred = [(g, outcome(g, inverse, rg)) for g in pg]

    def unsupported(self) -> None:
        ru, pu = self.r.batch.unsupported, self.p.batch.unsupported
        self.ua.unsupported_n = (len(ru), len(pu))
        if not ru or not pu:
            return
        base = min(len(ru), len(pu)) + 1
        m = np.zeros((len(ru), len(pu)))
        for i, a in enumerate(ru):
            for j, b in enumerate(pu):
                ov = _overlap((a.start, a.end), (b.start, b.end))
                if ov > 0:
                    m[i, j] = base + ov / ((a.end - a.start) + (b.end - b.start))
        self.ua.unsupported_pairs = [(ru[i].local_ref, pu[j].local_ref) for i, j, _ in assign(m)]

    def run(self) -> UnitAlignment:
        self.entities()
        self.claims()
        self.scopes()
        self.alternatives()
        self.unsupported()
        return self.ua


def _through(core_map: Mapping[str, str]) -> Callable[[str, str], bool]:
    return lambda x, y: core_map.get(x) == y


def _present(value: Any) -> Any:
    return None if value is MISSING else value


def _ref(raw: Any) -> str | None:
    if isinstance(raw, V.EntityRef):
        return raw.ref
    return raw.get("ref") if isinstance(raw, dict) and isinstance(raw.get("ref"), str) else None


def _value(raw: Any) -> Any:
    if isinstance(raw, V.CoreModel):
        return raw
    try:
        return _STORED_VALUE.validate_python(raw)
    except Exception:
        return None


def _condition(raw: Any) -> Any:
    if raw is None or not isinstance(raw, dict):
        return raw
    try:
        return _STORED_CONDITION.validate_python(raw)
    except Exception:
        return None


def align(ref: AlignmentSide, pred: AlignmentSide, context: AlignmentContext) -> UnitAlignment:
    """Align `pred` to `ref`, two claim sets of the same unit on one rendition."""
    return _Aligner(ref, pred, context).run()
