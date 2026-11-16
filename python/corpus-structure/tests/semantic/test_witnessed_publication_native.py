"""Exact named component from actual sentence/construction production and native admission.

This literal functional case does not establish whole applicability or general
linguistic accuracy. The independent A/B/C authors are explicitly attributed.
"""

import pytest

from corpus_structure.evaluate.declared_structural_admission import DdoStructuralAssessmentFrame
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.identity import canonical_bytes
from semantic.current_pdf_source_support import (
    admit_current_target,
)
from semantic.current_pdf_source_support import (
    current_pdf_source_factory as current_pdf_source_factory,
)
from semantic.structural_production_native_support import (
    NAMED,
    produce_source_reports,
    publish_statement,
    read_statement,
    recipe,
    selected_for_source,
    source_pin,
)


def test_exact_component_admits_without_whole_applicability(current_pdf_source_factory, tmp_path):
    literal = "We define variance as spread."
    source = current_pdf_source_factory((("text", literal, literal, None),))
    kernel = admit_current_target(source, recipe(tmp_path / "recipe"), tmp_path / "consumer")
    _, original, products, _ = produce_source_reports(source, kernel, NAMED, text=literal)
    (report,) = selected_for_source(
        kernel, products, "urn:corpus:structural:DeclaredDefinitionComponentsReport", original
    )
    (component,) = report.body["definition_components"]["components"]
    # Span meaning is independent literal expectation; native primary block and
    # product addresses supply only the selected physical scope/custody identity.
    passage = next(
        value
        for value in report.body["inputs"]["passages"]
        if value["passage_id"] == component["term"]["passage_id"]
    )
    assert passage["text"] == literal

    def span(start, end):
        return dict(
            source=source_pin(original),
            start=start,
            end=end,
            text=literal[start:end],
            scope=passage["scope"],
        )

    expected = dict(
        version="structural-public-statement-3",
        kind="definition_components",
        scope="selected-native-blocks",
        coverage_limits=[],
        exclusions=[],
        definition_component=dict(
            term=span(10, 18),
            content=span(22, 28),
            interpretation="definition",
            scope=passage["scope"],
        ),
    )
    issued, admission, _, passes = publish_statement(
        kernel,
        report,
        expected,
        component_id=component["component_id"],
        inference="actual-named-definition",
    )
    assert admission.body["policy_id"] == "independent-definition-component-1"
    assert admission.body["component_id"] == component["component_id"]
    assert admission.body["scientific_truth"] == "not_established"
    assert admission.body["member_truth"] == "not_established_by_assembly_admission"
    assert (
        admission.body["statement_meaning_json"]
        == canonical_bytes(semantic_value(expected)).decode()
    )
    _, page = read_statement(kernel, issued["demand_id"], report, admission)
    assert page["public_admission"] == "selected_native_statements"
    assert page["reports"][0]["public_assertions"][0]["admission"] == admission.body
    with pytest.raises(ValueError):
        DdoStructuralAssessmentFrame.model_validate(
            {**passes[2]["frame"], "rubric_version": "independent-witnessed-applicability-1"}
        )
