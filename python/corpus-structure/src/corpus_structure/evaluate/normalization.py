"""Pure canonical value and condition forms used by scientific comparison.

Reference equivalence is supplied by the evaluator; no storage key scheme or candidate
keying context participates in value comparison.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from typing import Any, assert_never

from pydantic import MISSING

from corpus_structure.core.canonical import canonical_json
from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.tex import symbol_form, token_form
from corpus_structure.core.values import (
    AuthoredAnd,
    AuthoredCondition,
    AuthoredEnumValue,
    AuthoredForall,
    AuthoredNot,
    AuthoredOr,
    AuthoredPhrase,
    AuthoredPhraseNode,
    AuthoredUnsupportedNode,
    AuthoredValue,
    BoolValue,
    ClaimNode,
    CmpNode,
    DateValue,
    EntityRef,
    Formula,
    IntervalValue,
    MemberNode,
    NumberValue,
    PredNode,
    SetValue,
    StoredAnd,
    StoredCondition,
    StoredEnumValue,
    StoredForall,
    StoredNot,
    StoredOr,
    StoredPhrase,
    StoredPhraseNode,
    StoredUnsupportedNode,
    StoredValue,
    TextValue,
)
from corpus_structure.core.vocab import CONVERSE_REWRITTEN, SYMMETRIC_RELATION, CaseRule, Relation
from corpus_structure.semantic.label_normalization import collapse, text_form

Json = Any
type Value = AuthoredValue | StoredValue
type Condition = AuthoredCondition | StoredCondition


def canonical_value(
    value: EntityRef | Value,
    macros: Mapping[str, MacroDef],
    resolve: Callable[[str], str],
    case: CaseRule = CaseRule.FOLD,
) -> Json:
    """The key form of a value or entity reference (JSON), per D1 §6.2; text and phrases under
    the declared case policy."""
    match value:
        case EntityRef(ref=ref):
            return {"key": resolve(ref)}
        case TextValue(v=v):
            return {"t": "text", "v": text_form(v, case)}
        case NumberValue():
            out: Json = {"t": "number", "v": value.v}
            if value.unit is not MISSING:
                out["unit"] = collapse(value.unit)
            if value.basis is not MISSING:
                out["basis"] = collapse(value.basis)
            return out
        case Formula(latex=latex) | SetValue(latex=latex):
            return {"t": value.t, "latex": token_form(latex, macros)}
        case IntervalValue():
            interval: Json = {"t": "interval"}
            if value.start is not MISSING:
                interval["start"] = canonical_value(value.start, macros, resolve)
            if value.end is not MISSING:
                interval["end"] = canonical_value(value.end, macros, resolve)
            if value.start_incl is not MISSING:
                interval["start_incl"] = value.start_incl
            if value.end_incl is not MISSING:
                interval["end_incl"] = value.end_incl
            return interval
        case AuthoredPhrase(text=text) | StoredPhrase(text=text):
            return {"t": "phrase", "text": text_form(text, case)}
        case BoolValue(v=v):
            return {"t": "bool", "v": v}
        case StoredEnumValue(enum=enum, v=v):
            return {"t": "enum", "enum": enum, "v": v}
        case AuthoredEnumValue():
            raise TypeError(
                f"the authored enum value {value.enum}.{value.v} names its enum locally; keys read "
                "the stored form, which names it prefixed (X2-01)"
            )
        case DateValue(v=v):
            return {"t": "date", "v": v}
        case _:
            assert_never(value)


def _parts(node: Condition) -> tuple[tuple[Condition, ...], tuple[EntityRef | Value, ...]]:
    """A node's child conditions and its value positions: the one structural dispatch."""
    match node:
        case (
            AuthoredAnd(args=args)
            | StoredAnd(args=args)
            | AuthoredOr(args=args)
            | StoredOr(args=args)
        ):
            return args, ()
        case AuthoredNot(arg=arg) | StoredNot(arg=arg):
            return (arg,), ()
        case AuthoredForall(set=set_, body=body) | StoredForall(set=set_, body=body):
            return (body,), (set_,)
        case ClaimNode():
            return (), ()
        case MemberNode(x=x, set=set_):
            return (), (x, set_)
        case CmpNode(lhs=lhs, rhs=rhs):
            return (), (lhs, rhs)
        case PredNode(args=pred_args):
            return (), pred_args
        case (
            AuthoredPhraseNode()
            | StoredPhraseNode()
            | AuthoredUnsupportedNode()
            | StoredUnsupportedNode()
        ):
            return (), ()
        case _:
            assert_never(node)


def condition_nodes(node: Condition) -> Iterator[Condition]:
    """Every node of a condition tree, children before their parent, left to right."""
    children, _ = _parts(node)
    for child in children:
        yield from condition_nodes(child)
    yield node


def claim_refs(node: Condition) -> list[str]:
    """The claim refs a condition tree references, in tree order."""
    return [n.ref for n in condition_nodes(node) if isinstance(n, ClaimNode)]


def _sort(items: Iterable[Json]) -> list[Json]:
    return sorted(items, key=canonical_json)


def canonical_condition(
    node: Condition,
    macros: Mapping[str, MacroDef],
    resolve: Callable[[str], str],
    symmetric: frozenset[str] = frozenset(),
) -> Json | None:
    """The D1 §7 canonical form of a condition tree, bottom-up; `None` is no condition."""
    done: dict[int, Json | None] = {}

    def value(v: EntityRef | Value) -> Json:
        return canonical_value(v, macros, resolve)

    for n in condition_nodes(node):  # children first, so each child's form is ready
        done[id(n)] = _canonical_node(n, done, value, resolve, symmetric, macros)
    return done[id(node)]


def _canonical_node(
    n: Condition,
    done: Mapping[int, Json | None],
    value: Callable[[EntityRef | Value], Json],
    resolve: Callable[[str], str],
    symmetric: frozenset[str],
    macros: Mapping[str, MacroDef],
) -> Json | None:
    match n:
        case (
            AuthoredAnd(op=op, args=args)
            | StoredAnd(op=op, args=args)
            | AuthoredOr(op=op, args=args)
            | StoredOr(op=op, args=args)
        ):
            flat: list[Json] = []
            for child in args:
                c = done[id(child)]
                if c is None:
                    continue
                flat.extend(c["args"] if c["op"] == op else [c])
            unique = {canonical_json(a): a for a in flat}  # identical args once
            if not unique:
                return None
            if len(unique) == 1:
                return next(iter(unique.values()))
            return {"op": op, "args": [unique[k] for k in sorted(unique)]}
        case AuthoredNot(arg=arg) | StoredNot(arg=arg):
            inner = done[id(arg)]
            return None if inner is None else {"op": "not", "arg": inner}
        case ClaimNode(ref=ref):
            return {"op": "claim", "ref": resolve(ref)}
        case MemberNode(x=x, set=set_):
            return {"op": "member", "x": value(x), "set": value(set_)}
        case CmpNode(rel=rel, lhs=lhs, rhs=rhs):
            if rel in CONVERSE_REWRITTEN:  # > as <, >= as <=, the sides swapped
                rel, lhs, rhs = Relation(rel.replace(">", "<")), rhs, lhs
            sides = [value(lhs), value(rhs)]
            if rel in SYMMETRIC_RELATION:  # operands in canonical order
                sides = _sort(sides)
            return {"op": "cmp", "rel": rel, "lhs": sides[0], "rhs": sides[1]}
        case PredNode(name=name, args=pred_args):
            canonical_args = [value(a) for a in pred_args]
            if name in symmetric:
                canonical_args = _sort(canonical_args)
            return {"op": "pred", "name": name, "args": canonical_args}
        case (
            AuthoredForall(var=var, set=set_, body=body)
            | StoredForall(var=var, set=set_, body=body)
        ):
            inner = done[id(body)]
            if inner is None:
                return None
            return {"op": "forall", "var": symbol_form(var, macros), "set": value(set_),
                    "body": inner}  # fmt: skip
        case (
            AuthoredPhraseNode(op=op, text=text)
            | StoredPhraseNode(op=op, text=text)
            | AuthoredUnsupportedNode(op=op, text=text)
            | StoredUnsupportedNode(op=op, text=text)
        ):
            return {"op": op, "text": text_form(text)}
        case _:
            assert_never(n)


def expressions(value: EntityRef | Value | Condition) -> Iterator[Formula | SetValue]:
    """Every formula and set inside a value or a condition tree (through `condition_nodes`)."""
    match value:
        case Formula() | SetValue():
            yield value
        case IntervalValue():
            for bound in (value.start, value.end):
                if isinstance(bound, Formula):
                    yield bound
        case (
            TextValue() | NumberValue() | BoolValue() | AuthoredEnumValue() | StoredEnumValue()
            | DateValue()
            | AuthoredPhrase() | StoredPhrase() | EntityRef()
        ):  # fmt: skip
            return
        case (
            AuthoredAnd() | AuthoredOr() | AuthoredNot() | AuthoredForall() | StoredAnd()
            | StoredOr() | StoredNot() | StoredForall() | ClaimNode() | MemberNode() | CmpNode()
            | PredNode() | AuthoredPhraseNode() | StoredPhraseNode()
            | AuthoredUnsupportedNode() | StoredUnsupportedNode()
        ):  # fmt: skip
            for node in condition_nodes(value):
                for v in _parts(node)[1]:
                    yield from expressions(v)
        case _:
            assert_never(value)
