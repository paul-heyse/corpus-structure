"""Exact retained clause answer controls; no provider execution is claimed."""

from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.clause_products import (
    canonical_context_rows,
    declared_clause_focus,
    retained_clause_functions,
)
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


def paired_answer(
    *, score=0.9, candidate_product="product:functions", scores=None, selected_keys=("definition",)
):
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


def current_focus_inputs():
    from methods.declared_primary_fixture import selected_source

    from corpus_structure.semantic.structural_products import StructuralPassage

    text = " " * 20 + "Before. Focus. Next."
    _, frame, _context = selected_source(text)
    contribution_id = "source-contribution:" + "a" * 64
    passage = StructuralPassage(
        passage_id="sample",
        source_ref="source",
        start=20,
        end=40,
        text="Before. Focus. Next.",
        scope="sample",
    )
    contributions = [
        dict(
            contribution_id=contribution_id,
            pin=frame.pin.values(),
            component=dict(
                kind="predicate_frame",
                focus_state="exact",
                scope="sample",
                frame_members=[
                    dict(role="focus", outcome="complete", extents=[dict(start=28, end=33)])
                ],
                block="native-block",
            ),
        )
    ]
    from corpus_structure.semantic.data_operation_partitions import partition_header
    from corpus_structure.semantic.sentence_partitions import SentenceBlock

    packet = SentenceBlock(
        "native-block",
        0,
        20,
        40,
        tuple(
            dict(record_type="sentence", ordinal=ordinal, start=lo, end=hi, extent=20)
            for ordinal, (lo, hi) in enumerate(((0, 7), (8, 14), (15, 20)))
        ),
    ).packet()
    packets = (packet,)
    canonical = canonical_context_rows(
        dict(rows=partition_header(packets)), packets, text_length=len(text)
    )
    return contribution_id, passage, frame, contributions, canonical


@pytest.mark.parametrize("policy", ["exact_focus", "adjacent_sentences"])
def test_declared_clause_focus_preserves_original_extent_and_source_owned_context(policy):
    args = current_focus_inputs()
    focus, preceding, following, references = declared_clause_focus(*args, context_policy=policy)
    assert (focus.start, focus.end, focus.text) == (28, 33, "Focus")
    if policy == "adjacent_sentences":
        assert preceding is not None and following is not None
        assert (preceding.start, preceding.end, preceding.text) == (20, 27, "Before.")
        assert (following.start, following.end, following.text) == (35, 40, "Next.")
        ordinals = (0, 1, 2)
    else:
        assert preceding is None and following is None
        ordinals = (1,)
    assert [reference.item_key for reference in references] == [
        ("sentence", ordinal) for ordinal in ordinals
    ]
    assert all(
        (reference.role, reference.collection, reference.partition_key)
        == ("canonical", "rows", "native-block")
        for reference in references
    )


@pytest.mark.parametrize("change", ["partial", "foreign-source", "ambiguous-frame"])
def test_declared_clause_focus_refuses_partial_foreign_and_ambiguous_retained_frames(change):
    contribution_id, passage, frame, contributions, canonical = current_focus_inputs()
    if change == "partial":
        contributions[0]["component"]["focus_state"] = "partial"
    elif change == "foreign-source":
        contributions[0]["pin"] = dict(
            frame.pin.values(), source_product="unadmitted:foreign-source"
        )
    else:
        contributions.append(deepcopy(contributions[0]))
    with pytest.raises(ValueError, match=r"exactly one|actual retained native predicate scope"):
        declared_clause_focus(
            contribution_id,
            passage,
            frame,
            contributions,
            canonical,
            context_policy="adjacent_sentences",
        )


def test_target_clause_inventory_keeps_unknown_frames():
    from corpus_structure.semantic.data_product_reference import SemanticReference
    from corpus_structure.semantic.structural_products import (
        DeclaredClauseClassificationProduct,
    )

    reference = SemanticReference.member("predicates", "contribution:test-frame").member_value()
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


def test_selected_clause_requires_the_original_predicate_member(monkeypatch):
    from corpus_structure.semantic import selected_structural_projection
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.data_product_reference import SemanticReference
    from corpus_structure.semantic.structural_products import DeclaredClauseClassificationProduct

    member_id = "contribution:frame"
    reference = SemanticReference.member("predicates", member_id)
    choice = reference.member_value()
    clause = DeclaredClauseClassificationProduct(
        context_policy="exact_focus",
        readings=(),
        inspection_outcome="partial",
        inspected_frames=(choice,),
        unprojectable_frames=(choice,),
    )
    report = SimpleNamespace(
        condition_qualification=None,
        clause_classification=clause,
        predicate_input={"variant": "product", "role": "predicates"},
    )
    monkeypatch.setattr(
        selected_structural_projection,
        "read_nonrich_root",
        lambda _model, _selected: SimpleNamespace(structural=report),
    )

    operation = "structure.clause_classification/declared"
    target = {
        "output_role": "result",
        "path": "/clause_classification/inspected_frames/*",
        "input_role": "predicates",
        "variant": "member",
        "input_kind": "predicates-report",
    }
    parent_target = {**target, "path": "/predicate_input", "variant": "product"}
    original = {"role": "predicates", "product_id": "original", "position": 0, "multiplicity": 1}
    inputs = [original]
    actual_body = {
        "candidate_type": "contribution",
        "component": {"kind": "predicate_frame"},
        "contribution_id": "frame",
    }
    members = {("original", member_id): {"body": semantic_value(actual_body)}}
    maps = {
        "ops.demand_use": {
            "use": {
                "fate": "fulfilled",
                "derivation_id": "episode",
                "selection": {"inputs": inputs},
            },
        },
        "ops.data_derivation": {"episode": {"release_id": "release"}},
        "sem.data_operation_definition": {
            ("release", operation): {
                "support_contract": {"reference_targets": [parent_target, target]}
            },
        },
        "kb.data_product": {
            "original": {
                "project_id": "project",
                "kind_contract": "kind:predicates",
            }
        },
        "kb.data_product_member": members,
        "kb.data_product_partition": {},
        "sem.data_kind_contract": {"kind:predicates": {"kind": target["input_kind"]}},
    }

    def original_edges(relation, **fields):
        assert relation == "ops.data_derivation_input"
        assert fields == {"derivation_id": "episode", "role": "predicates"}
        return (original,)

    scope = SimpleNamespace(
        model=object(),
        cut=SimpleNamespace(record={"project_id": "project"}),
        index=SimpleNamespace(
            mapping=lambda relation, _: maps[relation],
            rows_for=original_edges,
        ),
    )
    selected = SimpleNamespace(
        operation_id=operation, derivation_id="episode", use_id="use", output={"role": "result"}
    )
    assert selected_structural_projection.structural_report(scope, selected) is report

    members["original", member_id]["body"] = semantic_value(
        {**actual_body, "component": {"kind": "qualification"}}
    )
    with pytest.raises(ValueError, match="does not resolve its predicate contribution"):
        selected_structural_projection.structural_report(scope, selected)

    # An empty frame inventory still carries the actual inspection's selected input.
    report.clause_classification = DeclaredClauseClassificationProduct(
        context_policy="exact_focus", readings=()
    )
    assert selected_structural_projection.structural_report(scope, selected) is report

    inputs[0] = {**original, "product_id": "equal-content-substitute"}
    with pytest.raises(ValueError, match="unavailable in the exact selected use"):
        selected_structural_projection.structural_report(scope, selected)


def test_current_clause_answer_preserves_overlaps_raw_scores_and_exact_focal_scope():
    prepared, frame, focus, pair = paired_answer(
        scores=(("definition", 0.92), ("example", 0.8), ("description", 0.4)),
        selected_keys=("definition", "example"),
    )
    labels, references, digest, disposition, _ = retained_clause_functions(
        prepared, frame, focus, (7, 13), (pair,)
    )
    assert [(label.label, label.score, label.accepted) for label in labels] == [
        ("definition", 0.92, True),
        ("example", 0.8, True),
        ("description", 0.4, False),
    ]
    assert len(references) == 1 and disposition == "observed" and digest
    assert pair[1]["members"][0]["body"]["anchors"] == ()
    assert retained_clause_functions(prepared, frame, focus, (0, 19), (pair,))[3] == "failed"
