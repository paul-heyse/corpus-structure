"""Independent semantic identity and provenance boundaries for public projection."""

from copy import deepcopy

import pytest

from corpus_structure.semantic.contextual_links import RetainedRelationshipDecisionRef
from corpus_structure.semantic.structural_admission import structural_claim_id, structural_statement
from corpus_structure.semantic.structural_products import (
    ApplicabilityPremise,
    DefinitionProduct,
    DossierMember,
    DossierProduct,
    ExternalSourceRef,
    LocatedDefinitionSpan,
    RetainedComponentRef,
    StructuralDefinitionReading,
    StructuralInput,
    StructuralPassage,
    StructuralProductReport,
    definition_component,
)


def source():
    return ExternalSourceRef(
        project_id="source-project",
        run_id=1,
        cut_id=2,
        release_id="old",
        result_revision=4,
        source_view_id=5,
        native_task_id=6,
        native_product_key="book",
        native_content_digest="a" * 64,
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        coordinate_version=3,
    )


def inputs():
    ref = source()
    return StructuralInput(
        question="What defines this usage?",
        scope="statistics",
        inventory_id="frozen-targets",
        policy_id="declared-source-1",
        sources=(ref,),
        passages=(
            StructuralPassage(
                passage_id="usage",
                source_ref=ref.identity,
                start=0,
                end=4,
                text="mean",
                scope="statistics",
            ),
            StructuralPassage(
                passage_id="target",
                source_ref=ref.identity,
                start=5,
                end=14,
                text="sum/count",
                scope="statistics",
            ),
        ),
        dependencies=("frozen-source-input", "component-product"),
    )


def fixture_component():
    passage = inputs().passages[1]
    span = LocatedDefinitionSpan(
        passage_id=passage.passage_id, start=passage.start, end=passage.end, text=passage.text
    )
    return definition_component(
        term=span,
        content=span,
        interpretation="definition",
        basis="model_reading",
        scope=passage.scope,
        evidence=(passage.passage_id,),
        reason="Literal shape fixture",
    )


def definition():
    return StructuralProductReport(
        kind="definition_applicability",
        inputs=inputs(),
        definition=DefinitionProduct(
            usage_id="usage",
            candidate_list_id="list1",
            eligible_targets=(fixture_component().component_id,),
            candidate_targets=(fixture_component().component_id,),
            readings=(
                StructuralDefinitionReading(
                    target_id=fixture_component().component_id,
                    component_ref=RetainedComponentRef(
                        product_id="component-product",
                        component_id=fixture_component().component_id,
                        operation_id="structure.definition_components",
                        operation_version="1",
                        project_id="book",
                        run_id=1,
                        cut_id=1,
                        release_id="r",
                        result_revision=1,
                        selected_task_id=1,
                        origin_task_id=1,
                        runtime_fingerprint="runtime",
                        dependencies=("source",),
                    ),
                    link_ref=RetainedRelationshipDecisionRef(
                        project_id="book",
                        run_id=1,
                        cut_id=1,
                        release_id="r",
                        result_revision=1,
                        selected_task_id=2,
                        origin_task_id=2,
                        runtime_fingerprint="runtime",
                        operation_key="operation",
                        decision_id="decision",
                        edge_id="edge",
                        occurrence_contribution_id="occurrence",
                    ),
                    component=fixture_component(),
                    premises=tuple(
                        ApplicabilityPremise(
                            dimension=dimension,
                            state="unknown"
                            if dimension in {"parent", "parameterization", "convention"}
                            else "compatible",
                            evidence=("target",),
                            reason="Independent explicit fixture premise",
                        )
                        for dimension in (
                            "sense",
                            "parameterization",
                            "convention",
                            "scope",
                            "version",
                            "parent",
                        )
                    ),
                    outcome="unresolved",
                    evidence=("target",),
                    reason="supplied reading",
                ),
            ),
        ),
    )


def test_definition_projection_preserves_meaning_without_derivation():
    value = structural_statement(definition())
    assert value["definition"]["usage"]["text"] == "mean"
    assert value["definition"]["readings"][0]["outcome"] == "unresolved"
    assert value["definition"]["readings"][0]["evidence"][0]["start"] == 5
    physical = value["definition"]["usage"]["source"]
    assert physical["native_content_digest"] == "a" * 64
    assert not {"run_id", "native_task_id", "source_view_id"} & physical.keys()
    assert "candidate_list_id" not in value["definition"]
    assert "reason" not in value["definition"]["readings"][0]


def test_generated_alias_and_execution_changes_do_not_change_claim():
    original = definition()
    changed = deepcopy(original.model_dump(mode="json"))
    changed["inputs"]["sources"][0].update(
        run_id=99,
        cut_id=100,
        release_id="replay",
        result_revision=101,
        source_view_id=102,
        native_task_id=103,
    )
    new_ref = ExternalSourceRef.model_validate(changed["inputs"]["sources"][0])
    for p in changed["inputs"]["passages"]:
        p["source_ref"] = new_ref.identity
    changed["definition"]["candidate_list_id"] = "list-after-replay"
    changed["definition"]["readings"][0]["reason"] = "different derivation explanation"
    after = StructuralProductReport.model_validate(changed)
    assert original.product_id != after.product_id
    assert structural_claim_id(structural_statement(original)) == structural_claim_id(
        structural_statement(after)
    )


def test_scope_and_outcome_are_semantic():
    original = definition()
    changed = original.model_dump(mode="json")
    changed["definition"]["readings"][0]["outcome"] = "mention"
    assert structural_claim_id(structural_statement(original)) != structural_claim_id(
        structural_statement(StructuralProductReport.model_validate(changed))
    )


def test_dossier_complete_membership_does_not_depend_on_display():
    members = tuple(
        DossierMember(
            member_id=str(i),
            passage_id="target",
            role=role,
            sense="mean",
            scope="statistics",
            relation_product_id="structural:upstream",
        )
        for i, role in enumerate(("definition", "exception", "conflict"))
    )
    report = StructuralProductReport(
        kind="dossier",
        inputs=inputs(),
        dossier=DossierProduct(
            root_id="mean",
            members=members,
            representatives=("0", "1", "2"),
            missing_sections=("revision",),
        ),
    )
    statement = structural_statement(report)
    assert len(statement["dossier"]["members"]) == 3
    assert statement["dossier"]["admission_scope"] == "membership_assembly_not_member_truth"
    assert report.dossier is not None
    displayed = report.model_copy(
        update={"dossier": report.dossier.model_copy(update={"representatives": ("0",)})}
    )
    assert structural_statement(displayed) == statement


def test_public_statement_and_policy_are_released_shapes():
    from pathlib import Path

    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
    from corpus_structure.semantic.observations import observation_inputs

    path = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    prepared = prepare_release(
        observation_inputs(SourceBundle("core", (SourceArtifact("core", path.read_bytes()),)))
    )
    prepared.validate_python(
        "StructuralPublicationPolicy",
        {
            "policy_id": "independent-witnessed-applicability-1",
            "policy_version": "1",
            "product_kind": "definition_applicability",
            "facet": "public_statement",
        },
    )
    from corpus_structure.semantic.identity import canonical_bytes

    prepared.validate_json(
        "StructuralPublicStatement", canonical_bytes(structural_statement(definition()))
    )


def test_numeric_retrieval_is_raw_task_provenance_not_envelope_identity():
    report = definition()
    with_scores = report.model_copy(
        update={"retrieval_report": {"score": 0.000001, "vector": [0.1, -0.0]}}
    )
    changed_scores = report.model_copy(
        update={"retrieval_report": {"score": 0.000002, "vector": [0.2, -0.0]}}
    )
    assert with_scores.product_id == changed_scores.product_id == report.product_id
    from corpus_structure.semantic.identity import canonical_bytes

    assert canonical_bytes(with_scores.model_dump(mode="json")) != canonical_bytes(
        changed_scores.model_dump(mode="json")
    )


def test_definition_attachment_fact_identity_excludes_interpretation_proof_and_retrieval():
    from corpus_structure.semantic.structural_products import DefinitionComponentsProduct

    component = fixture_component()
    report = StructuralProductReport(
        kind="definition_components",
        inputs=inputs(),
        definition_components=DefinitionComponentsProduct(components=(component,), stages=()),
    )
    meaning = component.model_dump(exclude={"component_id"})
    meaning.update(basis="matched_cue", alternatives=("another-private-proposal",))
    revised = definition_component(**meaning)
    after = report.model_copy(
        update={
            "inputs": report.inputs.model_copy(
                update={"inventory_id": "new-inventory", "policy_id": "new-nomination-policy"}
            ),
            "definition_components": DefinitionComponentsProduct(components=(revised,), stages=()),
        }
    )
    assert report.product_id != after.product_id
    assert structural_statement(report, component.component_id) == structural_statement(
        after, revised.component_id
    )


def test_applicability_claim_excludes_nomination_and_component_derivation():
    original = definition()
    changed = original.model_dump(mode="json")
    first = changed["definition"]["readings"][0]
    meaning = {key: value for key, value in first["component"].items() if key != "component_id"}
    meaning.update(basis="matched_cue", reason="Separate source-supported producer basis")
    revised = definition_component(**meaning)
    first["component"] = revised.model_dump(mode="json")
    first["component_ref"]["component_id"] = revised.component_id
    first["target_id"] = revised.component_id
    changed["definition"].update(
        candidate_targets=[revised.component_id],
        eligible_targets=[revised.component_id, "another-candidate"],
        candidate_list_id="different-list",
        inventory_coverage="known_gap",
    )
    changed["inputs"].update(
        inventory_id="different-inventory",
        policy_id="different-nomination",
        question="Different request wording",
    )
    after = StructuralProductReport.model_validate(changed)
    assert original.product_id != after.product_id
    assert structural_statement(original) == structural_statement(after)
    assert set(structural_statement(after)["definition"]) == {"usage", "readings"}


def test_physical_citation_aliases_do_not_duplicate_applicability_evidence():
    original = definition()
    changed = original.model_dump(mode="json")
    alias = dict(changed["inputs"]["passages"][1], passage_id="same-physical-target")
    changed["inputs"]["passages"].append(alias)
    changed["definition"]["readings"][0]["evidence"] = ["target", "target", "same-physical-target"]
    for premise in changed["definition"]["readings"][0]["premises"]:
        premise["evidence"] = ["target", "same-physical-target", "target"]
    after = StructuralProductReport.model_validate(changed)
    assert structural_statement(original) == structural_statement(after)


@pytest.mark.parametrize(
    "change",
    [
        pytest.param("question", id="domain-identity-independent-question-wording"),
        pytest.param("reading_reason", id="domain-identity-independent-reading-explanation"),
        pytest.param("premise_reason", id="domain-identity-independent-premise-explanation"),
        pytest.param("policy", id="domain-identity-independent-nomination-policy"),
    ],
)
def test_assessment_wording_cannot_change_domain_statement_identity(change):
    original = definition()
    body = original.model_dump(mode="json")
    if change == "question":
        body["inputs"]["question"] = "Which source text could apply at the selected occurrence?"
    elif change == "reading_reason":
        body["definition"]["readings"][0]["reason"] = "Independent assessor wording"
    elif change == "premise_reason":
        body["definition"]["readings"][0]["premises"][0]["reason"] = "Independent premise wording"
    else:
        body["inputs"]["policy_id"] = "independent-nomination-policy"
    after = StructuralProductReport.model_validate(body)
    assert after.product_id != original.product_id
    statement = structural_statement(original)
    assert structural_statement(after) == statement
    assert structural_claim_id(structural_statement(after)) == structural_claim_id(statement)
    # An actual domain change must still discriminate, independent of the wording mutation.
    body["definition"]["readings"][0]["outcome"] = "mention"
    different = StructuralProductReport.model_validate(body)
    assert structural_claim_id(structural_statement(different)) != structural_claim_id(statement)
