"""Early source-local function roles, before interpreted extraction or M13 binding.

Only the admitted function-definition rule supplies roles. Syntax is shared with the
selected expression owner; no symbolic value or later scope observation enters this pass.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from lark import Tree

from corpus_structure.core.evidence import MacroDef, RenditionContent, Segment
from corpus_structure.core.vocab import ANNOTATION_UNIT, SECTION_LIKE
from corpus_structure.semantic.analysis_contracts import (
    SymbolDeclaration,
    prepare_interpretation_context,
)

from . import _tree, grammar
from .prepared import PreparedMathInput
from .spans import MathSpan, math_spans
from .transform import bare, symbol_name


class EarlyMathContextUnavailable(ValueError):
    """An earlier candidate could not supply a complete source declaration basis."""


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


@dataclass(frozen=True)
class PreparedSourceMath:
    spans: tuple[MathSpan, ...]
    definitions: tuple[EarlyFunctionDeclaration, ...]
    operands: tuple[PreparedMathInput, ...]


def _scope_key(source_id: str, segment: Segment) -> str:
    return f"{source_id}:{segment.kind.value}:{segment.start}:{segment.end}"


def _heads(result: grammar.MathResult):
    if result.tree is None:
        return
    def equations(node):
        if not isinstance(node, Tree):
            return
        if node.data in {"eq", "rel_chain"}:
            yield node
        elif node.data in {"_ambig", "any_value", "formula", "relation", "value_list", "text_join",
                            "group_curly_parentheses", "group_round_parentheses"}:
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
            if not arguments or any(token.type not in grammar._SYMBOL_TOKENS for token in arguments):
                continue
            where = _tree.span(head)
            name = bare(symbol_name(head.children[0], result.latex, result.macros))
            if where is not None and (name, where) not in seen:
                seen.add((name, where))
                yield name, where


def prepare_source_math(
    content: RenditionContent,
    *,
    prepared=None,
    macros: Mapping[str, MacroDef],
    constants: Sequence[str] = (),
    source_id: str,
    seconds: float = grammar.PARSE_SECONDS,
    through_offset: int | None = None,
    source_views: Mapping[tuple[int, int], str] | None = None,
    demand: str = "symbolic",
) -> PreparedSourceMath:
    """Prepare preceding admitted definitions and lazily owned expressions.

    Candidate recognition retains the existing per-expression budget. Non-candidates
    remain unrecognized until requested. Unavailable candidates affect only subsequent
    uses in their structural scope, never earlier or outside expressions.
    """
    base = prepare_interpretation_context(prepared, macros=macros, constants=constants,
                                          source_id=source_id, demand=demand)
    all_spans = tuple(math_spans(content))
    indexed = [(index, span) for index, span in enumerate(all_spans)
               if through_offset is None or span.offset <= through_offset]
    regions = [segment for segment in content.document.walk()
               if segment.kind in ANNOTATION_UNIT | SECTION_LIKE]
    definitions: list[EarlyFunctionDeclaration] = []
    issues: list[tuple[str, int, int, grammar.Failure]] = []
    initial: list[tuple[MathSpan, PreparedMathInput, grammar.MathResult | None]] = []
    for index, span in indexed:
        operand = PreparedMathInput(base, span.latex, seconds=seconds,
            source_text=content.text(span.segment), source_start=span.segment.start,
            parse_start=span.offset)
        recognized = None
        # Every admitted function-definition head contains a parenthesized formal
        # argument before '='. This only selects work; the grammar supplies meaning.
        if base.allow_local_definitions and "(" in span.latex.partition("=")[0] and "=" in span.latex:
            recognized = operand.syntax()
            if recognized.tree is None:
                region = min((s for s in regions if s.start <= span.segment.start and span.segment.end <= s.end),
                             key=lambda s: (s.end - s.start, -s.start))
                failure = recognized.failure or grammar.Failure("context_unavailable", "SourceDeclarationUnavailable")
                issues.append((_scope_key(source_id, region), span.segment.end, region.end, failure))
            for name, head in _heads(recognized):
                region = min((s for s in regions if s.start <= span.segment.start and span.segment.end <= s.end),
                             key=lambda s: (s.end - s.start, -s.start))
                start, end = span.segment.end, region.end
                if start >= end:
                    continue
                view_range = (span.offset, span.offset + len(span.latex))
                node_id = f"view:{index}" if source_views is None else source_views.get(view_range)
                if node_id is None:
                    raise EarlyMathContextUnavailable("declaration view is missing from the selected text product")
                key = _scope_key(source_id, region)
                declaration = SymbolDeclaration(name, "function", "source",
                    f"function-definition-1:{span.offset + head[0]}:{span.offset + head[1]}",
                    source_id, key, start, end)
                definitions.append(EarlyFunctionDeclaration(declaration, *view_range,
                    span.offset + head[0], span.offset + head[1], start, end, key,
                    *view_range, node_id))
        initial.append((span, operand, recognized))
    operands = []
    for span, operand, recognized in initial:
        chain = sorted((s for s in regions if s.start <= span.segment.start and span.segment.end <= s.end),
                       key=lambda s: (s.end - s.start, -s.start))
        candidates = [definition for definition in definitions
                      if definition.scope_start <= span.offset < definition.scope_end
                      and definition.scope_key in {_scope_key(source_id, s) for s in chain}]
        visible: dict[str, EarlyFunctionDeclaration] = {}
        for definition in sorted(candidates, key=lambda d: (
            next(i for i, region in enumerate(chain) if _scope_key(source_id, region) == d.scope_key),
            -d.declaration_start)):
            visible.setdefault(definition.declaration.symbol, definition)
        basis = tuple(sorted(visible.values(), key=lambda d: (d.declaration.symbol, d.head_start)))
        context = prepare_interpretation_context(prepared, macros=macros, constants=constants,
            source_id=source_id, scope=_scope_key(source_id, chain[0]),
            scope_chain=tuple(_scope_key(source_id, s) for s in chain),
            declarations=tuple(d.declaration for d in basis), offset=span.offset, demand=demand)
        active_issue = next((failure for key, start, end, failure in issues
                             if start <= span.offset < end and key in {_scope_key(source_id, s) for s in chain}), None)
        context_failure = None
        if active_issue is not None:
            context_failure = grammar.Failure(
                "timeout" if active_issue.category == "timeout" else "context_unavailable",
                "SourceDeclarationUnavailable", detail="earlier source declaration basis unavailable: " + source_id)
        scoped = replace(operand, context=context, source_declarations=basis,
                         source_context_failure=context_failure)
        if recognized is not None:
            # Recognition has no declaration dependencies; preserve the one successful
            # physical parse instead of parsing a candidate again under its new context.
            object.__setattr__(scoped, "_syntax", recognized)
        operands.append(scoped)
    return PreparedSourceMath(tuple(span for _, span in indexed), tuple(definitions), tuple(operands))
