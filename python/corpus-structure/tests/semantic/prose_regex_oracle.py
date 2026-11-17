"""Independent positioned-regex reference for construction parser verification."""

from __future__ import annotations

import re
from pathlib import Path

from lark import Lark

from corpus_structure.semantic.constructions import forest
from corpus_structure.semantic.constructions.forest import terminal_guard
from corpus_structure.semantic.constructions.lexical import (
    LEXICAL,
    PositionedTerminal,
    ProtectedAtom,
    classify,
)

_GRAMMAR_ROOT = Path(forest.__file__).with_name("grammars")


def _literal_pattern(value: str) -> str:
    """Escape original text for a regex inside a single-line Lark declaration."""
    escaped = re.escape(value)
    for control, spelling in (
        ("\n", r"\n"),
        ("\r", r"\r"),
        ("\t", r"\t"),
        ("\f", r"\f"),
        ("\v", r"\v"),
    ):
        escaped = escaped.replace("\\" + control, spelling)
    return escaped


def _positioned_values(text: str, terminal: str, values: tuple[PositionedTerminal, ...]) -> str:
    alternatives = []
    for row in values:
        if (
            row.terminal not in {*LEXICAL, "WS"}
            or not 0 <= row.start < row.end <= len(text)
            or text[row.start : row.end] != row.text
        ):
            raise ValueError("retained lexical observation differs from exact original source")
        if row.terminal == terminal:
            alternatives.append(
                r"(?<=\A[\s\S]{" + str(row.start) + "})" + _literal_pattern(row.text)
            )
    return "(?:" + "|".join(alternatives) + ")" if alternatives else r"(?!)x"


def _regex_parser_oracle(
    text: str,
    atoms: tuple[ProtectedAtom, ...],
    grammar: str | None = None,
    *,
    terminals: tuple[PositionedTerminal, ...] | None = None,
) -> Lark:
    """Independent per-region compiler for parser-equivalence verification only."""
    previous = 0
    for atom in sorted(atoms, key=lambda a: a.start):
        if not previous <= atom.start < atom.end <= len(text):
            raise ValueError("protected atoms overlap or lie outside their source region")
        previous = atom.end
    values = classify(text, atoms) if terminals is None else terminals
    starts = {}
    for row in values:
        key = row.terminal, row.start
        if key in starts and starts[key] != row:
            raise ValueError(
                "same-terminal same-start alternatives exceed dynamic Earley lexical support"
            )
        starts[key] = row
        terminal_guard(row.start, row.end, atoms, atom=False)
    lexical = {name: _positioned_values(text, name, values) for name in LEXICAL}
    lexical["ATOM"] = (
        "(?:"
        + "|".join(
            r"(?<=\A[\s\S]{" + str(a.start) + "})" + _literal_pattern(text[a.start : a.end])
            for a in atoms
        )
        + ")"
        if atoms
        else r"(?!)x"
    )
    lexical["WS"] = _positioned_values(text, "WS", values)
    declarations = "\n".join(
        f"%override {name}: /{pattern.replace('/', r'\/')}/"
        for name, pattern in lexical.items()
        if name != "WS"
    )
    if grammar is None:
        imports = ", ".join(["clause", *LEXICAL, "ATOM"])
        grammar = f"%import .prose ({imports})\nstart: clause PUNCT?"
    parser = Lark(
        grammar + "\n" + declarations + "\nWS: /" + lexical["WS"] + "/\n%ignore WS",
        import_paths=[str(_GRAMMAR_ROOT)],
        parser="earley",
        lexer="dynamic",
        ambiguity="forest",
        priority=None,
        ordered_sets=True,
        start=["start"],
        keep_all_tokens=True,
    )
    forest._grammar_resource(_GRAMMAR_ROOT / "prose.lark").check()
    return parser
