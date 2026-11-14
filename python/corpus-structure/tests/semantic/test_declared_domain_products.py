"""Target structural values preserve domain invariants and reject physical address aliases."""

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.structural_products import (
    DeclaredDeclarationChainWitness,
    DeclaredPrimaryReference,
    DeclaredLocatedDefinitionComponent,
    declared_definition_component,
    _DECLARED_STRUCTURAL_REPORT,
)


def chain():
    return DeclaredDeclarationChainWitness(
        primary_evidence=(DeclaredPrimaryReference(product_id="primary:actual", member_id="member:frame"),),
        scope_digest="a" * 64,
        label=dict(passage_id="p", start=0, end=1, text="x"),
        bindings=(dict(frame="binder", subject_token=0, use_token=1),),
        construction_frame="construction", construction_subject_token=2,
        naming_frame="naming", naming_antecedent_token=3,
    )


def test_target_declaration_chain_has_flat_primary_addresses_and_no_parser_fallback():
    witness = chain()
    body = witness.model_dump(mode="json")
    assert body["primary_evidence"] == [{"product_id": "primary:actual", "member_id": "member:frame"}]
    assert "parser" not in body and "annotation_task_id" not in body
    with pytest.raises(ValidationError, match="parser"):
        DeclaredDeclarationChainWitness.model_validate({**body, "parser": {"task_id": 7}})
    with pytest.raises(ValidationError):
        DeclaredPrimaryReference.model_validate({"layer": {"task_id": 7}, "local_id": "frame"})


def test_target_component_keeps_exact_domain_hash_and_independent_source_spans():
    component = declared_definition_component(
        term=dict(passage_id="p", start=0, end=1, text="x"),
        content=dict(passage_id="p", start=2, end=3, text="y"),
        interpretation="definition", basis="declaration_chain", declaration_chain=chain(),
        scope="selected", evidence=("p",), reason="explicit retained primary chain",
    )
    assert component.declaration_chain is not None
    with pytest.raises(ValueError, match="component identity"):
        DeclaredLocatedDefinitionComponent.model_validate({**component.model_dump(mode="json"), "reason": "changed meaning"})


def test_target_structural_report_schema_cannot_accept_historical_reference_variants():
    schema = _DECLARED_STRUCTURAL_REPORT.json_schema()
    assert not {
        "AnnotationReference", "ProductReference", "RetainedContributionRef", "RetainedComponentRef",
        "RetainedStructuralRef", "ExternalSourceRef", "RetainedRelationshipDecisionRef",
    } & schema["$defs"].keys()
