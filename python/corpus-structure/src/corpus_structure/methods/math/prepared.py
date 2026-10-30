"""Owned mathematical preparation at one operation's validity boundary.

Contexts are compiled semantic inputs. Parser trees remain private physical products;
consumers share readings and lazily requested immutable SymPy values, never source identity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from . import grammar
from .transform import NotRepresentable

if TYPE_CHECKING:
    from corpus_structure.semantic.analysis_contracts import PreparedInterpretationContext

_UNSET = object()


@dataclass(frozen=True)
class PreparedMathInput:
    context: PreparedInterpretationContext
    latex: str
    kind: grammar.Kind | None = None
    seconds: float = grammar.PARSE_SECONDS
    _reading: grammar.MathResult | None = field(default=None, init=False, repr=False, compare=False)
    _value: Any = field(default=_UNSET, init=False, repr=False, compare=False)
    _unrepresentable: str | None = field(default=None, init=False, repr=False, compare=False)

    @property
    def key(self) -> tuple[str, str, str]:
        return self.latex, self.kind or self.context.kind, self.context.stage_key("symbolic")

    def reading(self) -> grammar.MathResult:
        if self._reading is not None:
            return self._reading
        kind = self.kind or self.context.kind
        if kind not in grammar.STARTS:
            raise ValueError(f"unsupported mathematical kind {kind!r}")
        result = grammar.parse(
            self.latex,
            kind,
            self.context.macros,
            self.context.grammar_context,
            seconds=self.seconds,
        )
        if result.failure is None or result.failure.category != "timeout":
            object.__setattr__(self, "_reading", result)
        return result

    def symbolic_value(self) -> Any:
        if self._value is not _UNSET:
            return self._value
        if self._unrepresentable is not None:
            raise NotRepresentable(self._unrepresentable)
        result = self.reading()
        try:
            with grammar.deadline(self.seconds):
                value = grammar.to_sympy(result)
        except NotRepresentable as error:
            object.__setattr__(self, "_unrepresentable", str(error))
            raise
        self.context.validate_result(
            produced=("lexical", "occurrences", "interpretation", "symbolic"),
            interpretation=result.status.value,
        )
        object.__setattr__(self, "_value", value)
        return value
