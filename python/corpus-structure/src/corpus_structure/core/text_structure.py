"""Complete source capture and optional native TeX structure, without mathematical recognition.

Coordinates are code points in the named representation. Native parser objects are local to a
single call; only immutable ranges escape. Lexical completeness never asserts syntax support.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from corpus_structure.methods.math.grammar import MathResult

from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.tex import Expansion, MacroBinding, Token, TokenKind, expand, tokens

ADAPTER_ID = "lark-structure-1"
IMPLEMENTATION_REVISION = "text-structure-2"
FRONTEND_REVISION = "sympy-1.14.0-lark-1.3.1"


TEX_COMPONENT_CATEGORIES: Mapping[TokenKind, str] = MappingProxyType(
    {
        "word": "control_word",
        "symbol": "control_symbol",
        "open": "group_open",
        "close": "group_close",
        "param": "parameter",
        "space": "whitespace",
        "char": "character",
    }
)
_PROSE_RUNS = re.compile(r"\s+|[^\s]+")


@dataclass(frozen=True, slots=True)
class TextComponent:
    category: str
    start: int
    end: int


def canonical_partition(
    text: str, math_ranges: Sequence[tuple[int, int]], *, regions: Sequence[TextComponent] = ()
) -> tuple[TextComponent, ...]:
    """Partition canonical prose into uninterpreted runs and declared math into TeX tokens.

    Supplied disjoint regions preserve their boundaries and explicit non-prose categories.
    The TeX scanner owns whole math ranges, including delimiters; origin/markup boundaries
    inside those ranges belong to overlapping mappings rather than splitting a control word.
    """
    mathematical = sorted(math_ranges)
    known = sorted(regions, key=lambda row: (row.start, row.end))
    for rows in (mathematical, [(r.start, r.end) for r in known]):
        previous = 0
        for a, b in rows:
            if not previous <= a < b <= len(text):
                raise ValueError("canonical partition regions overlap or lie outside source")
            previous = b
    out: list[TextComponent] = []
    region_index = 0

    def runs(a: int, b: int, category: str = "text") -> None:
        for match in _PROSE_RUNS.finditer(text, a, b):
            kind = (
                ("whitespace" if match.group().isspace() else "text")
                if category in {"text", "whitespace", "math"}
                else category
            )
            out.append(TextComponent(kind, match.start(), match.end()))

    def prose(a: int, b: int) -> None:
        nonlocal region_index
        while a < b:
            while region_index < len(known) and known[region_index].end <= a:
                region_index += 1
            if region_index == len(known) or known[region_index].start >= b:
                runs(a, b)
                return
            region = known[region_index]
            if a < region.start:
                runs(a, region.start)
                a = region.start
            end = min(b, region.end)
            runs(a, end, region.category)
            a = end

    position = 0
    for a, b in mathematical:
        prose(position, a)
        out.extend(
            TextComponent(TEX_COMPONENT_CATEGORIES[t.kind], a + t.start, a + t.end)
            for t in tokens(text[a:b])
        )
        position = b
    prose(position, len(text))
    return tuple(out)


@dataclass(frozen=True, slots=True)
class ParseView:
    source_start: int
    source_end: int
    start: int
    end: int
    text: str


def parse_view(
    text: str, *, start: int = 0, opener: str | None = None, closer: str | None = None
) -> ParseView:
    """An explicit inner slice; retain environment wrappers and ordinary dollar characters."""
    a, b = 0, len(text)
    if (
        opener
        and closer
        and not opener.startswith(r"\begin")
        and opener != "$"
        and text.startswith(opener)
        and text.endswith(closer)
        and len(text) >= len(opener) + len(closer)
    ):
        a, b = len(opener), len(text) - len(closer)
    while a < b and text[a].isspace():
        a += 1
    while b > a and text[b - 1].isspace():
        b -= 1
    return ParseView(start, start + len(text), start + a, start + b, text[a:b])


@dataclass(frozen=True, slots=True)
class StructureNode:
    node_id: str
    kind: str
    start: int
    end: int
    parent: str | None = None
    role: str = "content"
    name: str | None = None
    argument_index: int | None = None


@dataclass(frozen=True, slots=True)
class TextCapture:
    representation_id: str
    start: int
    end: int
    lexical: tuple[Token, ...]
    view: ParseView
    nodes: tuple[StructureNode, ...] = ()
    structure_outcome: str = "not_requested"
    issues: tuple[str, ...] = ()
    expansion: Expansion | None = None


def capture_text(
    text: str,
    *,
    start: int = 0,
    representation_id: str = "canonical",
    structure: bool = False,
    opener: str | None = None,
    closer: str | None = None,
    macros: Mapping[str, MacroDef] | None = None,
    bindings: Mapping[str, MacroBinding] | None = None,
    expand_macros: bool = True,
) -> TextCapture:
    """Capture every source token; only an explicit structure demand calls the positioned grammar.

    ``macros`` supplies declared structural arguments. Unless ``expand_macros=False``, an
    explicit table also requests bounded expansion against named artifacts; callers archive
    binding artifacts with the resulting product. ``macros=None`` leaves expansion unrequested.
    """
    from dataclasses import replace

    lexical = tuple(replace(t, start=t.start + start, end=t.end + start) for t in tokens(text))
    view = parse_view(text, start=start, opener=opener, closer=closer)
    expansion = (
        expand(lexical, macros, source_ref=representation_id, bindings=bindings)
        if macros is not None and expand_macros
        else None
    )
    nodes, outcome, issues = (
        _structure(view, macros or {}) if structure else ((), "not_requested", ())
    )
    return TextCapture(
        representation_id,
        start,
        start + len(text),
        lexical,
        view,
        nodes,
        outcome,
        issues,
        expansion,
    )


def _structure(
    view: ParseView, macros: Mapping[str, MacroDef]
) -> tuple[tuple[StructureNode, ...], str, tuple[str, ...]]:
    """Project the admitted mathematical syntax tree without constructing native values.

    This is the PDF frontend's structure recipe, not the retired general TeX walker.
    Unrecognized input retains complete lexical capture; it does not acquire invented
    nodes or a successful structural-coverage claim.
    """
    from corpus_structure.methods.math import grammar

    return syntax_structure(view, grammar.syntax(view.text, macros=macros))


def syntax_structure(
    view: ParseView, result: MathResult
) -> tuple[tuple[StructureNode, ...], str, tuple[str, ...]]:
    """Project an already prepared positioned tree; never reparse or evaluate it."""
    from lark import Token, Tree

    from corpus_structure.methods.math import _tree

    if result.latex != view.text:
        raise ValueError("syntax structure input differs from its recognized-text view")
    if result.tree is None:
        issue = result.failure.category if result.failure is not None else "no_syntax_tree"
        outcome = "partial" if issue == "unknown_command" else "invalid"
        return (), outcome, (issue,)
    out: list[StructureNode] = []

    def visit(node: _tree.Node, parent: str | None = None) -> None:
        bounds = _tree.span(node)
        if bounds is None:
            return
        key = f"s{len(out)}"
        kind = node.data if isinstance(node, Tree) else "token"
        name = str(node) if isinstance(node, Token) else None
        out.append(
            StructureNode(key, kind, view.start + bounds[0], view.start + bounds[1], parent,
                          "alternative" if kind == "_ambig" else "content", name)
        )
        if isinstance(node, Tree):
            for child in node.children:
                if isinstance(child, Tree | Token):
                    visit(child, key)

    visit(result.tree)
    issues = () if result.failure is None else (result.failure.category,)
    return tuple(out), "partial" if issues else "available", issues


def source_atoms(
    length: int, math: tuple[tuple[int, int], ...], references: tuple[tuple[int, int], ...]
) -> tuple[tuple[int, int, str], ...]:
    """Source-bound atom projection shared with consumer-owned sentence layouts."""
    rows = sorted([(a, b, "math") for a, b in math] + [(a, b, "reference") for a, b in references])
    out: list[tuple[int, int, str]] = []
    position = 0
    for a, b, role in rows:
        if not 0 <= a < b <= length:
            raise ValueError("atom outside canonical source extent")
        if a < position:
            continue
        out.append((a, b, role))
        position = b
    return tuple(out)
