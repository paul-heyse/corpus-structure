"""Parse tree -> SymPy, as a subclass of SymPy's own ``TransformToSymPyExpr`` (ADR-0009).

SymPy's methods handle the shipped rules; the methods here handle the extension's rules:
operators -> undefined ``Function``; sets -> ``Reals`` / ``Naturals0`` / ``Interval`` /
``Complement`` / ``FiniteSet`` / ``ConditionSet`` / ``ProductSet``; ``member`` -> ``Contains``;
relations -> ``Rel`` (chains -> ``And``). Constructs SymPy cannot represent (``\\pm``, ellipses,
named sets, subset relations, symbolic set powers) raise ``NotRepresentable``.

Symbols with subscripts are named from their source structure before transformation
(``\\sigma_{X_1}`` -> ``sigma_{X_1}``, ``X_{(n)}`` -> ``X_{(n)}``, ``X_1`` -> ``X_{1}`` as SymPy
names it), so subscripts are never lost or merged.
"""

from __future__ import annotations

import sympy
from lark import Token, Tree
from sympy.parsing.latex.lark.transformer import TransformToSymPyExpr

from .build import MacroClass
from .printer import tree_canonical

KNOWN_FUNCTIONS = {"Gamma": sympy.gamma}  # a symbol applied as a function by default (context)


class NotRepresentable(Exception):
    """The construct parses but has no SymPy value."""


def _base_name(tok: Token) -> str:
    s = str(tok)
    if s.startswith("\\"):
        s = s[1:]
        if s.startswith("var") and len(s) > 3:  # as SymPy: varphi -> phi
            s = s[3:]
    return s


def symbol_name(node, bodies: dict[str, str]) -> str:
    """Name of a symbol node: a letter token, or a ``sub_symbol`` tree."""
    if isinstance(node, Token):
        return _base_name(node)
    if node.data == "sub_symbol":
        base, _us, arg = node.children
        if isinstance(arg, Tree) and arg.data == "script_group":
            sub = tree_canonical(Tree("x", arg.children[1:-1]), bodies)
        else:
            sub = tree_canonical(arg, bodies)
        return f"{_base_name(base)}_{{{sub}}}"
    return tree_canonical(node, bodies)


def name_symbols(node, bodies: dict[str, str]):
    """Replace ``sub_symbol`` / ``sup_sub`` subtrees by ``NAMED_SYMBOL`` tokens (top-down)."""
    if isinstance(node, Token):
        return node
    if node.data == "sub_symbol":
        return Token("NAMED_SYMBOL", symbol_name(node, bodies))
    if node.data == "sup_sub":  # base ^ exp _ sub  ->  superscript(base_sub, ^, exp)
        base, caret, exp, us, arg = node.children
        named = Token("NAMED_SYMBOL", symbol_name(Tree("sub_symbol", [base, us, arg]), bodies))
        return Tree("superscript", [named, caret, name_symbols(exp, bodies)])
    return Tree(node.data, [name_symbols(c, bodies) for c in node.children], node.meta)


def _args(x) -> list:
    if isinstance(x, (list, tuple)):
        return list(x)
    if isinstance(x, filter):
        return list(x)
    return [x]


class ToSympy(TransformToSymPyExpr):
    """Extension-aware transformer; ``mc`` is the macro classification of the parse."""

    def __init__(self, mc: MacroClass, functions: set[str] | None = None):
        super().__init__()
        self.mc = mc
        self.functions = set(functions or ())

    # ---- symbols and constants
    def NAMED_SYMBOL(self, tok):
        return sympy.Symbol(str(tok))

    def pi_constant(self, tokens):
        return sympy.pi

    def styled(self, tokens):
        inner = [t for t in tokens if not isinstance(t, Token) or t.type not in ("CMD_STYLE", "GEN_STYLE", "CMD_MATHRM", "L_BRACE", "R_BRACE")]
        return inner[0]

    def ellipsis(self, tokens):
        raise NotRepresentable("ellipsis")

    def plus_minus(self, tokens):
        raise NotRepresentable("\\pm")

    def function_applied(self, tokens):
        name = str(tokens[0])
        f = KNOWN_FUNCTIONS.get(name)
        return f(*_args(tokens[2])) if f else sympy.Function(name)(*_args(tokens[2]))

    # ---- operators
    def op_name(self, tokens):
        if len(tokens) == 1:
            return self.mc.op(str(tokens[0])) or str(tokens[0]).lstrip("\\")
        return str(tokens[2])

    def conditional(self, tokens):
        return sympy.Function("Given")(*_args(tokens[0]), *_args(tokens[2]))


    def op_applied(self, tokens):
        name, args = tokens[0], tokens[2]
        return sympy.Function(name)(*_args(args))

    # ---- sets
    def set_const(self, tokens):
        if isinstance(tokens[0], Token) and tokens[0].type == "GEN_SET":
            letter = self.mc.set_letter(str(tokens[0]))
            rest = tokens[1:]
        else:  # \mathbb { X }
            letter = str(tokens[2])
            rest = tokens[4:]
        base = {"R": sympy.S.Reals, "N": sympy.S.Naturals0, "Z": sympy.S.Integers,
                "Q": sympy.S.Rationals, "C": sympy.S.Complexes}[letter]
        i = 0
        if i < len(rest) and isinstance(rest[i], str) and rest[i] in ("+", "-"):
            sign = rest[i]
            i += 1
            if letter == "C":
                raise NotRepresentable("signed complex numbers")
            half = sympy.Interval.open(0, sympy.oo) if sign == "+" else sympy.Interval.open(-sympy.oo, 0)
            base = sympy.S.Naturals if (sign == "+" and letter in ("N", "Z")) else sympy.Intersection(base, half)
        if i < len(rest):  # ^ exponent
            n = rest[i + 1]
            if not (isinstance(n, sympy.Integer) and n > 0):
                raise NotRepresentable("set power with a symbolic exponent")
            base = sympy.ProductSet(*([base] * int(n)))
        return base

    def set_sign(self, tokens):
        t = [x for x in tokens if isinstance(x, Token) and x.type in ("ADD", "SUB")]
        return "+" if t[0].type == "ADD" else "-"

    def interval(self, tokens):
        lo, hi = tokens[1], tokens[3]
        return sympy.Interval(lo, hi, left_open=str(tokens[0]) == "(", right_open=str(tokens[4]) == ")")

    def set_list(self, tokens):
        return sympy.FiniteSet(*_args(tokens[1]))

    def set_builder(self, tokens):
        head, cond = tokens[1], tokens[3:-1]
        conds = [c for c in cond if not isinstance(c, Token)]
        if isinstance(head, sympy.Contains):
            var, base = head.args
        else:
            var, base = head, sympy.S.Reals
        if not isinstance(var, sympy.Symbol):
            raise NotRepresentable("set builder over an expression")
        return sympy.ConditionSet(var, sympy.And(*conds), base)

    def empty_set(self, tokens):
        return sympy.S.EmptySet

    def set_named(self, tokens):
        raise NotRepresentable("named set")

    def set_group(self, tokens):
        return tokens[1]

    def set_minus(self, tokens):
        return sympy.Complement(tokens[0], tokens[2])

    def set_union(self, tokens):
        return sympy.Union(tokens[0], tokens[2])

    def set_intersection(self, tokens):
        return sympy.Intersection(tokens[0], tokens[2])

    def set_product(self, tokens):
        return sympy.ProductSet(tokens[0], tokens[2])

    # ---- typed starts and relations
    def member(self, tokens):
        xs, op, s = _args(tokens[0]), tokens[1], tokens[2]
        parts = [sympy.Contains(x, s) for x in xs]
        out = sympy.And(*parts) if len(parts) > 1 else parts[0]
        return sympy.Not(out) if op.type == "CMD_NOTIN" else out

    def rel_chain(self, tokens):
        ops = {"LT": sympy.Lt, "LTE": sympy.Le, "GT": sympy.Gt, "GTE": sympy.Ge, "EQUAL": sympy.Eq, "NOT_EQUAL": sympy.Ne}
        terms, opers = tokens[0::2], tokens[1::2]
        return sympy.And(*(ops[o.type](terms[i], terms[i + 1]) for i, o in enumerate(opers)))

    def cond_list(self, tokens):
        return sympy.And(*[t for t in tokens if not isinstance(t, Token)])

    def _no_value(self, tokens, what="construct"):
        raise NotRepresentable(what)

    def norm(self, tokens):
        raise NotRepresentable("norm")

    def lim_infsup(self, tokens):
        raise NotRepresentable("liminf / limsup")

    def extremum(self, tokens):
        raise NotRepresentable("sup / inf / indexed max, min")

    def set_integral(self, tokens):
        raise NotRepresentable("integral over a set")

    def set_indexed(self, tokens):
        raise NotRepresentable("sum, product or integral indexed by a set")

    def wedge_vee(self, tokens):
        raise NotRepresentable("wedge / vee")

    def set_event(self, tokens):
        raise NotRepresentable("event set")

    def approach(self, tokens):
        raise NotRepresentable("convergence statement")

    def other_rel(self, tokens):
        raise NotRepresentable(f"relation {tokens[1]}")

    def value_list(self, tokens):
        return sympy.Tuple(*[t for t in tokens if not isinstance(t, Token)])

    def subset_rel(self, tokens):
        raise NotRepresentable("subset relation")

    def formula(self, tokens):
        return tokens[0]

    def relation(self, tokens):
        return tokens[0]

    def any_value(self, tokens):
        return tokens[0]

    def script_group(self, tokens):  # only reached outside sub_symbol (never in practice)
        return _args(tokens[1])


def transform(tree: Tree, mc: MacroClass, functions: set[str] | None = None):
    """Raises ``lark.exceptions.VisitError`` wrapping ``NotRepresentable`` (``api.to_sympy`` unwraps)."""
    bodies = mc.table()
    return ToSympy(mc, functions).transform(name_symbols(tree, bodies))
