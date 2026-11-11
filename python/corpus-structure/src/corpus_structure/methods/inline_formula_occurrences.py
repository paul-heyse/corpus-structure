"""Read introduced inline equations from exact retained formal products; no parsing."""

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from corpus_structure.semantic.characterization import annotation_reference
from corpus_structure.semantic.formal_sources import (
    INLINE_FORMULA_OCCURRENCE_FIELDS as INLINE_FORMULA_OCCURRENCE_FIELDS,
)
from corpus_structure.semantic.formal_sources import (
    INLINE_FORMULA_POLICY as INLINE_FORMULA_POLICY,
)
from corpus_structure.semantic.formal_sources import (
    INLINE_FORMULA_QUESTION as INLINE_FORMULA_QUESTION,
)
from corpus_structure.semantic.formal_sources import (
    INLINE_FORMULA_VERSION as INLINE_FORMULA_VERSION,
)
from corpus_structure.semantic.formal_sources import (
    NORMALIZATION_RECIPE,
    mapped_formal_extents,
)
from corpus_structure.semantic.formal_sources import (
    InlineEquation as InlineEquation,
)


@dataclass(frozen=True, slots=True)
class InlineSymbol:
    start: int
    end: int
    primary_node: Mapping[str, Any] | None = None
    parent_occurrence: str | None = None


def _inputs(
    primary_layers, projection, text, *, source_view_id=None, pointer=None, start=None, end=None
):
    for pin, report in primary_layers.items():
        body = report.payload
        occurrences = {row["local_id"]: row for row in body["occurrences"]}
        for annotation in body["annotations"]:
            value = annotation.get("formal_input")
            if (
                annotation["kind"] != "formal.input"
                or annotation.get("native_label") != "introduced_inline_equation"
                or value is None
                or value.get("normalization_recipe") != NORMALIZATION_RECIPE
            ):
                continue
            parent = occurrences[value["parent_occurrence"]]
            extents = parent["extents"]
            if len(extents) != 1:
                continue
            extent = extents[0]
            if (
                extent.get("synthetic")
                or extent["projection"] != projection
                or (source_view_id is not None and extent["source_view_id"] != source_view_id)
                or (pointer is not None and extent["native_pointer"] != pointer)
            ):
                continue
            a, b = extent.get("start"), extent.get("end")
            if (
                type(a) is not int
                or type(b) is not int
                or not 0 <= a < b <= len(text)
                or extent.get("text") != text[a:b]
            ):
                continue
            if (
                (start is not None and a != start)
                or (end is not None and b != end)
                or value.get("original_text") != text[a:b]
            ):
                continue
            yield pin, body, annotation, value, occurrences, extent


def inline_equations(
    text: str,
    pieces: Iterable[Mapping[str, Any]],
    items: Mapping[str, Mapping[str, Any]],
    selection: Sequence[tuple[str, int, int, str | None]] | None,
    *,
    max_chars: int,
    primary_layers=None,
    projection=None,
    source_view_id=None,
) -> Iterator[InlineEquation]:
    """Enumerate retained nominations, including their source-bound failure outcomes."""
    if primary_layers is None or projection is None:
        return
    grouped = {}
    for row in _inputs(primary_layers, projection, text, source_view_id=source_view_id):
        pin, _body, annotation, value, occurrences, extent = row
        pointer, a, b = extent["native_pointer"], extent["start"], extent["end"]
        if pointer not in items or not any(
            piece.get("item_ref") == pointer and piece["start"] <= a < b <= piece["end"]
            for piece in pieces
        ):
            continue
        support = [
            part for key in annotation["occurrences"] for part in occurrences[key]["extents"]
        ]
        if any(
            part["projection"] != projection
            or part["native_pointer"] != pointer
            or part.get("synthetic")
            for part in support
        ):
            continue
        lo, hi = min(part["start"] for part in support), max(part["end"] for part in support)
        if selection is not None and not any(
            left <= lo and hi <= right for _key, left, right, _version in selection
        ):
            continue
        category = value.get("diagnostic", {}).get("category")
        status = (
            "limited"
            if category == "inline_nomination_limited" or b - a > max_chars
            else "unsupported"
            if category == "inline_nomination_unsupported"
            else "captured"
        )
        grouped.setdefault((pointer, a, b), []).append(
            InlineEquation(
                pointer,
                a,
                b,
                status,
                lo,
                hi,
                annotation_reference(pin, annotation["local_id"]).values(),
            )
        )
    for key in sorted(grouped, key=lambda value: (value[1], value[2], value[0])):
        rows = grouped[key]
        if len(rows) == 1:
            yield rows[0]
        else:
            first = rows[0]
            yield InlineEquation(
                first.pointer,
                first.start,
                first.end,
                "captured",
                first.support_start,
                first.support_end,
            )


def inline_symbols(
    text: str,
    equation: InlineEquation,
    *,
    seconds: float | None = None,
    primary_layers=None,
    projection=None,
    source_view_id=None,
) -> tuple[tuple[InlineSymbol, ...], str]:
    """Map retained complete symbol intervals through the published normalization map."""
    if equation.status != "captured":
        return (), equation.status
    if primary_layers is None or projection is None:
        return (), "unsupported"
    roots = list(
        _inputs(
            primary_layers,
            projection,
            text,
            source_view_id=source_view_id,
            pointer=equation.pointer,
            start=equation.start,
            end=equation.end,
        )
    )
    if equation.primary_input is not None:
        roots = [
            row
            for row in roots
            if annotation_reference(row[0], row[2]["local_id"]).values() == equation.primary_input
        ]
    if len(roots) != 1:
        return (), "ambiguous" if roots else "unsupported"
    pin, body, root, value, occurrences, _extent = roots[0]
    if value["syntax_outcome"] != "complete" or value.get("symbol_outcome") != "complete":
        return (), "ambiguous" if value[
            "syntax_outcome"
        ] == "ambiguous" else "timeout" if value.get("diagnostic", {}).get(
            "category"
        ) == "timeout" else "unsupported"
    symbols = []
    for annotation in body["annotations"]:
        formal = annotation.get("formal")
        if (
            annotation["kind"] != "formal.symbol"
            or formal is None
            or formal["input_id"] != root["local_id"]
        ):
            continue
        if formal.get("symbol_parent") is not None:
            return (), "unmapped"
        try:
            extents = mapped_formal_extents(value, formal["start"], formal["end"], occurrences)
        except ValueError:
            return (), "unmapped"
        if (
            len(extents) != 1
            or extents[0]["native_pointer"] != equation.pointer
            or not equation.start <= extents[0]["start"] < extents[0]["end"] <= equation.end
        ):
            return (), "unmapped"
        symbols.append(
            InlineSymbol(
                extents[0]["start"],
                extents[0]["end"],
                annotation_reference(pin, annotation["local_id"]).values(),
                value["parent_occurrence"],
            )
        )
    return tuple(sorted(symbols, key=lambda symbol: (symbol.start, symbol.end))), "parsed"
