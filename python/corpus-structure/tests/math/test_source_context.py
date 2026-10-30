"""Source declarations precede their consumers and retain structural scope/custody."""

from __future__ import annotations

import pytest

from corpus_structure.core.evidence import RenditionContent, Segment
from corpus_structure.core.vocab import ParseOutcome, SegmentKind
from corpus_structure.methods.math import grammar
from corpus_structure.methods.math.source_context import (
    EarlyMathContextUnavailable,
    prepare_source_math,
)

SOURCE = "text:7:text:" + "b" * 64


def content(items):
    text = ""

    def build(item):
        nonlocal text
        if isinstance(item, str):
            start = len(text)
            text += item
            segment = Segment(kind=SegmentKind.MATH_INLINE, start=start, end=len(text))
            text += " "
            return segment
        kind, children = item
        start = len(text)
        built = tuple(build(child) for child in children)
        return Segment(kind=kind, start=start, end=len(text), children=built)

    children = tuple(build(item) for item in items)
    return RenditionContent(
        canonical_text=text,
        document=Segment(kind=SegmentKind.DOCUMENT, start=0, end=len(text), children=children),
    )


def prepare(value, **options):
    return prepare_source_math(value, macros={}, source_id=SOURCE, **options)


def test_later_function_use_receives_only_preceding_definition_and_reuses_syntax(monkeypatch):
    value = content(["f(t)", "f(t)=t^2", "f(t)"])
    calls = []
    original = grammar.syntax

    def observe(*args, **kwargs):
        calls.append(args[0])
        return original(*args, **kwargs)

    monkeypatch.setattr(grammar, "syntax", observe)
    monkeypatch.setattr(grammar, "transform", lambda *a, **kw: pytest.fail("native prepass"))
    source = prepare(value)
    assert calls == ["f(t)=t^2"]
    assert source.operands[0].source_declarations == ()
    assert source.operands[0].interpretation().status is ParseOutcome.AMBIGUOUS
    assert source.operands[1].interpretation().status is ParseOutcome.OK
    assert source.operands[2].interpretation().status is ParseOutcome.OK
    assert calls.count("f(t)=t^2") == 1
    basis = source.operands[2].source_declarations[0]
    assert basis.declaration.source_id == SOURCE
    assert value.canonical_text[basis.head_start : basis.head_end] == "f(t)"
    assert basis.scope_start == source.spans[1].segment.end
    assert basis.declaration.start == basis.scope_start
    assert basis.source_view_node_id == "view:1"
    assert basis.rule_id == "function-definition-1"


def test_unit_declaration_shadows_inherited_source_role_without_leaking_outside():
    value = content(
        [
            "f(t)=t",
            (SegmentKind.SECTION, ["f(u)", (SegmentKind.UNIT, ["f(t)=t^2", "f(u)"]), "f(u)"]),
        ]
    )
    source = prepare(value)
    inherited = source.operands[1]
    inner = source.operands[3]
    outside = source.operands[4]
    assert inherited.symbolic_value().func == outside.symbolic_value().func
    assert inner.symbolic_value().func != outside.symbolic_value().func
    assert inner.source_declarations[0].scope_key != inherited.source_declarations[0].scope_key
    assert len(inner.context.declarations) == 2  # selected source f and admitted Gamma


def test_section_definition_does_not_reach_sibling_section():
    value = content([(SegmentKind.SECTION, ["f(t)=t", "f(t)"]), (SegmentKind.SECTION, ["f(t)"])])
    source = prepare(value)
    assert source.operands[1].interpretation().status is ParseOutcome.OK
    assert source.operands[2].source_declarations == ()
    assert source.operands[2].interpretation().status is ParseOutcome.AMBIGUOUS


def test_request_cutoff_never_recognizes_future_source_syntax(monkeypatch):
    value = content(["f(t)", "f(t)=t", r"f(t)=\unknown"])
    first_end = next(value.document.walk()).children[0].end
    calls = []
    monkeypatch.setattr(grammar, "syntax", lambda *a, **kw: calls.append(a[0]))
    source = prepare(value, through_offset=first_end)
    assert len(source.operands) == 1
    assert source.definitions == ()
    assert calls == []


def test_source_prepass_timeout_is_one_failed_attempt(monkeypatch):
    value = content(["f(t)=t", "f(t)"])
    calls = []

    def timeout(*args, **kwargs):
        calls.append(None)
        return grammar.MathResult(
            "f(t)=t",
            "any_value",
            ParseOutcome.FAILED,
            failure=grammar.Failure("timeout", "Timeout"),
        )

    monkeypatch.setattr(grammar, "syntax", timeout)
    source = prepare(value)
    for result in (
        source.operands[0].syntax(),
        source.operands[1].interpretation(),
        source.operands[1].symbolic_reading(),
    ):
        assert result.failure is not None and result.failure.category == "timeout"
    assert len(calls) == 1


def test_selected_text_must_custody_the_preceding_declaration_view():
    with pytest.raises(EarlyMathContextUnavailable, match="missing"):
        prepare(content(["f(t)=t", "f(t)"]), source_views={})


def test_function_values_do_not_become_declarations():
    source = prepare(content(["f(0)=1", "f(t)"]))
    assert source.definitions == ()
    assert source.operands[1].interpretation().status is ParseOutcome.AMBIGUOUS


def test_malformed_candidate_only_blocks_subsequent_context_in_its_own_unit():
    value = content(["f(t)", (SegmentKind.UNIT, [r"f(t)=\unknown", "f(t)"]), "f(t)"])
    source = prepare(value)
    assert source.operands[0].source_context_failure is None
    assert source.operands[2].source_context_failure is not None
    assert source.operands[2].source_context_failure.category == "context_unavailable"
    assert source.operands[2].interpretation().status is ParseOutcome.AMBIGUOUS
    assert source.operands[3].source_context_failure is None


def test_production_readings_share_early_source_context(monkeypatch):
    from types import SimpleNamespace

    from corpus_structure.methods.math import methods
    from corpus_structure.semantic.parsing_products import ProductReference

    value = content(["f(t)=t", "f(t)"])
    ren = methods._Rendition(1, "rendition", "digest", value, {})
    selected = SimpleNamespace(reference=ProductReference(7, "text", "b" * 64))
    reader = SimpleNamespace(
        math_readings_batch=methods.MathReadingsBatch(),
        layered_products=lambda *args, **kwargs: (selected,),
    )
    first = methods._readings(ren, methods.NormalizeFormulaConfig(), reader)
    second = methods._readings(ren, methods.ExtractMathConfig(), reader)
    assert first is second
    assert first[1].result.status is ParseOutcome.OK
    assert first[1].prepared.source_declarations[0].declaration.source_id == SOURCE


def test_equality_inside_an_operator_condition_does_not_declare_outer_function():
    source = prepare(content([r"\operatorname{P}(f(t)=t)", "f(t)"]))
    assert source.definitions == ()
    assert source.operands[1].interpretation().status is ParseOutcome.AMBIGUOUS
