"""Canonical forms (D1 §6.2) and tiered value equivalence (instruments §4, D7 §5.3).

Tiers, recorded per comparison (evidence for OPEN-D7-2):

1. ``canonical``: D1 §6.2 canonical form (normalized LaTeX; numbers in base units; text NFC
   casefolded). The same function feeds ``keys``, so key agreement and tier-1 equality agree.
2. ``sympy``: the value read by the math grammar (``code/mathgrammar``, ADR-0009) under its
   declared kind and converted by ``mathgrammar.to_sympy``; ``simplify(a - b) == 0`` under a
   time limit; sets by SymPy set equality; relations and memberships as relations.
3. ``numeric``: evaluation at random points satisfying the claims' ``member``/``cmp``
   conditions (rejection sampling, fixed seed); numbers after unit conversion.
4. ``manual``: decisions read from the root's ``manual_equivalence.tsv``; undecided pairs are
   returned as ``pending`` (equal=None) and listed in ``ValueComparator.pending``.

Recorded choices (results/s0/instruments_tests.md): simplify time limit 5 s (SIGALRM, main
thread); numeric tier: seed 20261028, up to 12 **distinct** accepted points from at most 4,000
draws; reals half uniform in [-5, 5] and half of magnitude 10^-2..10^3 (random sign), shifted
or bounded by numeric bounds from ``member`` sets and ``symbol <rel> number`` leaves; integers
(symbols in integer sets) uniform over [lower bound, +200] (default [-100, 100]); equality
``math.isclose(rel_tol=1e-9, abs_tol=1e-12)``; at least 6 distinct valid points to decide,
otherwise manual. Relations (``x < 1``) compare as relations (kind ``relation``).

Reading math has one authority, the math grammar: tier-1 canonical forms are printed from its
tree (``mathgrammar.canonical``; token normalization only for values that do not parse), tier 2
converts its tree. A value that does not parse, is ambiguous (``\\Phi(x)``: application or
product, undeclared) or has no SymPy value (``\\pm``, ellipses) goes to manual; ``PARSE_LOG``
records each such value with the grammar's status and reason. Symbols listed in a formula's
binding map are declared variables, which lets the grammar read ``a(b + c)`` as a product.
"""

from __future__ import annotations

import math
import random
import re
import signal
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Context, Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Iterable

# D2 §12.1 `math.macros` (fallback when a page does not define a macro), copied verbatim.
FALLBACK_MACROS: dict[str, str] = {
    "\\R": "\\mathbb{R}",
    "\\N": "\\mathbb{N}",
    "\\Z": "\\mathbb{Z}",
    "\\Q": "\\mathbb{Q}",
    "\\P": "\\mathbb{P}",
    "\\E": "\\mathbb{E}",
    "\\var": "\\text{var}",
    "\\sd": "\\text{sd}",
    "\\cov": "\\text{cov}",
    "\\cor": "\\text{cor}",
    "\\skw": "\\text{skew}",
    "\\kur": "\\text{kurt}",
    "\\mse": "\\text{mse}",
    "\\sgn": "\\text{sgn}",
    "\\bs": "\\boldsymbol",
    "\\ms": "\\mathscr",
}
CONSTANTS = ("e", "\\pi")  # D2 §12.1 math.constants

SIMPLIFY_SECONDS = 5.0
NUMERIC_SEED = 20261028
NUMERIC_POINTS = 12
NUMERIC_MAX_DRAWS = 4000
NUMERIC_MIN_POINTS = 6  # distinct valid points needed to decide
REL_TOL = 1e-9
ABS_TOL = 1e-12

# ============================================================================ LaTeX tokens

import mathgrammar as MG  # noqa: E402  (code/ is on sys.path for every instruments consumer)


def merged_macros(page_macros: dict | None) -> dict[str, dict]:
    """Page macro table (S1 ``parse_detail.macros``) layered over the D2 §12.1 fallback."""
    out = {k: {"nargs": 0, "body": v} for k, v in FALLBACK_MACROS.items()}
    for k, spec in (page_macros or {}).items():
        if isinstance(spec, str):
            spec = {"nargs": 0, "body": spec}
        out[k] = {"nargs": int(spec.get("nargs") or 0), "body": spec.get("body", "")}
    return out


def strip_math_delimiters(latex: str) -> str:
    return MG.printer.strip_delimiters(latex)


def math_parse(latex: str, kind: str = "any_value", macros: dict | None = None, variables: Iterable[str] = ()):
    """The grammar's reading of a value; ``macros`` are page macros (D2 §12.1 fallback beneath)."""
    ctx = {"variables": sorted(variables)} if variables else None
    return MG.parse(latex, kind, macros=merged_macros(macros), context=ctx)


def canonical_latex(latex: str, macros: dict | None = None) -> str:
    """D1 §6.2 canonical LaTeX, printed from the grammar's tree (token form when unparsed)."""
    return MG.canonical(math_parse(latex, "any_value", macros))


def canonical_symbol(symbol: str | None, macros: dict | None = None) -> str | None:
    """Normalized symbol of a local entity or binding key: canonical LaTeX, leading ``\\``
    optional (``mu`` and ``\\mu`` are the same symbol)."""
    if symbol is None:
        return None
    c = canonical_latex(symbol, macros)
    return c[1:] if re.fullmatch(r"\\[A-Za-z]+", c) else c


# ============================================================================ other values


def text_norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFC", s).casefold().split())


# Fallback unit table, used only when pint is absent or does not know a unit: unit -> (base unit, factor).
_UNITS: dict[str, tuple[str | None, Decimal]] = {
    "m": ("m", Decimal(1)),
    "cm": ("m", Decimal("0.01")),
    "mm": ("m", Decimal("0.001")),
    "km": ("m", Decimal(1000)),
    "in": ("m", Decimal("0.0254")),
    "ft": ("m", Decimal("0.3048")),
    "kg": ("kg", Decimal(1)),
    "g": ("kg", Decimal("0.001")),
    "s": ("s", Decimal(1)),
    "min": ("s", Decimal(60)),
    "h": ("s", Decimal(3600)),
    "%": (None, Decimal("0.01")),
}
try:  # pint 0.26.2 is in the spike env since de5bd4c
    import pint  # type: ignore

    _UREG = pint.UnitRegistry()
except Exception:  # noqa: BLE001
    _UREG = None


def number_base(v: str, unit: str | None) -> tuple[Decimal | None, str | None]:
    """Decimal value in pint base units (D1 §6.2). pint 0.26.2 is the route; its float
    conversion factors are rounded to 15 significant digits so the canonical string carries no
    float noise. The fallback table applies only when pint is absent or does not know the unit
    (then the table's factor, else the unit string kept as written with factor 1)."""
    try:
        d = Decimal(str(v).strip())
    except InvalidOperation:
        return None, unit
    if not unit:
        return d, None
    if _UREG is not None:
        try:
            q = _UREG.Quantity(d, unit.strip()).to_base_units()
            return Context(prec=15).create_decimal(str(q.magnitude)), str(q.units)
        except Exception:  # noqa: BLE001 - unknown unit: fall through to the table
            pass
    base, f = _UNITS.get(unit.strip(), (unit.strip(), Decimal(1)))
    return d * f, base


def _dec_str(d: Decimal) -> str:
    s = format(d.normalize(), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def canonical_value(v: Any, macros: dict | None = None, ref_key: Callable[[str], Any] | None = None) -> Any:
    """JSON-able canonical form of a D1 value (dict) or a ``{"ref": ...}`` object.

    ``ref_key`` maps a local ref to the identity used in keys (entity key); default: the ref.
    """
    if hasattr(v, "model_dump"):
        v = v.model_dump(exclude_none=True)
    if isinstance(v, str):  # bare formula position
        return {"t": "formula", "latex": canonical_latex(v, macros)}
    t = v.get("t")
    rk = ref_key or (lambda r: r)
    if t is None and "ref" in v:
        return {"ref": rk(v["ref"])}
    if t in ("formula", "set"):
        return {"t": t, "latex": canonical_latex(v["latex"], macros)}
    if t == "number":
        d, u = number_base(v["v"], v.get("unit"))
        return {"t": "number", "v": _dec_str(d) if d is not None else text_norm(v["v"]), "unit": u}
    if t == "text":
        return {"t": "text", "v": text_norm(v["v"])}
    if t == "bool":
        return {"t": "bool", "v": bool(v["v"])}
    if t == "enum":
        return {"t": "enum", "enum": v["enum"], "v": v["v"]}
    if t == "entity":
        return {"ref": rk(v["ref"])}
    if t == "date":
        return {"t": "date", "v": v["v"].strip()}
    if t == "phrase":
        return {"t": "phrase", "text": text_norm(v["text"])}
    if t == "interval":
        return {
            "t": "interval",
            "start": canonical_value(v["start"], macros, ref_key) if v.get("start") else None,
            "end": canonical_value(v["end"], macros, ref_key) if v.get("end") else None,
            "start_incl": v.get("start_incl"),
            "end_incl": v.get("end_incl"),
        }
    return v


# ============================================================================ SymPy tier

PARSE_LOG: list[dict] = []  # values the grammar did not read into SymPy: status and reason, for S5


class _Timeout(Exception):
    pass


@contextmanager
def time_limit(seconds: float):
    def handler(signum, frame):  # noqa: ARG001
        raise _Timeout()

    old = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


@dataclass
class ParseResult:
    expr: Any = None
    status: str = "failed"  # the grammar's status: ok | partial | ambiguous | failed
    kind: str | None = None
    error: str | None = None


_LOGGED: set = set()


def _read(latex: str, kinds: tuple[str, ...], macros, variables) -> ParseResult:
    last = None
    for k in kinds:
        r = math_parse(latex, k, macros, variables)
        if r.status in ("ok", "partial"):
            try:
                return ParseResult(MG.to_sympy(r), r.status, r.kind or k)
            except Exception as ex:  # noqa: BLE001  NotRepresentable and conversion errors
                res = ParseResult(None, r.status, r.kind or k, f"no SymPy value: {ex}")
                break
        if r.status == "ambiguous":
            res = ParseResult(None, "ambiguous", r.kind or k, "ambiguous: " + "; ".join(r.notes))
            break
        last = r
    else:
        why = (last.reason or {}) if last else {}
        res = ParseResult(None, "failed", None, f"failed: {why.get('category', '?')} at {why.get('at', '')!r}")
    key = (latex, kinds)
    if key not in _LOGGED:
        _LOGGED.add(key)
        PARSE_LOG.append({"latex": latex, "kinds": list(kinds), "status": res.status, "error": res.error})
    return res


def parse_formula(latex: str, macros: dict | None = None, variables: Iterable[str] = ()) -> ParseResult:
    """A formula position: an expression or equation, else a relation or a membership."""
    return _read(latex, ("formula", "relation", "member"), macros, variables)


def parse_set(latex: str, macros: dict | None = None, variables: Iterable[str] = ()) -> ParseResult:
    return _read(latex, ("set_expr",), macros, variables)


# ============================================================================ comparison


@dataclass
class Equivalence:
    equal: bool | None
    tier: str  # canonical | sympy | numeric | manual | pending
    kind: str
    a: str
    b: str
    detail: str = ""
    grammar: str = ""  # the grammar's status of the two values, e.g. "ok/ok"


def _collect_constraints(conds: Iterable[Any], macros) -> tuple[list, list]:
    """Top-level conjunctive ``member`` and ``cmp`` leaves of condition trees."""
    import sympy

    members, rels = [], []

    def walk(n):
        if n is None:
            return
        if hasattr(n, "model_dump"):
            n = n.model_dump(exclude_none=True)
        op = n.get("op")
        if op == "and":
            for a in n["args"]:
                walk(a)
        elif op == "member":
            x = n["x"] if isinstance(n["x"], str) else n["x"]["latex"]
            st = n["set"] if isinstance(n["set"], str) else n["set"]["latex"]
            px, ps = parse_formula(x, macros), parse_set(st, macros)
            if px.expr is not None and ps.expr is not None and isinstance(px.expr, sympy.Symbol):
                members.append((px.expr, ps.expr))
        elif op == "cmp":
            lhs = n["lhs"] if isinstance(n["lhs"], str) else n["lhs"]["latex"]
            rhs = n["rhs"] if isinstance(n["rhs"], str) else n["rhs"]["latex"]
            pl, pr = parse_formula(lhs, macros), parse_formula(rhs, macros)
            if pl.expr is not None and pr.expr is not None:
                rels.append((n["rel"], pl.expr, pr.expr))

    for c in conds:
        walk(c)
    return members, rels


_REL = {"<": lambda a, b: a < b, "<=": lambda a, b: a <= b, "=": lambda a, b: math.isclose(a, b),
        "!=": lambda a, b: not math.isclose(a, b), ">": lambda a, b: a > b, ">=": lambda a, b: a >= b}


def _num(expr, pt) -> complex | None:
    try:
        v = complex(expr.xreplace(pt).evalf())
    except Exception:  # noqa: BLE001
        return None
    if not (math.isfinite(v.real) and math.isfinite(v.imag)):
        return None
    return v


def _close(x: complex, y: complex) -> bool:
    return abs(x - y) <= max(REL_TOL * max(abs(x), abs(y)), ABS_TOL)


def _bounds(sym, members, rels) -> tuple[float, float]:
    """Numeric lower/upper bounds on ``sym`` from its member sets and ``sym <rel> number`` leaves."""
    lo, hi = -math.inf, math.inf
    for s, st in members:
        if s != sym:
            continue
        for attr, which in (("inf", "lo"), ("sup", "hi")):
            try:
                v = getattr(st, attr)
                if v.is_number and v.is_finite:
                    if which == "lo":
                        lo = max(lo, float(v))
                    else:
                        hi = min(hi, float(v))
            except Exception:  # noqa: BLE001
                pass
    for rel, lhs, rhs in rels:
        if lhs == sym and rhs.is_number:
            c, r = float(rhs), rel
        elif rhs == sym and lhs.is_number:
            c, r = float(lhs), {"<": ">", "<=": ">=", ">": "<", ">=": "<="}.get(rel, rel)
        else:
            continue
        if r in ("<", "<="):
            hi = min(hi, c)
        elif r in (">", ">="):
            lo = max(lo, c)
    return lo, hi


def _draw_real(rng: random.Random, lo: float, hi: float) -> float:
    if math.isfinite(lo) and math.isfinite(hi):
        return rng.uniform(lo, hi)
    # half small (|v| <= 5), half large-magnitude (10^-2 .. 10^3), so piecewise forms such as
    # min(x, 10) are exercised beyond the unit range
    v = rng.uniform(-5.0, 5.0) if rng.random() < 0.5 else rng.choice((-1, 1)) * 10 ** rng.uniform(-2, 3)
    if math.isfinite(lo):
        return lo + abs(v)
    if math.isfinite(hi):
        return hi - abs(v)
    return v


def _draw_int(rng: random.Random, lo: float, hi: float) -> int:
    a = math.ceil(lo) if math.isfinite(lo) else (math.floor(hi) - 200 if math.isfinite(hi) else -100)
    b = math.floor(hi) if math.isfinite(hi) else a + 200
    return rng.randint(a, b) if a <= b else a


def sample_points(symbols, members, rels, rng: random.Random) -> list[dict]:
    """Distinct points satisfying the constraints (rejection sampling)."""
    import sympy

    sym_sets: dict = {}
    for s, st in members:
        sym_sets.setdefault(s, []).append(st)
    syms = sorted(symbols, key=str)
    spec = {}
    for s in syms:
        integer = any(bool(st.is_subset(sympy.S.Integers)) for st in sym_sets.get(s, []))
        spec[s] = (integer, *_bounds(s, members, rels))
    pts, seen = [], set()
    draws = 0
    while len(pts) < NUMERIC_POINTS and draws < NUMERIC_MAX_DRAWS:
        draws += 1
        pt = {}
        for s in syms:
            integer, lo, hi = spec[s]
            pt[s] = sympy.Integer(_draw_int(rng, lo, hi)) if integer else sympy.Float(_draw_real(rng, lo, hi), 30)
        key = tuple(str(pt[s]) for s in syms)
        if key in seen:
            continue
        ok = True
        for s, st in members:
            if s in pt and st.contains(pt[s]) is not sympy.true:
                ok = False
                break
        if ok:
            for rel, lhs, rhs in rels:
                a, b = _num(lhs, pt), _num(rhs, pt)
                if a is None or b is None or abs(a.imag) > ABS_TOL or abs(b.imag) > ABS_TOL:
                    ok = False
                    break
                if not _REL[rel](a.real, b.real):
                    ok = False
                    break
        if ok:
            seen.add(key)
            pts.append(pt)
    return pts


@dataclass
class ValueComparator:
    """Tiered equivalence with a log of every comparison and its deciding tier."""

    macros: dict | None = None
    manual: dict[tuple[str, str], tuple[bool, str]] = field(default_factory=dict)
    seed: int = NUMERIC_SEED
    log: list[Equivalence] = field(default_factory=list)
    pending: list[Equivalence] = field(default_factory=list)
    _cache: dict = field(default_factory=dict)
    _vars: tuple = ()  # symbols declared variables by the compared values' binding maps

    @classmethod
    def with_manual_tsv(cls, path: str | Path | None, **kw) -> "ValueComparator":
        """Read the root's decisions: TSV columns ``kind a b decision reason`` (decision
        ``equal``/``unequal``; empty = undecided)."""
        manual = {}
        if path and Path(path).exists():
            for line in Path(path).read_text(encoding="utf-8").splitlines()[1:]:
                parts = line.split("\t")
                if len(parts) >= 4 and parts[3] in ("equal", "unequal"):
                    manual[(parts[1], parts[2])] = (parts[3] == "equal", parts[4] if len(parts) > 4 else "")
        return cls(manual=manual, **kw)

    def pending_tsv(self) -> str:
        rows = ["kind\ta\tb\tdecision\treason"]
        seen = set()
        for e in self.pending:
            if (e.a, e.b) not in seen:
                seen.add((e.a, e.b))
                rows.append(f"{e.kind}\t{e.a}\t{e.b}\t\t{e.detail}")
        return "\n".join(rows) + "\n"

    def tally(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in self.log:
            out[e.tier] = out.get(e.tier, 0) + 1
        return out

    # -----

    def compare(self, va: Any, vb: Any, conds: Iterable[Any] = (), ref_eq: Callable[[str, str], bool] | None = None) -> Equivalence:
        if hasattr(va, "model_dump"):
            va = va.model_dump(exclude_none=True)
        if hasattr(vb, "model_dump"):
            vb = vb.model_dump(exclude_none=True)
        if isinstance(va, str):
            va = {"t": "formula", "latex": va}
        if isinstance(vb, str):
            vb = {"t": "formula", "latex": vb}
        ta = va.get("t", "ref" if "ref" in va else None)
        tb = vb.get("t", "ref" if "ref" in vb else None)
        ta = "ref" if ta == "entity" else ta
        tb = "ref" if tb == "entity" else tb
        if ta == "ref" or tb == "ref":
            eq = ta == tb and ref_eq is not None and ref_eq(va["ref"], vb["ref"])
            return Equivalence(eq, "canonical", "ref", va.get("ref", "?"), vb.get("ref", "?"))
        ca, cb = canonical_value(va, self.macros), canonical_value(vb, self.macros)
        sa, sb = repr(ca), repr(cb)
        if ta != tb:
            res = Equivalence(False, "canonical", f"{ta}/{tb}", sa, sb, "different value types")
            self.log.append(res)
            return res
        conds = list(conds)
        self._vars = tuple(sorted({k.lstrip("\\") for v in (va, vb) for k in (v.get("symbols") or {})}))
        ck = (sa, sb, repr([c.model_dump() if hasattr(c, "model_dump") else c for c in conds]), self._vars)
        if ck in self._cache:
            return self._cache[ck]
        res = self._compare(ta, va, vb, ca, cb, conds)
        self._cache[ck] = res
        self.log.append(res)
        if res.tier == "pending":
            self.pending.append(res)
        return res

    def _manual(self, kind, a, b, why) -> Equivalence:
        d = self.manual.get((a, b)) or self.manual.get((b, a))
        if d is not None:
            return Equivalence(d[0], "manual", kind, a, b, d[1])
        return Equivalence(None, "pending", kind, a, b, why)

    def _compare(self, t, va, vb, ca, cb, conds) -> Equivalence:
        if ca == cb:
            return Equivalence(True, "canonical", t, va.get("latex", repr(ca)), vb.get("latex", repr(cb)))
        if t in ("formula", "set"):
            return self._compare_math(t, ca["latex"], cb["latex"], va["latex"], vb["latex"], conds)
        if t == "number":
            da, ua = number_base(va["v"], va.get("unit"))
            db, ub = number_base(vb["v"], vb.get("unit"))
            if da is None or db is None or ua != ub:
                return Equivalence(False, "numeric", t, repr(ca), repr(cb), "incommensurable")
            return Equivalence(_close(complex(da), complex(db)), "numeric", t, repr(ca), repr(cb))
        if t == "phrase":
            if None not in (va.get("start"), vb.get("start")):
                ov = va["start"] < vb["end"] and vb["start"] < va["end"]
                return Equivalence(ov, "canonical", t, repr(ca), repr(cb), "span overlap")
            return Equivalence(False, "canonical", t, repr(ca), repr(cb))
        if t == "interval":
            ok = True
            for part in ("start", "end"):
                pa, pb = va.get(part), vb.get(part)
                if (pa is None) != (pb is None):
                    ok = False
                elif pa is not None:
                    ok = ok and bool(self.compare(pa, pb, conds).equal)
            ok = ok and va.get("start_incl") == vb.get("start_incl") and va.get("end_incl") == vb.get("end_incl")
            return Equivalence(ok, "canonical", t, repr(ca), repr(cb))
        # text, enum, bool, date: canonical form decides
        return Equivalence(False, "canonical", t, repr(ca), repr(cb))

    def _compare_math(self, t, a, b, la, lb, conds) -> Equivalence:
        import sympy

        parse = parse_set if t == "set" else parse_formula
        pa, pb = parse(la, self.macros, self._vars), parse(lb, self.macros, self._vars)
        gs = f"{pa.status}/{pb.status}"
        if pa.expr is None or pb.expr is None:
            why = f"parse failed: {pa.error or ''} {pb.error or ''}".strip()
            r = self._manual(t, a, b, why)
            r.grammar = gs
            return r
        if t == "set":
            try:
                with time_limit(SIMPLIFY_SECONDS):
                    d = pa.expr.symmetric_difference(pb.expr)
                if d == sympy.S.EmptySet or pa.expr == pb.expr:
                    return Equivalence(True, "sympy", t, a, b, grammar=gs)
                if not d.free_symbols and d.is_empty is False:
                    return Equivalence(False, "sympy", t, a, b, "symmetric difference non-empty", gs)
            except _Timeout:
                pass
            r = self._manual(t, a, b, "set equality inconclusive")
            r.grammar = gs
            return r
        ea, eb = pa.expr, pb.expr
        ka, kb = _expr_kind(ea), _expr_kind(eb)
        if "boolean" in (ka, kb):  # memberships, chains (And), negations: structural SymPy equality
            if ka == kb and ea == eb:
                return Equivalence(True, "sympy", "relation", a, b, grammar=gs)
            if ka != kb:
                return Equivalence(False, "sympy", "relation", a, b, f"{ka} versus {kb}", gs)
            return self._manual("relation", a, b, "membership or chain equivalence inconclusive")
        if "relation" in (ka, kb):
            return self._compare_relation(ea, eb, ka, kb, a, b, gs)
        rel_a, rel_b = ka == "equation", kb == "equation"
        if rel_a != rel_b:
            return Equivalence(False, "sympy", t, a, b, "equation versus expression", gs)
        diffs = [ea.lhs - ea.rhs - (eb.lhs - eb.rhs), ea.lhs - ea.rhs + (eb.lhs - eb.rhs)] if rel_a else [ea - eb]
        detail = ""
        try:
            with time_limit(SIMPLIFY_SECONDS):
                simp = [sympy.simplify(d) for d in diffs]
            if any(s == 0 for s in simp):
                return Equivalence(True, "sympy", t, a, b, grammar=gs)
            if all(s.is_number and s.is_zero is False for s in simp):
                return Equivalence(False, "sympy", t, a, b, "difference is a nonzero constant", gs)
            detail = "simplify inconclusive"
        except _Timeout:
            detail = f"simplify timed out ({SIMPLIFY_SECONDS}s)"
        except Exception as ex:  # noqa: BLE001
            detail = f"simplify error {type(ex).__name__}"
        # tier 3: numeric
        rng = random.Random(self.seed)
        members, rels = _collect_constraints(conds, self.macros)
        syms = set(ea.free_symbols) | set(eb.free_symbols)  # all symbols: the relative scale needs them
        pts = sample_points(syms, members, rels, rng)
        verdicts = []
        for k, d in enumerate(diffs):
            base = (ea.lhs - ea.rhs) if rel_a else ea
            vals = []
            for pt in pts:
                x = _num(d, pt)
                s = _num(base, pt)
                if x is None or s is None:
                    continue
                vals.append(abs(x) <= max(REL_TOL * max(abs(s), abs(s - x)), ABS_TOL))
            verdicts.append(vals)
        n_valid = max((len(v) for v in verdicts), default=0)
        if n_valid >= NUMERIC_MIN_POINTS:
            eq = any(v and all(v) for v in verdicts)
            return Equivalence(eq, "numeric", t, a, b, f"{detail}; {n_valid} points", gs)
        r = self._manual(t, a, b, f"{detail}; numeric: {n_valid} valid points")
        r.grammar = gs
        return r

    def _compare_relation(self, ea, eb, ka, kb, a, b, gs) -> Equivalence:
        """Inequalities (``x < 1``, ``X \\le x``): equal when the operators agree after writing
        ``>``/``>=`` as ``<``/``<=`` and ``lhs - rhs`` simplifies to the same expression;
        unequal when the differences differ by a nonzero constant or the other side is not a
        relation; anything else goes to manual."""
        import sympy

        if ka != kb:
            return Equivalence(False, "sympy", "relation", a, b, f"{ka} versus {kb}", gs)
        ea, eb = _lt_form(ea), _lt_form(eb)
        if type(ea) is not type(eb):
            return self._manual("relation", a, b, f"operators differ: {type(ea).__name__} vs {type(eb).__name__}")
        da, db = ea.lhs - ea.rhs, eb.lhs - eb.rhs
        cands = [da - db] + ([da + db] if isinstance(ea, sympy.Unequality) else [])
        try:
            with time_limit(SIMPLIFY_SECONDS):
                simp = [sympy.simplify(c) for c in cands]
        except Exception as ex:  # noqa: BLE001  (timeout included)
            return self._manual("relation", a, b, f"simplify {type(ex).__name__}")
        if any(c == 0 for c in simp):
            return Equivalence(True, "sympy", "relation", a, b, grammar=gs)
        if all(c.is_number and c.is_zero is False for c in simp):
            return Equivalence(False, "sympy", "relation", a, b, "sides differ by a nonzero constant", gs)
        return self._manual("relation", a, b, "relation equivalence inconclusive")


def _expr_kind(e) -> str:
    import sympy

    if isinstance(e, sympy.Equality):
        return "equation"
    if (isinstance(e, sympy.logic.boolalg.Boolean) and not isinstance(e, sympy.core.relational.Relational)
            and not isinstance(e, sympy.Expr)):  # Contains, And, Not; Min/Max are lattice Exprs
        return "boolean"
    if isinstance(e, sympy.core.relational.Relational):
        return "relation"
    return "expression"


def _lt_form(e):
    import sympy

    if isinstance(e, (sympy.StrictGreaterThan, sympy.GreaterThan)):
        return e.reversed
    return e
