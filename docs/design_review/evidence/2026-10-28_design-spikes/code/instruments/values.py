"""Canonical forms (D1 §6.2) and tiered value equivalence (instruments §4, D7 §5.3).

Tiers, recorded per comparison (evidence for OPEN-D7-2):

1. ``canonical``: D1 §6.2 canonical form (normalized LaTeX; numbers in base units; text NFC
   casefolded). The same function feeds ``keys``, so key agreement and tier-1 equality agree.
2. ``sympy``: ``parse_latex(..., backend="lark")`` on the macro-expanded LaTeX, then
   ``simplify(a - b) == 0`` under a time limit; sets by SymPy set equality.
3. ``numeric``: evaluation at random points satisfying the claims' ``member``/``cmp``
   conditions (rejection sampling, fixed seed); numbers after unit conversion.
4. ``manual``: decisions read from the root's ``manual_equivalence.tsv``; undecided pairs are
   returned as ``pending`` (equal=None) and listed in ``ValueComparator.pending``.

Recorded choices (results/s0/instruments_tests.md): simplify time limit 5 s (SIGALRM, main
thread); numeric tier draws 12 accepted points, at most 4,000 draws, seed 20261028, reals
uniform in [-5, 5], integers in [-10, 10] for symbols constrained to integer sets; equality
``math.isclose(rel_tol=1e-9, abs_tol=1e-12)``; at least 3 valid points are needed to decide.

The SymPy 1.14 lark grammar lacks ``\\sigma``, ``\\pi``, ``\\lvert``/``\\rvert`` and implicit
multiplication after a power (``b^2 \\sigma^2``). Each formula is parsed raw first; a raw
failure is logged in ``PARSE_LOG`` for S5 and the parse is retried through a compatibility
shim (``_lark_shim``); the comparison records whether the shim was needed.
"""

from __future__ import annotations

import math
import random
import re
import signal
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
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
NUMERIC_MIN_POINTS = 3
REL_TOL = 1e-9
ABS_TOL = 1e-12

# ============================================================================ LaTeX tokens

_TOKEN_RE = re.compile(r"\\[A-Za-z]+\*?|\\.|\s+|.", re.S)
_DROP = {"\\,", "\\;", "\\!", "\\left", "\\right"}  # D1 §6.2
_CW = re.compile(r"\\[A-Za-z]+\*?$")


def tokenize(latex: str) -> list[str]:
    return _TOKEN_RE.findall(latex)


def merged_macros(page_macros: dict | None) -> dict[str, dict]:
    """Page macro table (S1 ``parse_detail.macros``) layered over the D2 §12.1 fallback."""
    out = {k: {"nargs": 0, "body": v} for k, v in FALLBACK_MACROS.items()}
    for k, spec in (page_macros or {}).items():
        if isinstance(spec, str):
            spec = {"nargs": 0, "body": spec}
        out[k] = {"nargs": int(spec.get("nargs") or 0), "body": spec.get("body", "")}
    return out


def _read_arg(tokens: list[str], j: int) -> tuple[list[str], int]:
    while j < len(tokens) and tokens[j].isspace():
        j += 1
    if j >= len(tokens):
        return [], j
    if tokens[j] == "{":
        depth, k = 0, j
        while k < len(tokens):
            if tokens[k] == "{":
                depth += 1
            elif tokens[k] == "}":
                depth -= 1
                if depth == 0:
                    return tokens[j + 1 : k], k + 1
            k += 1
        return tokens[j + 1 :], len(tokens)
    return [tokens[j]], j + 1


def expand_macros(tokens: list[str], macros: dict[str, dict], depth: int = 0) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        spec = macros.get(t)
        if spec is None or depth > 20:
            out.append(t)
            i += 1
            continue
        args = []
        j = i + 1
        for _ in range(spec["nargs"]):
            a, j = _read_arg(tokens, j)
            args.append(a)
        body = tokenize(spec["body"])
        sub: list[str] = []
        k = 0
        while k < len(body):
            if body[k] == "#" and k + 1 < len(body) and body[k + 1].isdigit():
                n = int(body[k + 1]) - 1
                sub.extend(["{", *(args[n] if n < len(args) else []), "}"])
                k += 2
            else:
                sub.append(body[k])
                k += 1
        out.extend(expand_macros(sub, macros, depth + 1))
        i = j
    return out


def strip_math_delimiters(latex: str) -> str:
    s = latex.strip()
    for o, c in (("$$", "$$"), ("$", "$"), ("\\(", "\\)"), ("\\[", "\\]")):
        if s.startswith(o) and s.endswith(c) and len(s) >= len(o) + len(c):
            return s[len(o) : len(s) - len(c)].strip()
    return s


def _group_tree(tokens: list[str]):
    stack: list[list] = [[]]
    for t in tokens:
        if t == "{":
            stack.append([])
        elif t == "}":
            if len(stack) == 1:
                return None
            g = stack.pop()
            stack[-1].append(g)
        else:
            stack[-1].append(t)
    return stack[0] if len(stack) == 1 else None


def _simplify_groups(items: list) -> list:
    out = []
    for it in items:
        if isinstance(it, list):
            inner = _simplify_groups(it)
            if len(inner) == 1 and isinstance(inner[0], str):
                out.append(inner[0])  # braces around a single token dropped (b^{2} -> b^2)
            else:
                out.append(inner)
        else:
            out.append(it)
    return out


def _flatten(items: list) -> list[str]:
    out: list[str] = []
    for it in items:
        if isinstance(it, list):
            out.extend(["{", *_flatten(it), "}"])
        else:
            out.append(it)
    return out


def serialize(tokens: list[str]) -> str:
    """Join tokens; a space follows a control word only where TeX needs it (next is a letter)."""
    out = []
    prev = ""
    for t in tokens:
        if prev and _CW.match(prev) and t[:1].isalpha():
            out.append(" ")
        out.append(t)
        prev = t
    return "".join(out)


def canonical_tokens(latex: str, macros: dict | None = None) -> list[str]:
    toks = expand_macros(tokenize(strip_math_delimiters(latex)), merged_macros(macros))
    toks = [t for t in toks if not t.isspace() and t not in _DROP]
    tree = _group_tree(toks)
    if tree is None:
        return toks
    return _flatten(_simplify_groups(tree))


def canonical_latex(latex: str, macros: dict | None = None) -> str:
    """D1 §6.2 normalized LaTeX."""
    return serialize(canonical_tokens(latex, macros))


def expanded_latex(latex: str, macros: dict | None = None) -> str:
    """Macro-expanded LaTeX with original spacing (input to SymPy)."""
    return "".join(expand_macros(tokenize(strip_math_delimiters(latex)), merged_macros(macros)))


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


# Fallback unit table (pint is not installed in the spike env): unit -> (base unit, factor).
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
try:  # pragma: no cover - pint absent at E0
    import pint  # type: ignore

    _UREG = pint.UnitRegistry()
except Exception:  # noqa: BLE001
    _UREG = None


def number_base(v: str, unit: str | None) -> tuple[Decimal | None, str | None]:
    try:
        d = Decimal(str(v).strip())
    except InvalidOperation:
        return None, unit
    if not unit:
        return d, None
    if _UREG is not None:  # pragma: no cover
        q = _UREG.Quantity(d, unit).to_base_units()
        return Decimal(str(q.magnitude)), str(q.units)
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

PARSE_LOG: list[dict] = []  # raw lark failures and shim outcomes, for S5

_LARK_GREEK = {
    "alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "zeta", "eta", "theta",
    "vartheta", "kappa", "lambda", "mu", "nu", "xi", "rho", "varrho", "tau", "upsilon",
    "phi", "varphi", "chi", "psi", "omega",
}
_SHIM_GREEK = {"sigma", "varsigma", "iota", "pi", "varpi", "Gamma", "Delta", "Theta", "Lambda",
               "Xi", "Pi", "Sigma", "Upsilon", "Phi", "Psi", "Omega"}
_NON_ATOM_AFTER = {"+", "-", "=", "<", ">", ",", ")", "]", "}", "^", "_", "|", "!", "/", "*",
                   "\\cdot", "\\times", "\\le", "\\ge", "\\leq", "\\geq", "\\ne", "\\neq",
                   "\\in", "\\setminus", "\\div", "\\mid", "&"}
_DIGITS = "abcdefghij"


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


def _lark_shim(tokens: list[str]) -> tuple[str, dict[str, str]]:
    """Rewrite canonical tokens into what SymPy 1.14's lark grammar accepts.

    Returns the LaTeX string and a symbol rename map (placeholder name -> intended name).
    """
    renames: dict[str, str] = {}
    toks: list[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in ("\\lvert", "\\rvert", "\\vert", "\\lVert", "\\rVert"):
            toks.append("|")
        elif t.startswith("\\") and t[1:] in _SHIM_GREEK:
            name = t[1:]
            sub = None
            if i + 2 < len(tokens) and tokens[i + 1] == "_":
                if tokens[i + 2] == "{":
                    k = tokens.index("}", i + 2) if "}" in tokens[i + 2 :] else None
                    if k is not None:
                        sub = "".join(tokens[i + 3 : k])
                        i = k
                else:
                    sub = tokens[i + 2]
                    i += 2
            if sub is not None and re.fullmatch(r"[A-Za-z0-9]+", sub):
                enc = "".join(_DIGITS[int(c)] if c.isdigit() else c for c in sub)
                ph = f"{name}ZZ{enc}"
                renames[ph] = f"{name}_{{{sub}}}"
            else:
                ph = name
            toks.extend(["\\mathit", "{", ph, "}"])
        else:
            toks.append(t)
        i += 1
    # implicit multiplication after a power and after a closing |...|
    out: list[str] = []
    bar_open = False
    i = 0
    while i < len(toks):
        t = toks[i]
        out.append(t)
        end_of_factor = False
        if t == "^" and i + 1 < len(toks):
            if toks[i + 1] == "{":
                depth, k = 0, i + 1
                while k < len(toks):
                    depth += toks[k] == "{"
                    depth -= toks[k] == "}"
                    if depth == 0:
                        break
                    k += 1
                out.extend(toks[i + 1 : k + 1])
                i = k
            else:
                out.append(toks[i + 1])
                i += 1
                if toks[i] == "\\mathit" and i + 3 < len(toks):
                    out.extend(toks[i + 1 : i + 4])
                    i += 3
            end_of_factor = True
        elif t == "|":
            bar_open = not bar_open
            end_of_factor = not bar_open
        elif t == "}":  # end of an argument group (\sqrt{..}, \frac{..}{..}, \mathit{..})
            end_of_factor = True
        if end_of_factor and i + 1 < len(toks):
            nxt = toks[i + 1]
            if nxt not in _NON_ATOM_AFTER and nxt != "{" and not (nxt == "|" and bar_open):
                out.append("\\cdot")
        i += 1
    return " ".join(out), renames


def _plain(expr, renames: dict[str, str]):
    import sympy

    rep = {}
    for s in expr.free_symbols:
        name = renames.get(str(s), str(s))
        if name == "e":
            rep[s] = sympy.E
        elif name == "pi":
            rep[s] = sympy.pi
        else:
            rep[s] = sympy.Symbol(name)
    return expr.xreplace(rep)


@dataclass
class ParseResult:
    expr: Any = None
    shim: bool = False
    error: str | None = None


_PARSE_CACHE: dict[str, ParseResult] = {}


def parse_formula(latex: str, macros: dict | None = None) -> ParseResult:
    from sympy.parsing.latex import parse_latex

    raw = expanded_latex(latex, macros).strip()
    key = repr((raw, sorted((macros or {}).items()) if macros else None))
    if key in _PARSE_CACHE:
        return _PARSE_CACHE[key]
    res = ParseResult()
    try:
        res.expr = _plain(parse_latex(raw, backend="lark"), {})
    except Exception as ex:  # noqa: BLE001
        raw_err = f"{type(ex).__name__}: {str(ex).splitlines()[0][:120]}"
        shimmed, ren = _lark_shim(canonical_tokens(latex, macros))
        try:
            res.expr = _plain(parse_latex(shimmed, backend="lark"), ren)
            res.shim = True
        except Exception as ex2:  # noqa: BLE001
            res.error = f"{type(ex2).__name__}: {str(ex2).splitlines()[0][:120]}"
        PARSE_LOG.append({"latex": latex, "expanded": raw, "raw_error": raw_err,
                          "shimmed": shimmed, "shim_ok": res.error is None, "shim_error": res.error})
    _PARSE_CACHE[key] = res
    return res


# ----- sets

_BLACKBOARD = {"R": "Reals", "Z": "Integers", "Q": "Rationals", "C": "Complexes", "N": "Naturals0"}


def _match_close(toks: list[str], i: int, closers: set[str]) -> tuple[int, int]:
    """From an opener at i, return (comma index at depth 0, closer index)."""
    depth, comma = 0, -1
    for k in range(i + 1, len(toks)):
        t = toks[k]
        if t in ("(", "[", "{", "\\{"):
            depth += 1
        elif t in (")", "]", "}", "\\}") and depth > 0:
            depth -= 1
        elif depth == 0 and t == ",":
            comma = k
        elif depth == 0 and t in closers:
            return comma, k
    return -1, -1


def _set_term(toks: list[str], i: int, macros):
    import sympy

    t = toks[i]
    if t == "\\mathbb" and i + 1 < len(toks):
        name = _BLACKBOARD.get(toks[i + 1])
        if name is None:
            raise ValueError(f"unknown blackboard set {toks[i + 1]}")
        s = getattr(sympy.S, name)
        j = i + 2
        if j + 1 < len(toks) and toks[j] in ("_", "^") and toks[j + 1] == "+":
            s = sympy.Interval.open(0, sympy.oo) if name == "Reals" else (
                sympy.S.Naturals if name in ("Naturals0", "Integers") else s.intersect(sympy.Interval.open(0, sympy.oo)))
            j += 2
        return s, j
    if t in ("\\emptyset", "\\varnothing"):
        return sympy.S.EmptySet, i + 1
    if t in ("(", "["):
        comma, close = _match_close(toks, i, {")", "]"})
        if comma < 0 or close < 0:
            raise ValueError("unbalanced interval")
        lo = parse_formula(serialize(toks[i + 1 : comma]), macros)
        hi = parse_formula(serialize(toks[comma + 1 : close]), macros)
        if lo.expr is None or hi.expr is None:
            raise ValueError(f"interval endpoint: {lo.error or hi.error}")
        return sympy.Interval(lo.expr, hi.expr, left_open=t == "(", right_open=toks[close] == ")"), close + 1
    if t == "\\{":
        depth, k, parts, cur = 0, i + 1, [], []
        while k < len(toks):
            x = toks[k]
            if x == "\\}" and depth == 0:
                break
            if x in ("(", "[", "{"):
                depth += 1
            elif x in (")", "]", "}"):
                depth -= 1
            if x == "," and depth == 0:
                parts.append(cur)
                cur = []
            else:
                cur.append(x)
            k += 1
        parts.append(cur)
        elems = []
        for p in parts:
            if not p:
                continue
            r = parse_formula(serialize(p), macros)
            if r.expr is None:
                raise ValueError(f"set element: {r.error}")
            elems.append(r.expr)
        return sympy.FiniteSet(*elems), k + 1
    raise ValueError(f"unexpected token {t!r}")


def parse_set(latex: str, macros: dict | None = None) -> ParseResult:
    import sympy

    toks = canonical_tokens(latex, macros)
    try:
        s, i = _set_term(toks, 0, macros)
        while i < len(toks):
            op = toks[i]
            rhs, i = _set_term(toks, i + 1, macros)
            if op in ("\\setminus", "\\backslash", "-"):
                s = sympy.Complement(s, rhs)
            elif op == "\\cup":
                s = sympy.Union(s, rhs)
            elif op == "\\cap":
                s = sympy.Intersection(s, rhs)
            else:
                raise ValueError(f"unknown set operator {op!r}")
        return ParseResult(expr=s)
    except Exception as ex:  # noqa: BLE001
        PARSE_LOG.append({"latex": latex, "set": True, "error": str(ex)[:120]})
        return ParseResult(error=f"set: {ex}")


# ============================================================================ comparison


@dataclass
class Equivalence:
    equal: bool | None
    tier: str  # canonical | sympy | numeric | manual | pending
    kind: str
    a: str
    b: str
    detail: str = ""
    shim: bool = False


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


def sample_points(symbols, members, rels, rng: random.Random) -> list[dict]:
    import sympy

    sym_sets: dict = {}
    for s, st in members:
        sym_sets.setdefault(s, []).append(st)
    pts = []
    draws = 0
    syms = sorted(symbols, key=str)
    while len(pts) < NUMERIC_POINTS and draws < NUMERIC_MAX_DRAWS:
        draws += 1
        pt = {}
        for s in syms:
            sets = sym_sets.get(s, [])
            integer = any(bool(st.is_subset(sympy.S.Integers)) for st in sets)
            val = rng.randint(-10, 10) if integer else rng.uniform(-5.0, 5.0)
            pt[s] = sympy.Integer(val) if integer else sympy.Float(val, 30)
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
        ck = (sa, sb, repr([c.model_dump() if hasattr(c, "model_dump") else c for c in conds]))
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
        pa, pb = parse(la, self.macros), parse(lb, self.macros)
        shim = pa.shim or pb.shim
        if pa.expr is None or pb.expr is None:
            why = f"parse failed: {pa.error or ''} {pb.error or ''}".strip()
            r = self._manual(t, a, b, why)
            r.shim = shim
            return r
        if t == "set":
            try:
                with time_limit(SIMPLIFY_SECONDS):
                    d = pa.expr.symmetric_difference(pb.expr)
                if d == sympy.S.EmptySet or pa.expr == pb.expr:
                    return Equivalence(True, "sympy", t, a, b, shim=shim)
                if not d.free_symbols and d.is_empty is False:
                    return Equivalence(False, "sympy", t, a, b, "symmetric difference non-empty", shim)
            except _Timeout:
                pass
            r = self._manual(t, a, b, "set equality inconclusive")
            r.shim = shim
            return r
        ea, eb = pa.expr, pb.expr
        rel_a, rel_b = isinstance(ea, sympy.Equality), isinstance(eb, sympy.Equality)
        if rel_a != rel_b:
            return Equivalence(False, "sympy", t, a, b, "equation versus expression", shim)
        diffs = [ea.lhs - ea.rhs - (eb.lhs - eb.rhs), ea.lhs - ea.rhs + (eb.lhs - eb.rhs)] if rel_a else [ea - eb]
        detail = ""
        try:
            with time_limit(SIMPLIFY_SECONDS):
                simp = [sympy.simplify(d) for d in diffs]
            if any(s == 0 for s in simp):
                return Equivalence(True, "sympy", t, a, b, shim=shim)
            if all(s.is_number and s.is_zero is False for s in simp):
                return Equivalence(False, "sympy", t, a, b, "difference is a nonzero constant", shim)
            detail = "simplify inconclusive"
        except _Timeout:
            detail = f"simplify timed out ({SIMPLIFY_SECONDS}s)"
        except Exception as ex:  # noqa: BLE001
            detail = f"simplify error {type(ex).__name__}"
        # tier 3: numeric
        rng = random.Random(self.seed)
        members, rels = _collect_constraints(conds, self.macros)
        syms = set().union(*(d.free_symbols for d in diffs))
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
            return Equivalence(eq, "numeric", t, a, b, f"{detail}; {n_valid} points", shim)
        r = self._manual(t, a, b, f"{detail}; numeric: {n_valid} valid points")
        r.shim = shim
        return r
