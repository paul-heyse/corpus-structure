"""Read the wider original affine producer scope without changing the frozen query."""

import re
from dataclasses import asdict, dataclass
from itertools import pairwise
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.methods.inline_formula_occurrences import inline_equations, inline_symbols
from corpus_structure.methods.witnessed_source_links import DECLARATION, RECAP
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.settings import Settings

_DECLARATION_CUE = re.compile(
    r"\b(?:let|where|suppose|define)\s+([a-z])\s+"
    r"(?:be|denotes?|is|represents?)\b",
    re.IGNORECASE,
)
_LINE_SPACING = str.maketrans("\n\t", "  ")


@dataclass(frozen=True, slots=True)
class OrderedSourceExtent:
    """A native item and an item-relative half-open extent."""

    pointer: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class OrderedRecapCandidate:
    """Located input for a new witness; does not confer admission authority."""

    passage: str
    scope: str
    section: str
    paragraph: str
    inline_group: str
    symbol: str
    symbol_site: tuple[OrderedSourceExtent, ...]
    description: tuple[OrderedSourceExtent, ...]
    declared_name: tuple[OrderedSourceExtent, ...]
    recap: OrderedSourceExtent
    equation: OrderedSourceExtent


def _children(node):
    return tuple(item.get("$ref") for item in node.get("children", ()))


def _parent(node):
    return (node.get("parent") or {}).get("$ref")


def _ordered_extents(parts, start, end):
    return tuple(
        OrderedSourceExtent(pointer, max(a, start) - a, min(b, end) - a)
        for pointer, a, b in parts
        if a < end and start < b
    )


def inspect_ordered_recapped_declarations(text, pieces, items, passage):
    """Locate one explicit declaration across a native inline text wrapper.

    Only complete selected body text children of a single inline wrapper qualify.
    Replacing native line breaks with spaces for matching preserves all character
    offsets. The returned addresses refer to original items and omit synthetic text.
    """
    if not 0 <= passage.start < passage.end <= len(text) or passage.end - passage.start > 4096:
        return ()
    selected = tuple(
        piece for piece in pieces if piece["start"] < passage.end and passage.start < piece["end"]
    )
    if (
        not selected
        or len(selected) > 128
        or selected[0]["start"] != passage.start
        or selected[-1]["end"] != passage.end
        or any(left["end"] != right["start"] for left, right in pairwise(selected))
    ):
        return ()
    physical = {}
    for piece in selected:
        if piece.get("kind") != "native_text" or piece.get("source_field", "text") != "text":
            continue
        pointer = piece.get("item_ref")
        a, b = piece["start"], piece["end"]
        node = items.get(pointer, {})
        if (
            isinstance(pointer, str)
            and passage.start <= a < b <= passage.end
            and "cell_index" not in piece
            and node.get("content_layer") == "body"
            and node.get("label") == "text"
            and node.get("text") == text[a:b]
        ):
            if pointer in physical:
                return ()
            physical[pointer] = (pointer, a, b)
    results = []
    for use_pointer, a, b in physical.values():
        section = _parent(items[use_pointer])
        if not isinstance(section, str):
            continue
        container = items.get(section, {})
        if container.get("label") != "section" or container.get("content_layer") != "body":
            continue
        siblings = _children(container)
        if siblings.count(use_pointer) != 1:
            continue
        use = RECAP.match(text[a:b].translate(_LINE_SPACING))
        if use is None:
            continue
        preceding_text = text[passage.start : a]
        symbol = use["symbol"]
        cues = [
            passage.start + m.start(1)
            for m in _DECLARATION_CUE.finditer(preceding_text)
            if m[1] == symbol
        ]
        if len(cues) != 1:
            continue
        for paragraph in siblings[: siblings.index(use_pointer)]:
            if not isinstance(paragraph, str):
                continue
            owner = items.get(paragraph, {})
            groups = _children(owner)
            if (
                owner.get("label") != "text"
                or owner.get("content_layer") != "body"
                or _parent(owner) != section
                or owner.get("text") != ""
                or len(groups) != 1
                or siblings.count(paragraph) != 1
            ):
                continue
            (inline,) = groups
            if not isinstance(inline, str):
                continue
            group = items.get(inline, {})
            children = _children(group)
            if (
                group.get("label") != "inline"
                or group.get("content_layer") != "body"
                or _parent(group) != paragraph
                or not 2 <= len(children) <= 32
                or len(set(children)) != len(children)
                or not all(
                    child in physical and _parent(items[child]) == inline for child in children
                )
            ):
                continue
            parts = tuple(physical[child] for child in children)
            start, end = parts[0][1], parts[-1][2]
            if end > a or any(left[2] != right[1] for left, right in pairwise(parts)):
                continue
            declaration = DECLARATION.match(text[start:end].translate(_LINE_SPACING))
            if (
                declaration is None
                or start + declaration.start("symbol") != cues[0]
                or declaration["symbol"] != symbol
                or declaration["name"] != use["name"]
                or not declaration["description"].startswith(
                    "a " + declaration["family"] + " with parameters "
                )
            ):
                continue

            symbol_site, description, declared_name = (
                _ordered_extents(parts, start + lo, start + hi)
                for lo, hi in map(declaration.span, ("symbol", "description", "name"))
            )

            results.append(
                OrderedRecapCandidate(
                    passage.passage_id,
                    passage.scope,
                    section,
                    paragraph,
                    inline,
                    symbol,
                    symbol_site,
                    description,
                    declared_name,
                    OrderedSourceExtent(use_pointer, 0, use.end("symbol")),
                    OrderedSourceExtent(use_pointer, *use.span("equation")),
                )
            )
    return tuple(results)


def main():
    source_input = StructuralInput.model_validate_json(
        (
            Path(__file__).resolve().parents[1] / "2026-11-09_pm2-adoption/raw/query-inputs.json"
        ).read_bytes()
    )
    (query,) = [p for p in source_input.passages if p.passage_id == "affine"]
    (source,) = [s for s in source_input.sources if s.identity == query.source_ref]
    with (
        open_runtime_engine(Settings(), "pm2-affine-ordered-source", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        conn.execute(
            select(func.ops.validate_structural_source(cast(source.model_dump(mode="json"), JSONB)))
        ).one()
        view = load_source_view(
            conn,
            source.source_view_id,
            analysis=False,
            read_budget=PublishedReadBudget(max_rows=100_000, max_bytes=256 * 1024 * 1024),
        )
    if view.text[query.start : query.end] != query.text:
        raise ValueError("the query differs from the original selected projection")
    items = {item["self_ref"]: item for item in (*view.ancestors, *view.items)}
    (first,) = [p for p in view.pieces if p.get("item_ref") == "#/texts/4475"]
    producer = SimpleNamespace(
        start=first["start"],
        end=query.end,
        passage_id="affine-witness-diagnostic",
        scope=query.scope,
    )
    assert not inspect_ordered_recapped_declarations(view.text, view.pieces, items, query)
    (candidate,) = inspect_ordered_recapped_declarations(view.text, view.pieces, items, producer)
    children = items[candidate.inline_group]["children"]
    reordered = {
        **items,
        candidate.inline_group: {
            **items[candidate.inline_group],
            "children": list(reversed(children)),
        },
    }
    foreign = {
        **items,
        candidate.recap.pointer: {
            **items[candidate.recap.pointer],
            "parent": {"$ref": "#/body"},
        },
    }
    synthetic = [
        {**p, "kind": "synthetic_separator"} if p.get("item_ref") == "#/texts/4476" else p
        for p in view.pieces
    ]
    assert not inspect_ordered_recapped_declarations(view.text, view.pieces, reordered, producer)
    assert not inspect_ordered_recapped_declarations(view.text, view.pieces, foreign, producer)
    assert not inspect_ordered_recapped_declarations(view.text, synthetic, items, producer)
    selected = ((query.passage_id, query.start, query.end, query.effective_version),)
    (equation,) = tuple(inline_equations(view.text, view.pieces, items, selected, max_chars=2048))
    symbols, outcome = inline_symbols(view.text, equation, seconds=0.5)
    assert outcome == "parsed"
    assert candidate.symbol == "Z"
    assert [part.pointer for part in candidate.declared_name] == ["#/texts/4476", "#/texts/4477"]
    equation_piece = next(p for p in view.pieces if p.get("item_ref") == equation.pointer)
    assert candidate.equation.pointer == equation.pointer
    assert (
        candidate.equation.start + equation_piece["start"],
        candidate.equation.end + equation_piece["start"],
    ) == (equation.start, equation.end)
    print(
        canonical_bytes(
            {
                "source": source.model_dump(mode="json"),
                "query": [query.start, query.end],
                "producer_scope": [producer.start, producer.end],
                "candidate": asdict(candidate),
                "refused": [
                    "query_scope_only",
                    "reordered_children",
                    "foreign_recap",
                    "synthetic_name_piece",
                ],
                "equation_occurrences": [
                    {
                        "literal": view.text[s.start : s.end],
                        "native": [
                            s.start - equation_piece["start"],
                            s.end - equation_piece["start"],
                        ],
                    }
                    for s in symbols
                ],
                "qualification": "candidate_only",
            }
        ).decode()
    )


if __name__ == "__main__":
    main()
