"""Mathematical span values, occurrences and relations shared by native kernels.

Source-view owners supply qualified spans and prepared readings. Historical rendition
adapters belong to test fixture interpretation, not current production acquisition.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Literal

from lark import Token, Tree

from corpus_structure.core.evidence import Segment
from corpus_structure.core.keys import symbol_form
from corpus_structure.core.values import Formula, SetValue, SymbolBinding
from corpus_structure.core.vocab import BindKind, MathKind, SegmentKind
from corpus_structure.methods.math import _tree
from corpus_structure.methods.math.grammar import (
    MathResult,
    Occurrence,
)

MATH_KINDS = frozenset({SegmentKind.MATH_INLINE, SegmentKind.MATH_DISPLAY})
_MATH_KIND = {
    "formula": MathKind.FORMULA,
    "relation": MathKind.RELATION,
    "member": MathKind.MEMBERSHIP,
    "set_expr": MathKind.SET,
    "list": MathKind.LIST,
}
_EQUALS = frozenset({"EQUAL"})


@dataclass(frozen=True, slots=True)
class MathSpan:
    segment: Segment
    latex: str  # the parse input
    offset: int  # canonical-text offset of latex[0]


@dataclass(frozen=True, slots=True)
class SpanReading:
    span: MathSpan
    result: MathResult
    prepared: object | None = None

    def __getstate__(self):
        # Preparation is operation/process owned. Transport finished source-shaped
        # readings without native handles, contexts or caches to a different owner.
        return self.span, self.result

    def __setstate__(self, state):
        object.__setattr__(self, "span", state[0])
        object.__setattr__(self, "result", state[1])
        object.__setattr__(self, "prepared", None)


def _free(result: MathResult) -> list[Occurrence]:
    return [o for o in result.occurrences if not o.constant and o.in_subscript_of is None]


# ============================================================================ M11


@dataclass(frozen=True, slots=True)
class SpanValue:
    segment: Segment
    value: Formula | SetValue
    kind: str | None  # the detected kind: formula | relation | member | set_expr | list | ambiguous
    parse_error: str | None  # the failure category, when the value did not parse whole

    @property
    def math_kind(self) -> MathKind | None:
        """The payload's `math_kind`: none when the value did not parse or its kind is ambiguous."""
        return _MATH_KIND.get(self.kind or "")


def formula_values(readings: Sequence[SpanReading]) -> list[SpanValue]:
    out = []
    for reading in readings:
        result, latex = reading.result, reading.span.latex
        symbols = {
            symbol_form(latex[o.start : o.end], result.macros): SymbolBinding(
                bind=BindKind.UNRESOLVED
            )
            for o in _free(result)
        }
        value: Formula | SetValue
        if result.kind == "set_expr":
            value = SetValue(t="set", latex=latex, symbols=symbols, parse=result.status)
        else:
            value = Formula(t="formula", latex=latex, symbols=symbols, parse=result.status)
        error = result.failure.category if result.failure is not None else None
        out.append(SpanValue(reading.span.segment, value, result.kind, error))
    return out


# ============================================================================ M09


@dataclass(frozen=True, slots=True)
class SymbolMention:
    """A `symbol` mention of M09: canonical-text offsets and the occurrence's decoration."""

    segment: Segment  # the math span
    start: int
    end: int
    name: str
    base: str
    sub: str | None
    sup: str | None
    constant: bool
    in_subscript_of: str | None


type RelationLabel = Literal["in_set", "equals", "compares"]


@dataclass(frozen=True, slots=True)
class MathRelation:
    segment: Segment
    label: RelationLabel
    head: tuple[int, int]  # canonical-text offsets
    tail: tuple[int, int]
    operator: str  # the operator's source text


@dataclass(frozen=True, slots=True)
class MathExtraction:
    mentions: tuple[SymbolMention, ...]
    relations: tuple[MathRelation, ...]


def extract(readings: Sequence[SpanReading]) -> MathExtraction:
    mentions: list[SymbolMention] = []
    relations: list[MathRelation] = []
    for reading in readings:
        span, result = reading.span, reading.result
        for o in result.occurrences:
            mentions.append(
                SymbolMention(
                    span.segment,
                    span.offset + o.start,
                    span.offset + o.end,
                    o.name,
                    o.base,
                    o.sub,
                    o.sup,
                    o.constant,
                    o.in_subscript_of,
                )
            )
        if result.tree is not None:
            found = sorted(_relations(result.tree, span), key=lambda r: (r.head, r.tail))
            relations.extend(found)
    return MathExtraction(tuple(mentions), tuple(relations))


def _children(node: Tree[Token]) -> list[_tree.Node]:
    return [c for c in node.children if isinstance(c, Tree | Token)]


def _cover(nodes: Sequence[_tree.Node]) -> tuple[int, int] | None:
    spans = [s for s in (_tree.span(n) for n in nodes) if s is not None]
    if not spans:
        return None
    return min(s[0] for s in spans), max(s[1] for s in spans)


def _relations(tree: Tree[Token], span: MathSpan) -> Iterator[MathRelation]:
    def make(
        label: RelationLabel,
        head: Sequence[_tree.Node],
        operator: _tree.Node,
        tail: Sequence[_tree.Node],
    ) -> Iterator[MathRelation]:
        h, t = _cover(head), _cover(tail)
        if h is not None and t is not None:
            shift = span.offset
            yield MathRelation(
                span.segment,
                label,
                (h[0] + shift, h[1] + shift),
                (t[0] + shift, t[1] + shift),
                _tree.text(operator, span.latex),
            )

    def membership(
        elements: _tree.Node, operator: _tree.Node, target: Sequence[_tree.Node]
    ) -> Iterator[MathRelation]:
        if not (isinstance(operator, Token) and operator.type == "CMD_IN"):
            return
        if isinstance(elements, Tree) and elements.data == "list_of_expressions":
            items = [
                c for c in _children(elements) if not (isinstance(c, Token) and c.type == "COMMA")
            ]
        else:
            items = [elements]
        for item in items:
            yield from make("in_set", [item], operator, target)

    def chain(parts: list[_tree.Node]) -> Iterator[MathRelation]:
        for i in range(0, len(parts) - 2, 2):
            operator = parts[i + 1]
            label: RelationLabel = (
                "equals" if isinstance(operator, Token) and operator.type in _EQUALS else "compares"
            )
            yield from make(label, [parts[i]], operator, [parts[i + 2]])

    def value(node: _tree.Node) -> Iterator[MathRelation]:
        if not isinstance(node, Tree) or node.data == "_ambig":
            return
        parts = _children(node)
        rule = node.data
        if rule == "any_value" and parts:
            yield from value(parts[0])
        elif rule in ("value_list", "text_join"):
            for part in parts:
                yield from value(part)
        elif rule == "formula":
            if len(parts) == 1:
                yield from value(parts[0])
            elif len(parts) >= 3:  # a tuple equation
                yield from make("equals", [parts[0]], parts[1], parts[2:])
        elif rule == "eq" and len(parts) >= 3:
            yield from make("equals", [parts[0]], parts[1], parts[2:])
        elif rule == "relation" and parts:
            yield from value(parts[0])
        elif (
            rule
            in (
                "ne",
                "lt",
                "lte",
                "gt",
                "gte",
                "subset_rel",
                "approach",
                "other_rel",
                "maps_to",
                "fn_signature",
            )
            and len(parts) >= 3
        ):
            yield from make("compares", [parts[0]], parts[1], parts[2:])
        elif rule in ("set_eq", "interval_eq") and len(parts) >= 3:
            yield from make("equals", [parts[0]], parts[1], parts[2:])
        elif rule == "rel_chain":
            yield from chain(parts)
        elif rule == "chain_member" and len(parts) >= 3:
            terms = parts[:-2]
            yield from chain(terms)
            yield from membership(terms[-1], parts[-2], [parts[-1]])
        elif rule == "member" and len(parts) >= 3:
            yield from membership(parts[0], parts[1], parts[2:])

    yield from value(tree)
