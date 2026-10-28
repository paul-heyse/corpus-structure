"""Math reader: one extended Lark grammar as the single authority for reading LaTeX math (ADR-0009).

SymPy 1.14's shipped ``latex.lark`` (unedited) + ``extension.lark`` (``%extend``/``%override``) +
terminals generated from the rendition's macro table. See ``api`` for the contract. Keys use the
token form (``printer``, D1 §6.2), never the tree (ADR-0012).
"""

from .api import (Ambiguous, MathResult, NotParsed, Occurrence, bare_unit, canonical, occurrences_in_span, parse,
                  to_sympy, tree_token_agreement)
from .printer import DROP_LIST, macro_table, token_form
from .build import MacroClass, classify
from .to_sympy import NotRepresentable

__all__ = ["Ambiguous", "bare_unit", "DROP_LIST", "MacroClass", "MathResult", "NotParsed", "NotRepresentable", "Occurrence",
           "canonical", "classify", "macro_table", "occurrences_in_span", "parse", "to_sympy", "token_form",
           "tree_token_agreement"]
