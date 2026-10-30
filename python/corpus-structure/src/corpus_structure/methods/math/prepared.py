"""One operation owns capture, recognition, contextual meaning and demanded native work.

Native handles and attempt diagnostics remain here. A weaker request never starts a
stronger stage, and a timeout never becomes a reusable semantic conclusion.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from functools import cached_property
from typing import TYPE_CHECKING, Any, Literal

import sympy
from lark import Token, Tree

from corpus_structure.core import tex
from corpus_structure.core.vocab import ParseOutcome

from . import _tree, grammar
from .native_context import NativePremises, PREDICATES
from .transform import NotRepresentable, transform

if TYPE_CHECKING:
    from corpus_structure.semantic.analysis_contracts import PreparedInterpretationContext
    from corpus_structure.core.text_structure import TextCapture

_UNSET = object()


@dataclass(frozen=True)
class StageState:
    work: Literal["not_requested", "running", "available", "failed"] = "not_requested"
    coverage: Literal["complete", "partial"] | None = None
    outcome: str | None = None
    diagnostic: str | None = None


@dataclass(frozen=True)
class DefinednessCondition:
    start: int
    end: int
    expression: str
    requirement: str = "nonzero"


@dataclass(frozen=True)
class MathAssessment:
    question: str
    outcome: Literal["resolved", "unknown", "unsupported", "invalid", "timeout"]
    value: Any = None
    conditions: tuple[DefinednessCondition, ...] = ()
    diagnostic: str | None = None


@dataclass(frozen=True)
class PreparedMathInput:
    context: PreparedInterpretationContext
    latex: str
    kind: grammar.Kind | None = None
    seconds: float = grammar.PARSE_SECONDS
    source_text: str | None = None
    source_start: int = 0
    parse_start: int = 0
    _lexical: tuple[tex.Token, ...] | None = field(default=None, init=False, repr=False, compare=False)
    _structure: TextCapture | None = field(default=None, init=False, repr=False, compare=False)
    _syntax: grammar.MathResult | None = field(default=None, init=False, repr=False, compare=False)
    _reading: grammar.MathResult | None = field(default=None, init=False, repr=False, compare=False)
    _symbolic_reading: grammar.MathResult | None = field(default=None, init=False, repr=False, compare=False)
    _value: Any = field(default=_UNSET, init=False, repr=False, compare=False)
    _unrepresentable: str | None = field(default=None, init=False, repr=False, compare=False)
    _states: dict[str, StageState] = field(default_factory=dict, init=False, repr=False, compare=False)
    _assessments: dict[Any, MathAssessment] = field(default_factory=dict, init=False, repr=False, compare=False)

    @property
    def key(self) -> tuple[str, str, str]:
        return self.latex, self.kind or self.context.kind, self.context.stage_key("symbolic")

    def stage_key(self, demand: str):
        return self.latex, self.kind or self.context.kind, self.context.stage_key(demand)

    def state(self, demand: str) -> StageState:
        return self._states.get(demand, StageState())

    def lexical(self) -> tuple[tex.Token, ...]:
        """The complete original span, including delimiters and whitespace."""
        if self._lexical is None:
            text = self.latex if self.source_text is None else self.source_text
            result = tuple(replace(t, start=t.start + self.source_start,
                                   end=t.end + self.source_start) for t in tex.tokens(text))
            object.__setattr__(self, "_lexical", result)
            self._states["lexical"] = StageState("available", "complete", "unanalysed")
        assert self._lexical is not None
        return self._lexical

    def structure(self) -> TextCapture:
        """Source structure through the existing pure structural owner, never Earley."""
        if self._structure is None:
            from corpus_structure.core.text_structure import capture_text

            self.lexical()
            result = capture_text(self.latex if self.source_text is None else self.source_text,
                                  start=self.source_start, structure=True, macros=self.context.macros)
            object.__setattr__(self, "_structure", result)
            coverage = "complete" if result.structure_outcome == "available" else "partial"
            self._states["structure"] = StageState("available", coverage, result.structure_outcome)
        assert self._structure is not None
        return self._structure

    def _remember(self, demand: str, result: grammar.MathResult) -> bool:
        timeout = result.failure is not None and result.failure.category == "timeout"
        self._states[demand] = StageState(
            "failed" if result.status is ParseOutcome.FAILED else "available",
            "partial" if result.failure or result.status is not ParseOutcome.OK else "complete",
            result.status.value,
            None if result.failure is None else result.failure.category,
        )
        return not timeout

    def syntax(self) -> grammar.MathResult:
        if self._syntax is None:
            self.lexical()
            kind = self.kind or self.context.kind
            if kind not in grammar.STARTS:
                raise ValueError(f"unsupported mathematical kind {kind!r}")
            result = grammar.syntax(self.latex, kind,
                                    self.context.macros, seconds=self.seconds)
            if self._remember("syntax", result):
                object.__setattr__(self, "_syntax", result)
            return result
        return self._syntax

    def interpretation(self) -> grammar.MathResult:
        """Pure contextual role filtering with correlated alternatives retained."""
        if self._reading is None:
            recognized = self.syntax()
            result = grammar.interpret(recognized, self.context.grammar_context, seconds=self.seconds)
            if self._remember("interpretation", result):
                object.__setattr__(self, "_reading", result)
            self._states["occurrences"] = self._states["interpretation"]
            return result
        return self._reading

    def reading(self) -> grammar.MathResult:
        return self.interpretation()

    def symbolic_reading(self) -> grammar.MathResult:
        """Explicit stronger reading: native equality may collapse admissible alternatives.

        Extraction methods request this capability to retain their interpreted promise;
        syntax and contextual inspection preserve alternatives without native work.
        """
        if self._symbolic_reading is None:
            result = self.interpretation()
            if result.status is ParseOutcome.AMBIGUOUS:
                result = grammar.interpret(self.syntax(), self.context.grammar_context,
                                           seconds=self.seconds, symbolic=True)
            if self._remember("symbolic", result):
                object.__setattr__(self, "_symbolic_reading", result)
            return result
        return self._symbolic_reading

    @cached_property
    def premises(self) -> NativePremises:
        return NativePremises(self.context)

    def symbolic_value(self) -> Any:
        if self._value is not _UNSET:
            return self._value
        if self._unrepresentable is not None:
            raise NotRepresentable(self._unrepresentable)
        result = self.symbolic_reading()
        try:
            with grammar.deadline(self.seconds):
                if self.premises.unsupported:
                    raise NotRepresentable("unsupported source assumptions")
                self.premises.validate()
                value = grammar.to_sympy(result, symbol_factory=self.premises.symbol)
        except NotRepresentable as error:
            object.__setattr__(self, "_unrepresentable", str(error))
            self._states["symbolic"] = StageState("available", "partial", "unsupported", str(error))
            raise
        except grammar.Expired:
            self._states["symbolic"] = StageState("failed", "partial", "timeout")
            raise
        except ValueError as error:
            self._states["symbolic"] = StageState("available", "partial", "invalid", str(error))
            raise
        self._states["symbolic"] = StageState("available", "complete", "resolved")
        object.__setattr__(self, "_value", value)
        return value

    def definedness(self) -> tuple[DefinednessCondition, ...]:
        """Retain source denominator exclusions before native cancellation (x/x -> 1)."""
        result = self.interpretation()
        if result.tree is None:
            return ()
        found = set()
        for node in result.tree.iter_subtrees():
            denominator = None
            if node.data in {"div", "fraction"} and len(node.children) >= 3:
                denominator = node.children[2]
            if denominator is not None and (where := _tree.span(denominator)) is not None:
                found.add(DefinednessCondition(self.parse_start + where[0],
                                              self.parse_start + where[1],
                                              self.latex[where[0]:where[1]]))
        return tuple(sorted(found, key=lambda item: (item.start, item.end, item.expression)))

    def unproved_definedness(self) -> tuple[str, ...]:
        """Restrictions still required after native facts, before comparison policies."""
        required = set()
        with grammar.deadline(self.seconds):
            for condition in self.definedness():
                denominator = PreparedMathInput(self.context, condition.expression, kind="formula",
                                                seconds=self.seconds).symbolic_value()
                if self.premises.ask(sympy.Q.nonzero(denominator)) is not True:
                    required.add(tex.token_form(condition.expression, self.context.macros))
        return tuple(sorted(required))

    def assess(self, question: str, *, predicate: str | None = None) -> MathAssessment:
        key = question, predicate
        if key in self._assessments:
            return self._assessments[key]
        reading = self.interpretation()
        conditions = self.definedness()
        if reading.tree is None:
            timeout = reading.failure is not None and reading.failure.category == "timeout"
            return MathAssessment(question, "timeout" if timeout else "invalid", conditions=conditions,
                                  diagnostic="source interpretation is unavailable; definedness is incomplete")
        try:
            with grammar.deadline(self.seconds):
                if self.premises.unsupported:
                    result = MathAssessment(question, "unsupported", conditions=conditions,
                                            diagnostic="unsupported source assumptions")
                elif question == "definedness":
                    result = MathAssessment(question,
                        "unknown" if reading.status is ParseOutcome.AMBIGUOUS else "resolved",
                        conditions, conditions)
                else:
                    value = self.symbolic_value()
                    if question == "predicate" and predicate in PREDICATES:
                        answer = self.premises.ask(getattr(sympy.Q, predicate)(value))
                        result = MathAssessment(question, "unknown" if answer is None else "resolved",
                                                answer, conditions)
                    elif question == "refine":
                        result = MathAssessment(question, "resolved", self.premises.refine(value), conditions)
                    elif question == "free_symbols":
                        result = MathAssessment(question, "resolved", value.free_symbols, conditions)
                    elif question == "calculate":
                        result = MathAssessment(question, "resolved", value.doit(), conditions)
                    else:
                        result = MathAssessment(question, "unsupported", conditions=conditions,
                                                diagnostic="unsupported mathematical question")
        except grammar.Expired:
            self._states["scientific"] = StageState("failed", "partial", "timeout")
            return MathAssessment(question, "timeout", conditions=conditions)
        except (NotRepresentable, grammar.NotParsed, grammar.Ambiguous) as error:
            result = MathAssessment(question, "unsupported", conditions=conditions, diagnostic=str(error))
        except ValueError as error:
            result = MathAssessment(question, "invalid", conditions=conditions, diagnostic=str(error))
        self._states["scientific"] = StageState("available", "complete", result.outcome, result.diagnostic)
        self._assessments[key] = result
        return result


def interpret_parsing_math(operand: PreparedMathInput, *, symbolic: bool = False) -> grammar.MathResult:
    return operand.symbolic_reading() if symbolic else operand.interpretation()


def assess_parsing_math(operand: PreparedMathInput, question: str, **options) -> MathAssessment:
    return operand.assess(question, **options)
