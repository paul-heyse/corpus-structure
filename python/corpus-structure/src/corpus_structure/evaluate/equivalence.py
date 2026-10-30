"""Tiered value equivalence and condition-tree equivalence (D7 §5.3, OPEN-D7-2; evaluation §3.5).

Each comparison records the tier that decided it:

1. **canonical**: F2b's canonical forms (`core/keys.py` `canonical_value`): formulas and sets by
   the token form, numbers as canonical decimals with units as written, text NFC and casefolded,
   dates verbatim, intervals by endpoints and inclusivity, references by entity alignment, phrases
   by span overlap (by text when a side has no span);
2. **symbolic**: the math grammar's reading of each value under its slot's kind (formula, then
   relation, then member; `set_expr` for sets), the binding map's symbols declared variables,
   converted by the grammar's transformer; `simplify(a - b) == 0` under a time limit, equations up
   to sign, relations after writing `>` as `<`, sets by an empty symmetric difference, memberships
   and chains structurally;
3. **numeric**: evaluation at points satisfying the claims' top-level `member` and `cmp`
   conditions, rejection-sampled from `numpy.random.default_rng(seed)`, the seed the SHA-256 of
   the sorted pair of canonical forms and the canonical conditions (so independent of argument
   order); at least six distinct valid points decide, at relative tolerance 1e-9;
4. **undecided**: counted unequal, logged with the pair, the reason and the grammar's status.

Tiers 2 and 3 run on a process's main thread only (the grammar's timer); `compare` raises
`OffMainThread` anywhere else. Results are cached by canonical pair, canonical conditions and
declared variables.

`decisions` is a test-only input (the S0 parity test supplies S0's recorded equivalence decisions
through it): a pair it names is decided by it instead of counting as undecided. No command or
configuration passes it.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np
import sympy
from pydantic import MISSING
from scipy.optimize import linear_sum_assignment

from corpus_structure.core import values as V
from corpus_structure.core.canonical import canonical_json
from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.keys import Uniform, canonical_condition, canonical_value
from corpus_structure.core.vocab import Relation
from corpus_structure.methods.math import grammar
from corpus_structure.semantic.scientific_evidence import MathReading as _Reading
from corpus_structure.semantic.scientific_evidence import _bounds as _bounds
from corpus_structure.semantic.scientific_evidence import _draw_int as _draw_int
from corpus_structure.semantic.scientific_evidence import _draw_real as _draw_real
from corpus_structure.semantic.scientific_evidence import _num as _num
from corpus_structure.semantic.scientific_evidence import _seed as _seed
from corpus_structure.semantic.scientific_evidence import grammar_name as grammar_name
from corpus_structure.semantic.scientific_evidence import sample_points as sample_points

_IDENTITY = Uniform(lambda ref: ref)

type RefEq = Callable[[str, str], bool]


class Tier(StrEnum):
    CANONICAL = "canonical"
    SYMBOLIC = "symbolic"
    NUMERIC = "numeric"
    DECIDED = "decided"  # the test-only decision input
    UNDECIDED = "undecided"


@dataclass(frozen=True)
class Equivalence:
    equal: bool
    tier: Tier
    kind: str
    a: str  # canonical forms, as compared
    b: str
    detail: str = ""
    grammar: str = ""  # the grammar's status of the two values, "ok/ambiguous"


def _json(value: Any) -> str:
    return canonical_json(value).decode()


def _form(value: Any, macros: Mapping[str, MacroDef]) -> str:
    return _json(canonical_value(value, macros, _IDENTITY))


class ValueComparator:
    """Tiered equivalence over one rendition's effective macro table, with its comparison log."""

    def __init__(
        self,
        macros: Mapping[str, MacroDef],
        constants: Sequence[str] = (),
        *,
        decisions: Mapping[tuple[str, str], bool] | None = None,
    ) -> None:
        self.macros = macros
        self.constants = frozenset(constants)
        self.decisions = dict(decisions or {})
        self.log: list[Equivalence] = []
        self._cache: dict[tuple[str, str, str, tuple[str, ...]], Equivalence] = {}

    @property
    def undecided(self) -> list[Equivalence]:
        return [e for e in self.log if e.tier is Tier.UNDECIDED]

    def canonical_equal(self, a: Any, b: Any, ref_eq: RefEq | None = None) -> bool:
        """Tier 1 alone: equal canonical forms (references by `ref_eq`)."""
        if isinstance(a, V.EntityRef) or isinstance(b, V.EntityRef):
            both = isinstance(a, V.EntityRef) and isinstance(b, V.EntityRef)
            return both and ref_eq is not None and ref_eq(a.ref, b.ref)
        return _form(a, self.macros) == _form(b, self.macros)

    def compare(
        self,
        a: Any,
        b: Any,
        conditions: Iterable[V.StoredCondition] = (),
        ref_eq: RefEq | None = None,
    ) -> Equivalence:
        grammar.require_main_thread()
        if isinstance(a, V.EntityRef) or isinstance(b, V.EntityRef):
            same = isinstance(a, V.EntityRef) and isinstance(b, V.EntityRef)
            equal = same and ref_eq is not None and ref_eq(a.ref, b.ref)
            ra, rb = getattr(a, "ref", "?"), getattr(b, "ref", "?")
            return Equivalence(equal, Tier.CANONICAL, "ref", ra, rb)
        ta, tb = getattr(a, "t", None), getattr(b, "t", None)
        fa, fb = _form(a, self.macros), _form(b, self.macros)
        if ta != tb:
            out = Equivalence(False, Tier.CANONICAL, f"{ta}/{tb}", fa, fb, "different value types")
            self.log.append(out)
            return out
        conds = list(conditions)
        names = sorted(grammar_name(k) for v in (a, b) for k in (getattr(v, "symbols", None) or {}))
        variables = tuple(dict.fromkeys(names))
        cform = _json(sorted(_json(canonical_condition(c, self.macros, _IDENTITY)) for c in conds))
        left_form, right_form = sorted((fa, fb))
        key = (left_form, right_form, cform, variables)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        out = self._compare(str(ta), a, b, fa, fb, conds, cform, variables)
        self._cache[key] = out
        self.log.append(out)
        return out

    # -- tiers -----------------------------------------------------------------------------------

    def _undecided(self, kind: str, fa: str, fb: str, why: str, status: str = "") -> Equivalence:
        decided = self.decisions.get((fa, fb), self.decisions.get((fb, fa)))
        if decided is not None:
            return Equivalence(decided, Tier.DECIDED, kind, fa, fb, why, status)
        return Equivalence(False, Tier.UNDECIDED, kind, fa, fb, why, status)

    def _compare(
        self,
        t: str,
        a: Any,
        b: Any,
        fa: str,
        fb: str,
        conds: list[V.StoredCondition],
        cform: str,
        variables: tuple[str, ...],
    ) -> Equivalence:
        if fa == fb:
            return Equivalence(True, Tier.CANONICAL, t, fa, fb)
        if isinstance(a, V.Formula | V.SetValue):
            return self._math(t, a.latex, b.latex, fa, fb, conds, cform, variables)
        if isinstance(a, V.StoredPhrase) and isinstance(b, V.StoredPhrase):
            overlap = a.start < b.end and b.start < a.end
            return Equivalence(overlap, Tier.CANONICAL, t, fa, fb, "span overlap")
        if isinstance(a, V.IntervalValue) and isinstance(b, V.IntervalValue):
            ok = a.start_incl == b.start_incl and a.end_incl == b.end_incl
            for x, y in ((a.start, b.start), (a.end, b.end)):
                if (x is MISSING) != (y is MISSING):
                    ok = False
                elif x is not MISSING and y is not MISSING:
                    ok = ok and self.compare(x, y, conds).equal
            return Equivalence(ok, Tier.CANONICAL, t, fa, fb)
        return Equivalence(False, Tier.CANONICAL, t, fa, fb)

    def _read(
        self, latex: str, kinds: tuple[grammar.Kind, ...], variables: tuple[str, ...]
    ) -> _Reading:
        from corpus_structure.semantic.scientific_evidence import MathematicalEvidence

        return MathematicalEvidence(self.macros, self.constants)._read(latex, kinds, variables)

    def _math(
        self,
        t: str,
        la: str,
        lb: str,
        fa: str,
        fb: str,
        conds: list[V.StoredCondition],
        cform: str,
        variables: tuple[str, ...],
    ) -> Equivalence:
        from corpus_structure.semantic.scientific_evidence import EvidenceTier, MathematicalEvidence

        evidence = MathematicalEvidence(
            self.macros, self.constants, constraints=self._constraints
        )._math(t, la, lb, fa, fb, conds, cform, variables)
        if evidence.tier is EvidenceTier.UNDECIDED:
            return self._undecided(t, fa, fb, evidence.detail, evidence.grammar)
        return Equivalence(
            evidence.agreement is True,
            Tier(evidence.tier.value),
            evidence.kind,
            fa,
            fb,
            evidence.detail,
            evidence.grammar,
        )

    def _constraints(
        self, conds: list[V.StoredCondition], variables: tuple[str, ...]
    ) -> tuple[list[Any], list[Any]]:
        """Top-level conjunctive `member` and `cmp` leaves, read by the grammar."""
        members: list[tuple[Any, Any]] = []
        relations: list[tuple[str, Any, Any]] = []

        def walk(node: Any) -> None:
            if isinstance(node, V.StoredAnd):
                for arg in node.args:
                    walk(arg)
            elif isinstance(node, V.MemberNode):
                x = self._read(node.x.latex, ("formula",), variables).expr
                s = self._read(node.set.latex, ("set_expr",), variables).expr
                if isinstance(x, sympy.Symbol) and s is not None:
                    members.append((x, s))
            elif isinstance(node, V.CmpNode):
                lhs = self._read(node.lhs.latex, ("formula",), variables).expr
                rhs = self._read(node.rhs.latex, ("formula",), variables).expr
                if lhs is not None and rhs is not None:
                    relations.append((node.rel.value, lhs, rhs))

        for c in conds:
            walk(c)
        return members, relations


# --- Condition trees -------------------------------------------------------------------------


@dataclass(frozen=True)
class TreeMatch:
    """How two condition trees' leaves are judged (D7 §5.3)."""

    value_eq: Callable[[Any, Any], bool]
    claim_eq: Callable[[str, str], bool]
    ref_eq: RefEq
    span_eq: Callable[[Any, Any], bool]
    canonical_eq: Callable[[Any, Any], bool] = field(default=lambda a, b: False)


_FLIP = {Relation.GT: Relation.LT, Relation.GE: Relation.LE}


def normalize_tree(node: V.StoredCondition | None) -> V.StoredCondition | None:
    """Nested `and`/`or` flattened, one-argument ones collapsed, empty ones dropped, `>`/`>=`
    written as `<`/`<=` with sides swapped."""
    if node is None:
        return None
    if isinstance(node, V.StoredAnd | V.StoredOr):
        args: list[V.StoredCondition] = []
        for arg in node.args:
            n = normalize_tree(arg)
            if n is None:
                continue
            if (isinstance(node, V.StoredAnd) and isinstance(n, V.StoredAnd)) or (
                isinstance(node, V.StoredOr) and isinstance(n, V.StoredOr)
            ):
                args.extend(n.args)
            else:
                args.append(n)
        if not args:
            return None
        if len(args) == 1:
            return args[0]
        return (
            V.StoredAnd(op="and", args=tuple(args))
            if isinstance(node, V.StoredAnd)
            else V.StoredOr(op="or", args=tuple(args))
        )
    if isinstance(node, V.StoredNot):
        inner = normalize_tree(node.arg)
        return node if inner is None else V.StoredNot(op="not", arg=inner)
    if isinstance(node, V.CmpNode) and node.rel in _FLIP:
        return V.CmpNode(op="cmp", rel=_FLIP[node.rel], lhs=node.rhs, rhs=node.lhs)
    if isinstance(node, V.StoredForall):
        body = normalize_tree(node.body)
        return node if body is None else node.model_copy(update={"body": body})
    return node


def perfect_match(xs: Sequence[Any], ys: Sequence[Any], eq: Callable[[Any, Any], bool]) -> bool:
    if len(xs) != len(ys):
        return False
    if not xs:
        return True
    m = np.array([[1.0 if eq(x, y) else 0.0 for y in ys] for x in xs])
    rows, cols = linear_sum_assignment(m, maximize=True)
    return bool(m[rows, cols].sum() == len(xs))


def trees_equivalent(
    a: V.StoredCondition | None, b: V.StoredCondition | None, match: TreeMatch
) -> bool:
    """Both trees normalized; leaves matched one-to-one. Values compare by canonical form first,
    and by the tiered comparison only when that finds no perfect leaf matching."""
    na, nb = normalize_tree(a), normalize_tree(b)
    return _tree_eq(na, nb, match.canonical_eq, match) or _tree_eq(na, nb, match.value_eq, match)


def _tree_eq(x: Any, y: Any, value_eq: Callable[[Any, Any], bool], m: TreeMatch) -> bool:
    if x is None or y is None:
        return x is None and y is None
    if x.op != y.op:
        return False
    match x:
        case V.StoredAnd() | V.StoredOr():
            return perfect_match(x.args, y.args, lambda p, q: _tree_eq(p, q, value_eq, m))
        case V.StoredNot():
            return _tree_eq(x.arg, y.arg, value_eq, m)
        case V.ClaimNode():
            return m.claim_eq(x.ref, y.ref)
        case V.MemberNode():
            return value_eq(x.x, y.x) and value_eq(x.set, y.set)
        case V.CmpNode():
            same = x.rel == y.rel and value_eq(x.lhs, y.lhs) and value_eq(x.rhs, y.rhs)
            if not same and x.rel == y.rel and x.rel in (Relation.EQ, Relation.NE):
                same = value_eq(x.lhs, y.rhs) and value_eq(x.rhs, y.lhs)
            return same
        case V.PredNode():

            def arg_eq(p: Any, q: Any) -> bool:
                if isinstance(p, V.EntityRef) != isinstance(q, V.EntityRef):
                    return False
                return m.ref_eq(p.ref, q.ref) if isinstance(p, V.EntityRef) else value_eq(p, q)

            return x.name == y.name and perfect_match(x.args, y.args, arg_eq)
        case V.StoredForall():
            return (
                x.var == y.var and value_eq(x.set, y.set) and _tree_eq(x.body, y.body, value_eq, m)
            )
        case V.StoredPhraseNode() | V.StoredUnsupportedNode():
            return m.span_eq(x, y)
    return False
