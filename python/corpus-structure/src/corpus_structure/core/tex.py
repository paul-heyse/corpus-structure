"""The TeX tokenizer and the token form (D1 §6.2; ADR-0012; foundations §3.4).

Coordinator decision 13 puts it in `core`.

The only TeX reader below the grammar. The math grammar (I2a), M01's macro reader, the quote
cascade (A0) and the keys all use this tokenizer, this drop list and `effective_macros`, so no two
readers tokenize, drop or merge macro tables differently.

- `tokens`: TeX's tokens with positions. A control word is `\\` and ASCII letters (never a `*`), a
  control symbol is `\\` and one other character, `{`, `}` and `#n` are their own kinds, a
  whitespace run is one token, anything else is one character. `%` is an ordinary character.
- `DROP`: every `%ignore` literal of SymPy 1.14's `latex.lark` plus the sizing commands.
- `TEXT_MODE`: commands whose argument keeps its whitespace, collapsed to one space.
- `effective_macros`: the rendition's table over the pack's fallback map.
- `expand`: macros by whole name, arguments read as TeX reads them, bounded at depth 16; a macro
  left at the bound is kept and reported.
- `token_form`: the key form of a formula: one outer delimiter pair stripped, macros expanded,
  drop-list tokens and whitespace removed (whitespace collapsed inside text-mode arguments),
  braces around a single token dropped, a space kept after a control word followed by a letter.

The module is frozen once `s5.keys-property` is final; after that, a change to any output is a key
migration and goes through the design owner.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, cast

import regex

from corpus_structure.core.evidence import MacroDef

MAX_DEPTH = 16
# An expansion that would grow a formula beyond this many tokens stops there (the macro is kept
# and reported, like one at the depth bound), so a pathological table cannot exhaust memory.
MAX_TOKENS = 100_000

# Outer environments whose first argument is a column count, stripped with the delimiter.
COLUMN_COUNT_ENVIRONMENTS: frozenset[str] = frozenset({"alignat", "alignat*"})

# Environments whose `\begin`/`\end` pair is an outer math delimiter (the display environments
# M01's profiles declare; operator ruling 2026-10-28, widened to I-R2's set). Any other
# environment is content.
OUTER_ENVIRONMENTS: frozenset[str] = frozenset(
    {
        *(name + star
          for name in ("equation", "align", "alignat", "flalign", "gather", "multline", "eqnarray")
          for star in ("", "*")),
        "displaymath",  # neither has a starred form
        "math",
    }
)  # fmt: skip

TokenKind = Literal["word", "symbol", "open", "close", "param", "space", "char"]

_TOKEN = regex.compile(
    r"(?P<word>\\[A-Za-z]+)|(?P<symbol>\\.)|(?P<open>\{)|(?P<close>\})|(?P<param>#[0-9])"
    r"|(?P<space>\s+)|(?P<char>.)",
    regex.DOTALL,
)
_LETTER = regex.compile(r"[A-Za-z]")

# SymPy 1.14.0 `sympy/parsing/latex/lark/grammar/latex.lark`, lines 3-11 (the string `%ignore`
# literals; line 1 ignores whitespace, which the token form removes separately).
SYMPY_IGNORE: frozenset[str] = frozenset(
    {
        *(r"\,", r"\thinspace", r"\:", r"\medspace", r"\;", r"\thickspace"),
        *(r"\quad", r"\qquad"),
        *(r"\!", r"\negthinspace", r"\negmedspace", r"\negthickspace"),
        *(r"\vrule", r"\vcenter", r"\vbox", r"\vskip", r"\vspace", r"\hfill"),
        *(r"\*", r"\-", r"\.", r"\/", r"\(", r"\="),
        *(r"\left", r"\right"),
        *(r"\limits", r"\nolimits"),
        r"\displaystyle",
    }
)
SIZING: frozenset[str] = frozenset(
    f"\\{size}{side}" for size in ("big", "Big", "bigg", "Bigg") for side in ("", "l", "r", "m")
)
DROP: frozenset[str] = SYMPY_IGNORE | SIZING

TEXT_MODE: frozenset[str] = frozenset(
    {r"\text", r"\mathrm", r"\textrm", r"\mbox", r"\operatorname"}
)


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    text: str
    start: int
    end: int


def tokens(latex: str) -> list[Token]:
    """TeX's tokens of `latex` with their code-point positions; total over every string."""
    out: list[Token] = []
    for match in _TOKEN.finditer(latex):
        kind = cast(TokenKind, match.lastgroup)
        out.append(Token(kind, match.group(), match.start(), match.end()))
    return out


def token_at(latex: str, pos: int) -> Token | None:
    """The token containing position `pos` (a grammar error's position), or None outside."""
    for token in tokens(latex):
        if token.start <= pos < token.end:
            return token
    return None


# TeX's control space: `\ `, and `\` followed by a tab or an end of line, are one control symbol
# (IR-15, operator 2026-10-28); the token form spells it `\ `.
CONTROL_SPACE = "\\ "
_CONTROL_SPACES = frozenset({"\\ ", "\\\t", "\\\n", "\\\r"})


def _texts(latex: str) -> list[str]:
    """Token texts for the token form: every control-space spelling as `CONTROL_SPACE`, and the
    blanks right after one skipped, as TeX skips them (so `\\` + CR LF is one control space)."""
    out: list[str] = []
    for token in tokens(latex):
        if token.text in _CONTROL_SPACES:
            out.append(CONTROL_SPACE)
        elif not (token.kind == "space" and out[-1:] == [CONTROL_SPACE]):
            out.append(token.text)
    return out


def _is_space(text: str) -> bool:
    return text.isspace()


def _is_word(text: str) -> bool:
    return len(text) > 1 and text[0] == "\\" and _LETTER.match(text[1]) is not None


# --- Macros ------------------------------------------------------------------------------------


def effective_macros(
    rendition_table: Mapping[str, MacroDef], pack_map: Mapping[str, MacroDef]
) -> dict[str, MacroDef]:
    """The one effective macro table: the page's definitions over the pack's fallback map."""
    return {**pack_map, **rendition_table}


@dataclass(frozen=True, slots=True)
class Expansion:
    tokens: tuple[str, ...]
    unexpanded: tuple[str, ...]  # distinct macros left unexpanded at a bound, first seen first


Item = tuple[str, int]  # a token's text and its expansion depth


class _Input:
    """TeX's input stream as a stack (next token last), recording what a macro call consumes."""

    def __init__(self, source: Sequence[str]) -> None:
        self.stack: list[Item] = [(text, 0) for text in reversed(source)]
        self.consumed: list[Item] = []

    def pop(self) -> Item:
        item = self.stack.pop()
        self.consumed.append(item)
        return item

    def peek(self) -> str | None:
        return self.stack[-1][0] if self.stack else None

    def skip_spaces(self) -> None:
        while self.stack and _is_space(self.stack[-1][0]):
            self.pop()

    def group(self) -> list[Item]:
        """At an opening brace: the group's inner tokens (to the end when it never closes)."""
        self.pop()
        depth, inner = 1, []
        while self.stack:
            item = self.pop()
            depth += item[0] == "{"
            depth -= item[0] == "}"
            if depth == 0:
                return inner
            inner.append(item)
        return inner

    def argument(self) -> list[Item]:
        """An undelimited argument as TeX reads it: spaces skipped, then a group or one token.

        Missing, or at the enclosing group's `}`: an empty argument, the `}` not consumed.
        """
        self.skip_spaces()
        top = self.peek()
        if top is None or top == "}":
            return []
        if top == "{":
            return self.group()
        return [self.pop()]

    def optional(self) -> list[Item] | None:
        """An optional `[...]` argument (brackets inside braces do not close it), or None."""
        k = len(self.stack) - 1
        while k >= 0 and _is_space(self.stack[k][0]):
            k -= 1
        if k < 0 or self.stack[k][0] != "[":
            return None
        depth = 0
        for m in range(k - 1, -1, -1):
            text = self.stack[m][0]
            depth += text == "{"
            depth -= text == "}"
            if depth == 0 and text == "]":
                inner = self.stack[m + 1 : k][::-1]
                self.consumed.extend(self.stack[m:][::-1])
                del self.stack[m:]
                return inner
        return None  # no closing bracket: not an optional argument


def expand(
    source: Sequence[str], table: Mapping[str, MacroDef], drop: frozenset[str] = frozenset()
) -> Expansion:
    """Expand macros by whole name, re-reading each expansion as TeX does, to depth 16.

    A macro met at depth 16 (sixteen nested expansions deep), or whose expansion would make the
    formula longer than `MAX_TOKENS`, is kept unexpanded and reported, with its arguments left in
    place. Arguments are substituted without their braces, as TeX substitutes them. Tokens in
    `drop` are removed from macro bodies and defaults before they are read, so a dropped command
    never becomes an argument.
    """
    stream = _Input(source)
    out: list[str] = []
    unexpanded: list[str] = []
    bodies: dict[str, list[str]] = {}
    while stream.stack:
        text, depth = stream.stack.pop()
        definition = table.get(text) if _is_word(text) else None
        if definition is None or depth >= MAX_DEPTH:
            out.append(text)
            if definition is not None:
                unexpanded.append(text)
            continue
        stream.consumed = []
        arguments: list[list[Item]] = []
        if definition.nargs:
            if definition.default is not None:
                optional = stream.optional()
                if optional is None:
                    optional = [(t, depth) for t in _texts(definition.default) if t not in drop]
                arguments.append(optional)
            while len(arguments) < definition.nargs:
                arguments.append(stream.argument())
        body = bodies.get(text)
        if body is None:
            body = bodies[text] = [t for t in _texts(definition.body) if t not in drop]
        replacement: list[Item] = []
        for piece in body:
            if piece[0] == "#" and len(piece) == 2 and piece[1].isdigit():
                n = int(piece[1])
                if 1 <= n <= len(arguments):
                    replacement.extend((t, depth + 1) for t, _ in arguments[n - 1])
                    continue
            replacement.append((piece, depth + 1))
        if len(out) + len(stream.stack) + len(replacement) > MAX_TOKENS:
            stream.stack.extend(reversed(stream.consumed))  # leave the arguments in place
            out.append(text)
            unexpanded.append(text)
            continue
        stream.stack.extend(reversed(replacement))
    return Expansion(tuple(out), tuple(dict.fromkeys(unexpanded)))


# --- The token form ------------------------------------------------------------------------------


def _env_name(toks: list[str], i: int) -> tuple[str, int] | None:
    """After `\\begin` or `\\end` at `i`: the environment name and the index after its group."""
    j = _skip_spaces_list(toks, i + 1)
    if j >= len(toks) or toks[j] != "{":
        return None
    k = j + 1
    name: list[str] = []
    while k < len(toks) and toks[k] != "}":
        if toks[k] == "{":
            return None
        name.append(toks[k])
        k += 1
    if k >= len(toks):
        return None
    return "".join(name).strip(), k + 1


def _skip_spaces_list(toks: list[str], i: int) -> int:
    while i < len(toks) and _is_space(toks[i]):
        i += 1
    return i


def strip_delimiters(toks: list[str]) -> list[str]:
    """Remove one outer pair of math delimiters: `\\(…\\)`, `\\[…\\]` or an outer environment.

    The pair is removed only when its opener begins and its matching closer ends the formula
    (surrounding whitespace aside); `\\(a\\) + \\(b\\)` keeps both pairs. `$` is never a delimiter.
    """
    first = _skip_spaces_list(toks, 0)
    last = len(toks) - 1
    while last >= 0 and _is_space(toks[last]):
        last -= 1
    if first >= last:
        return toks
    opener = toks[first]
    if opener in (r"\(", r"\["):
        closer = r"\)" if opener == r"\(" else r"\]"
        if toks[last] != closer:
            return toks
        depth = 0
        for k in range(first, last + 1):
            depth += toks[k] == opener
            depth -= toks[k] == closer
            if depth == 0 and k < last:
                return toks
        return toks[first + 1 : last]
    if opener == r"\begin":
        begun = _env_name(toks, first)
        if begun is None:
            return toks
        name, body_start = begun
        if name not in OUTER_ENVIRONMENTS:
            return toks
        depth = 0
        k = first
        end_at: int | None = None
        while k <= last:
            if toks[k] in (r"\begin", r"\end"):
                parsed = _env_name(toks, k)
                if parsed is not None and parsed[0] == name:
                    depth += 1 if toks[k] == r"\begin" else -1
                    if depth == 0:
                        end_at = k
                        k = parsed[1]
                        break
                    k = parsed[1]
                    continue
            k += 1
        if end_at is None or _skip_spaces_list(toks, k) <= last:
            return toks
        if name in COLUMN_COUNT_ENVIRONMENTS:  # the column count is layout, not the formula
            j = _skip_spaces_list(toks, body_start)
            if j < end_at and toks[j] == "{":
                depth = 0
                for m in range(j, end_at):
                    depth += toks[m] == "{"
                    depth -= toks[m] == "}"
                    if depth == 0:
                        body_start = m + 1
                        break
        return toks[body_start:end_at]
    return toks


def _text_mode_spans(toks: list[str]) -> list[bool]:
    """For each token, whether it lies inside a text-mode argument (its own braces included)."""
    inside = [False] * len(toks)
    i = 0
    while i < len(toks):
        if toks[i] not in TEXT_MODE or inside[i]:
            i += 1
            continue
        j = _skip_spaces_list(toks, i + 1)
        if j < len(toks) and toks[j] == "*":
            j = _skip_spaces_list(toks, j + 1)
        if j >= len(toks) or toks[j] == "}":
            i += 1
            continue
        if toks[j] == "{":
            depth = 0
            k = j
            while k < len(toks):
                depth += toks[k] == "{"
                depth -= toks[k] == "}"
                if depth == 0:
                    break
                k += 1
            end = min(k, len(toks) - 1)
            for m in range(j, end + 1):
                inside[m] = True
            i = end + 1
        else:
            inside[j] = True
            i = j + 1
    return inside


def _balanced(toks: list[str]) -> bool:
    depth = 0
    for text in toks:
        depth += text == "{"
        depth -= text == "}"
        if depth < 0:
            return False
    return depth == 0


def _drop_single_token_braces(toks: list[str]) -> list[str]:
    """`{x}` -> `x` for a group holding exactly one non-space token, innermost groups first."""
    stack: list[list[str]] = [[]]
    for text in toks:
        if text == "{":
            stack.append([])
        elif text == "}":
            group = stack.pop()
            if len(group) == 1 and group[0] != "{" and not _is_space(group[0]):
                stack[-1].extend(group)
            else:
                stack[-1].extend(["{", *group, "}"])
        else:
            stack[-1].append(text)
    return stack[0]


def _serialize(toks: list[str]) -> str:
    out: list[str] = []
    previous = ""
    for text in toks:
        if previous and _is_word(previous) and _LETTER.match(text[:1]):
            out.append(" ")
        out.append(text)
        previous = text
    return "".join(out)


@dataclass(frozen=True, slots=True)
class TokenForm:
    form: str
    unexpanded: tuple[str, ...]  # macros kept unexpanded at a bound (for parse_detail)


def normalize(latex: str, table: Mapping[str, MacroDef]) -> TokenForm:
    """The token form of `latex` under `table` (an effective macro table), with its report.

    The input is NFC-normalized first, so canonically equivalent LaTeX has one form."""
    toks = strip_delimiters(_texts(unicodedata.normalize("NFC", latex)))
    toks = [t for t in toks if t not in DROP]
    expansion = expand(toks, table, DROP)
    toks = [t for t in expansion.tokens if t not in DROP]
    inside = _text_mode_spans(toks)
    kept: list[str] = []
    for text, in_text in zip(toks, inside, strict=True):
        if _is_space(text):
            # one space per run; none right after a control space, also once a drop-list token
            # between them is gone (TeX skips blanks after a control space)
            if in_text and kept[-1:] not in ([" "], [CONTROL_SPACE]):
                kept.append(" ")
            continue
        kept.append(text)
    if _balanced(kept):
        kept = _drop_single_token_braces(kept)
    return TokenForm(_serialize(kept), expansion.unexpanded)


def token_form(latex: str, table: Mapping[str, MacroDef]) -> str:
    """The key form of a formula (D1 §6.2): total, and independent of whether it parses."""
    return normalize(latex, table).form
