"""Actual sentence/predicate/condition execution and protected native conclusions.

The two literal cases are specific provider functional expectations. Controlled
Docling decoding and attributed A/B/C authorship do not establish model accuracy.
"""

from copy import deepcopy

import pytest
from sqlalchemy.exc import DBAPIError

from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_service import DemandOperationSelection
from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
from corpus_structure.semantic.identity import canonical_bytes
from semantic.current_pdf_source_support import (
    admit_current_target,
)
from semantic.current_pdf_source_support import (
    current_pdf_source_factory as current_pdf_source_factory,
)
from semantic.structural_admission_native_support import ISSUER, execute, request, selected
from semantic.structural_production_native_support import (
    CONDITION,
    PREDICATES,
    assert_native_transport_parity,
    produce_source_reports,
    publish_statement,
    read_statement,
    recipe,
    selected_for_source,
    source_pin,
)


@pytest.mark.parametrize(
    "literal,qualifier,host",
    [
        (
            "If the sample includes duplicates, the algorithm computes the mean.",
            "If the sample includes duplicates",
            "computes",
        ),
        (
            "If the manager approves the invoice, the clerk must release the payment.",
            "If the manager approves the invoice",
            "release",
        ),
    ],
    ids=("textbook", "business"),
)
def test_condition_admits_only_the_exact_supported_roles(
    current_pdf_source_factory, native_settings, literal, qualifier, host, tmp_path
):
    source = current_pdf_source_factory((("text", literal, literal, None),))
    kernel = admit_current_target(source, recipe(tmp_path / "recipe"), tmp_path / "consumer")
    _, original, products, _ = produce_source_reports(source, kernel, PREDICATES, text=literal)
    (predicates,) = selected_for_source(
        kernel,
        products,
        "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoPredicateInspectionReport",
        original,
    )
    attachments = [
        member["body"]
        for member in predicates.body["members"]
        if member["body"].get("component", {}).get("qualifier_kind") == "condition"
    ]
    assert len(attachments) == 1
    selection = DemandOperationSelection(
        operation=CONDITION,
        parameters=dict(
            start=0,
            end=len(literal),
            passage_id="condition",
            attachment=attachments[0]["contribution_id"],
            question="Which exact predicate is qualified?",
            scope="condition-scope",
            inventory_id="actual-native-condition",
            policy_id="exact-retained-structural-v1",
        ),
    )
    producer_request = request(
        kernel,
        (CONDITION,),
        original.context,
        source_sets=(
            FrozenSourceSet.from_selected("structural-source", (original.entry(),)),
            FrozenSourceSet.from_selected("structural-report", (predicates.entry(),)),
        ),
        selections=(selection,),
        inference="actual-condition-producer",
    )
    retained, result = execute(kernel, producer_request)
    assert result.receipt_count == 1
    (report,) = selected(
        kernel, retained["demand_id"], kind="urn:corpus:structural:DeclaredConditionReport"
    )
    pointer = next(
        piece["item_ref"] for piece in original.body["pieces"] if piece["kind"] == "native_text"
    )

    def citation(text):
        start = literal.index(text)
        return dict(
            source_pointer=pointer,
            passage=dict(
                source=source_pin(original),
                start=start,
                end=start + len(text),
                text=text,
                scope="condition-scope",
            ),
        )

    expected = dict(
        version="structural-public-statement-3",
        kind="condition_qualification",
        scope="condition-scope",
        coverage_limits=[],
        exclusions=[],
        condition_qualification=dict(
            relation="condition", qualifier=[citation(qualifier)], host_predicate=[citation(host)]
        ),
    )
    issued, admission, originals, _ = publish_statement(
        kernel, report, expected, inference="condition-support:" + host
    )
    assert admission.body["policy_id"] == "independent-condition-qualification-1"
    assert admission.body["component_id"] is None
    assert admission.body["scientific_truth"] == "not_established"
    assert (
        admission.body["statement_meaning_json"]
        == canonical_bytes(semantic_value(expected)).decode()
    )
    pending, page = read_statement(kernel, issued["demand_id"], report, admission)
    assert page["public_admission"] == "selected_native_statements"
    assert page["reports"][0]["public_assertions"][0]["admission"] == admission.body
    assert page["reports"][0]["public_assertions"][0]["authority"]["standing"] == "valid"
    if host == "computes":
        assert_native_transport_parity(kernel, native_settings, pending, page, tmp_path)

    # A different whole-statement expectation is genuinely authored, then refused
    # by the same command; prior valid support is not re-used for switched roles.
    from semantic.structural_reference_native_support import original_passes

    switched = deepcopy(expected)
    (
        switched["condition_qualification"]["qualifier"],
        switched["condition_qualification"]["host_predicate"],
    ) = (
        switched["condition_qualification"]["host_predicate"],
        switched["condition_qualification"]["qualifier"],
    )
    wrong, _ = original_passes(kernel, report, switched, inference="switched-condition:" + host)
    with pytest.raises(NativeDemandExecutionError):
        execute(
            kernel,
            request(
                kernel,
                (ISSUER,),
                report.context,
                originals=wrong,
                admission_report=report,
                admission_variant="condition",
                inference="refuse-switched-condition:" + host,
            ),
            purpose="evaluate",
            author=True,
        )
    # Ordinary writer authority cannot author the protected judgments or issue.
    with pytest.raises(DBAPIError) as denied:
        execute(
            kernel,
            request(
                kernel,
                (ISSUER,),
                report.context,
                originals=originals,
                admission_report=report,
                admission_variant="condition",
                inference="refuse-writer-condition:" + host,
            ),
            author=True,
        )

    assert getattr(denied.value.orig, "sqlstate", None) == "42501"
