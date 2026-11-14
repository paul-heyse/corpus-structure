"""Source-local function declaration facts and the native syntax head kernel."""

from __future__ import annotations

from dataclasses import dataclass

from lark import Tree

from corpus_structure.semantic.analysis_contracts import SymbolDeclaration

from . import _tree, grammar
from .transform import bare, symbol_name


@dataclass(frozen=True)
class EarlyFunctionDeclaration:
    declaration: SymbolDeclaration
    declaration_start: int
    declaration_end: int
    head_start: int
    head_end: int
    scope_start: int
    scope_end: int
    scope_key: str
    source_view_start: int
    source_view_end: int
    source_view_node_id: str
    rule_id: str = "function-definition-1"


def _heads(result: grammar.MathResult):
    if result.tree is None:
        return

    def equations(node):
        if not isinstance(node, Tree):
            return
        if node.data in {"eq", "rel_chain"}:
            yield node
        elif node.data in {
            "_ambig",
            "any_value",
            "formula",
            "relation",
            "value_list",
            "text_join",
            "group_curly_parentheses",
            "group_round_parentheses",
        }:
            for child in node.children:
                yield from equations(child)

    seen = set()
    for node in equations(result.tree):
        if node.data not in {"eq", "rel_chain"} or not node.children:
            continue
        left = node.children[0]
        alternatives = left.children if isinstance(left, Tree) and left.data == "_ambig" else [left]
        for head in alternatives:
            if not isinstance(head, Tree) or head.data != "function_applied":
                continue
            arguments = [token for token in _tree.leaves(head.children[2]) if token.type != "COMMA"]
            if not arguments or any(
                token.type not in grammar._SYMBOL_TOKENS for token in arguments
            ):
                continue
            where = _tree.span(head)
            name = bare(symbol_name(head.children[0], result.latex, result.macros))
            if where is not None and (name, where) not in seen:
                seen.add((name, where))
                yield name, where
