r"""The page macro reader (D4 M01 "Page macros"; ingest and math §3.3 step 3).

It reads a macro source (Siegrist's `div.latex`) with `core/tex.py`'s tokenizer, the one the token
form uses, so the reader and the keys never tokenize differently:

- `\newcommand`, `\renewcommand` and `\providecommand`, each with an optional `*`, then the name
  (`{\name}` or `\name`), an optional `[n]`, an optional default `[...]` and the body, read as TeX
  reads an undelimited argument (one token, or a balanced group);
- `\DeclareMathOperator[*]{\name}{text}` as an operator: body `\operatorname{text}`
  (`\operatorname*{text}` with the star).

TeX's semantics decide the table: `\renewcommand` replaces, `\providecommand` defines only an
undefined name, and a `\newcommand` of a defined name keeps the first (TeX's error, reported).
Whatever the reader cannot take (a name that is no control word, an argument count outside 0-9, a
default without an argument, `\def`) is reported, never guessed. The table is content: canonical
forms expand by it (D1 §6.2).
"""

from __future__ import annotations

import re

from corpus_structure.core.evidence import MACRO_NAME, MacroDef
from corpus_structure.core.tex import tokens

DEFINERS = frozenset({r"\newcommand", r"\renewcommand", r"\providecommand"})
OPERATOR = r"\DeclareMathOperator"
UNREAD = frozenset({r"\def", r"\gdef", r"\edef", r"\xdef", r"\let", r"\DeclareRobustCommand"})
_NAME = re.compile(MACRO_NAME)


def _skip(t: list[str], i: int) -> int:
    while i < len(t) and t[i].isspace():
        i += 1
    return i


def _argument(t: list[str], i: int) -> tuple[list[str], int]:
    """An undelimited argument at `i`: a group's inner tokens, or one token."""
    i = _skip(t, i)
    if i >= len(t):
        return [], i
    if t[i] != "{":
        return [t[i]], i + 1
    depth = 0
    for k in range(i, len(t)):
        depth += t[k] == "{"
        depth -= t[k] == "}"
        if depth == 0:
            return t[i + 1 : k], k + 1
    return t[i + 1 :], len(t)


def _optional(t: list[str], i: int) -> tuple[list[str] | None, int]:
    """An optional `[...]` at `i` (a `]` inside braces does not close it), else None."""
    j = _skip(t, i)
    if j >= len(t) or t[j] != "[":
        return None, i
    depth = 0
    for k in range(j + 1, len(t)):
        depth += t[k] == "{"
        depth -= t[k] == "}"
        if depth == 0 and t[k] == "]":
            return t[j + 1 : k], k + 1
    return None, i


def read_macros(source: str) -> tuple[dict[str, MacroDef], list[str]]:
    """The macro table a source defines, and notes on what was not taken as written."""
    t = [token.text for token in tokens(source)]
    table: dict[str, MacroDef] = {}
    notes: list[str] = []
    i = 0
    while i < len(t):
        command = t[i]
        if command not in DEFINERS and command != OPERATOR:
            if command in UNREAD:
                notes.append(f"{command} is not read")
            i += 1
            continue
        j = _skip(t, i + 1)
        star = j < len(t) and t[j] == "*"
        if star:
            j += 1
        name_tokens, j = _argument(t, j)
        name = "".join(x for x in name_tokens if not x.isspace())
        if command == OPERATOR:
            body_tokens, j = _argument(t, j)
            opener = r"\operatorname*{" if star else r"\operatorname{"
            definition: tuple[int, str | None, str] | None = (
                0,
                None,
                opener + "".join(body_tokens) + "}",
            )
        else:
            count, j = _optional(t, j)
            default = None
            if count is not None:
                default_tokens, after = _optional(t, j)
                if default_tokens is not None:
                    default, j = "".join(default_tokens), after
            body_tokens, j = _argument(t, j)
            text = "".join(count or []).strip()
            definition = None
            if count is not None and not (text.isdigit() and int(text) <= 9):
                notes.append(f"{command}{{{name}}}: argument count {text!r} is not 0-9; not read")
            elif default is not None and int(text or 0) == 0:
                notes.append(f"{command}{{{name}}}: a default without an argument; not read")
            else:
                definition = (int(text or 0), default, "".join(body_tokens))
        i = j
        if definition is None:
            continue
        if not _NAME.match(name):
            notes.append(f"{command}: name {name!r} is not a control word; not read")
            continue
        nargs, default, body = definition
        if command == r"\providecommand" and name in table:
            continue
        if command in (r"\newcommand", OPERATOR) and name in table:
            notes.append(f"{name} redefined by {command} (TeX error; the first is kept)")
            continue
        if command == r"\renewcommand" and name not in table:
            notes.append(f"{name}: \\renewcommand without a prior definition on the page")
        table[name] = MacroDef(nargs=nargs, default=default, body=body)
    return table, notes
