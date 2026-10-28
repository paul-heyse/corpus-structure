"""Math reader: one extended Lark grammar as the single authority for reading LaTeX math (ADR-0009).

SymPy 1.14's shipped ``latex.lark`` (unedited) + ``extension.lark`` (``%extend``/``%override``) +
terminals generated from the rendition's macro table. See ``api`` for the contract.
"""

from .api import (Ambiguous, MathResult, NotParsed, Occurrence, bare_unit, canonical, occurrences_in_span, parse,
                  to_sympy)
from .build import MacroClass, classify
from .to_sympy import NotRepresentable

__all__ = ["Ambiguous", "bare_unit", "MacroClass", "MathResult", "NotParsed", "NotRepresentable", "Occurrence", "canonical",
           "classify", "occurrences_in_span", "parse", "to_sympy"]
