"""Exact retained clause answer controls; no provider execution is claimed."""

from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.clause_products import retained_clause_functions
from corpus_structure.semantic.contributions import contribution_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import (
    characterization_question_dependencies,
    compile_question_families,
    declared_families,
)
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.structural_products import LocatedDefinitionSpan
from corpus_structure.semantic.types import ResolvedDependencies


def paired_answer(*, score=0.9, candidate_product="product:functions", scores=None, selected_keys=("definition",)):
    scores = (("definition", score), ("explanation", 0.4)) if scores is None else scores
    prepared = SimpleNamespace(
        registry_rows=compile_question_families(
            characterization_question_dependencies(ResolvedDependencies()).artifacts
        )
    )
    family = declared_families(prepared.registry_rows)["character_gliner_function_v1"]
    pin = {"source": "actual-native-source"}
    frame = SimpleNamespace(
        text="First. Focus. Last.", pin=SimpleNamespace(values=lambda: dict(pin))
    )
    scope = dict(pin=pin, projection_extent=[7, 13], scope_digest="a" * 64)
    request = dict(
        declaration_digest=family.digest,
        question_key="functions",
        label_keys=[option.key for option in family.questions[0].options],
        assessed_scope=scope,
        item={"text": "Focus."},
        threshold=0.5,
    )
    report = dict(
        provider="gliner",
        question=family.family,
        version="2",
        request=request,
        native={
            "outcome": "succeeded",
            "native": {
                "functions": [
                    *({"label": label, "confidence": probability} for label, probability in scores),
                ]
            },
        },
        input_digest="b" * 64,
    )
    value = dict(
        question_key="functions",
        answer_kind="choice",
        state="proposed",
        native_answer={
            "type": "gliner_classification",
            "scores": dict(scores),
        },
        assessed_scope=scope,
        observed_keys=[label for label, _ in scores],
        selected_keys=list(selected_keys),
    )
    row = dict(
        contract="RetainedContributionSemantics",
        kind="proposal",
        semantic_type="interpretation." + family.family,
        operation_key="actual:operation",
        item_key="interpretation:functions",
        pin=pin,
        anchors=(),
        value=source_value(value),
        disposition="unassessed",
        standing="retained_private",
        score_state="missing",
        computation_dependencies=(report["input_digest"],),
    )
    row["contribution_id"] = contribution_identity(row)
    observation = dict(source_pin=pin, observations=[source_value(report)])
    candidates = dict(
        source_pin=pin,
        operations=[
            dict(
                operation_key=row["operation_key"],
                question=family.family,
                report_digest=sha256(canonical_bytes(report)).hexdigest(),
                computation_dependencies=[report["input_digest"]],
            )
        ],
        members=[
            dict(
                member_id="contribution:" + row["contribution_id"],
                body={"candidate_type": "contribution", **row},
            )
        ],
    )
    focus = LocatedDefinitionSpan(passage_id="original-block", start=7, end=13, text="Focus.")
    return prepared, frame, focus, (observation, candidates, candidate_product)


def test_exact_native_clause_answer_preserves_released_labels_scores_and_member_reference():
    prepared, frame, focus, pair = paired_answer()
    labels, references, digest, disposition, _reason = retained_clause_functions(
        prepared, frame, focus, (7, 13), (pair,)
    )
    assert [(label.label, label.score, label.accepted) for label in labels] == [
        ("definition", 0.9, True),
        ("explanation", 0.4, False),
    ]
    assert disposition == "observed" and digest
    assert references[0].product_id == "product:functions"
    assert references[0].member_id == pair[1]["members"][0]["member_id"]
    assert "task_id" not in references[0].model_dump()


def test_rival_exact_answers_preserve_both_origins_without_selecting_a_provider():
    prepared, frame, focus, first = paired_answer()
    _prepared, _frame, _focus, second = paired_answer(score=0.8, candidate_product="product:rival")
    labels, references, digest, disposition, _reason = retained_clause_functions(
        prepared, frame, focus, (7, 13), (first, second)
    )
    assert labels == () and digest is None and disposition == "failed"
    assert {reference.product_id for reference in references} == {
        "product:functions",
        "product:rival",
    }


def test_context_question_cannot_substitute_for_exact_clause_and_wrong_pair_refuses():
    prepared, frame, focus, pair = paired_answer()
    assert retained_clause_functions(prepared, frame, focus, (0, 19), (pair,))[3] == "failed"
    changed = deepcopy(pair)
    changed[1]["operations"][0]["report_digest"] = "different-observation"
    with pytest.raises(ValueError, match="exact request/reply pair"):
        retained_clause_functions(prepared, frame, focus, (7, 13), (changed,))


def test_target_clause_inventory_keeps_unknown_frames_and_historical_empty_refusal():
    from corpus_structure.semantic.declared_structural_references import (
        DeclaredContributionRef,
        DeclaredStructuralSource,
    )
    from corpus_structure.semantic.structural_products import (
        ClauseClassificationProduct,
        DeclaredClauseClassificationProduct,
        StructuralInput,
        StructuralPassage,
        StructuralProductReport,
    )

    reference = DeclaredContributionRef(
        product_id="product:predicates",
        kind_contract="kind:predicate",
        project_id="p",
        subject="native:source",
        original_source="book",
        analyzed_scope_meaning="{}",
        contribution_id="source-contribution:" + "a" * 64,
        subject_definition="original-source-view",
    )
    partial = DeclaredClauseClassificationProduct(
        context_policy="exact_focus",
        readings=(),
        inspection_outcome="partial",
        inspected_frames=(reference,),
        unprojectable_frames=(reference,),
    )
    assert partial.inspection_outcome == "partial" and partial.unprojectable_frames == (reference,)
    assert (
        DeclaredClauseClassificationProduct(
            context_policy="exact_focus", readings=()
        ).inspection_outcome
        == "complete"
    )
    with pytest.raises(ValueError, match="partial inspection"):
        DeclaredClauseClassificationProduct(
            context_policy="exact_focus",
            readings=(),
            inspected_frames=(reference,),
            unprojectable_frames=(reference,),
        )
    with pytest.raises(ValueError, match="inspected frame closure"):
        DeclaredClauseClassificationProduct(
            context_policy="exact_focus", readings=(), inspected_frames=(reference,)
        )
    source = DeclaredStructuralSource(
        source='["product:source",null]',
        subject="native:source",
        document="book",
        projection_digest="b" * 64,
        section_pointer="#/groups/0",
        membership="direct",
        project_id="p",
        original_source="book",
        analyzed_scope_meaning="{}",
        source_product="product:source",
        kind_contract="kind:source",
        subject_definition="original-source-view",
    )
    passage = StructuralPassage(
        passage_id="p", source_ref=source.identity, start=0, end=1, text="x", scope="local"
    )
    inputs = StructuralInput(
        question="Classify",
        scope="local",
        inventory_id="selected",
        policy_id="clause",
        sources=(source,),
        passages=(passage,),
        dependencies=(reference.product_id,),
    )
    with pytest.raises(ValueError, match="distinct selected focuses"):
        StructuralProductReport(
            kind="clause_classification",
            inputs=inputs,
            clause_classification=ClauseClassificationProduct(
                context_policy="exact_focus", readings=()
            ),
        )


def test_current_clause_answer_preserves_overlaps_raw_scores_and_exact_focal_scope():
    prepared, frame, focus, pair = paired_answer(scores=(("definition", 0.92), ("example", 0.8), ("description", 0.4)), selected_keys=("definition", "example"))
    labels, references, digest, disposition, _ = retained_clause_functions(prepared, frame, focus, (7, 13), (pair,))
    assert [(label.label, label.score, label.accepted) for label in labels] == [("definition", 0.92, True), ("example", 0.8, True), ("description", 0.4, False)]
    assert len(references) == 1 and disposition == "observed" and digest
    assert pair[1]["members"][0]["body"]["anchors"] == ()
    assert retained_clause_functions(prepared, frame, focus, (0, 19), (pair,))[3] == "failed"
