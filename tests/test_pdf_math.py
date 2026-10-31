"""PDF-native formula boundaries challenge identity, recognition and demand separation."""

from dataclasses import replace

import pytest
import sympy

from corpus_structure.core.vocab import ParseOutcome
from corpus_structure.methods.math import grammar
from corpus_structure.methods.math.pdf import FormulaOccurrence, FormulaRecognitionUnavailable
from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context


def context():
    return prepare_interpretation_context(macros={}, kind="formula")


def formula(text="x+x", **changes):
    return replace(
        FormulaOccurrence("a" * 64, "#/texts/3", text, "backend text", "succeeded"), **changes
    )


def test_native_input_keeps_recognized_text_and_occurrence_coordinates():
    source = formula("  x+x  ")
    prepared = source.prepare(context())
    assert prepared.operand.latex == "  x+x  "
    assert source.original_text == "backend text"
    assert [(row.symbol.start, row.symbol.end) for row in prepared.occurrences()] == [
        (2, 3),
        (4, 5),
    ]
    assert prepared.operand.state("symbolic").work == "not_requested"
    assert prepared.operand.symbolic_value() == sympy.Mul(sympy.Integer(2), sympy.Symbol("x"))
    assert len(prepared.occurrences()) == 2


def test_equal_formulas_in_different_items_and_builds_keep_distinct_identity():
    one = formula().prepare(context())
    two = formula(item_pointer="#/texts/4").prepare(context())
    other_build = formula(conversion_digest="b" * 64).prepare(context())
    assert (
        len({one.stage_key("syntax"), two.stage_key("syntax"), other_build.stage_key("syntax")})
        == 3
    )
    assert one.occurrences()[0].identity != two.occurrences()[0].identity


@pytest.mark.parametrize("health", ["unknown", "failed", "not_requested"])
def test_nonempty_fallback_cannot_enter_math_as_success(health, monkeypatch):
    monkeypatch.setattr(grammar, "syntax", lambda *a, **kw: pytest.fail("parsed fallback"))
    with pytest.raises(FormulaRecognitionUnavailable):
        formula(recognition_health=health).prepare(context())


def test_syntax_and_structure_share_a_prepared_tree_without_native_values(monkeypatch):
    calls = []
    original = grammar.syntax

    def syntax(*a, **kw):
        calls.append(None)
        return original(*a, **kw)

    monkeypatch.setattr(grammar, "syntax", syntax)
    monkeypatch.setattr(
        grammar, "transform", lambda *a, **kw: pytest.fail("native value requested")
    )
    value = formula().prepare(context()).operand
    structure = value.structure()
    assert structure.nodes
    assert value.syntax().tree is not None
    assert len(calls) == 1
    assert value.state("symbolic").work == "not_requested"


def test_malformed_trailing_input_is_not_success():
    reading = formula("x +").prepare(context()).operand.syntax()
    assert reading.status is ParseOutcome.FAILED
    assert reading.failure is not None


def test_function_ambiguity_and_source_definedness_remain_available():
    assert (
        formula("f(x)").prepare(context()).operand.interpretation().status is ParseOutcome.AMBIGUOUS
    )
    value = formula("x/x").prepare(context()).operand
    assert value.symbolic_value() == 1
    assert [(c.expression, c.requirement) for c in value.definedness()] == [("x", "nonzero")]


@pytest.mark.parametrize(
    "changes",
    [
        {"conversion_digest": "current"},
        {"item_pointer": "#/texts/-1"},
        {"item_pointer": "#/tables/0"},
        {"recognized_latex": " "},
    ],
)
def test_native_formula_requires_qualified_valid_source(changes):
    with pytest.raises(ValueError):
        formula(**changes)


def test_structure_timeout_is_not_cached_as_a_semantic_result(monkeypatch):
    original = grammar.syntax
    calls = []

    def syntax(*a, **kw):
        calls.append(None)
        if len(calls) == 1:
            return grammar.MathResult(
                "x+x",
                "any_value",
                ParseOutcome.FAILED,
                failure=grammar.Failure("timeout", "Timeout"),
            )
        return original(*a, **kw)

    monkeypatch.setattr(grammar, "syntax", syntax)
    prepared = formula().prepare(context()).operand
    assert prepared.structure().structure_outcome == "invalid"
    assert prepared.state("structure").work == "failed"
    assert prepared.structure().structure_outcome == "available"
    assert len(calls) == 2


def test_successful_recognition_can_equal_backend_text():
    prepared = formula("x", original_text="x", kind="formula").prepare(context())
    assert prepared.operand.syntax().status is ParseOutcome.OK
