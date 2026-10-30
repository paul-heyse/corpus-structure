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
