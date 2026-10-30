"""Demand isolation, source definedness and actual native premise/deadline behavior."""

from __future__ import annotations

import signal
import threading
import time

import pytest
import sympy
from sympy.assumptions import global_assumptions

from corpus_structure.core.vocab import ParseOutcome
from corpus_structure.methods.math import grammar
from corpus_structure.methods.math.prepared import PreparedMathInput
from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context


def operand(text, **context):
    context.setdefault("kind", "formula")
    return PreparedMathInput(prepare_interpretation_context(macros={}, **context), text)


def test_lexical_and_structure_do_not_recognize_or_construct(monkeypatch):
    value = operand("x + @")
    monkeypatch.setattr(grammar, "parser_for", lambda *a: pytest.fail("recognition requested"))
    monkeypatch.setattr(grammar, "transform", lambda *a: pytest.fail("native requested"))
    assert "".join(t.text for t in value.lexical()) == "x + @"
    assert value.structure().end == 5
    assert value.state("syntax").work == "not_requested"
    assert value.state("symbolic").work == "not_requested"


def test_syntax_and_context_preserve_correlated_function_alternatives(monkeypatch):
    value = operand("f(x)")
    monkeypatch.setattr(grammar, "transform", lambda *a: pytest.fail("native requested"))
    syntax = value.syntax()
    assert syntax.tree is not None
    assert any(node.data == "_ambig" for node in syntax.tree.iter_subtrees())
    assert value.interpretation().status is ParseOutcome.AMBIGUOUS
    assert value.state("symbolic").work == "not_requested"


def test_symbolic_equivalence_is_an_explicit_stronger_request():
    value = operand("a b / c", demand="symbolic")
    assert value.interpretation().status is ParseOutcome.AMBIGUOUS
    assert value.symbolic_reading().status is ParseOutcome.OK
    assert value.interpretation().status is ParseOutcome.AMBIGUOUS
    assert value.symbolic_value() == sympy.Mul(sympy.Symbol("a"), sympy.Symbol("b"), sympy.Pow(sympy.Symbol("c"), -1))


def test_original_delimiters_and_exact_occurrence_offsets_remain_separate():
    context = prepare_interpretation_context(macros={}, kind="formula")
    value = PreparedMathInput(context, "x+x", source_text="$ x+x $", source_start=10, parse_start=12)
    assert [(t.text, t.start, t.end) for t in value.lexical()] == [
        ("$", 10, 11), (" ", 11, 12), ("x", 12, 13), ("+", 13, 14),
        ("x", 14, 15), (" ", 15, 16), ("$", 16, 17),
    ]
    assert [(o.start, o.end) for o in value.reading().occurrences] == [(0, 1), (2, 3)]
    assert value.symbolic_value() == sympy.Mul(2, sympy.Symbol("x"))


def test_ask_and_refine_do_not_read_ambient_assumptions():
    x = sympy.Symbol("x")
    before = set(global_assumptions)
    global_assumptions.add(sympy.Q.positive(x))
    try:
        plain = operand("x")
        assert plain.assess("predicate", predicate="positive").outcome == "unknown"
        assert plain.symbolic_value().is_real is None
        square_root = operand(r"\sqrt{x^2}")
        assert square_root.assess("refine").value != x
        admitted = operand(r"\sqrt{x^2}", assumptions=[{"symbol":"x", "predicate":"positive"}])
        assert admitted.assess("refine").value == x
        assert global_assumptions == before | {sympy.Q.positive(x)}
    finally:
        global_assumptions.clear()
        global_assumptions.update(before)


def test_unsupported_and_contradictory_premises_remain_typed():
    unsupported = operand("x", assumptions=[{"source_condition":"x > 0"}])
    assert unsupported.assess("predicate", predicate="positive").outcome == "unsupported"
    invalid = operand("x", assumptions=[{"symbol":"x", "predicate":"positive"},
                                         {"symbol":"x", "predicate":"negative"}])
    assert invalid.assess("predicate", predicate="positive").outcome == "invalid"


def test_native_cancellation_retains_source_denominator_exclusion():
    value = operand("x/x")
    assert value.symbolic_value() == 1
    conditions = value.definedness()
    assert [(c.start, c.end, c.expression, c.requirement) for c in conditions] == [(2, 3, "x", "nonzero")]
    assert value.assess("refine").conditions == conditions


def test_binders_are_distinct_from_same_spelling_free_occurrences():
    value = operand(r"\int_0^1 x dx + x")
    native = value.symbolic_value()
    integral = next(iter(native.atoms(sympy.Integral)))
    assert isinstance(integral.variables[0], sympy.Dummy)
    assert native.free_symbols == {sympy.Symbol("x")}


def test_scoped_declarations_create_distinct_native_identity():
    def scoped(scope):
        return operand("x", source_id="document", scope=scope, declarations=[{
            "symbol":"x", "role":"variable", "authority":"source", "evidence":"declaration",
            "source_id":"document", "scope":scope,
        }])
    left, right = scoped("left"), scoped("right")
    assert left.symbolic_value() != right.symbolic_value()
    assert left.symbolic_value() == scoped("left").symbolic_value()
    assert left.stage_key("syntax") == right.stage_key("syntax")
    assert left.stage_key("interpretation") != right.stage_key("interpretation")


def test_nested_deadline_restores_outer_remaining_budget():
    with grammar.deadline(0.5):
        before, _ = signal.getitimer(signal.ITIMER_REAL)
        with grammar.deadline(0.1):
            time.sleep(0.02)
        after, _ = signal.getitimer(signal.ITIMER_REAL)
        assert 0 < after < before - 0.01
    assert signal.getitimer(signal.ITIMER_REAL) == (0, 0)


def test_outer_deadline_cannot_be_extended_by_inner_stage():
    started = time.monotonic()
    with pytest.raises(grammar.Expired), grammar.deadline(0.04), grammar.deadline(0.5):
        time.sleep(0.1)
    assert time.monotonic() - started < 0.3


def test_native_demand_refuses_off_main_thread():
    value = operand("x")
    failures = []
    def run():
        try:
            value.symbolic_value()
        except BaseException as error:
            failures.append(error)
    worker = threading.Thread(target=run)
    worker.start()
    worker.join()
    assert len(failures) == 1 and isinstance(failures[0], grammar.OffMainThread)


def test_timeout_attempt_does_not_poison_a_later_native_request(monkeypatch):
    value = operand("x")
    original = grammar.to_sympy
    calls = []
    def transient(reading, **options):
        calls.append(None)
        if len(calls) == 1:
            raise grammar.Expired()
        return original(reading, **options)
    monkeypatch.setattr(grammar, "to_sympy", transient)
    with pytest.raises(grammar.Expired):
        value.symbolic_value()
    assert value.state("symbolic").work == "failed"
    assert value.symbolic_value() == sympy.Symbol("x")
    assert value.state("symbolic").outcome == "resolved"
    assert len(calls) == 2
