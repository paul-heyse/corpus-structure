"""Small source-preserving field grammars, prepared once per declared route."""

import re
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


# Cued English clause fields are deliberately separate from the numerical grammar.
# Exact source strings are retained; absent/competing fields remain unknown.
CLAUSE_NOUN = (
    r"[A-Za-z][A-Za-z0-9_-]*"
    r"(?:\s+(?!(?:if|when|unless|except|before|after)\b)[A-Za-z][A-Za-z0-9_-]*){0,7}"
)
CLAUSE_END = r"(?=\s+(?:if|when|unless|except|before|after)\b|\.(?=\s|$)|[;\n]|$)"
CLAUSE_BODY = r"(?:(?!\s+(?:if|when|unless|except|before|after)\b|\.(?=\s|$)|[;\n]).)+"
CLAUSE_ACTIVE = (
    r"(?:^|[,;]\s*|\bthen\s+)(" + CLAUSE_NOUN + r")\s+"
    r"(must|shall|should|may|can)\s+((?!be\b)[A-Za-z]+)\s+(" + CLAUSE_BODY + r")" + CLAUSE_END
)
CLAUSE_PASSIVE = (
    r"(?:^|[,;]\s*|\bthen\s+)(.+?)\s+(must|shall|should|may|can)\s+"
    r"be\s+([A-Za-z]+)\s+by\s+(" + CLAUSE_NOUN + r")" + CLAUSE_END
)
CLAUSE_QUALIFIER = (
    r"\b(if|when|provided(?:\s+that)?|unless|except(?:\s+(?:when|if))?|before|after)\s+"
    r"((?:(?!,|\s+(?:unless|except|before|after)\b|\.(?=\s|$)|[;\n]).)+)"
)


def clause_fields(text):
    import re

    found = {}

    def add(dimension, start, end):
        while start < end and text[start].isspace():
            start += 1
        while start < end and text[end - 1].isspace():
            end -= 1
        if start < end:
            found.setdefault(dimension, []).append(dict(start=start, end=end, text=text[start:end]))

    for pattern, roles in (
        (CLAUSE_PASSIVE, ("object", "modality", "action", "actor")),
        (CLAUSE_ACTIVE, ("actor", "modality", "action", "object")),
    ):
        for match in re.finditer(pattern, text, re.IGNORECASE):
            for group, role in enumerate(roles, 1):
                add(role, *match.span(group))
    for match in re.finditer(CLAUSE_QUALIFIER, text, re.IGNORECASE):
        cue = match[1].casefold()
        dimension = (
            "exception"
            if cue.startswith(("unless", "except"))
            else "order_dependency"
            if cue in {"before", "after"}
            else "condition"
        )
        add(dimension, match.start(), match.end())
    return {dimension: values[0] for dimension, values in found.items() if len(values) == 1}
