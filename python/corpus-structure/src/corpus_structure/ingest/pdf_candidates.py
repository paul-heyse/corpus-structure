"""Compact inline-math candidate capture before native page cleanup; no second PDF parser."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_MATH_FONT = re.compile(r"(?:CMMI|CMSY|CMEX|MSAM|MSBM|Math|Symbol|STIX)", re.I)
_MATH_TOKEN = re.compile(r"[=<>≤≥∈∉∪∩∑∏∫√∞α-ωΑ-Ω]|\\[A-Za-z]+|\b[A-Za-z]\s*\^")


@dataclass(frozen=True, slots=True)
class InlineCandidate:
    page_no: int
    text: str
    left: float
    top: float
    right: float
    bottom: float
    origin: str
    font: str | None
    basis: str


@dataclass(frozen=True, slots=True)
class CandidatePage:
    page_no: int
    has_words: bool
    has_chars: bool
    candidates: tuple[InlineCandidate, ...]


def capture_candidates(page: Any) -> CandidatePage:
    """Enumerate available native words once; unknown extraction is not empty evidence.

    These are attributed discovery rules, not a universal mathematical-absence classifier.
    Recognition coverage is qualified separately over demanded source views.
    """
    parsed = page.parsed_page
    if parsed is None:
        return CandidatePage(page.page_no, False, False, ())
    rows = []
    for cell in parsed.word_cells:
        font = getattr(cell, "font_name", None)
        font_match = font is not None and _MATH_FONT.search(font) is not None
        token_match = _MATH_TOKEN.search(cell.text) is not None
        if not cell.text.strip() or not (font_match or token_match):
            continue
        box = cell.rect.to_bounding_box()
        rows.append(InlineCandidate(page.page_no, cell.text, box.l, box.t, box.r, box.b,
            box.coord_origin.value, font,
            "native-math-font-v1" if font_match else "native-math-token-v1"))
    return CandidatePage(page.page_no, parsed.has_words, parsed.has_chars, tuple(rows))
