"""Demand-shaped native analysis preserves positions and avoids hidden symbolic work."""

import pytest
from semantic.declared_math_support import _inputs, _role
from semantic.declared_math_support import math_profile as math_profile
from semantic.formal_products_support import selected

from corpus_structure.methods.math import grammar
from corpus_structure.semantic.construction_products import (
    ConstructionOptions,
    PreparedConstructionProfile,
)
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.declared_math_analysis import analyze_declared_math
from corpus_structure.semantic.declared_math_products import DeclaredMathOptions
from corpus_structure.semantic.math_context import acquire_analysis_context_profile


def inputs(profile, text="x+x", health="succeeded", *, contextual=False):
    source = selected(
        profile,
        text,
        items=[{"label": "formula", "self_ref": "#/texts/0", "orig": "backend", "text": text}],
        recognition=[{"pointer": "#/texts/0", "outcome": health}],
    )
    source, formal, source_member, formal_member = _inputs(profile, source)
    context = SubjectContext(
        "outside-statistics",
        source_member.subject,
        source_member.original_source,
        source_member.analyzed_scope,
        subject_definition=source_member.subject_definition,
    )
    roles = (_role("source", (source_member,)), _role("formal", (formal_member,)))
    arguments = {
        "source": source.value,
        "formal": formal.value.model_dump(mode="json", exclude_unset=True),
        "pointer": "",
        "question": "",
        "predicate": "",
        "seconds": 2.0,
    }
    if contextual:
        from dataclasses import replace

        construction = PreparedConstructionProfile(
            profile.prepared, bound_data_operation_model(profile.prepared)
        ).run(source, (formal,), ConstructionOptions(), subject_context=context)
        roles += (
            _role("constructions", (replace(formal_member, product=construction.semantic_id),)),
            _role("inherited", ()),
            _role("ancestor_sources", ()),
        )
        arguments.update(
            {
                "constructions": construction.value.model_dump(mode="json", exclude_unset=True),
                "inherited": (),
                "ancestor_sources": (),
            }
        )
    return roles, context, arguments


def analyze(profile, prepared, demand, **options):
    roles, context, arguments = prepared
    return analyze_declared_math(
        profile.prepared,
        roles,
        context,
        DeclaredMathOptions(),
        acquire_analysis_context_profile(),
        {**arguments, "demand": demand, **options},
        check_active=lambda: None,
    )


def test_lexical_demand_never_enters_grammar(math_profile, monkeypatch):
    prepared = inputs(math_profile)
    monkeypatch.setattr(grammar, "syntax", lambda *a, **k: pytest.fail("syntax requested"))
    result = analyze(math_profile, prepared, "lexical")
    assert "".join(t["text"] for t in result["items"][0]["lexical"]) == "x+x"
    assert result["items"][0]["orig"] == "backend"
    assert result["items"][0]["stages"]["symbolic"]["work"] == "not_requested"


def test_syntax_retains_positions_and_ambiguity_without_native(math_profile, monkeypatch):
    prepared = inputs(math_profile, "f(x)")
    monkeypatch.setattr(grammar, "to_sympy", lambda *a, **k: pytest.fail("native requested"))
    result = analyze(math_profile, prepared, "syntax")
    assert result["items"][0]["syntax"]["format"] == "lark-working-dag-1"
    packed = analyze(math_profile, prepared, "structure")["items"][0]["structure"]
    assert packed["choices"] and packed["nodes"]
    assert result["items"][0]["outcome"] == "ambiguous"
    assert result["items"][0]["stages"]["symbolic"]["work"] == "not_requested"


def test_scientific_definedness_does_not_force_symbolic_value(math_profile, monkeypatch):
    prepared = inputs(math_profile, "x/x", contextual=True)
    from corpus_structure.methods.math.prepared import PreparedMathInput

    monkeypatch.setattr(
        PreparedMathInput, "symbolic_value", lambda *a, **k: pytest.fail("strong value")
    )
    result = analyze(math_profile, prepared, "scientific", question="definedness")
    assert result["items"][0]["assessment"]["conditions"][0]["expression"] == "x"
    assert result["items"][0]["definedness"]["conditions"][0]["expression"] == "x"
    assert result["items"][0]["scientific_question"]["prerequisites"] == ["interpretation"]
    assert result["items"][0]["stages"]["symbolic"]["work"] == "not_requested"


def test_symbolic_output_keeps_occurrences_and_source_definedness(math_profile):
    prepared = inputs(math_profile, "x/x", contextual=True)
    result = analyze(math_profile, prepared, "symbolic")
    assert len(result["items"][0]["occurrences"]) == 2
    assert result["items"][0]["symbolic"]["expression"] == "Integer(1)"
    assert result["items"][0]["definedness"]["conditions"][0]["expression"] == "x"


def test_unattributed_text_never_becomes_successful_interpretation(math_profile, monkeypatch):
    prepared = inputs(math_profile, health="failed")
    monkeypatch.setattr(grammar, "syntax", lambda *a, **k: pytest.fail("fallback parsed"))
    result = analyze(math_profile, prepared, "syntax")
    assert result["items"][0]["availability"] == "unavailable"


def test_selector_must_name_formula_in_pinned_view(math_profile):
    prepared = inputs(math_profile)
    with pytest.raises(ValueError, match="outside"):
        analyze(math_profile, prepared, "syntax", pointer="#/texts/8")


def test_unmodeled_scientific_question_never_requests_inference(math_profile, monkeypatch):
    prepared = inputs(math_profile, "x/x", contextual=True)
    monkeypatch.setattr(
        grammar, "syntax", lambda *a, **k: pytest.fail("unmodeled question entered grammar")
    )
    result = analyze(math_profile, prepared, "scientific", question="invented_question")
    item = result["items"][0]
    assert item["assessment"]["outcome"] == "unsupported"
    assert item["scientific_question"] is None
    assert item["stages"]["syntax"]["work"] == "available"
    assert item["primary_input"]
    assert item["stages"]["symbolic"]["work"] == "not_requested"


def test_scientific_symbolic_leaf_retains_declared_input_basis(math_profile):
    prepared = inputs(math_profile, "x/x", contextual=True)
    result = analyze(math_profile, prepared, "scientific", question="free_symbols")
    item = result["items"][0]
    assert item["scientific_question"]["prerequisites"] == ["symbolic"]
    assert item["symbolic"]["expression"] == "Integer(1)"
    assert item["definedness"]["conditions"][0]["expression"] == "x"
    assert item["assessment"]["outcome"] == "resolved"
