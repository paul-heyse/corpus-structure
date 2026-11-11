"""Source-owned inline equation nomination and explicit normalization correspondence."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

INLINE_FORMULA_QUESTION = "source_formula_occurrences"
INLINE_FORMULA_VERSION = "1"
INLINE_FORMULA_POLICY = "captured_inline_equation"
NORMALIZATION_RECIPE = "introduced-inline-equation-unicode-tex-1"
INLINE_FORMULA_OCCURRENCE_FIELDS = dict(
    syntax_parent=None,
    syntax_standing="syntax_only",
    input_policy=INLINE_FORMULA_POLICY,
    mapping="exact_native_field",
)
_EQUATION_CUE = re.compile(r"\busing the equation[ \t]+(?=[A-Za-z][ \t]*=)", re.IGNORECASE)
_LINE_BOUNDARY = re.compile(r"\.(?=$|\s)|[\r\n]")
_LATEX_ATOMS = {"σ": r"\sigma", "µ": r"\mu", "μ": r"\mu"}  # noqa: RUF001 - literal mathematical sigma
_PLAIN_MATH = re.compile(r"[A-Za-z0-9" + re.escape("".join(_LATEX_ATOMS)) + r" \t=+*/().\-]+")


@dataclass(frozen=True, slots=True)
class InlineEquation:
    pointer: str
    start: int
    end: int
    status: Literal["captured", "unsupported", "limited"]
    support_start: int | None = None
    support_end: int | None = None
    primary_input: Mapping[str, Any] | None = None

    def diagnostic(self, outcome: str) -> dict[str, Any]:
        return dict(
            pointer=self.pointer,
            start=self.start,
            end=self.end,
            outcome=outcome,
            input_policy=INLINE_FORMULA_POLICY,
            mapping="unchanged_native_field",
        )


@dataclass(frozen=True, slots=True)
class NormalizationPiece:
    input_start: int
    input_end: int
    relation: Literal["exact", "normalized", "synthetic"]
    source_start: int
    source_end: int


@dataclass(frozen=True, slots=True)
class NormalizedFormalInput:
    text: str
    pieces: tuple[NormalizationPiece, ...]
    recipe: str = NORMALIZATION_RECIPE


def nominate_inline_equations(
    text: str,
    pieces: Iterable[Mapping[str, Any]],
    items: Mapping[str, Mapping[str, Any]],
    selection: Sequence[tuple[str, int, int, str | None]] | None = None,
    *,
    max_chars: int = 2048,
) -> Iterator[InlineEquation]:
    """Examine selected native prose for the existing explicitly introduced equation rule."""
    for piece in pieces:
        pointer = piece.get("item_ref")
        if (
            not isinstance(pointer, str)
            or piece.get("kind") != "native_text"
            or piece.get("source_field") != "text"
            or piece.get("cell_index") is not None
            or items.get(pointer, {}).get("label") not in {"text", "list_item"}
        ):
            continue
        for cue in _EQUATION_CUE.finditer(text, piece["start"], piece["end"]):
            start = cue.end()
            scan_end = min(piece["end"], start + max_chars + 2)
            boundary = _LINE_BOUNDARY.search(text, start, scan_end)
            end = boundary.start() if boundary is not None else scan_end
            support_end = end + 1 if boundary is not None else end
            if selection is not None and not any(
                a <= cue.start() and support_end <= b for _key, a, b, _version in selection
            ):
                continue
            status = (
                "limited"
                if end - start > max_chars
                else "unsupported"
                if boundary is None or boundary.group() != "."
                else "captured"
            )
            yield InlineEquation(pointer, start, end, status, cue.start(), support_end)


def normalize_inline_equation(source: str) -> NormalizedFormalInput | None:
    """Expand only the selected literal atoms; inserted separators remain synthetic."""
    if _PLAIN_MATH.fullmatch(source) is None:
        return None
    output, pieces = [], []
    offset = 0
    for index, character in enumerate(source):
        value = _LATEX_ATOMS.get(character, character)
        output.append(value)
        end = offset + len(value)
        relation = "normalized" if character in _LATEX_ATOMS else "exact"
        if (
            relation == "exact"
            and pieces
            and pieces[-1].relation == "exact"
            and pieces[-1].input_end == offset
        ):
            previous = pieces.pop()
            pieces.append(
                NormalizationPiece(
                    previous.input_start, end, "exact", previous.source_start, index + 1
                )
            )
        else:
            pieces.append(NormalizationPiece(offset, end, relation, index, index + 1))
        offset = end
        if relation == "normalized":
            output.append(" ")
            pieces.append(NormalizationPiece(offset, offset + 1, "synthetic", index + 1, index + 1))
            offset += 1
    return NormalizedFormalInput("".join(output), tuple(pieces))


def mapped_formal_extents(
    formal_input: Mapping[str, Any],
    start: int,
    end: int,
    occurrences: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Read exact original extents from a retained complete correspondence partition.

    Partial unchanged runs map linearly. A transformed atom must be consumed whole;
    no endpoint inside a generated control word obtains source-character authority.
    """
    if not 0 <= start < end <= len(formal_input["text"]):
        raise ValueError("formal represented interval is outside retained input")
    result = []
    position = start
    for row in formal_input["correspondence"]:
        a, b = row["input_start"], row["input_end"]
        left, right = max(start, a), min(end, b)
        if left >= right:
            continue
        if left != position:
            raise ValueError("formal correspondence has an unmapped represented gap")
        position = right
        if row["relation"] == "synthetic":
            continue
        if row["relation"] == "contained_in_atom":
            raise ValueError("recognized LaTeX has no original character map")
        extents = [
            dict(extent)
            for key in row["source_occurrences"]
            for extent in occurrences[key]["extents"]
        ]
        if any(extent.get("synthetic") or "text" not in extent for extent in extents):
            raise ValueError("formal correspondence has no exact literal source")
        if row["relation"] == "normalized":
            if (left, right) != (a, b):
                raise ValueError("formal interval cuts a normalized source atom")
            result.extend(extents)
            continue
        copied = "".join(extent["text"] for extent in extents)
        if copied != formal_input["text"][a:b]:
            raise ValueError("retained exact correspondence differs from represented source")
        offset = 0
        for extent in extents:
            count = len(extent["text"])
            lo, hi = max(left - a, offset), min(right - a, offset + count)
            if lo < hi:
                result.append(
                    {
                        **extent,
                        "start": extent["start"] + lo - offset,
                        "end": extent["start"] + hi - offset,
                        "text": extent["text"][lo - offset : hi - offset],
                    }
                )
            offset += count
    if position != end or not result:
        raise ValueError("formal interval has no complete original-source correspondence")
    merged = []
    for extent in result:
        if (
            merged
            and all(
                merged[-1].get(key) == extent.get(key)
                for key in ("projection", "source_view_id", "native_pointer", "page", "synthetic")
            )
            and merged[-1]["end"] == extent["start"]
        ):
            merged[-1] = {
                **merged[-1],
                "end": extent["end"],
                "text": merged[-1]["text"] + extent["text"],
            }
        else:
            merged.append(extent)
    return tuple(merged)
