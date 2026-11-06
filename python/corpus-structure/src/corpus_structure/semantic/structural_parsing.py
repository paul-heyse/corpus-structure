"""Small source-preserving field grammars, prepared once per declared route."""

from functools import lru_cache
from decimal import Decimal

from lark import Lark, Token, UnexpectedInput

from corpus_structure.semantic.scientific_evidence import canonical_operand


@lru_cache(maxsize=1)
def field_lexer():
    return Lark(r'''
        start: atom*
        ?atom: OP | NUMBER | WORD | OTHER
        OP.3: ">=" | "<=" | ">" | "<" | "=" | "≥" | "≤"
        NUMBER.2: /[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?/
        WORD: /[^\W\d][\w.-]*/u
        OTHER: /[^\s]/
        %import common.WS
        %ignore WS
    ''', parser=None, lexer="basic", propagate_positions=True)


@lru_cache(maxsize=1)
def threshold_grammar():
    return Lark(r'''
        start: SYMBOL? OP NUMBER UNIT?
        SYMBOL: /[A-Za-z][A-Za-z0-9_]*/
        OP: ">=" | "<=" | ">" | "<" | "=" | "≥" | "≤"
        NUMBER: /[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?/
        UNIT: /[%$€£]|[A-Za-z][A-Za-z0-9_\/-]*/
        %import common.WS
        %ignore WS
    ''', parser="lalr", lexer="contextual", propagate_positions=True)


def located_tokens(text):
    """Tokens preserve original start/end coordinates; no normalized text is re-anchored."""
    return tuple(field_lexer().lex(text))


def parse_threshold(text):
    """Parse one complete threshold field. Unsupported prose is not silently discarded."""
    try:
        tree = threshold_grammar().parse(text)
    except UnexpectedInput:
        return None
    values = {token.type: token for token in tree.scan_values(lambda v: isinstance(v, Token))}
    number = values["NUMBER"]
    canonical = canonical_operand(dict(kind="number", number=Decimal(str(number))), {})
    return dict(
        value=canonical["v"],
        comparator=str(values["OP"]).replace("≥", ">=").replace("≤", "<="),
        quantity=str(values["SYMBOL"]) if "SYMBOL" in values else None,
        unit=str(values["UNIT"]) if "UNIT" in values else None,
        positions={name: (token.start_pos, token.end_pos) for name, token in values.items()},
        grammar="threshold-lalr-1",
    )


def threshold_fields(text):
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
        if i + 2 < len(tokens) and str(tokens[i + 2]) in {"%", "$", "€", "£", "USD", "EUR", "kg", "m", "s"}:
            end = tokens[i + 2].end_pos
        if start is None or end is None:
            raise ValueError("field lexer omitted source positions")
        parsed = parse_threshold(text[start:end])
        if parsed is not None:
            result.append(dict(start=start, end=end, text=text[start:end], **parsed))
    return tuple(result)
