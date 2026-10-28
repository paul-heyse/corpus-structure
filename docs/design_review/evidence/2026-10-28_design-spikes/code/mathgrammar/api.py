"""Public API of the math reader (ADR-0009).

    r = parse(latex, kind="formula", macros=page_macros, context={"variables": {"a", "b"}})
    r.status          ok | ambiguous | partial | failed
    r.kind            detected kind: formula | relation | member | set_expr
    r.reason          None, or {"error", "pos", "at", "category", ...}
    r.occurrences     symbol occurrences with offsets into ``latex``
    canonical(r)      D1 §6.2 token form of the value (keys; total, never from the tree)
    tree_token_agreement(r)   the tree printer against the token form (validation property)
    to_sympy(r)       SymPy object (raises Ambiguous / NotRepresentable / NotParsed)
    occurrences_in_span(text, start, end, macros)   symbols of a math span of canonical text

Ambiguity (Earley, ``ambiguity="explicit"``) is resolved only from declared context:

- a symbol directly followed by ``(...)`` is a function application only if it is declared a
  function (``context["functions"]``, or ``KNOWN_FUNCTIONS``: ``\\Gamma``); it is a product only
  if every such symbol is declared a variable (``context["variables"]``, e.g. the formula's
  symbol bindings). Operators from the macro table are never ambiguous (their own rule).
- readings whose SymPy values are identical (associativity: ``a b / c``) are one reading.
- anything left is reported ``ambiguous``: never picked silently. A product reading of
  ``symbol(...)`` with an undeclared symbol is ambiguous even when the grammar offers no other
  reading.
- a definition ``g(x) = ...`` (a symbol applied to symbols on the left of ``=``) declares ``g`` a
  function within that value.
- ``(a, b)`` is an interval only where the kind is a set: under ``any_value`` a bare interval is
  reported ambiguous ("interval or pair").
- under ``any_value`` a lone symbol (``X``, ``\\bs{Y}``) is read as a formula, not as a named set:
  a named set needs a set position (``x \\in A``) or the ``set_expr`` kind. The note says so.
- ``a, b \\in S`` (a membership of a list, or a list ending in a membership) is read as the
  membership of every listed element, the standard convention; the note says so.

``partial``: the input parsed only after dropping trailing sentence punctuation (``.``, ``,``,
``;``) that display math often carries.
"""

from __future__ import annotations

import re
import signal
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

import lark
import sympy
from lark import Token, Tree

from .build import STARTS, MacroClass, classify, parser_for
from .printer import leaves, node_text, strip_delimiters, token_form, tokens_canonical, tree_canonical
from .to_sympy import KNOWN_FUNCTIONS, NotRepresentable, symbol_name, transform

PARSE_SECONDS = 2.0
_KIND_ALIAS = {"set": "set_expr", "any": "any_value", "expression": "formula"}
_SET_ROOTS = {"set_const", "interval", "set_list", "set_builder", "empty_set", "set_named", "set_group",
              "set_minus", "set_union", "set_intersection", "set_product", "set_expr"}
CONSTANTS = {"e"}  # D2 §12.1 math.constants (\pi is its own rule)


class Ambiguous(Exception):
    pass


class NotParsed(Exception):
    pass


class _Timeout(Exception):
    pass


@contextmanager
def _limit(seconds: float):
    def handler(signum, frame):  # noqa: ARG001
        raise _Timeout()

    try:
        old = signal.signal(signal.SIGALRM, handler)
    except ValueError:  # not the main thread: no limit
        yield
        return
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


@dataclass
class Occurrence:
    name: str  # canonical LaTeX of the symbol with its subscript: X_1, \sigma_{X_1}, \mathscr F
    base: str  # X, \sigma
    sub: str | None
    sup: str | None  # exponent when the symbol is the base of a power
    start: int
    end: int
    constant: bool = False
    in_subscript_of: str | None = None


@dataclass
class MathResult:
    latex: str  # the parser's input (delimiters stripped for reading)
    requested: str
    status: str
    kind: str | None = None
    tree: Any = None
    reason: dict | None = None
    occurrences: list[Occurrence] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    mc: MacroClass | None = None
    context: dict = field(default_factory=dict)
    offset: int = 0  # where ``latex`` starts within the caller's text
    source: str = ""  # the value as given (the token form's input)


# ============================================================================ errors


ERROR_EXAMPLES = {
    "limit-arrow": [r"\lim_{x \to 0^{+}} f(x)", r"\lim_{n \to \infty} \frac{a_n}{n}=", r"\lim\limits_{n \to \infty} a_n"],
    "integral-bounds": [r"\int_{-\infty}^\infty f(x) dx", r"\int_A f", r"\int_0^1 f(x) \, d x = "],
    "sum-bounds": [r"\sum_{i \in I} x_i", r"\sum_{x \in S} f(x)", r"\prod_{i \in I} x_i"],
    "environment": [r"\begin{cases} x \end{cases}", r"\begin{align} x \end{align}"],
    "text-in-math": [r"x \text{ if } y", r"\text{for } x > 0"],
}
_CMD = re.compile(r"\\[A-Za-z]+")


def _category(e: lark.exceptions.UnexpectedInput, s: str, parse_fn) -> str:
    """Failure category. The offending command decides first (precise); otherwise
    ``UnexpectedInput.match_examples`` over ``ERROR_EXAMPLES``. With Earley, an error where an
    expression is expected shares its parser state with most examples, so match_examples is
    used only when the error is not at a command."""
    if isinstance(e, lark.exceptions.UnexpectedEOF) or (isinstance(e, lark.exceptions.UnexpectedToken) and e.token.type == "$END"):
        return "incomplete"
    pos = getattr(e, "pos_in_stream", None)
    if pos is None and isinstance(e, lark.exceptions.UnexpectedToken):
        pos = e.token.start_pos
    at = s[pos:] if pos is not None else ""
    m = _CMD.match(at)
    if m:
        cmd = m.group(0)
        if cmd in ("\\lim", "\\to"):
            return "limit-arrow"
        if cmd in ("\\int", "\\iint", "\\oint"):
            return "integral-bounds"
        if cmd in ("\\sum", "\\prod"):
            return "sum-bounds"
        if cmd in ("\\begin", "\\end"):
            return "environment"
        if cmd in ("\\text", "\\mbox", "\\textrm"):
            return "text-in-math"
        if cmd in ("\\mapsto", "\\Rightarrow", "\\iff", "\\implies"):
            return "unsupported-relation"
        return "unknown-command"
    if at[:1] == "&":
        return "alignment"
    try:
        label = e.match_examples(parse_fn, ERROR_EXAMPLES, use_accepts=True)
    except Exception:  # noqa: BLE001
        label = None
    if label:
        return label
    if at[:1] in (",", ";", ".", ":"):
        return "punctuation-or-list"
    return "unexpected-token"


def _reason(e: Exception, s: str, parse_fn) -> dict:
    out = {"error": type(e).__name__}
    if isinstance(e, lark.exceptions.UnexpectedCharacters):
        out.update(pos=e.pos_in_stream, at=s[e.pos_in_stream: e.pos_in_stream + 16])
    elif isinstance(e, lark.exceptions.UnexpectedToken):
        out.update(pos=e.token.start_pos, at=str(e.token)[:16], expected=sorted(e.expected)[:8])
    elif isinstance(e, lark.exceptions.UnexpectedEOF):
        out.update(pos=len(s), at="<EOF>")
    if isinstance(e, lark.exceptions.UnexpectedInput):
        out["category"] = _category(e, s, parse_fn)
    elif isinstance(e, _Timeout):
        out["category"] = "timeout"
    else:
        out["category"] = "internal"
        out["detail"] = str(e)[:120]
    return out


# ============================================================================ ambiguity


def _norm(name: str) -> str:
    return name[1:] if re.fullmatch(r"\\[A-Za-z]+", name) else name


def _unbrace(node):
    """The content of a ``{...}`` group, else the node."""
    if isinstance(node, Tree) and node.data == "group_curly_parentheses" and len(node.children) == 3:
        return node.children[1]
    return node


def _leftmost_token(node):
    while isinstance(node, Tree):
        if not node.children:
            return None
        node = node.children[0]
    return node


def _application_flags(node, bodies) -> tuple[set[str], set[str]]:
    """(symbols applied as functions, symbols multiplied by a following parenthesized group)."""
    fun, prod = set(), set()
    if isinstance(node, Token):
        return fun, prod
    if node.data == "function_applied":
        fun.add(_norm(symbol_name(node.children[0], bodies)))
    elif node.data == "adjacent_expressions" and len(node.children) == 2:
        first, second = node.children
        lt = _leftmost_token(second)
        if lt is not None and lt.type == "L_PAREN":
            if (isinstance(first, Token) and first.type in ("SYMBOL", "GREEK_SYMBOL_WITH_PRIMES")) or (
                    isinstance(first, Tree) and first.data == "sub_symbol"):
                prod.add(_norm(symbol_name(first, bodies)))
            elif isinstance(first, Tree) and first.data == "superscript" and len(first.children) == 3:
                # F^{-1}(p): inverse-function notation, read silently as a product by the grammar
                base, _c, exp = first.children
                if tree_canonical(_unbrace(exp), bodies) == "-1" and (
                        (isinstance(base, Token) and base.type in ("SYMBOL", "GREEK_SYMBOL_WITH_PRIMES"))
                        or (isinstance(base, Tree) and base.data == "sub_symbol")):
                    prod.add(_norm(symbol_name(base, bodies)))
    if node.data != "_ambig":
        for c in node.children:
            f, p = _application_flags(c, bodies)
            fun |= f
            prod |= p
    return fun, prod


class _Resolver:
    def __init__(self, mc: MacroClass, context: dict):
        self.mc = mc
        self.bodies = mc.table()
        self.functions = {_norm(x) for x in context.get("functions", ())} | set(KNOWN_FUNCTIONS)
        self.variables = {_norm(x) for x in context.get("variables", ())}
        self.notes: list[str] = []
        self.unresolved = 0

    def declare_definitions(self, tree) -> None:
        """``g(x) = ...``: the left side applies g to symbols, so g is a function here."""
        for node in tree.iter_subtrees():
            if node.data not in ("eq", "rel_chain") or not node.children:
                continue
            left = node.children[0]
            alts = left.children if isinstance(left, Tree) and left.data == "_ambig" else [left]
            for a in alts:
                if isinstance(a, Tree) and a.data == "function_applied":
                    args = [c for c in leaves(a.children[2]) if c.type not in ("COMMA",)]
                    if args and all(t.type in ("SYMBOL", "GREEK_SYMBOL_WITH_PRIMES") for t in args):
                        name = _norm(symbol_name(a.children[0], self.bodies))
                        if name not in self.variables:
                            self.functions.add(name)
                            self.notes.append(f"{name} declared a function by its definition")

    def lone_symbol_formula(self, node):
        """any_value over [formula(symbol), set_named(symbol)] -> the formula reading."""
        if not (isinstance(node, Tree) and node.data == "_ambig"):
            return None
        forms = [a for a in node.children if isinstance(a, Tree) and a.data == "any_value"
                 and isinstance(a.children[0], Tree) and a.children[0].data == "formula"]
        sets = [a for a in node.children if isinstance(a, Tree) and a.data == "any_value"
                and isinstance(a.children[0], Tree) and a.children[0].data == "set_named"]
        if len(forms) == 1 and sets and len(forms) + len(sets) == len(node.children):
            self.notes.append("a lone symbol: read as a formula (a named set needs a set position)")
            return forms[0]
        members = [a for a in node.children if isinstance(a, Tree) and a.data == "any_value"
                   and isinstance(a.children[0], Tree) and a.children[0].data == "member"]
        lists = [a for a in node.children if isinstance(a, Tree) and a.data == "any_value"
                 and isinstance(a.children[0], Tree) and a.children[0].data == "value_list"]
        if len(members) == 1 and lists and len(members) + len(lists) == len(node.children):
            self.notes.append("a comma list before \\in: every listed element is a member")
            return members[0]
        return None

    def admissible(self, alt) -> bool:
        fun, prod = _application_flags(alt, self.bodies)
        return fun <= self.functions and prod <= self.variables

    def _value(self, alt):
        try:
            return transform(alt, self.mc, self.functions)
        except Exception:  # noqa: BLE001
            return None

    def resolve(self, node):
        if isinstance(node, Token):
            return node
        children = [self.resolve(c) for c in node.children]
        if node.data != "_ambig":
            return Tree(node.data, children, node.meta)
        keep = [a for a in children if self.admissible(a)]
        if len(keep) == 1:
            return keep[0]
        cands = keep or children
        vals = [self._value(a) for a in cands]
        if all(v is not None for v in vals) and all(v == vals[0] for v in vals[1:]):
            return cands[0]
        self.unresolved += 1
        fun = set().union(*(_application_flags(a, self.bodies)[0] for a in children))
        prod = set().union(*(_application_flags(a, self.bodies)[1] for a in children))
        what = []
        if fun or prod:
            what.append(f"application or product: {', '.join(sorted(fun | prod))}")
        self.notes.append("unresolved ambiguity (" + ("; ".join(what) or f"{len(cands)} readings") + ")")
        return Tree("_ambig", cands, node.meta)

    def residual_products(self, node) -> set[str]:
        """Product readings of ``symbol(...)`` with an undeclared symbol, left in the tree."""
        _, prod = _application_flags(node, self.bodies)
        return prod - self.variables


# ============================================================================ parse


def _detect(tree) -> str | None:
    node = tree
    if node.data == "_ambig":
        kinds = {_detect(c) for c in node.children}
        return kinds.pop() if len(kinds) == 1 else "ambiguous"
    if node.data == "any_value":
        node = node.children[0]
        if isinstance(node, Tree) and node.data == "_ambig":
            kinds = {_detect(Tree("any_value", [c])) for c in node.children}
            return kinds.pop() if len(kinds) == 1 else "ambiguous"
    if isinstance(node, Tree):
        if node.data in ("formula", "relation", "member"):
            return node.data
        if node.data == "value_list":
            return "list"
        if node.data in _SET_ROOTS:
            return "set_expr"
    return None


def _bare_interval(tree) -> bool:
    node = tree.children[0] if tree.data == "any_value" else tree
    return isinstance(node, Tree) and node.data == "interval"


_CACHE: dict[tuple, MathResult] = {}
_MC_CACHE: dict[str, MacroClass] = {}


def _macro_class(macros: dict | None) -> MacroClass:
    k = repr(sorted((macros or {}).items()))
    mc = _MC_CACHE.get(k)
    if mc is None:
        mc = _MC_CACHE[k] = classify(macros)
    return mc


def parse(latex: str, kind: str = "any_value", macros: dict | None = None, context: dict | None = None,
          mc: MacroClass | None = None) -> MathResult:
    """Parse ``latex`` (math delimiters optional) under the start symbol ``kind``.

    ``macros``: the rendition's macro table (``parse_detail.macros``; callers layer any fallback
    map under it). ``context``: ``{"functions": [...], "variables": [...]}`` for ambiguity.
    Results are cached per (latex, kind, macro table, context)."""
    kind = _KIND_ALIAS.get(kind, kind)
    if kind not in STARTS:
        raise ValueError(f"kind {kind!r} not in {STARTS}")
    mc = mc or _macro_class(macros)
    ctx = {k: sorted(v) for k, v in (context or {}).items() if v}
    ck = (latex, kind, mc.full_key, repr(sorted(ctx.items())))
    hit = _CACHE.get(ck)
    if hit is not None:
        return hit
    res = _parse(latex, kind, mc, ctx)
    _CACHE[ck] = res
    return res


def _parse(latex: str, kind: str, mc: MacroClass, ctx: dict) -> MathResult:
    raw = latex
    inner = strip_delimiters(raw)
    offset = raw.find(inner) if inner else 0
    res = MathResult(latex=inner, requested=kind, status="failed", mc=mc, context=ctx, offset=max(offset, 0),
                     source=raw)
    p = parser_for(mc)

    def parse_fn(s):
        return p.parse(s, start=kind)

    tree, partial = None, False
    try:
        with _limit(PARSE_SECONDS):
            tree = p.parse(inner, start=kind)
    except Exception as e:  # noqa: BLE001
        res.reason = _reason(e, inner, parse_fn)
        trimmed = inner.rstrip().rstrip(".,;").rstrip()
        if trimmed and trimmed != inner.strip():
            try:
                with _limit(PARSE_SECONDS):
                    tree = p.parse(trimmed, start=kind)
                partial = True
            except Exception:  # noqa: BLE001
                tree = None
    if tree is None:
        return res
    rv = _Resolver(mc, ctx)
    rv.declare_definitions(tree)
    tree = rv.lone_symbol_formula(tree) or tree
    tree = rv.resolve(tree)
    tree = rv.lone_symbol_formula(tree) or tree
    res.tree = tree
    res.kind = _detect(tree) if kind == "any_value" else kind
    res.notes = rv.notes
    res.occurrences = occurrences(tree, inner, mc)
    residual = rv.residual_products(tree) if not rv.unresolved else set()
    if residual:
        res.notes.append(f"product or application: {', '.join(sorted(residual))} (undeclared symbol before '(')")
    if rv.unresolved or residual:
        res.status = "ambiguous"
    elif kind == "any_value" and _bare_interval(tree):
        res.status = "ambiguous"
        res.notes.append("interval or pair: a bare (a, b) without a declared set kind")
    elif partial:
        res.status = "partial"
        res.notes.append("trailing punctuation dropped")
    else:
        res.status = "ok"
    res.reason = None if res.status != "failed" and not partial else res.reason
    return res


def canonical(result: MathResult) -> str:
    """D1 §6.2 canonical form for keys: the token form of the value as given, for every value
    (ADR-0012); it does not depend on whether or how the value parses."""
    bodies = result.mc.table() if result.mc else {}
    return tokens_canonical(result.source or result.latex, bodies)


def tree_token_agreement(result: MathResult) -> dict:
    """The tree/token property (D1 §6.2): for a parsed value, the tree printer's form against the
    token form. ``{"parsed", "agree", "tree", "token", "unexpanded"}``; ``agree`` is None when
    the value did not parse. A disagreement is reported, never resolved: the token form is the key."""
    bodies = result.mc.table() if result.mc else {}
    tok, unexpanded = token_form(result.source or result.latex, bodies)
    if result.tree is None:
        return {"parsed": False, "agree": None, "tree": None, "token": tok, "unexpanded": unexpanded}
    tree = tree_canonical(result.tree, bodies)
    return {"parsed": True, "agree": tree == tok, "tree": tree, "token": tok, "unexpanded": unexpanded}


def to_sympy(result: MathResult):
    if result.tree is None:
        raise NotParsed(result.reason)
    if result.status == "ambiguous":
        raise Ambiguous("; ".join(result.notes))
    funcs = {_norm(x) for x in result.context.get("functions", ())}
    try:
        value = transform(result.tree, result.mc, funcs)
    except lark.exceptions.VisitError as e:
        raise e.orig_exc if isinstance(e.orig_exc, (NotRepresentable, Ambiguous)) else NotRepresentable(
            f"{type(e.orig_exc).__name__}: {e.orig_exc}") from e
    if isinstance(value, sympy.Basic):  # D2 §12.1 math.constants: e (\pi has its own rule)
        value = value.xreplace({s: sympy.E for s in value.free_symbols if isinstance(s, sympy.Symbol) and s.name == "e"})
    return value


def bare_unit(result: MathResult) -> str | None:
    """Letters of a formula that is only a number followed by letters (``1 cm`` -> ``"cm"``),
    which the grammar reads as a product (1·c·m); the caller decides whether they name a unit."""
    if result.tree is None:
        return None
    node = result.tree
    while isinstance(node, Tree) and node.data in ("formula", "any_value") and len(node.children) == 1:
        node = node.children[0]
    if not (isinstance(node, Tree) and node.data == "adjacent_expressions"):
        return None
    toks = leaves(node)
    if not toks or toks[0].type != "number" and not (isinstance(node.children[0], Tree) and node.children[0].data == "number"):
        return None
    rest = toks[1:]
    if rest and all(t.type == "SYMBOL" and len(str(t)) == 1 for t in rest):
        return "".join(str(t) for t in rest)
    return None


# ============================================================================ occurrences


_SYMBOL_TOKENS = ("SYMBOL", "GREEK_SYMBOL_WITH_PRIMES")
_SKIP_INSIDE = {"op_name", "multi_letter_symbol"}


def occurrences(tree, source: str, mc: MacroClass) -> list[Occurrence]:
    bodies = mc.table()
    out: dict[tuple, Occurrence] = {}

    def text(n):
        return tree_canonical(_unbrace(n), bodies)

    def add(node, sup=None, parent=None):
        if isinstance(node, Token):
            name, base, sub = tree_canonical(node, bodies), tree_canonical(node, bodies), None
            st, en = node.start_pos, node.end_pos
        elif node.data == "sub_symbol":
            base_tok, _us, arg = node.children
            base = tree_canonical(base_tok, bodies)
            sub_node = Tree("x", arg.children[1:-1]) if isinstance(arg, Tree) and arg.data == "script_group" else arg
            sub = tree_canonical(sub_node, bodies)
            name = tree_canonical(node, bodies)
            st, en = node.meta.start_pos, node.meta.end_pos
        else:  # styled, multi_letter_symbol
            name = base = tree_canonical(node, bodies)
            sub = None
            st, en = node.meta.start_pos, node.meta.end_pos
        key = (st, en, name)
        if key not in out:
            out[key] = Occurrence(name, base, sub, sup, st, en, constant=(name in CONSTANTS and sub is None),
                                  in_subscript_of=parent)

    def walk(node, parent_sub=None):
        if isinstance(node, Token):
            if node.type in _SYMBOL_TOKENS:
                add(node, parent=parent_sub)
            return
        d = node.data
        if d in _SKIP_INSIDE:
            if d == "multi_letter_symbol":
                add(node, parent=parent_sub)
            return
        if d == "superscript" and len(node.children) >= 3:
            b = node.children[0]
            exp = node.children[2] if len(node.children) == 3 else node.children[3]
            if (isinstance(b, Token) and b.type in _SYMBOL_TOKENS) or (isinstance(b, Tree) and b.data in ("sub_symbol", "styled")):
                if isinstance(b, Tree) and b.data == "sub_symbol":
                    add(b, sup=text(exp), parent=parent_sub)
                    walk(b.children[2], parent_sub=tree_canonical(b, bodies))
                elif isinstance(b, Tree):
                    add(b, sup=text(exp), parent=parent_sub)
                else:
                    add(b, sup=text(exp), parent=parent_sub)
                walk(exp, parent_sub)
                return
        if d == "sup_sub":
            base, _c, exp, us, arg = node.children
            st = Tree("sub_symbol", [base, us, arg], node.meta)
            add(st, sup=text(exp), parent=parent_sub)
            walk(arg, parent_sub=tree_canonical(st, bodies))
            walk(exp, parent_sub)
            return
        if d == "sub_symbol":
            add(node, parent=parent_sub)
            walk(node.children[2], parent_sub=tree_canonical(node, bodies))
            return
        if d == "styled":
            add(node, parent=parent_sub)
            return
        if d == "pi_constant":
            tok = node.children[0]
            out[(tok.start_pos, tok.end_pos, "\\pi")] = Occurrence("\\pi", "\\pi", None, None, tok.start_pos, tok.end_pos, constant=True)
            return
        for c in node.children:
            walk(c, parent_sub)

    walk(tree)
    return sorted(out.values(), key=lambda o: (o.start, o.end))


def occurrences_in_span(text: str, start: int, end: int, macros: dict | None = None,
                        context: dict | None = None) -> tuple[MathResult, list[Occurrence]]:
    """Symbol occurrences of the math span ``text[start:end]`` (delimiters included or not),
    with offsets into ``text``. For M13 (D4): binding sites and scopes from symbol positions."""
    span = text[start:end]
    r = parse(span, "any_value", macros=macros, context=context)
    base = start + r.offset
    occ = [Occurrence(o.name, o.base, o.sub, o.sup, o.start + base, o.end + base, o.constant, o.in_subscript_of)
           for o in r.occurrences]
    return r, occ
