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
    assert value.symbolic_value() == sympy.Mul(
        sympy.Symbol("a"), sympy.Symbol("b"), sympy.Pow(sympy.Symbol("c"), -1)
    )


def test_original_delimiters_and_exact_occurrence_offsets_remain_separate():
    context = prepare_interpretation_context(macros={}, kind="formula")
    value = PreparedMathInput(
        context, "x+x", source_text="$ x+x $", source_start=10, parse_start=12
    )
    assert [(t.text, t.start, t.end) for t in value.lexical()] == [
        ("$", 10, 11),
        (" ", 11, 12),
        ("x", 12, 13),
        ("+", 13, 14),
        ("x", 14, 15),
        (" ", 15, 16),
        ("$", 16, 17),
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
        admitted = operand(r"\sqrt{x^2}", assumptions=[{"symbol": "x", "predicate": "positive"}])
        assert admitted.assess("refine").value == x
        assert global_assumptions == before | {sympy.Q.positive(x)}
    finally:
        global_assumptions.clear()
        global_assumptions.update(before)


def test_unsupported_and_contradictory_premises_remain_typed():
    unsupported = operand("x", assumptions=[{"source_condition": "x > 0"}])
    assert unsupported.assess("predicate", predicate="positive").outcome == "unsupported"
    invalid = operand(
        "x",
        assumptions=[
            {"symbol": "x", "predicate": "positive"},
            {"symbol": "x", "predicate": "negative"},
        ],
    )
    assert invalid.assess("predicate", predicate="positive").outcome == "invalid"


def test_native_cancellation_retains_source_denominator_exclusion():
    value = operand("x/x")
    assert value.symbolic_value() == 1
    conditions = value.definedness()
    assert [(c.start, c.end, c.expression, c.requirement) for c in conditions] == [
        (2, 3, "x", "nonzero")
    ]
    assert value.assess("refine").conditions == conditions


def test_binders_are_distinct_from_same_spelling_free_occurrences():
    value = operand(r"\int_0^1 x dx + x")
    native = value.symbolic_value()
    integral = next(iter(native.atoms(sympy.Integral)))
    assert isinstance(integral.variables[0], sympy.Dummy)
    assert native.free_symbols == {sympy.Symbol("x")}


def test_scoped_declarations_create_distinct_native_identity():
    def scoped(scope):
        return operand(
            "x",
            source_id="document",
            scope=scope,
            declarations=[
                {
                    "symbol": "x",
                    "role": "variable",
                    "authority": "source",
                    "evidence": "declaration",
                    "source_id": "document",
                    "scope": scope,
                }
            ],
        )

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


def test_indefinite_integral_keeps_its_free_argument():
    value = operand(r"\int x dx")
    assert value.symbolic_value().free_symbols == {sympy.Symbol("x")}


def test_limit_has_source_bound_identity():
    value = operand(r"(\lim_{x\to 0} x) + y")
    native = value.symbolic_value()
    limit = next(iter(native.atoms(sympy.Limit)))
    assert isinstance(limit.args[1], sympy.Dummy)
    assert native.free_symbols == {sympy.Symbol("y")}


def test_unavailable_source_does_not_assert_empty_definedness():
    value = operand("x/")
    answer = value.assess("definedness")
    assert answer.outcome == "invalid"
    assert answer.diagnostic is not None and "incomplete" in answer.diagnostic


def test_scoped_function_declarations_have_distinct_native_identity():
    def scoped(scope):
        return operand(
            "f(x)",
            source_id="document",
            scope=scope,
            declarations=[
                {
                    "symbol": "f",
                    "role": "function",
                    "authority": "source",
                    "evidence": "declaration",
                    "source_id": "document",
                    "scope": scope,
                }
            ],
        )

    assert scoped("left").symbolic_value() != scoped("right").symbolic_value()
    assert scoped("left").symbolic_value() == scoped("left").symbolic_value()


def test_binder_role_conflict_cannot_silently_adopt_outer_constant_meaning():
    value = operand(r"\int_0^1 e de", constants=("e",))
    reading = value.symbolic_reading()
    assert reading.status is ParseOutcome.AMBIGUOUS
    assert any("binder role conflicts" in note for note in reading.notes)
    with pytest.raises(grammar.Ambiguous):
        value.symbolic_value()


@pytest.mark.parametrize("text", [r"x^{-1}x", r"x^{-2}x^2", r"x^{-\frac{1}{2}}\sqrt{x}"])
def test_negative_power_exclusions_survive_native_cancellation(text):
    value = operand(text)
    assert value.symbolic_value() == 1
    captured = value.definedness_result()
    assert captured.coverage == "complete"
    assert any(c.expression == "x" and c.start == 0 and c.end == 1 for c in captured.conditions)
    assert value.unproved_definedness() == ("x",)


@pytest.mark.parametrize("text", [r"x^{-n}x^n", "x^0", "x^{1/2}", r"x^{-2}_i", r"\log{x}-\log{x}"])
def test_unsupported_source_domains_are_explicitly_incomplete(text):
    from corpus_structure.methods.math.prepared import IncompleteDefinedness

    value = operand(text)
    captured = value.definedness_result()
    assert captured.coverage == "partial"
    assert captured.diagnostics
    answer = value.assess("definedness")
    assert answer.outcome == "unknown"
    assert answer.coverage == "partial"
    with pytest.raises(IncompleteDefinedness, match="source definedness incomplete"):
        value.unproved_definedness()


def test_positive_integer_powers_have_no_new_exclusion():
    value = operand("x^2")
    captured = value.definedness_result()
    assert captured.coverage == "complete"
    assert captured.conditions == ()
    assert value.unproved_definedness() == ()


def test_definedness_preparation_is_operation_owned_and_shared():
    value = operand(r"x^{-1}x")
    first = value.definedness_result()
    assert value.definedness_result() is first
    value.symbolic_value()
    assert value.definedness_result() is first


def test_unavailable_definedness_has_partial_work_state():
    value = operand("x/")
    answer = value.assess("definedness")
    assert answer.coverage == "partial"
    assert value.state("scientific").work == "available"
    assert value.state("scientific").coverage == "partial"


def test_actual_tiny_budget_always_restores_deadline_setup_state():
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    assert previous_timer == (0, 0)
    for _ in range(20):
        with pytest.raises(grammar.Expired), grammar.deadline(1e-9):
            time.sleep(0.01)
        assert signal.getsignal(signal.SIGALRM) is previous_handler
        assert signal.getitimer(signal.ITIMER_REAL) == previous_timer


def test_direct_assessment_does_not_retry_failed_interpretation(monkeypatch):
    value = operand("x+x")
    calls = []

    def timed_out(self):
        calls.append(1)
        return grammar.MathResult(
            "x+x",
            "formula",
            ParseOutcome.FAILED,
            failure=grammar.Failure("timeout", "budget expired"),
        )

    monkeypatch.setattr(PreparedMathInput, "interpretation", timed_out)
    monkeypatch.setattr(
        PreparedMathInput,
        "definedness_result",
        lambda self: pytest.fail("failed source was retried"),
    )
    result = value.assess("definedness")
    assert result.outcome == "timeout" and result.coverage == "partial"
    assert calls == [1]
