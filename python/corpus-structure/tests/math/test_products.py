"""Pure mathematical transport retains qualified source occurrences and named evidence."""

from __future__ import annotations

import pytest

from corpus_structure.methods.math.prepared import PreparedMathInput
from corpus_structure.methods.math.products import assessment_product_payload, interpretation_product_payload
from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context
from corpus_structure.semantic.parsing_products import prepare_layered_product

ROOT = dict(task_id=7, product_key="source", content_digest="a" * 64)
TEXT = dict(task_id=7, product_key="text", content_digest="b" * 64)


def value(text):
    return PreparedMathInput(prepare_interpretation_context(macros={}, kind="formula"), text,
                             source_text="$ " + text + " $", source_start=10, parse_start=12)


def test_interpretation_transport_keeps_occurrences_after_native_combination():
    operand = value("x+x")
    p = prepare_layered_product(interpretation_product_payload(operand, root=ROOT,
        text_product=TEXT, source_node_id="view:0", symbolic=True)).values()
    assert p["interpretations"][0]["occurrence_ids"] == ["occurrence:0", "occurrence:1"]
    assert [(n["name"], n["start_offset"], n["end_offset"]) for n in p["nodes"] if n["kind"] == "symbol"] == [
        ("x", 0, 1), ("x", 2, 3),
    ]
    source = next(e for e in p["mapping_endpoints"] if e["side"] == "source")
    assert (source["target_task_id"], source["target_product_key"], source["start_offset"], source["end_offset"]) == (7, "text", 12, 15)
    assert operand.state("scientific").work == "not_requested"


def test_weaker_interpretation_retains_ambiguity_in_persistable_product():
    operand = value("f(x)")
    p = prepare_layered_product(interpretation_product_payload(operand, root=ROOT,
        text_product=TEXT, source_node_id="view:0")).values()
    assert p["semantic_state"] == "ambiguous"
    assert p["interpretations"][0]["alternative_group"] == "alternatives:0"
    assert operand.state("symbolic").work == "not_requested"


def test_assessment_points_to_exact_interpretation_and_preserves_definedness():
    operand = value("x/x")
    interpretation = prepare_layered_product(interpretation_product_payload(operand, root=ROOT,
        text_product=TEXT, source_node_id="view:0"))
    reference = dict(task_id=8, product_key="math", content_digest=interpretation.digest)
    p = prepare_layered_product(assessment_product_payload(operand, operand.assess("refine"),
        root=ROOT, interpretation_product=reference)).values()
    assert p["assessments"][0]["question"] == "refine"
    assert p["assessments"][0]["interpretation_ids"] == ["interpretation:0"]
    assert p["endpoints"][1]["target_content_digest"] == interpretation.digest
    assert '"requirement":"nonzero"' in p["nodes"][0]["value"]
    assert '"format":"sympy-srepr-1"' in p["nodes"][0]["value"]


def test_source_endpoint_cannot_drop_its_product_qualification():
    p = interpretation_product_payload(value("x"), root=ROOT, text_product=TEXT, source_node_id="view:0")
    del p["endpoints"][1]["target_content_digest"]
    with pytest.raises(ValueError, match="product reference"):
        prepare_layered_product(p)


def test_syntax_transport_does_not_prepare_contextual_interpretation():
    operand = value("f(x)")
    p = prepare_layered_product(interpretation_product_payload(operand, root=ROOT,
        text_product=TEXT, source_node_id="view:0", stage="syntax")).values()
    assert p["semantic_state"] == "unknown"
    assert p["interpretations"] == []
    assert operand.state("interpretation").work == "not_requested"
    assert operand.state("symbolic").work == "not_requested"


def test_symbolic_transport_keeps_requested_native_evidence():
    p = prepare_layered_product(interpretation_product_payload(value("x+x"), root=ROOT,
        text_product=TEXT, source_node_id="view:0", stage="symbolic")).values()
    assert p["semantic_state"] == "ok"
    assert '"format":"sympy-srepr-1"' in p["nodes"][0]["value"]
    assert "Mul(Integer(2), Symbol('x'))" in p["nodes"][0]["value"]


def test_unsupported_symbolic_transport_retains_source_capture():
    p = prepare_layered_product(interpretation_product_payload(value(r"x \pm y"), root=ROOT,
        text_product=TEXT, source_node_id="view:0", stage="symbolic")).values()
    assert p["semantic_state"] == "unsupported"
    assert p["coverage"] == "partial"
    assert p["representations"][0]["text_content"] == r"x \pm y"


def test_unknown_definedness_transport_cannot_claim_complete_empty_conditions():
    operand = value(r"x^{-n}x^n")
    p = prepare_layered_product(assessment_product_payload(operand, operand.assess("definedness"),
        root=ROOT, interpretation_product=dict(task_id=8, product_key="math", content_digest="c" * 64))).values()
    assert p["semantic_state"] == "unknown"
    assert p["coverage"] == "partial"
    assert '"coverage":"partial"' in p["nodes"][0]["value"]
    assert 'unsupported source power domain' in p["nodes"][0]["value"]
    assert p["assessments"][0]["algorithm_revision"] == "native-assessment-2"


@pytest.mark.parametrize("stage", ["syntax", "interpretation", "symbolic"])
def test_every_stage_timeout_is_failed_without_serialization_retry(monkeypatch, stage):
    from corpus_structure.core.vocab import ParseOutcome
    from corpus_structure.methods.math import grammar

    operand = value("x+x")
    calls = []
    def timeout(*args, **kwargs):
        calls.append(None)
        return grammar.MathResult("x+x", "formula", ParseOutcome.FAILED,
                                  failure=grammar.Failure("timeout", "Timeout"))
    monkeypatch.setattr(grammar, "syntax", timeout)
    monkeypatch.setattr(PreparedMathInput, "definedness_result",
                        lambda self: pytest.fail("serializer retried definedness"))
    monkeypatch.setattr(PreparedMathInput, "symbolic_value",
                        lambda self: pytest.fail("serializer entered native after timeout"))
    p = prepare_layered_product(interpretation_product_payload(operand, root=ROOT,
        text_product=TEXT, source_node_id="view:0", stage=stage)).values()
    assert (p["lifecycle"], p["semantic_state"], p["coverage"]) == ("failed", "unknown", "partial")
    assert p["representations"][0]["text_content"] == "x+x"
    assert p["representations"][0]["partition_state"] == "complete"
    assert len(p["components"]) == 3
    assert len(calls) == 1


def test_native_timeout_does_not_enter_definedness_during_serialization(monkeypatch):
    from corpus_structure.methods.math import grammar

    operand = value("x")
    def expire(self):
        raise grammar.Expired()
    monkeypatch.setattr(PreparedMathInput, "symbolic_value", expire)
    monkeypatch.setattr(PreparedMathInput, "definedness_result",
                        lambda self: pytest.fail("serializer entered definedness after timeout"))
    p = prepare_layered_product(interpretation_product_payload(operand, root=ROOT,
        text_product=TEXT, source_node_id="view:0", stage="symbolic")).values()
    assert (p["lifecycle"], p["semantic_state"], p["coverage"]) == ("failed", "unknown", "partial")


def test_failed_read_can_be_requested_by_a_fresh_operation_with_a_new_budget(monkeypatch):
    from corpus_structure.core.vocab import ParseOutcome
    from corpus_structure.methods.math import grammar

    original = grammar.syntax
    first = value("x")
    later = PreparedMathInput(first.context, "x", seconds=3.0, parse_start=12)
    calls = []
    def budgeted(*args, **kwargs):
        calls.append(kwargs["seconds"])
        if len(calls) == 1:
            return grammar.MathResult("x", "formula", ParseOutcome.FAILED,
                                      failure=grammar.Failure("timeout", "Timeout"))
        return original(*args, **kwargs)
    monkeypatch.setattr(grammar, "syntax", budgeted)
    failed = interpretation_product_payload(first, root=ROOT, text_product=TEXT,
                                            source_node_id="view:0")
    succeeded = interpretation_product_payload(later, root=ROOT, text_product=TEXT,
                                               source_node_id="view:0")
    assert failed["lifecycle"] == "failed"
    assert succeeded["lifecycle"] == "available"
    assert succeeded["semantic_state"] == "ok"
    assert calls == [2.0, 3.0]


def test_assessment_timeout_serialization_never_reenters_source_stages(monkeypatch):
    from corpus_structure.methods.math.prepared import MathAssessment

    operand = value("x")
    monkeypatch.setattr(PreparedMathInput, "interpretation",
                        lambda self: pytest.fail("serializer retried interpretation"))
    monkeypatch.setattr(PreparedMathInput, "definedness_result",
                        lambda self: pytest.fail("serializer retried definedness"))
    p = prepare_layered_product(assessment_product_payload(operand,
        MathAssessment("definedness", "timeout", coverage="partial"), root=ROOT,
        interpretation_product=dict(task_id=8, product_key="math", content_digest="c" * 64))).values()
    assert (p["lifecycle"], p["semantic_state"], p["coverage"]) == ("failed", "unknown", "partial")
