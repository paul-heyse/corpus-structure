"""Independent prepared-input outcomes and operation-local reuse boundaries."""

from __future__ import annotations

import pytest
import sympy

from corpus_structure.core.vocab import ParseOutcome
from corpus_structure.methods.math import grammar
from corpus_structure.methods.math.prepared import PreparedMathInput
from corpus_structure.methods.math.transform import NotRepresentable
from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context


def context():
    return prepare_interpretation_context(macros={}, kind="formula", demand="symbolic")


def test_symbolic_preparation_is_lazy_and_reuses_one_value(monkeypatch):
    calls = []
    original = grammar.to_sympy

    def convert(reading):
        calls.append(reading)
        return original(reading)

    monkeypatch.setattr(grammar, "to_sympy", convert)
    prepared = PreparedMathInput(context(), "x + 1")
    assert prepared.reading().status is ParseOutcome.OK
    assert calls == []
    assert prepared.symbolic_value() == sympy.Add(sympy.Symbol("x"), 1)
    assert prepared.symbolic_value() is prepared.symbolic_value()
    assert len(calls) == 1


def test_unrepresentability_is_stable_in_the_same_operation(monkeypatch):
    calls = []
    original = grammar.to_sympy

    def convert(reading):
        calls.append(reading)
        return original(reading)

    monkeypatch.setattr(grammar, "to_sympy", convert)
    prepared = PreparedMathInput(context(), r"x \pm y")
    for _ in range(2):
        with pytest.raises(NotRepresentable):
            prepared.symbolic_value()
    assert len(calls) == 1


def test_transient_timeout_is_not_retained(monkeypatch):
    calls = []
    original = grammar.parse

    def parse(*args, **kwargs):
        calls.append(None)
        if len(calls) == 1:
            return grammar.MathResult(
                "x", "formula", ParseOutcome.FAILED, failure=grammar.Failure("timeout", "Timeout")
            )
        return original(*args, **kwargs)

    monkeypatch.setattr(grammar, "parse", parse)
    prepared = PreparedMathInput(context(), "x")
    failure = prepared.reading().failure
    assert failure is not None and failure.category == "timeout"
    assert prepared.reading().status is ParseOutcome.OK
    assert len(calls) == 2


def test_prepared_input_identity_includes_exact_text_and_kind():
    left = PreparedMathInput(context(), "x+1")
    spaced = PreparedMathInput(context(), "x + 1")
    set_kind = PreparedMathInput(context(), "x+1", kind="set_expr")
    assert left.key != spaced.key
    assert left.key != set_kind.key


def test_authorized_branch_prunes_proven_invalid_nested_alternative():
    from lark import Token, Tree

    f = Token("SYMBOL", "f", start_pos=0, end_pos=1)
    x = Token("SYMBOL", "x", start_pos=2, end_pos=3)
    opening = Token("L_PAREN", "(", start_pos=1, end_pos=2)
    closing = Token("R_PAREN", ")", start_pos=3, end_pos=4)
    allowed = Tree("function_applied", [f, opening, x, closing])
    invalid = Tree(
        "adjacent_expressions",
        [
            f,
            Tree(
                "group_round_parentheses",
                [
                    opening,
                    Tree("_ambig", [x, x]),
                    closing,
                ],
            ),
        ],
    )
    resolver = grammar._Resolver(
        "f(x)", {}, grammar.classify({}), grammar.MathContext(functions=frozenset({"f"}))
    )
    result = resolver.resolve(Tree("_ambig", [allowed, invalid]))
    assert isinstance(result, Tree)
    assert result.data == "function_applied"
    assert resolver.unresolved == 0
    assert resolver._values == {}


@pytest.mark.parametrize("field,value", [("latex", "y"), ("kind", "set_expr"), ("seconds", 0.0)])
def test_prepared_input_cannot_change_after_a_value_is_cached(field, value):
    from dataclasses import FrozenInstanceError

    prepared = PreparedMathInput(context(), "x + 1")
    expected = prepared.symbolic_value()
    with pytest.raises(FrozenInstanceError):
        setattr(prepared, field, value)
    assert prepared.symbolic_value() is expected


def test_prepared_context_cannot_be_rebound_after_reading():
    from dataclasses import FrozenInstanceError

    prepared = PreparedMathInput(context(), "x")
    reading = prepared.reading()
    with pytest.raises(FrozenInstanceError):
        prepared.context = context()
    assert prepared.reading() is reading


def test_filling_private_caches_does_not_change_input_equality():
    prepared_context = context()
    left = PreparedMathInput(prepared_context, "x + 1")
    right = PreparedMathInput(prepared_context, "x + 1")
    assert left == right
    left.symbolic_value()
    assert left == right
