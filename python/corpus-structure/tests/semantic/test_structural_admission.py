"""Independent semantic identity and provenance boundaries for public projection."""

from copy import deepcopy

import pytest

from corpus_structure.semantic.structural_admission import structural_claim_id, structural_statement
from corpus_structure.semantic.structural_products import (
    DeclaredDefinitionComponentsReport,
    DeclaredDossierMember,
    DeclaredStructuralProductReport,
    LocatedDefinitionSpan,
    declared_definition_component,
)
from semantic.definition_component_members_support import (
    unadmitted_component_members,
    unadmitted_component_source,
)
from semantic.structural_admission_support import (
    definition as definition,
)
from semantic.structural_admission_support import (
    fixture_component as fixture_component,
)
from semantic.structural_admission_support import (
    inputs as inputs,
)


def test_definition_projection_preserves_meaning_without_derivation():
    value = structural_statement(definition())
    assert value["definition"]["usage"]["text"] == "mean"
    assert value["definition"]["readings"][0]["outcome"] == "unresolved"
    assert value["definition"]["readings"][0]["evidence"][0]["start"] == 5
    physical = value["definition"]["usage"]["source"]
    assert physical == definition().inputs.sources[0].model_dump(mode="json", exclude_none=True)
    assert not {"run_id", "native_task_id", "source_view_id"} & physical.keys()
    assert "candidate_list_id" not in value["definition"]
    assert "reason" not in value["definition"]["readings"][0]


def test_nomination_and_explanation_changes_do_not_change_claim():
    original = definition()
    changed = deepcopy(original.model_dump(mode="json"))
    changed["definition"]["candidate_list_id"] = "list-after-replay"
    changed["definition"]["readings"][0]["reason"] = "different derivation explanation"
    after = DeclaredStructuralProductReport.model_validate(changed)
    assert original.product_id != after.product_id
    assert structural_claim_id(structural_statement(original)) == structural_claim_id(
        structural_statement(after)
    )


def test_scope_and_outcome_are_semantic():
    original = definition()
    changed = original.model_dump(mode="json")
    changed["definition"]["readings"][0]["outcome"] = "mention"
    assert structural_claim_id(structural_statement(original)) != structural_claim_id(
        structural_statement(DeclaredStructuralProductReport.model_validate(changed))
    )


def test_dossier_complete_membership_does_not_depend_on_display():
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralRef
    from semantic.structural_admission_support import component_reference

    root = component_reference()
    predecessor = DeclaredStructuralRef.model_validate(root.model_dump(exclude={"component_id"}))
    members = tuple(
        DeclaredDossierMember(
            member_id=str(i),
            passage_id="target",
            citation=LocatedDefinitionSpan(
                passage_id="target",
                start=inputs().passages[1].start,
                end=inputs().passages[1].end,
                text=inputs().passages[1].text,
            ),
            role=role,
            sense=root.component_id,
            scope="statistics",
            relation_product_id="structural:upstream",
        )
        for i, role in enumerate(("definition", "exception", "conflict"))
    )
    from corpus_structure.methods.structural_products import select_dossier

    report = select_dossier(
        inputs(),
        root_id=root.component_id,
        root_component=root,
        predecessors=(predecessor,),
        members=members,
        member_budget=3,
    )
    statement = structural_statement(report)
    assert len(statement["dossier"]["members"]) == 3
    assert statement["dossier"]["admission_scope"] == "membership_assembly_not_member_truth"
    assert report.dossier is not None
    displayed = report.model_copy(
        update={"dossier": report.dossier.model_copy(update={"representatives": ("0",)})}
    )
    assert structural_statement(displayed) == statement


def test_definition_attachment_fact_identity_excludes_interpretation_proof_and_retrieval():
    from corpus_structure.semantic.structural_products import DeclaredDefinitionComponentsProduct

    component = fixture_component()
    report = DeclaredDefinitionComponentsReport(
        kind="definition_components",
        inputs=inputs(),
        members=unadmitted_component_members((component,)),
        sources_input=(unadmitted_component_source(),),
        definition_components=DeclaredDefinitionComponentsProduct(stages=()),
    )
    meaning = component.model_dump(exclude={"component_id"})
    meaning.update(basis="matched_cue", alternatives=("another-private-proposal",))
    revised = declared_definition_component(**meaning)
    after = report.model_copy(
        update={
            "inputs": report.inputs.model_copy(
                update={"inventory_id": "new-inventory", "policy_id": "new-nomination-policy"}
            ),
            "members": unadmitted_component_members((revised,)),
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
    revised = declared_definition_component(**meaning)
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
    after = DeclaredStructuralProductReport.model_validate(changed)
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
    after = DeclaredStructuralProductReport.model_validate(changed)
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
    after = DeclaredStructuralProductReport.model_validate(body)
    assert after.product_id != original.product_id
    statement = structural_statement(original)
    assert structural_statement(after) == statement
    assert structural_claim_id(structural_statement(after)) == structural_claim_id(statement)
    # An actual domain change must still discriminate, independent of the wording mutation.
    body["definition"]["readings"][0]["outcome"] = "mention"
    different = DeclaredStructuralProductReport.model_validate(body)
    assert structural_claim_id(structural_statement(different)) != structural_claim_id(statement)
