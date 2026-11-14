"""Native formula occurrences enter the existing demand-driven mathematical frontend.

Recognition is a prerequisite, not inferred from a FORMULA label or changed text. Offsets
remain in recognized LaTeX; a Docling item's page box does not establish glyph positions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource, DeclaredSourcePin

from . import grammar
from .prepared import PreparedMathInput

if TYPE_CHECKING:
    from corpus_structure.semantic.analysis_contracts import PreparedInterpretationContext

RecognitionHealth = Literal["succeeded", "failed", "unknown", "not_requested"]


class FormulaRecognitionUnavailable(ValueError):
    """The selected occurrence has no attributable successful recognition."""


def _validate_formula(occurrence):
    if re.fullmatch(r"#/texts/(0|[1-9][0-9]*)", occurrence.item_pointer) is None:
        raise ValueError("formula requires an original-relative native text-item pointer")
    if occurrence.recognition_health not in {"succeeded", "failed", "unknown", "not_requested"}:
        raise ValueError("unknown recognition health")
    if occurrence.kind not in grammar.STARTS:
        raise ValueError("unsupported mathematical start kind")
    if occurrence.recognition_health == "succeeded" and not occurrence.recognized_latex.strip():
        raise ValueError("successful formula recognition requires nonempty recognized text")


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
        _validate_formula(self)

    @property
    def identity(self) -> tuple[str, str]:
        return self.conversion_digest, self.item_pointer

    def prepare(self, context: PreparedInterpretationContext) -> PreparedFormulaOccurrence:
        """Bind admitted context without eagerly parsing, interpreting or assessing."""
        return _prepare_formula(self, context)


@dataclass(frozen=True, slots=True)
class DeclaredFormulaOccurrence:
    """Formula located in one authentic original-relative semantic source member."""

    source: DeclaredSourcePin
    item_pointer: str
    recognized_latex: str
    original_text: str
    recognition_health: RecognitionHealth
    kind: grammar.Kind = "any_value"

    def __post_init__(self):
        if not isinstance(self.source, DeclaredSourcePin):
            raise TypeError("declared formula requires its exact semantic source pin")
        _validate_formula(self)

    @property
    def identity(self):
        return self.source.content, self.item_pointer

    def prepare(self, context: PreparedInterpretationContext) -> PreparedFormulaOccurrence:
        return _prepare_formula(self, context)


def _prepare_formula(source, context):
    if source.recognition_health != "succeeded":
        raise FormulaRecognitionUnavailable(source.recognition_health)
    if context.macros:
        raise ValueError("PDF native formula input cannot acquire an HTML macro environment")
    return PreparedFormulaOccurrence(source, PreparedMathInput(
        context, source.recognized_latex, kind=source.kind,
        source_text=source.recognized_latex, source_start=0, parse_start=0,
    ))



def formula_occurrence(source, item, health):
    """Preserve the actual address profile; no legacy digest or row is synthesized."""
    values = (item["self_ref"], item.get("text", ""), item.get("orig", ""), health)
    if isinstance(source, DeclaredNativeFrameSource):
        return DeclaredFormulaOccurrence(source.pin, *values)
    return FormulaOccurrence(source.native_product.content_digest, *values)


def formula_matches_source(occurrence, source):
    if isinstance(occurrence, DeclaredFormulaOccurrence):
        return isinstance(source, DeclaredNativeFrameSource) and occurrence.source == source.pin
    return not isinstance(source, DeclaredNativeFrameSource) and occurrence.conversion_digest == source.native_product.content_digest


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
class DeclaredFormulaSymbolOccurrence:
    source: DeclaredSourcePin
    item_pointer: str
    ordinal: int
    symbol: grammar.Occurrence

    @property
    def identity(self):
        return self.source.content, self.item_pointer, self.ordinal


@dataclass(frozen=True, slots=True)
class PreparedFormulaOccurrence:
    source: FormulaOccurrence | DeclaredFormulaOccurrence
    operand: PreparedMathInput

    def stage_key(self, demand: str) -> tuple[object, ...]:
        """Occurrence custody stays qualified even when equal formula values share work."""
        return (*self.source.identity, self.operand.stage_key(demand))

    def occurrences(self) -> tuple[FormulaSymbolOccurrence | DeclaredFormulaSymbolOccurrence, ...]:
        """Contextual occurrence inventory, independent of native simplification."""
        if isinstance(self.source, DeclaredFormulaOccurrence):
            return tuple(DeclaredFormulaSymbolOccurrence(self.source.source, self.source.item_pointer, ordinal, symbol) for ordinal, symbol in enumerate(self.operand.interpretation().occurrences))
        return tuple(FormulaSymbolOccurrence(*self.source.identity, ordinal, symbol) for ordinal, symbol in enumerate(self.operand.interpretation().occurrences))
