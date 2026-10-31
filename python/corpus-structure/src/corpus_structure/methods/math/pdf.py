"""Native formula occurrences enter the existing demand-driven mathematical frontend.

Recognition is a prerequisite, not inferred from a FORMULA label or changed text. Offsets
remain in recognized LaTeX; a Docling item's page box does not establish glyph positions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from . import grammar
from .prepared import PreparedMathInput

if TYPE_CHECKING:
    from corpus_structure.semantic.analysis_contracts import PreparedInterpretationContext

RecognitionHealth = Literal["succeeded", "failed", "unknown", "not_requested"]


class FormulaRecognitionUnavailable(ValueError):
    """The selected occurrence has no attributable successful recognition."""


@dataclass(frozen=True, slots=True)
class FormulaOccurrence:
    """A conversion-local occurrence, retaining both native text meanings unchanged."""

    conversion_digest: str
    item_pointer: str
    recognized_latex: str
    original_text: str
    recognition_health: RecognitionHealth
    kind: grammar.Kind = "any_value"

    def __post_init__(self) -> None:
        if re.fullmatch(r"[0-9a-f]{64}", self.conversion_digest) is None:
            raise ValueError("formula requires an immutable conversion content digest")
        if re.fullmatch(r"#/texts/(0|[1-9][0-9]*)", self.item_pointer) is None:
            raise ValueError("formula requires a conversion-qualified native text-item pointer")
        if self.recognition_health not in {"succeeded", "failed", "unknown", "not_requested"}:
            raise ValueError("unknown recognition health")
        if self.kind not in grammar.STARTS:
            raise ValueError("unsupported mathematical start kind")
        if self.recognition_health == "succeeded" and not self.recognized_latex.strip():
            raise ValueError("successful formula recognition requires nonempty recognized text")

    @property
    def identity(self) -> tuple[str, str]:
        return self.conversion_digest, self.item_pointer

    def prepare(self, context: PreparedInterpretationContext) -> PreparedFormulaOccurrence:
        """Bind admitted context without eagerly parsing, interpreting or assessing."""
        if self.recognition_health != "succeeded":
            raise FormulaRecognitionUnavailable(self.recognition_health)
        if context.macros:
            raise ValueError("PDF native formula input cannot acquire an HTML macro environment")
        return PreparedFormulaOccurrence(
            self,
            PreparedMathInput(
                context,
                self.recognized_latex,
                kind=self.kind,
                source_text=self.recognized_latex,
                source_start=0,
                parse_start=0,
            ),
        )


@dataclass(frozen=True, slots=True)
class FormulaSymbolOccurrence:
    conversion_digest: str
    item_pointer: str
    ordinal: int
    symbol: grammar.Occurrence

    @property
    def identity(self) -> tuple[str, str, int]:
        return self.conversion_digest, self.item_pointer, self.ordinal


@dataclass(frozen=True, slots=True)
class PreparedFormulaOccurrence:
    source: FormulaOccurrence
    operand: PreparedMathInput

    def stage_key(self, demand: str) -> tuple[object, ...]:
        """Occurrence custody stays qualified even when equal formula values share work."""
        return (*self.source.identity, self.operand.stage_key(demand))

    def occurrences(self) -> tuple[FormulaSymbolOccurrence, ...]:
        """Contextual occurrence inventory, independent of native simplification."""
        return tuple(
            FormulaSymbolOccurrence(*self.source.identity, ordinal, symbol)
            for ordinal, symbol in enumerate(self.operand.interpretation().occurrences)
        )
