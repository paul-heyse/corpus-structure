"""Demand-shaped native analysis preserves positions and avoids hidden symbolic work."""

import pytest

from corpus_structure.core.method import SourceViewRef
from corpus_structure.methods.math import grammar
from corpus_structure.methods.math.native import native_request_analysis
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_views import PreparedSourceView


def view(text="x+x", health="succeeded"):
    return PreparedSourceView(
        SourceViewRef(
            5,
            "native-demand",
            1,
            ProductReference(2, "native", "a" * 64),
            "#/groups/0",
            "direct",
            "b" * 64,
            "c" * 64,
        ),
        text,
        (
            {
                "kind": "native_text",
                "item_ref": "#/texts/0",
                "source_field": "text",
                "start": 0,
                "end": len(text),
            },
        ),
        ({"label": "formula", "self_ref": "#/texts/0", "orig": "backend", "text": text},),
        (),
        {"formula_outcomes": [{"pointer": "#/texts/0", "outcome": health}]},
    )


def test_lexical_demand_never_enters_grammar(monkeypatch):
    monkeypatch.setattr(grammar, "syntax", lambda *a, **k: pytest.fail("syntax requested"))
    result = native_request_analysis(view(), None, "lexical")
    assert "".join(t["text"] for t in result.items[0]["lexical"]) == "x+x"
    assert result.items[0]["orig"] == "backend"
    assert result.items[0]["stages"]["symbolic"]["work"] == "not_requested"


def test_syntax_retains_positions_and_ambiguity_without_native(monkeypatch):
    monkeypatch.setattr(grammar, "to_sympy", lambda *a, **k: pytest.fail("native requested"))
    result = native_request_analysis(view("f(x)"), None, "syntax")
    assert result.items[0]["syntax"]
    assert result.items[0]["outcome"] == "ambiguous"
    assert result.items[0]["stages"]["symbolic"]["work"] == "not_requested"


def test_scientific_definedness_does_not_force_symbolic_value(monkeypatch):
    from corpus_structure.methods.math.prepared import PreparedMathInput

    monkeypatch.setattr(
        PreparedMathInput, "symbolic_value", lambda *a, **k: pytest.fail("strong value")
    )
    result = native_request_analysis(view("x/x"), None, "scientific", question="definedness")
    assert result.items[0]["assessment"]["conditions"][0]["expression"] == "x"
    assert result.items[0]["definedness"]["conditions"][0]["expression"] == "x"
    assert result.items[0]["scientific_question"]["prerequisites"] == ("interpretation",)
    assert result.items[0]["stages"]["symbolic"]["work"] == "not_requested"


def test_symbolic_output_keeps_occurrences_and_source_definedness():
    result = native_request_analysis(view("x/x"), None, "symbolic")
    assert len(result.items[0]["occurrences"]) == 2
    assert result.items[0]["symbolic"]["expression"] == "Integer(1)"
    assert result.items[0]["definedness"]["conditions"][0]["expression"] == "x"


def test_unattributed_text_never_becomes_successful_interpretation(monkeypatch):
    monkeypatch.setattr(grammar, "syntax", lambda *a, **k: pytest.fail("fallback parsed"))
    result = native_request_analysis(view(health="failed"), None, "syntax")
    assert result.items[0]["availability"] == "unavailable"


def test_selector_must_name_formula_in_pinned_view():
    with pytest.raises(ValueError, match="outside"):
        native_request_analysis(view(), None, "syntax", pointer="#/texts/8")


def test_unmodeled_scientific_question_never_requests_inference(monkeypatch):
    monkeypatch.setattr(
        grammar, "syntax", lambda *a, **k: pytest.fail("unmodeled question entered grammar")
    )
    result = native_request_analysis(view("x/x"), None, "scientific", question="invented_question")
    item = result.items[0]
    assert item["assessment"]["outcome"] == "unsupported"
    assert item["scientific_question"] is None
    assert item["stages"]["syntax"]["work"] == "not_requested"
    assert item["stages"]["symbolic"]["work"] == "not_requested"


def test_scientific_symbolic_leaf_retains_declared_input_basis():
    result = native_request_analysis(view("x/x"), None, "scientific", question="free_symbols")
    item = result.items[0]
    assert item["scientific_question"]["prerequisites"] == ("symbolic",)
    assert item["symbolic"]["expression"] == "Integer(1)"
    assert item["definedness"]["conditions"][0]["expression"] == "x"
    assert item["assessment"]["outcome"] == "resolved"
