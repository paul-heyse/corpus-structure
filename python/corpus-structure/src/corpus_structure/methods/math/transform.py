"""The parse tree to SymPy (ingest and math §3.7 "SymPy"; D4 M11; ADR-0012).

`ToSympy` subclasses SymPy's `TransformToSymPyExpr`, the documented customization point. SymPy's
methods handle the shipped rules; the methods here handle the extension's: operators become an
undefined `Function`, sets `Reals`, `Naturals0`, `Interval`, `Complement`, `FiniteSet`,
`ConditionSet` or `ProductSet`, `member` becomes `Contains`, relations `Rel` (a chain `And`).
Constructs SymPy cannot represent (`\\pm`, ellipses, named sets, subset relations, symbolic set
powers, ...) raise `NotRepresentable`, and so does a sum or product with an operand that is not an
`Expr` (a set, a relation), instead of SymPy's deprecated path. The S5 rules with no method here
(tuples, maps, cases, ...) transform to trees: the ambiguity resolver compares readings by them,
and `to_sympy` refuses a value that holds one.

Symbols with subscripts are named from their source before transformation (`\\sigma_{X_1}` ->
`sigma_{X_1}`, `X_{(n)}` -> `X_{(n)}`, `X_1` -> `X_{1}` as SymPy names it), so a subscript is
never lost or merged.

`transform` raises `lark.exceptions.VisitError` around the transformer's own exceptions; the
grammar's `to_sympy` unwraps them.
"""

from __future__ import annotations

import hashlib
import warnings
from collections.abc import Callable, Mapping
from typing import Any

import sympy
from lark import Token, Tree
from sympy.parsing.latex.lark.transformer import TransformToSymPyExpr
from sympy.utilities.exceptions import SymPyDeprecationWarning

from corpus_structure.core.evidence import MacroDef
from corpus_structure.methods.math import _tree

# A symbol applied to a parenthesized argument is read as this function by default.
KNOWN_FUNCTIONS: Mapping[str, Callable[..., Any]] = {"Gamma": sympy.gamma}
_SET_LETTER = {
    "R": sympy.S.Reals,
    "N": sympy.S.Naturals0,
    "Z": sympy.S.Integers,
    "Q": sympy.S.Rationals,
    "C": sympy.S.Complexes,
}
_RELATIONS: Mapping[str, Callable[..., Any]] = {
    "LT": sympy.Lt,
    "LTE": sympy.Le,
    "GT": sympy.Gt,
    "GTE": sympy.Ge,
    "EQUAL": sympy.Eq,
    "NOT_EQUAL": sympy.Ne,
}


class NotRepresentable(Exception):
    """The construct parses but has no SymPy value."""


def bare(name: str) -> str:
    """A lone control word without its backslash (`\\Phi` -> `Phi`), as functions are declared."""
    if name.startswith("\\") and name[1:].isalpha():
        return name[1:]
    return name


def _base_name(base: _tree.Node, source: str, table: Mapping[str, MacroDef]) -> str:
    if isinstance(base, Token) and base.type in ("SYMBOL", "GREEK_SYMBOL_WITH_PRIMES"):
        name = str(base)
        if name.startswith("\\"):
            name = name[1:]
            if name.startswith("var") and len(name) > 3:  # as SymPy names it: varphi -> phi
                name = name[3:]
        return name
    return _tree.form(base, source, table)


def symbol_name(node: _tree.Node, source: str, table: Mapping[str, MacroDef]) -> str:
    """A symbol node's SymPy name: a letter token, or `sub_symbol` as `base_{sub}`."""
    if isinstance(node, Tree) and node.data == "sub_symbol":
        base, _underscore, argument = node.children
        sub = _tree.form(argument, source, table, braced=True)
        return f"{_base_name(base, source, table)}_{{{sub}}}"
    return _base_name(node, source, table)


def name_symbols(node: _tree.Node, source: str, table: Mapping[str, MacroDef]) -> _tree.Node:
    """Replace `sub_symbol` and `sup_sub` subtrees by `NAMED_SYMBOL` tokens, top-down."""
    if isinstance(node, Token):
        if node.type in {"SYMBOL", "GREEK_SYMBOL_WITH_PRIMES"}:
            return Token.new_borrow_pos("NAMED_SYMBOL", symbol_name(node, source, table), node)
        return node
    if node.data == "sub_symbol":
        return Token("NAMED_SYMBOL", symbol_name(node, source, table))
    if node.data == "sup_sub":  # base ^ exp _ sub  ->  superscript(base_sub, ^, exp)
        base, caret, exponent, underscore, argument = node.children
        sub = Tree("sub_symbol", [base, underscore, argument])
        named = Token("NAMED_SYMBOL", symbol_name(sub, source, table))
        return Tree("superscript", [named, caret, name_symbols(exponent, source, table)])
    children = [name_symbols(c, source, table) for c in node.children]
    return Tree(node.data, list(children), node.meta)


def _args(value: Any) -> list[Any]:
    if isinstance(value, list | tuple | filter):
        return list(value)
    return [value]


def _expr(*operands: Any) -> None:
    for operand in operands:
        if not isinstance(operand, sympy.Expr):
            raise NotRepresentable(f"arithmetic on a {type(operand).__name__}")


class ToSympy(TransformToSymPyExpr):
    """The extension-aware transformer; `sets` and `ops` are the macro classification's."""

    def __init__(
        self,
        sets: Mapping[str, str],
        ops: Mapping[str, str],
        symbol_factory: Callable[[str], Any] = sympy.Symbol,
        bound_symbols: Mapping[str, Any] | None = None,
        conventions: tuple[str, ...] = ("naturals-zero-1", "set-builder-real-domain-1"),
    ) -> None:
        super().__init__()
        self.sets = sets
        self.ops = ops
        self.symbol_factory = symbol_factory
        self.bound_symbols = bound_symbols or {}
        self.conventions = conventions

    # ---- arithmetic: operands must be expressions (no deprecated non-Expr Mul or Add)
    def add(self, tokens: list[Any]) -> Any:
        _expr(*(t for t in tokens if not isinstance(t, Token)))
        return super().add(tokens)

    def sub(self, tokens: list[Any]) -> Any:
        _expr(*(t for t in tokens if not isinstance(t, Token)))
        return super().sub(tokens)

    def mul(self, tokens: list[Any]) -> Any:
        _expr(tokens[0], tokens[2])
        return super().mul(tokens)

    def div(self, tokens: list[Any]) -> Any:
        _expr(tokens[0], tokens[2])
        return super().div(tokens)

    def adjacent_expressions(self, tokens: list[Any]) -> Any:
        if tokens[0] != sympy.Symbol("d") and not isinstance(tokens[0], tuple):
            _expr(tokens[0], tokens[1])
        return super().adjacent_expressions(tokens)

    # ---- symbols and constants
    def NAMED_SYMBOL(self, token: Token) -> Any:
        name = str(token)
        return self.bound_symbols[name] if name in self.bound_symbols else self.symbol_factory(name)

    def pi_constant(self, tokens: list[Any]) -> Any:
        return sympy.pi

    def styled(self, tokens: list[Any]) -> Any:
        skip = ("CMD_STYLE", "GEN_STYLE", "CMD_MATHRM", "L_BRACE", "R_BRACE")
        content = [t for t in tokens if not isinstance(t, Token) or t.type not in skip]
        return content[0]

    def ellipsis(self, tokens: list[Any]) -> Any:
        raise NotRepresentable("ellipsis")

    def plus_minus(self, tokens: list[Any]) -> Any:
        raise NotRepresentable("\\pm")

    def function_applied(self, tokens: list[Any]) -> Any:
        head = tokens[0]
        name = head.name if isinstance(head, sympy.Symbol) else str(head)
        # Source-scoped declarations have deterministic native identity. Preserve it
        # for callable construction as well as variable construction.
        if isinstance(head, sympy.Dummy):
            identity = hashlib.sha256(sympy.srepr(head).encode()).hexdigest()[:24]
            name = f"{name}@{identity}"
        known = KNOWN_FUNCTIONS.get(name)
        if known is not None:
            return known(*_args(tokens[2]))
        return sympy.Function(name)(*_args(tokens[2]))

    # ---- operators
    def op_name(self, tokens: list[Any]) -> Any:
        if len(tokens) == 1:
            first = str(tokens[0])
            return self.ops.get(first) or first.lstrip("\\")
        return str(tokens[2])

    def conditional(self, tokens: list[Any]) -> Any:
        return sympy.Function("Given")(*_args(tokens[0]), *_args(tokens[2]))

    def op_applied(self, tokens: list[Any]) -> Any:
        return sympy.Function(tokens[0])(*_args(tokens[2]))

    # ---- sets
    def set_const(self, tokens: list[Any]) -> Any:
        if isinstance(tokens[0], Token) and tokens[0].type == "GEN_SET":
            letter = self.sets[str(tokens[0])]
            rest = tokens[1:]
        else:  # \mathbb { X }
            letter = str(tokens[2])
            rest = tokens[4:]
        if letter == "N" and "naturals-zero-1" not in self.conventions:
            raise NotRepresentable("natural-number convention is not admitted")
        base = _SET_LETTER[letter]
        i = 0
        if i < len(rest) and isinstance(rest[i], str) and rest[i] in ("+", "-"):
            sign = rest[i]
            i += 1
            if letter == "C":
                raise NotRepresentable("signed complex numbers")
            half = (
                sympy.Interval.open(0, sympy.oo)
                if sign == "+"
                else sympy.Interval.open(-sympy.oo, 0)
            )
            if sign == "+" and letter in ("N", "Z"):
                base = sympy.S.Naturals
            else:
                base = sympy.Intersection(base, half)
        if i < len(rest):  # ^ exponent
            power = rest[i + 1]
            if not (isinstance(power, sympy.Integer) and power > 0):
                raise NotRepresentable("set power with a symbolic exponent")
            base = sympy.ProductSet(*([base] * int(power)))
        return base

    def set_sign(self, tokens: list[Any]) -> Any:
        signs = [x for x in tokens if isinstance(x, Token) and x.type in ("ADD", "SUB")]
        return "+" if signs[0].type == "ADD" else "-"

    def interval(self, tokens: list[Any]) -> Any:
        return sympy.Interval(
            tokens[1],
            tokens[3],
            left_open=str(tokens[0]) == "(",
            right_open=str(tokens[4]) == ")",
        )

    def set_list(self, tokens: list[Any]) -> Any:
        return sympy.FiniteSet(*_args(tokens[1]))

    def set_builder(self, tokens: list[Any]) -> Any:
        head = tokens[1]
        conditions = [c for c in tokens[3:-1] if not isinstance(c, Token)]
        if isinstance(head, sympy.Contains):
            variable, base = head.args
        else:
            if "set-builder-real-domain-1" not in self.conventions:
                raise NotRepresentable("unqualified set-builder domain is not admitted")
            variable, base = head, sympy.S.Reals
        if not isinstance(variable, sympy.Symbol):
            raise NotRepresentable("set builder over an expression")
        return sympy.ConditionSet(variable, sympy.And(*conditions), base)

    def empty_set(self, tokens: list[Any]) -> Any:
        return sympy.S.EmptySet

    def set_named(self, tokens: list[Any]) -> Any:
        raise NotRepresentable("named set")

    def set_group(self, tokens: list[Any]) -> Any:
        return tokens[1]

    def set_minus(self, tokens: list[Any]) -> Any:
        return sympy.Complement(tokens[0], tokens[2])

    def set_union(self, tokens: list[Any]) -> Any:
        return sympy.Union(tokens[0], tokens[2])

    def set_intersection(self, tokens: list[Any]) -> Any:
        return sympy.Intersection(tokens[0], tokens[2])

    def set_product(self, tokens: list[Any]) -> Any:
        return sympy.ProductSet(tokens[0], tokens[2])

    # ---- typed starts and relations
    # A source relation is formal syntax. SymPy's defaults may launch assumptions/evalf
    # (including numerical integration); explicit scientific assessment owns evaluation.
    def eq(self, tokens: list[Any]) -> Any:
        return sympy.Eq(tokens[0], tokens[2], evaluate=False)

    def ne(self, tokens: list[Any]) -> Any:
        return sympy.Ne(tokens[0], tokens[2], evaluate=False)

    def lt(self, tokens: list[Any]) -> Any:
        return sympy.Lt(tokens[0], tokens[2], evaluate=False)

    def lte(self, tokens: list[Any]) -> Any:
        return sympy.Le(tokens[0], tokens[2], evaluate=False)

    def gt(self, tokens: list[Any]) -> Any:
        return sympy.Gt(tokens[0], tokens[2], evaluate=False)

    def gte(self, tokens: list[Any]) -> Any:
        return sympy.Ge(tokens[0], tokens[2], evaluate=False)

    def member(self, tokens: list[Any]) -> Any:
        elements, operator, target = _args(tokens[0]), tokens[1], tokens[2]
        parts = [sympy.Contains(x, target) for x in elements]
        out = sympy.And(*parts) if len(parts) > 1 else parts[0]
        return sympy.Not(out) if operator.type == "CMD_NOTIN" else out

    def rel_chain(self, tokens: list[Any]) -> Any:
        terms, operators = tokens[0::2], tokens[1::2]
        if any(o.type not in _RELATIONS for o in operators):
            raise NotRepresentable("relation chain with a relation SymPy lacks")
        return sympy.And(
            *(
                _RELATIONS[o.type](terms[i], terms[i + 1], evaluate=False)
                for i, o in enumerate(operators)
            )
        )

    def cond_list(self, tokens: list[Any]) -> Any:
        return sympy.And(*[t for t in tokens if not isinstance(t, Token)])

    def value_list(self, tokens: list[Any]) -> Any:
        return sympy.Tuple(*[t for t in tokens if not isinstance(t, Token)])

    # ---- the I-R2 rules that parse but have no SymPy value (S5's rules without a method are
    # transformed to trees, compared as structure by the resolver and refused by `to_sympy`)
    def norm(self, tokens: list[Any]) -> Any:
        raise NotRepresentable("norm")

    def lim_infsup(self, tokens: list[Any]) -> Any:
        raise NotRepresentable("liminf / limsup")

    def extremum(self, tokens: list[Any]) -> Any:
        raise NotRepresentable("sup / inf / indexed max, min")

    def set_integral(self, tokens: list[Any]) -> Any:
        raise NotRepresentable("integral over a set")

    def set_indexed(self, tokens: list[Any]) -> Any:
        raise NotRepresentable("sum, product or integral indexed by a set")

    def wedge_vee(self, tokens: list[Any]) -> Any:
        raise NotRepresentable("wedge / vee")

    def set_event(self, tokens: list[Any]) -> Any:
        raise NotRepresentable("event set")

    def approach(self, tokens: list[Any]) -> Any:
        raise NotRepresentable("convergence statement")

    def other_rel(self, tokens: list[Any]) -> Any:
        raise NotRepresentable(f"relation {tokens[1]}")

    def subset_rel(self, tokens: list[Any]) -> Any:
        raise NotRepresentable("subset relation")

    def formula(self, tokens: list[Any]) -> Any:
        if len(tokens) == 1:
            return tokens[0]
        return Tree("formula", tokens)  # a tuple equation: compared as structure, no value

    def relation(self, tokens: list[Any]) -> Any:
        return tokens[0]

    def any_value(self, tokens: list[Any]) -> Any:
        return tokens[0]

    def script_group(self, tokens: list[Any]) -> Any:  # reached only outside sub_symbol
        return _args(tokens[1])


def _source_binders(tree: _tree.Node) -> tuple[_tree.Node, dict[str, Any]]:
    """Assign native bound identity at source-established Sum/Product/Integral/set binders.

    Body traversal carries lexical scope. Limits are outside it; a nested binder shadows
    its own body only. This runs before constructors can simplify assumed free symbols.
    """
    symbols: dict[str, Any] = {}

    def variable(node):
        return next((t for t in _tree.leaves(node) if t.type == "NAMED_SYMBOL"), None)

    def walk(node, environment):
        if isinstance(node, Token):
            if node.type == "NAMED_SYMBOL" and str(node) in environment:
                return Token.new_borrow_pos("NAMED_SYMBOL", environment[str(node)], node)
            return node
        declaration, body_indexes = None, set()
        if node.data in {"summation", "product"} and len(node.children) >= 3:
            declaration = variable(node.children[1])
            body_indexes = {2}
        elif node.data == "limit" and len(node.children) >= 4:
            declaration = variable(node.children[2])
            body_indexes = {len(node.children) - 1}
        elif (
            node.data == "normal_integral"
            and len(node.children) >= 3
            and any(
                isinstance(child, Token) and str(child) in {"_", "^"} for child in node.children
            )
        ):
            candidate = node.children[-1]
            if isinstance(candidate, Token) and candidate.type == "NAMED_SYMBOL":
                declaration = candidate
                # Native grammar places bound arguments before the integrand. Only
                # expression children after the last bound argument belong to the body.
                bound_end = 0
                for index, child in enumerate(node.children[:-2]):
                    if isinstance(child, Token) and str(child) in {"_", "^"}:
                        bound_end = index + 1
                body_indexes = set(range(bound_end + 1, len(node.children) - 2))
        elif node.data == "set_builder" and len(node.children) >= 4:
            declaration = variable(node.children[1])
            body_indexes = set(range(3, len(node.children) - 1))
        local = environment
        if declaration is not None:
            marker = f"@bound:{len(symbols)}:{declaration}"
            symbols[marker] = sympy.Dummy(str(declaration))
            local = {**environment, str(declaration): marker}
        children = []
        for index, child in enumerate(node.children):
            if child is declaration:
                children.append(walk(child, local))
            elif declaration is not None and (
                (index == 1 and node.data in {"summation", "product"})
                or (index == 2 and node.data == "limit")
            ):
                # Replace the declaration occurrence, not matching names in the bounds.
                def limits(part):
                    if part is declaration:
                        return walk(part, local)
                    if isinstance(part, Tree):
                        return Tree(part.data, [limits(c) for c in part.children], part.meta)
                    return walk(part, environment)

                children.append(limits(child))
            elif declaration is not None and index == 1 and node.data == "set_builder":

                def head(part):
                    if part is declaration:
                        return walk(part, local)
                    if isinstance(part, Tree):
                        return Tree(part.data, [head(c) for c in part.children], part.meta)
                    return walk(part, environment)

                children.append(head(child))
            else:
                children.append(walk(child, local if index in body_indexes else environment))
        return Tree(node.data, children, node.meta)

    return walk(tree, {}), symbols


def transform(
    tree: _tree.Node,
    source: str,
    table: Mapping[str, MacroDef],
    sets: Mapping[str, str],
    ops: Mapping[str, str],
    *,
    symbol_factory: Callable[[str], Any] = sympy.Symbol,
    conventions: tuple[str, ...] = ("naturals-zero-1", "set-builder-real-domain-1"),
) -> Any:
    """The SymPy value of `tree` (read from `source`); raises `VisitError` around failures.

    A path SymPy deprecates (a non-`Expr` operand of a product or sum reached through SymPy's own
    methods, such as a differential pair inside `\\frac`) raises `NotRepresentable` here instead
    of taking it, in production as under the tests' `-W error`.
    """
    named, bound_symbols = _source_binders(name_symbols(tree, source, table))
    with warnings.catch_warnings():
        warnings.simplefilter("error", SymPyDeprecationWarning)
        try:
            return ToSympy(sets, ops, symbol_factory, bound_symbols, conventions).transform(named)
        except SymPyDeprecationWarning as error:
            raise NotRepresentable(f"a path SymPy deprecates: {error}".splitlines()[0]) from error
