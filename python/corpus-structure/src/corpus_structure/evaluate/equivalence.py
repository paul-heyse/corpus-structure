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

import hashlib
import math
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
from corpus_structure.core.vocab import ParseOutcome, Relation
from corpus_structure.methods.math import grammar

SIMPLIFY_SECONDS = 5.0
NUMERIC_POINTS = 12
NUMERIC_MAX_DRAWS = 4000
NUMERIC_MIN_POINTS = 6
REL_TOL = 1e-9
ABS_TOL = 1e-12
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


@dataclass(frozen=True)
class _Reading:
    expr: Any = None
    status: str = "failed"
    error: str = ""


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
        key = (*sorted((fa, fb)), cform, variables)
        hit = self._cache.get(key)  # type: ignore[arg-type]
        if hit is not None:
            return hit
        out = self._compare(str(ta), a, b, fa, fb, conds, cform, variables)
        self._cache[key] = out  # type: ignore[index]
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
        context = grammar.MathContext(variables=frozenset(variables), constants=self.constants)
        for kind in kinds:
            result = grammar.parse(latex, kind, self.macros, context)
            if result.status in (ParseOutcome.OK, ParseOutcome.PARTIAL):
                try:
                    return _Reading(grammar.to_sympy(result), result.status.value)
                except Exception as error:
                    return _Reading(None, result.status.value, f"no SymPy value: {error}")
            if result.status is ParseOutcome.AMBIGUOUS:
                return _Reading(None, "ambiguous", "; ".join(result.notes))
        return _Reading(None, "failed", "the grammar does not read it")

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
        kinds: tuple[grammar.Kind, ...] = (
            ("set_expr",) if t == "set" else ("formula", "relation", "member")
        )
        ra, rb = self._read(la, kinds, variables), self._read(lb, kinds, variables)
        status = f"{ra.status}/{rb.status}"
        if ra.expr is None or rb.expr is None:
            why = f"no SymPy value: {ra.error or ''} {rb.error or ''}".strip()
            return self._undecided(t, fa, fb, why, status)
        ea, eb = ra.expr, rb.expr
        if t == "set":
            try:
                with grammar.deadline(SIMPLIFY_SECONDS):
                    if ea == eb or ea.symmetric_difference(eb) == sympy.S.EmptySet:
                        return Equivalence(True, Tier.SYMBOLIC, t, fa, fb, grammar=status)
                    d = ea.symmetric_difference(eb)
                    if not d.free_symbols and d.is_empty is False:
                        return Equivalence(False, Tier.SYMBOLIC, t, fa, fb, "differ", status)
            except grammar.Expired:
                pass
            return self._undecided(t, fa, fb, "set equality inconclusive", status)
        ka, kb = _expr_kind(ea), _expr_kind(eb)
        if "boolean" in (ka, kb):
            if ka == kb and ea == eb:
                return Equivalence(True, Tier.SYMBOLIC, "relation", fa, fb, grammar=status)
            if ka != kb:
                return Equivalence(False, Tier.SYMBOLIC, "relation", fa, fb, f"{ka}/{kb}", status)
            return self._undecided("relation", fa, fb, "membership or chain inconclusive", status)
        if "relation" in (ka, kb):
            return self._relation(ea, eb, ka, kb, fa, fb, status)
        if (ka == "equation") != (kb == "equation"):
            return Equivalence(False, Tier.SYMBOLIC, t, fa, fb, "equation/expression", status)
        if ka == "equation":
            diffs = [ea.lhs - ea.rhs - (eb.lhs - eb.rhs), ea.lhs - ea.rhs + (eb.lhs - eb.rhs)]
            base = ea.lhs - ea.rhs
        else:
            diffs, base = [ea - eb], ea
        detail = ""
        try:
            with grammar.deadline(SIMPLIFY_SECONDS):
                simplified = [sympy.simplify(d) for d in diffs]
            if any(s == 0 for s in simplified):
                return Equivalence(True, Tier.SYMBOLIC, t, fa, fb, grammar=status)
            if all(s.is_number and s.is_zero is False for s in simplified):
                return Equivalence(False, Tier.SYMBOLIC, t, fa, fb, "nonzero constant", status)
            detail = "simplify inconclusive"
        except grammar.Expired:
            detail = f"simplify timed out ({SIMPLIFY_SECONDS} s)"
        except Exception as error:
            detail = f"simplify {type(error).__name__}"
        rng = np.random.default_rng(_seed(fa, fb, cform))
        members, relations = self._constraints(conds, variables)
        points = sample_points(set(ea.free_symbols) | set(eb.free_symbols), members, relations, rng)
        verdicts = []
        for d in diffs:
            checks = []
            for point in points:
                x, s = _num(d, point), _num(base, point)
                if x is None or s is None:
                    continue
                checks.append(abs(x) <= max(REL_TOL * max(abs(s), abs(s - x)), ABS_TOL))
            verdicts.append(checks)
        valid = max((len(v) for v in verdicts), default=0)
        if valid >= NUMERIC_MIN_POINTS:
            equal = any(v and all(v) for v in verdicts)
            return Equivalence(equal, Tier.NUMERIC, t, fa, fb, f"{detail}; {valid} points", status)
        return self._undecided(t, fa, fb, f"{detail}; {valid} valid points", status)

    def _relation(
        self, ea: Any, eb: Any, ka: str, kb: str, fa: str, fb: str, status: str
    ) -> Equivalence:
        if ka != kb:
            return Equivalence(False, Tier.SYMBOLIC, "relation", fa, fb, f"{ka}/{kb}", status)
        ea, eb = _lt_form(ea), _lt_form(eb)
        if type(ea) is not type(eb):
            return self._undecided("relation", fa, fb, "operators differ", status)
        da, db = ea.lhs - ea.rhs, eb.lhs - eb.rhs
        candidates = [da - db] + ([da + db] if isinstance(ea, sympy.Unequality) else [])
        try:
            with grammar.deadline(SIMPLIFY_SECONDS):
                simplified = [sympy.simplify(c) for c in candidates]
        except grammar.Expired:
            return self._undecided("relation", fa, fb, "simplify timed out", status)
        except Exception as error:
            return self._undecided("relation", fa, fb, f"simplify {type(error).__name__}", status)
        if any(c == 0 for c in simplified):
            return Equivalence(True, Tier.SYMBOLIC, "relation", fa, fb, grammar=status)
        if all(c.is_number and c.is_zero is False for c in simplified):
            return Equivalence(False, Tier.SYMBOLIC, "relation", fa, fb, "differ", status)
        return self._undecided("relation", fa, fb, "relation inconclusive", status)

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


def grammar_name(symbol: str) -> str:
    """A binding map's key as a declared variable (a lone control word without its backslash)."""
    return symbol[1:] if symbol.startswith("\\") and symbol[1:].isalpha() else symbol


def _seed(fa: str, fb: str, cform: str) -> int:
    payload = _json([sorted((fa, fb)), cform])
    return int(hashlib.sha256(payload.encode()).hexdigest()[:16], 16)


def _expr_kind(e: Any) -> str:
    if isinstance(e, sympy.Equality):
        return "equation"
    relational = isinstance(e, sympy.core.relational.Relational)
    if (
        isinstance(e, sympy.logic.boolalg.Boolean)
        and not relational
        and not isinstance(e, sympy.Expr)
    ):
        return "boolean"
    return "relation" if relational else "expression"


def _lt_form(e: Any) -> Any:
    if isinstance(e, sympy.StrictGreaterThan | sympy.GreaterThan):
        return e.reversed
    return e


_REL: Mapping[str, Callable[[float, float], bool]] = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "=": lambda a, b: math.isclose(a, b),
    "!=": lambda a, b: not math.isclose(a, b),
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


def _num(expr: Any, point: Mapping[Any, Any]) -> complex | None:
    try:
        v = complex(expr.xreplace(point).evalf())
    except Exception:
        return None
    return v if math.isfinite(v.real) and math.isfinite(v.imag) else None


def _bounds(sym: Any, members: list[Any], relations: list[Any]) -> tuple[float, float]:
    lo, hi = -math.inf, math.inf
    for s, st in members:
        if s != sym:
            continue
        for attr, low in (("inf", True), ("sup", False)):
            try:
                v = getattr(st, attr)
                if v.is_number and v.is_finite:
                    lo, hi = (max(lo, float(v)), hi) if low else (lo, min(hi, float(v)))
            except Exception:
                pass
    flip = {"<": ">", "<=": ">=", ">": "<", ">=": "<="}
    for rel, lhs, rhs in relations:
        if lhs == sym and rhs.is_number:
            c, r = float(rhs), rel
        elif rhs == sym and lhs.is_number:
            c, r = float(lhs), flip.get(rel, rel)
        else:
            continue
        if r in ("<", "<="):
            hi = min(hi, c)
        elif r in (">", ">="):
            lo = max(lo, c)
    return lo, hi


def _draw_real(rng: np.random.Generator, lo: float, hi: float) -> float:
    if math.isfinite(lo) and math.isfinite(hi):
        return float(rng.uniform(lo, hi))
    if rng.random() < 0.5:
        v = float(rng.uniform(-5.0, 5.0))
    else:
        v = float(rng.choice([-1, 1]) * 10 ** rng.uniform(-2, 3))
    if math.isfinite(lo):
        return lo + abs(v)
    if math.isfinite(hi):
        return hi - abs(v)
    return v


def _draw_int(rng: np.random.Generator, lo: float, hi: float) -> int:
    a = (
        math.ceil(lo)
        if math.isfinite(lo)
        else (math.floor(hi) - 200 if math.isfinite(hi) else -100)
    )
    b = math.floor(hi) if math.isfinite(hi) else a + 200
    return int(rng.integers(a, b + 1)) if a <= b else a


def sample_points(
    symbols: Iterable[Any], members: list[Any], relations: list[Any], rng: np.random.Generator
) -> list[dict[Any, Any]]:
    """Distinct points satisfying the constraints, by rejection sampling."""
    by_symbol: dict[Any, list[Any]] = {}
    for s, st in members:
        by_symbol.setdefault(s, []).append(st)
    ordered = sorted(symbols, key=str)
    spec = {}
    for s in ordered:
        integer = any(bool(st.is_subset(sympy.S.Integers)) for st in by_symbol.get(s, []))
        spec[s] = (integer, *_bounds(s, members, relations))
    points: list[dict[Any, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for _ in range(NUMERIC_MAX_DRAWS):
        if len(points) >= NUMERIC_POINTS:
            break
        point: dict[Any, Any] = {}
        for s in ordered:
            integer, lo, hi = spec[s]
            if integer:
                point[s] = sympy.Integer(_draw_int(rng, lo, hi))
            else:
                point[s] = sympy.Float(_draw_real(rng, lo, hi), 30)
        key = tuple(str(point[s]) for s in ordered)
        if key in seen:
            continue
        ok = all(s not in point or st.contains(point[s]) is sympy.true for s, st in members)
        for rel, lhs, rhs in relations if ok else ():
            x, y = _num(lhs, point), _num(rhs, point)
            if x is None or y is None or abs(x.imag) > ABS_TOL or abs(y.imag) > ABS_TOL:
                ok = False
                break
            if not _REL[rel](x.real, y.real):
                ok = False
                break
        if ok:
            seen.add(key)
            points.append(point)
    return points


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
            args.extend(n.args if type(n) is type(node) else [n])  # type: ignore[union-attr]
        if not args:
            return None
        if len(args) == 1:
            return args[0]
        return type(node)(op=node.op, args=tuple(args))  # type: ignore[arg-type]
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
        case V.StoredPhraseNode():  # `unsupported` leaves included
            return m.span_eq(x, y)
    return False
