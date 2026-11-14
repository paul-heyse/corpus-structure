"""Source-qualified native declarations retain ordered visibility and exact custody."""

import pytest

from corpus_structure.core.vocab import ParseOutcome
from corpus_structure.methods.math import grammar
from corpus_structure.methods.math.prepared import PreparedMathInput
from corpus_structure.methods.math.source_context import _heads
from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context
from corpus_structure.semantic.types import PreparationError

SOURCE = "text:7:text:" + "b" * 64


def declaration(*, scope="section:left", start=2, end=8, source=SOURCE):
    return dict(
        symbol="f",
        role="function",
        authority="source",
        evidence="#/texts/definition:0:4",
        source_id=source,
        scope=scope,
        start=start,
        end=end,
    )


def operand(*, offset=3, scope="section:left", declarations=()):
    context = prepare_interpretation_context(
        macros={},
        source_id=SOURCE,
        scope=scope,
        offset=offset,
        declarations=declarations,
        demand="symbolic",
    )
    return PreparedMathInput(context, "f(t)")


def test_native_source_declaration_is_visible_only_after_definition_and_before_end():
    declared = (declaration(),)
    assert (
        operand(offset=1, declarations=declared).interpretation().status is ParseOutcome.AMBIGUOUS
    )
    within = operand(offset=2, declarations=declared)
    assert within.interpretation().status is ParseOutcome.OK
    assert (
        operand(offset=8, declarations=declared).interpretation().status is ParseOutcome.AMBIGUOUS
    )
    source_fact = next(d for d in within.context.declarations if d.symbol == "f")
    assert (source_fact.source_id, source_fact.evidence, source_fact.start, source_fact.end) == (
        SOURCE,
        "#/texts/definition:0:4",
        2,
        8,
    )


def test_native_local_function_scope_does_not_leak_to_sibling_source_scope():
    declared = (declaration(),)
    assert operand(declarations=declared).interpretation().status is ParseOutcome.OK
    sibling = operand(scope="section:right", declarations=declared)
    assert sibling.interpretation().status is ParseOutcome.AMBIGUOUS
    assert all(d.symbol != "f" for d in sibling.context.declarations)
    inner = operand(scope="unit:inner", declarations=(declaration(scope="unit:inner"),))
    assert inner.symbolic_value() != operand(declarations=declared).symbolic_value()


def test_native_declaration_cannot_borrow_another_original_source():
    value = operand(declarations=(declaration(source="another-source"),))
    assert value.interpretation().status is ParseOutcome.AMBIGUOUS
    with pytest.raises(PreparationError):
        operand(
            declarations=(
                {
                    "symbol": "f",
                    "role": "function",
                    "authority": "source",
                    "evidence": "missing source custody",
                },
            )
        )


@pytest.mark.parametrize("text", ["f(0)=1", r"\operatorname{P}(f(t)=t)"])
def test_native_function_values_and_operator_conditions_do_not_declare_functions(text):
    assert list(_heads(grammar.syntax(text, "any_value", {}))) == []


def test_native_function_head_preserves_exact_declared_source_extent():
    assert list(_heads(grammar.syntax("f(t)=t^2", "any_value", {}))) == [("f", (0, 4))]


def test_native_source_timeout_remains_failure_not_an_absent_declaration(monkeypatch):
    calls = []

    def timeout(*args, **kwargs):
        calls.append(args[0])
        return grammar.MathResult(
            "f(t)", "any_value", ParseOutcome.FAILED, failure=grammar.Failure("timeout", "Timeout")
        )

    monkeypatch.setattr(grammar, "syntax", timeout)
    value = operand(declarations=(declaration(),))
    result = value.syntax()
    assert result.status is ParseOutcome.FAILED
    assert result.failure is not None
    assert result.failure.category == "timeout"
    assert calls == ["f(t)"]
