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
from dataclasses import dataclass, replace
from collections.abc import Iterator
from typing import Literal

from corpus_structure.core.evidence import MACRO_NAME, MacroDef
from corpus_structure.core.tex import MacroBinding, Token, tokens

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


@dataclass(frozen=True, slots=True)
class MacroEvent:
    source_ref: str
    command: Token
    name: str
    name_tokens: tuple[Token, ...]
    body_tokens: tuple[Token, ...]
    default_tokens: tuple[Token, ...]
    count_tokens: tuple[Token, ...]
    start: int
    end: int
    status: Literal["accepted", "ignored", "replaced", "unsupported", "invalid"]
    definition: MacroDef | None


@dataclass(frozen=True, slots=True)
class MacroRead:
    table: dict[str, MacroDef]
    notes: list[str]
    tokens: tuple[Token, ...]
    events: tuple[MacroEvent, ...]

    @property
    def bindings(self) -> dict[str, MacroBinding]:
        return {event.name: MacroBinding(event.source_ref, event.start, event.end,
                                        event.body_tokens, event.default_tokens)
                for event in self.events if event.status == "accepted"}

    def __iter__(self) -> Iterator[dict[str, MacroDef] | list[str]]:
        # Existing consumers retain their table/notes projection.
        yield self.table
        yield self.notes


def read_macros(source: str, *, source_ref: str = "macro-source") -> MacroRead:
    """The macro table a source defines, and notes on what was not taken as written."""
    retained = tuple(tokens(source))
    t = [token.text for token in retained]
    events: list[MacroEvent] = []
    selected: dict[str, int] = {}

    def parts(a: int, b: int, optional: bool = False) -> tuple[Token, ...]:
        a = _skip(t, a)
        if a < b and t[a] == ("[" if optional else "{"):
            a += 1
            if b > a and t[b - 1] == ("]" if optional else "}"):
                b -= 1
        return retained[a:b]

    table: dict[str, MacroDef] = {}
    notes: list[str] = []
    i = 0
    while i < len(t):
        command = t[i]
        if command not in DEFINERS and command != OPERATOR:
            if command in UNREAD:
                notes.append(f"{command} is not read")
                events.append(MacroEvent(source_ref, retained[i], "", (), (), (), (), retained[i].start, retained[i].end, "unsupported", None))
            i += 1
            continue
        j = _skip(t, i + 1)
        star = j < len(t) and t[j] == "*"
        if star:
            j += 1
        name_at = j
        name_tokens, j = _argument(t, j)
        name_extent = parts(name_at, j)
        default_extent: tuple[Token, ...] = ()
        count_extent: tuple[Token, ...] = ()
        name = "".join(x for x in name_tokens if not x.isspace())
        if command == OPERATOR:
            body_at = j
            body_tokens, j = _argument(t, j)
            opener = r"\operatorname*{" if star else r"\operatorname{"
            definition: tuple[int, str | None, str] | None = (
                0,
                None,
                opener + "".join(body_tokens) + "}",
            )
        else:
            count_at = j
            count, j = _optional(t, j)
            count_extent = parts(count_at, j, True) if count is not None else ()
            default = None
            if count is not None:
                default_at = j
                default_tokens, after = _optional(t, j)
                if default_tokens is not None:
                    default_extent = parts(default_at, after, True)
                    default, j = "".join(default_tokens), after
            body_at = j
            body_tokens, j = _argument(t, j)
            text = "".join(count or []).strip()
            definition = None
            if count is not None and not (text.isdigit() and int(text) <= 9):
                notes.append(f"{command}{{{name}}}: argument count {text!r} is not 0-9; not read")
            elif default is not None and int(text or 0) == 0:
                notes.append(f"{command}{{{name}}}: a default without an argument; not read")
            else:
                definition = (int(text or 0), default, "".join(body_tokens))
        command_at = i
        i = j
        event = MacroEvent(source_ref, retained[command_at], name, name_extent,
                           parts(body_at, j), default_extent, count_extent,
                           retained[command_at].start, retained[j - 1].end,
                           "invalid", None)
        events.append(event)
        event_index = len(events) - 1
        if definition is None:
            continue
        if not _NAME.match(name):
            notes.append(f"{command}: name {name!r} is not a control word; not read")
            continue
        nargs, default, body = definition
        if command == r"\providecommand" and name in table:
            events[-1] = replace(event, status="ignored", definition=MacroDef(nargs=nargs, default=default, body=body))
            continue
        if command in (r"\newcommand", OPERATOR) and name in table:
            events[-1] = replace(event, status="ignored", definition=MacroDef(nargs=nargs, default=default, body=body))
            notes.append(f"{name} redefined by {command} (TeX error; the first is kept)")
            continue
        if command == r"\renewcommand" and name not in table:
            notes.append(f"{name}: \\renewcommand without a prior definition on the page")
        table[name] = MacroDef(nargs=nargs, default=default, body=body)
        if name in selected:
            at = selected[name]
            events[at] = replace(events[at], status="replaced")
        selected[name] = event_index
        events[-1] = replace(event, status="accepted", definition=table[name])
    return MacroRead(table, notes, retained, tuple(events))


@dataclass(frozen=True, slots=True)
class MacroFragment:
    start: int
    end: int
    decoded_sources: tuple[tuple[int, int], ...]
    reason: str


@dataclass(frozen=True, slots=True)
class MacroSource:
    source_ref: str
    text: str
    read: MacroRead
    fragments: tuple[MacroFragment, ...] = ()
