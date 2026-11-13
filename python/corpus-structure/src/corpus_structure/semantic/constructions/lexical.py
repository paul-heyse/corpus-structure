"""Primary positioned lexical observations for the released prose grammar.

Classification is independent of grammar inference. The same policy is used by
legacy direct recognition and the retained primary formal characterization.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

LEXICAL = {
    "WORD": r"[^\W\d_][\w'-]*|\d+(?:\.\d+)?",
    "COPULA": r"(?i:am|is|are|was|were|be|being|been)",
    "NEG": r"(?i:not|never|neither)",
    "MODAL": r"(?i:may|might|can|could|must|should|would|shall|will)",
    "QUANT": r"(?i:all|every|each|some|any|no|most|many|few)",
    "IF": r"(?i:if|unless|provided)",
    "THEN": r"(?i:then)",
    "REL": r"(?i:which|that|who|whom|whose)",
    "CONJ": r"(?i:and|or|nor|but)",
    "PREP": (
        r"(?i:with|of|by|for|in|on|from|than|before|after|because|although|except|until|while|"
        r"without)"
    ),
    "REPORT": r"(?i:says?|said|reports?|reported|claims?|claimed|states?|stated)",
    "QUOTE": r'["“”]',
    "QUESTION": r"\?",
    "PUNCT": r"[.!;:]",
    "COMMA": ",",
    "AUX": r"(?i:have|has|had|been|being|do|does|did)",
    "FUNCTION": r"(?i:define|assume|suppose|let|consider|example|definition|prove|show)",
}


@dataclass(frozen=True, slots=True)
class ProtectedAtom:
    start: int
    end: int
    occurrence: str


@dataclass(frozen=True, slots=True)
class PositionedTerminal:
    terminal: str
    start: int
    end: int
    text: str


def classify(text: str, atoms=()) -> tuple[PositionedTerminal, ...]:
    """Characterize the unprotected original segments, preserving boundary semantics."""
    previous = 0
    ordered = sorted(atoms, key=lambda atom: (atom.start, atom.end))
    for atom in ordered:
        if not previous <= atom.start < atom.end <= len(text):
            raise ValueError("protected atoms overlap or exceed lexical source")
        previous = atom.end
    boundaries = [0, *(p for atom in ordered for p in (atom.start, atom.end)), len(text)]
    result = []
    for terminal, raw in {**LEXICAL, "WS": r"\s+"}.items():
        pattern = (
            raw
            if terminal in {"QUOTE", "QUESTION", "PUNCT", "COMMA", "WS"}
            else r"(?<!\w)(?:" + raw + r")(?!\w)"
        )
        for index in range(0, len(boundaries) - 1, 2):
            start, end = boundaries[index : index + 2]
            result.extend(
                PositionedTerminal(terminal, start + m.start(), start + m.end(), m.group())
                for m in re.finditer(pattern, text[start:end])
            )
    return tuple(result)


def region_terminals(values, text: str, start: int, end: int) -> tuple[PositionedTerminal, ...]:
    """Slice retained characterizations without classifying the text again."""
    result = []
    for row in values:
        if row.end <= start or end <= row.start:
            continue
        a, b = max(start, row.start), min(end, row.end)
        if (a, b) != (row.start, row.end) and row.terminal != "WS":
            raise ValueError("construction region cuts a retained lexical observation")
        result.append(PositionedTerminal(row.terminal, a - start, b - start, text[a:b]))
    return tuple(result)
