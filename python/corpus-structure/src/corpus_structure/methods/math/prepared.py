"""One operation owns capture, recognition, contextual meaning and demanded native work.

Native handles and attempt diagnostics remain here. A weaker request never starts a
stronger stage, and a timeout never becomes a reusable semantic conclusion.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from fractions import Fraction
from functools import cached_property
from typing import TYPE_CHECKING, Any, Literal

import sympy
from lark import Token, Tree

from corpus_structure.core import tex
from corpus_structure.core.vocab import ParseOutcome

from . import _tree, grammar
from .native_context import PREDICATES, NativePremises
from .transform import NotRepresentable

if TYPE_CHECKING:
    from corpus_structure.core.text_structure import TextCapture
    from corpus_structure.semantic.analysis_contracts import PreparedInterpretationContext

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
class DefinednessResult:
    conditions: tuple[DefinednessCondition, ...] = ()
    coverage: Literal["complete", "partial"] = "complete"
    diagnostics: tuple[str, ...] = ()


class IncompleteDefinedness(NotRepresentable):
    """Native equality cannot discharge source domains this adapter has not captured."""


def _literal_exponent(node: _tree.Node) -> Fraction | None:
    """Read exact finite rational syntax without constructing or evaluating a native Pow."""
    if isinstance(node, Token):
        try:
            return Fraction(str(node)) if node.type == "DIGIT" else None
        except (ValueError, ZeroDivisionError):
            return None
    parts = [child for child in node.children if isinstance(child, Tree)]
    if node.data == "number" and len(node.children) == 1:
        try:
            return Fraction(str(node.children[0]))
        except (ValueError, ZeroDivisionError):
            return None
    if node.data in {"group_curly_parentheses", "group_round_parentheses", "group_square_brackets", "script_group"}:
        return _literal_exponent(parts[0]) if len(parts) == 1 else None
    if node.data == "sub" and len(node.children) == 2:
        value = _literal_exponent(node.children[1])
        return -value if value is not None else None
    if node.data not in {"add", "sub", "mul", "div", "fraction"} or len(parts) != 2:
        return None
    left, right = (_literal_exponent(child) for child in parts)
    if left is None or right is None or (node.data in {"div", "fraction"} and right == 0):
        return None
    if node.data == "add":
        result = left + right
    elif node.data == "sub":
        result = left - right
    elif node.data == "mul":
        result = left * right
    else:
        result = left / right
    # This finite literal reader does not expand arbitrary exponent arithmetic.
    return result if max(result.numerator.bit_length(), result.denominator.bit_length()) <= 8192 else None


# Their exact source domains/convergence are not part of the supported arithmetic
# restriction projection. Preserve native structures without claiming complete domains.
_UNSUPPORTED_DOMAIN_RULES = frozenset({
    "log", "tan", "csc", "sec", "cot", "coth", "csch", "sech", "factorial",
    "asin", "acos", "atan", "acot", "acsc", "asec", "asinh", "acosh", "atanh",
    "function_applied", "op_applied", "normal_integral", "integral_with_special_fraction",
    "summation", "product", "limit",
})


@dataclass(frozen=True)
class MathAssessment:
    question: str
    outcome: Literal["resolved", "unknown", "unsupported", "invalid", "timeout"]
    value: Any = None
    conditions: tuple[DefinednessCondition, ...] = ()
    diagnostic: str | None = None
    coverage: Literal["complete", "partial"] = "complete"


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
    _definedness: DefinednessResult | None = field(default=None, init=False, repr=False, compare=False)
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

    def definedness_result(self) -> DefinednessResult:
        """Capture supported source restrictions before any native cancellation.

        Negative exact rational powers require nonzero bases. Positive integer
        powers are total on the supported scalar field. Symbolic/zero/other power
        conventions and unsupported domain-bearing forms remain explicitly partial.
        """
        if self._definedness is not None:
            return self._definedness
        result = self.interpretation()
        if result.tree is None:
            captured = DefinednessResult(coverage="partial", diagnostics=("source interpretation unavailable",))
            if result.failure is None or result.failure.category != "timeout":
                object.__setattr__(self, "_definedness", captured)
            return captured
        found: set[DefinednessCondition] = set()
        diagnostics: set[str] = set()

        def restriction(node):
            where = _tree.span(node)
            if where is None:
                diagnostics.add("restriction has no source extent")
                return
            found.add(DefinednessCondition(self.parse_start + where[0],
                                           self.parse_start + where[1],
                                           self.latex[where[0]:where[1]]))

        for node in result.tree.iter_subtrees():
            if node.data in {"div", "fraction"} and len(node.children) >= 3:
                restriction(node.children[2])
            elif node.data in {"superscript", "sup_sub"}:
                exponent = _literal_exponent(node.children[2]) if len(node.children) > 2 else None
                if exponent is not None and exponent < 0 and node.data == "superscript":
                    restriction(node.children[0])
                elif exponent is None or exponent <= 0 or exponent.denominator != 1:
                    diagnostics.add(f"unsupported source power domain: {node.data} at {_tree.span(node)}")
            elif node.data.endswith("_power") or node.data in _UNSUPPORTED_DOMAIN_RULES:
                diagnostics.add(f"unsupported source domain: {node.data} at {_tree.span(node)}")
            elif node.data == "square_root" and len(node.children) > 2:
                diagnostics.add(f"unsupported indexed-root domain at {_tree.span(node)}")
        captured = DefinednessResult(
            tuple(sorted(found, key=lambda item: (item.start, item.end, item.expression))),
            "partial" if diagnostics else "complete", tuple(sorted(diagnostics)),
        )
        object.__setattr__(self, "_definedness", captured)
        return captured

    def definedness(self) -> tuple[DefinednessCondition, ...]:
        """Source conditions only; completeness is owned by definedness_result()."""
        return self.definedness_result().conditions

    def unproved_definedness(self) -> tuple[str, ...]:
        """Restrictions still required after native facts, before comparison policies."""
        captured = self.definedness_result()
        if captured.coverage != "complete":
            raise IncompleteDefinedness("source definedness incomplete: " + "; ".join(captured.diagnostics))
        required = set()
        with grammar.deadline(self.seconds):
            for condition in captured.conditions:
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
        if reading.tree is None:
            timeout = reading.failure is not None and reading.failure.category == "timeout"
            outcome = "timeout" if timeout else "invalid"
            diagnostic = "source interpretation is unavailable; definedness is incomplete"
            self._states["scientific"] = StageState("failed" if timeout else "available", "partial", outcome, diagnostic)
            return MathAssessment(question, outcome, conditions=(),
                                  diagnostic=diagnostic, coverage="partial")
        definedness = self.definedness_result()
        conditions = definedness.conditions
        try:
            with grammar.deadline(self.seconds):
                if self.premises.unsupported:
                    result = MathAssessment(question, "unsupported", conditions=conditions,
                                            diagnostic="unsupported source assumptions")
                elif question == "definedness":
                    result = MathAssessment(question,
                        "unknown" if reading.status is ParseOutcome.AMBIGUOUS or definedness.coverage != "complete" else "resolved",
                        conditions, conditions,
                        "; ".join(definedness.diagnostics) or None, definedness.coverage)
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
        if definedness.coverage != "complete":
            result = replace(result, coverage="partial", diagnostic=result.diagnostic or
                             "source definedness incomplete: " + "; ".join(definedness.diagnostics))
        self._states["scientific"] = StageState("available", result.coverage, result.outcome, result.diagnostic)
        self._assessments[key] = result
        return result


def interpret_parsing_math(operand: PreparedMathInput, *, symbolic: bool = False) -> grammar.MathResult:
    return operand.symbolic_reading() if symbolic else operand.interpretation()


def assess_parsing_math(operand: PreparedMathInput, question: str, **options) -> MathAssessment:
    return operand.assess(question, **options)
