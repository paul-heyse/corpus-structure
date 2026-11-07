"""Small source-preserving field grammars, prepared once per declared route."""

import re
from datetime import date
from decimal import Decimal
from functools import lru_cache
from typing import Literal, TypedDict

from lark import Lark, Token, UnexpectedInput

from corpus_structure.semantic.scientific_evidence import canonical_operand

Comparator = Literal[">", ">=", "<", "<=", "="]

COMPARISON_BASIS = re.compile(r"^Comparison basis:[ \t]*([^\n\r.]+?)[ \t]*\.?[ \t]*$", re.M)
REVISION_SUCCESSION = re.compile(
    r"^Revision ([A-Za-z0-9_-]+) supersedes revision ([A-Za-z0-9_-]+)\.[ \t]*$", re.M
)
REVISION_DECLARATION = re.compile(r"^Revision ([A-Za-z0-9_-]+)\.[ \t]*$", re.M)
REVISION_LINEAGE = re.compile(r"^Clause ([A-Za-z0-9_-]+)\.[ \t]*$", re.M)


class ParsedThreshold(TypedDict):
    value: str
    comparator: Comparator
    quantity: str | None
    unit: str | None
    positions: dict[str, tuple[int, int]]
    grammar: str


class LocatedThreshold(ParsedThreshold):
    start: int
    end: int
    text: str


@lru_cache(maxsize=1)
def field_lexer():
    return Lark(
        r"""
        start: atom*
        ?atom: OP | NUMBER | WORD | OTHER
        OP.3: ">=" | "<=" | ">" | "<" | "=" | "≥" | "≤"
        NUMBER.2: /[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?/
        WORD: /[^\W\d][\w.-]*/u
        OTHER: /[^\s]/
        %import common.WS
        %ignore WS
    """,
        parser=None,
        lexer="basic",
        propagate_positions=True,
    )


@lru_cache(maxsize=1)
def threshold_grammar():
    return Lark(
        r"""
        start: SYMBOL? OP NUMBER UNIT?
        SYMBOL: /[A-Za-z][A-Za-z0-9_]*/
        OP: ">=" | "<=" | ">" | "<" | "=" | "≥" | "≤"
        NUMBER: /[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?/
        UNIT: /[%$€£]|[A-Za-z][A-Za-z0-9_\/-]*/
        %import common.WS
        %ignore WS
    """,
        parser="lalr",
        lexer="contextual",
        propagate_positions=True,
    )


def located_tokens(text):
    """Tokens preserve original start/end coordinates; no normalized text is re-anchored."""
    return tuple(field_lexer().lex(text))


def parse_threshold(text: str) -> ParsedThreshold | None:
    """Parse one complete threshold field. Unsupported prose is not silently discarded."""
    try:
        tree = threshold_grammar().parse(text)
    except UnexpectedInput:
        return None
    values = {token.type: token for token in tree.scan_values(lambda v: isinstance(v, Token))}
    number = values["NUMBER"]
    canonical = canonical_operand(dict(kind="number", number=Decimal(str(number))), {})
    comparators: dict[str, Comparator] = {
        ">": ">",
        ">=": ">=",
        "<": "<",
        "<=": "<=",
        "=": "=",
        "≥": ">=",
        "≤": "<=",
    }
    return ParsedThreshold(
        value=canonical["v"],
        comparator=comparators[str(values["OP"])],
        quantity=str(values["SYMBOL"]) if "SYMBOL" in values else None,
        unit=str(values["UNIT"]) if "UNIT" in values else None,
        positions={name: (token.start_pos, token.end_pos) for name, token in values.items()},
        grammar="threshold-lalr-1",
    )


def threshold_fields(text: str) -> tuple[LocatedThreshold, ...]:
    """Nominate local grammatical fields from lexemes, retaining multiple possible readings."""
    tokens = located_tokens(text)
    result = []
    for i, token in enumerate(tokens):
        if token.type != "OP" or i + 1 >= len(tokens) or tokens[i + 1].type != "NUMBER":
            continue
        start = token.start_pos
        if i and tokens[i - 1].type == "WORD":
            start = tokens[i - 1].start_pos
        end = tokens[i + 1].end_pos
        # Units are nominated only by explicit conventional symbols/codes. Other words
        # remain prose rather than accidentally consuming the next sentence as a unit.
        if i + 2 < len(tokens) and str(tokens[i + 2]) in {
            "%",
            "$",
            "€",
            "£",
            "USD",
            "EUR",
            "kg",
            "m",
            "s",
        }:
            end = tokens[i + 2].end_pos
        if start is None or end is None:
            raise ValueError("field lexer omitted source positions")
        parsed = parse_threshold(text[start:end])
        if parsed is not None:
            result.append(LocatedThreshold(start=start, end=end, text=text[start:end], **parsed))
    return tuple(result)


@lru_cache(maxsize=1)
def literal_grammar():
    return Lark(
        r"""
        ?start: date | identifier | quantity | bounded_range
        date: "Date:" DATE
        identifier: "Identifier:" IDENTIFIER
        quantity: "Quantity:" NUMBER UNIT
        bounded_range: "Range:" OPEN NUMBER "," NUMBER CLOSE UNIT
        DATE: /[0-9]{4}-[0-9]{2}-[0-9]{2}/
        IDENTIFIER: /[A-Za-z][A-Za-z0-9_.-]*/
        NUMBER: /[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?/
        UNIT: /[%$€£]|[A-Za-z][A-Za-z0-9_\/-]*/
        OPEN: "[" | "("
        CLOSE: "]" | ")"
        %import common.WS
        %ignore WS
        """,
        parser="lalr",
        lexer="contextual",
        propagate_positions=True,
    )


def parse_comparison_literal(text: str) -> dict[str, str | bool] | None:
    """Parse an explicitly delimited operand, without supplying applicability."""
    if len(text) > 256:
        return None
    try:
        tree = literal_grammar().parse(text)
        values = [str(token) for token in tree.children]
        if tree.data == "date":
            return {"kind": "date", "value": date.fromisoformat(values[0]).isoformat()}
        if tree.data == "identifier":
            return {"kind": "identifier", "value": values[0]}
        numbers = [
            Decimal(value) for value in (values[:1] if tree.data == "quantity" else values[1:3])
        ]
        if any(number and abs(number.adjusted()) > 100 for number in numbers):
            return None
        canonical = [
            canonical_operand(dict(kind="number", number=number), {})["v"] for number in numbers
        ]
        if tree.data == "quantity":
            return {"kind": "quantity", "value": canonical[0], "unit": values[1]}
        lower_closed, upper_closed = values[0] == "[", values[3] == "]"
        if numbers[0] > numbers[1] or (
            numbers[0] == numbers[1] and not (lower_closed and upper_closed)
        ):
            return None
        return {
            "kind": "range",
            "lower": canonical[0],
            "upper": canonical[1],
            "lower_closed": lower_closed,
            "upper_closed": upper_closed,
            "unit": values[4],
        }
    except UnexpectedInput, ValueError, ArithmeticError:
        return None
