"""Located syntax from explicitly introduced equations in retained prose."""

import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

INLINE_FORMULA_QUESTION = "source_formula_occurrences"
INLINE_FORMULA_VERSION = "1"
INLINE_FORMULA_POLICY = "captured_inline_equation"
INLINE_FORMULA_OCCURRENCE_FIELDS = {
    "syntax_parent": None,
    "syntax_standing": "syntax_only",
    "input_policy": INLINE_FORMULA_POLICY,
    "mapping": "exact_native_field",
}

_EQUATION_CUE = re.compile(r"\busing the equation[ \t]+(?=[A-Za-z][ \t]*=)", re.IGNORECASE)
_LINE_BOUNDARY = re.compile(r"\.(?=$|\s)|[\r\n]")
_LATEX_ATOMS = {"\u03c3": r"\sigma", "\u00b5": r"\mu", "\u03bc": r"\mu"}
_PLAIN_MATH = re.compile(r"[A-Za-z0-9" + re.escape("".join(_LATEX_ATOMS)) + r" \t=+*/().\-]+")


@dataclass(frozen=True, slots=True)
class InlineEquation:
    pointer: str
    start: int
    end: int
    status: Literal["captured", "unsupported", "limited"]

    def diagnostic(self, outcome: str) -> dict[str, Any]:
        return {
            "pointer": self.pointer,
            "start": self.start,
            "end": self.end,
            "outcome": outcome,
            "input_policy": INLINE_FORMULA_POLICY,
            "mapping": "unchanged_native_field",
        }


@dataclass(frozen=True, slots=True)
class InlineSymbol:
    start: int
    end: int


def inline_equations(
    text: str,
    pieces: Iterable[Mapping[str, Any]],
    items: Mapping[str, Mapping[str, Any]],
    selection: Sequence[tuple[str, int, int, str | None]] | None,
    *,
    max_chars: int,
) -> Iterator[InlineEquation]:
    """Locate one complete equation inside a single selected native prose piece."""
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
        lo, hi = piece["start"], piece["end"]
        for cue in _EQUATION_CUE.finditer(text, lo, hi):
            start = cue.end()
            scan_end = min(hi, start + max_chars + 2)
            boundary = _LINE_BOUNDARY.search(text, start, scan_end)
            stop = boundary.start() if boundary is not None else scan_end
            selected_end = stop + 1 if boundary is not None else stop
            if selection is not None and not any(
                a <= cue.start() and selected_end <= b for _, a, b, _ in selection
            ):
                continue
            if stop - start > max_chars:
                status = "limited"
            elif boundary is None or boundary.group() != ".":
                status = "unsupported"
            else:
                status = "captured"
            yield InlineEquation(pointer, start, stop, status)


def inline_symbols(
    text: str, equation: InlineEquation, *, seconds: float
) -> tuple[tuple[InlineSymbol, ...], str]:
    """Parse a mapped copy while keeping the original character coordinates authoritative."""
    from .structural_roles import captured_formula_symbols

    if equation.status != "captured":
        return (), equation.status
    source = text[equation.start : equation.end]
    if _PLAIN_MATH.fullmatch(source) is None:
        return (), "unsupported"

    # Complete atom boundaries are reversible. The synthetic TeX control-word
    # separator maps to the same source boundary on both sides.
    parts = []
    boundaries = {0: 0}
    offset = 0
    for position, char in enumerate(source, start=1):
        part = _LATEX_ATOMS.get(char, char)
        parts.append(part)
        offset += len(part)
        boundaries[offset] = position
        if char in _LATEX_ATOMS:
            parts.append(" ")
            offset += 1
            boundaries[offset] = position

    occurrences, outcome = captured_formula_symbols("".join(parts), seconds=seconds)
    symbols = []
    for occurrence in occurrences:
        start = boundaries.get(occurrence["start"])
        end = boundaries.get(occurrence["end"])
        if (
            start is None
            or end is None
            or start >= end
            or occurrence["syntax_parent"] is not None
            or _LATEX_ATOMS.get(source[start:end], source[start:end]) != occurrence["name"]
        ):
            return (), "unmapped"
        symbols.append(InlineSymbol(equation.start + start, equation.start + end))
    return tuple(symbols), outcome
