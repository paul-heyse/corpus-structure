"""Parse-tree helpers shared by the grammar, the transformer and the printer.

Every name read from a tree is the token form (`core/tex.py`) of the source text the node covers,
found through the positions the parser propagates (`propagate_positions=True`), never a print of
the tree's leaves: so a symbol's name agrees with the keys (D1 §6.2).
"""

from __future__ import annotations

from collections.abc import Mapping

from lark import Token, Tree

from corpus_structure.core import tex
from corpus_structure.core.evidence import MacroDef

type Node = Tree[Token] | Token

BRACED = frozenset({"group_curly_parentheses", "script_group"})


def leaves(node: Node) -> list[Token]:
    """The node's tokens in order; of an unresolved `_ambig`, the first reading's (every reading
    covers the same input)."""
    if isinstance(node, Token):
        return [node]
    if node.data == "_ambig":
        first = node.children[0]
        return leaves(first) if isinstance(first, Tree | Token) else []
    out: list[Token] = []
    for child in node.children:
        if isinstance(child, Tree | Token):
            out.extend(leaves(child))
    return out


def span(node: Node) -> tuple[int, int] | None:
    """The node's `[start, end)` in the parsed text, or None when it covers nothing."""
    if isinstance(node, Token):
        if node.start_pos is None or node.end_pos is None:
            return None
        return node.start_pos, node.end_pos
    if node.data != "_ambig" and not node.meta.empty:
        return node.meta.start_pos, node.meta.end_pos
    toks = [t for t in leaves(node) if t.start_pos is not None and t.end_pos is not None]
    if not toks:
        return None
    return min(t.start_pos for t in toks if t.start_pos is not None), max(
        t.end_pos for t in toks if t.end_pos is not None
    )


def text(node: Node, source: str) -> str:
    where = span(node)
    return "" if where is None else source[where[0] : where[1]]


def inner(node: Node) -> tuple[int, int] | None:
    """The span of a braced group's content (`{X_1}` -> `X_1`), else the node's span."""
    if (
        isinstance(node, Tree)
        and node.data in BRACED
        and len(node.children) >= 2
        and isinstance(node.children[0], Token)
        and isinstance(node.children[-1], Token)
    ):
        first, last = node.children[0], node.children[-1]
        if first.end_pos is not None and last.start_pos is not None:
            return first.end_pos, last.start_pos
    return span(node)


def form(node: Node, source: str, table: Mapping[str, MacroDef], braced: bool = False) -> str:
    """The token form of the source the node covers (of its braces' content when `braced`)."""
    where = inner(node) if braced else span(node)
    return "" if where is None else tex.token_form(source[where[0] : where[1]], table)
