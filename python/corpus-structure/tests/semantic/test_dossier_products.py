"""Dossier target membership preserves exact native addresses and private standing."""

import pytest

from corpus_structure.methods.structural_products import produce_structural_dossier
from corpus_structure.semantic.declared_structural_references import (
    DeclaredComponentRef, DeclaredStructuralRef, DeclaredStructuralSource,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import (
    DeclaredDefinitionComponentsProduct, DeclaredDefinitionComponentsReport,
    DeclaredStructuralInput, DeclaredStructuralInputPin, StructuralPassage,
    declared_definition_component,
)


def _predecessor():
    reference = DeclaredStructuralSource(source=canonical_bytes(["source:actual", "member:actual"]).decode(), subject="document:actual", document="document:actual", projection_digest="a" * 64, section_pointer="/", membership="descendants", project_id="project", original_source="document:actual", analyzed_scope_meaning='{"scope":"selected"}', source_product="source:actual", source_member="member:actual", kind_contract="kind:source")
    passage = StructuralPassage(passage_id="definition", source_ref=reference.identity, start=0, end=8, text="term def", scope="selected")
    component = declared_definition_component(term=dict(passage_id="definition", start=0, end=4, text="term"), content=dict(passage_id="definition", start=5, end=8, text="def"), interpretation="unresolved", basis="unqualified", scope="selected", evidence=("definition",), reason="Independent selected candidate remains unresolved.")
    pin = DeclaredStructuralInputPin(product_id="source:actual", member_id="member:actual", reference=reference.source, kind_contract="kind:source", project_id="project", subject=reference.subject, original_source=reference.original_source, analyzed_scope_meaning=reference.analyzed_scope_meaning)
    report = DeclaredDefinitionComponentsReport(inputs=DeclaredStructuralInput(question="Read the retained definition.", scope="selected", inventory_id="inventory", policy_id="policy", sources=(reference,), passages=(passage,), dependencies=("primary:actual",)), definition_components=DeclaredDefinitionComponentsProduct(components=(component,)), sources_input=(pin,))
    address = dict(product_id="native:component-report", kind_contract="kind:components", project_id="project", subject=reference.subject, original_source=reference.original_source, analyzed_scope_meaning=reference.analyzed_scope_meaning, structural_id=report.product_id)
    root = DeclaredComponentRef(**address, component_id=component.component_id)
    predecessor = DeclaredStructuralRef(**address)
    inputs = report.inputs.model_copy(update={"dependencies": ("native:component-report", report.product_id, "primary:actual")})
    return component, root, predecessor, report, inputs


def test_declared_dossier_uses_real_root_report_and_preserves_proposed_membership():
    component, root, predecessor, report, inputs = _predecessor()
    result = produce_structural_dossier(inputs, root_component=root, root=component, retained=((predecessor, {"report": report}),), relationships={})
    assert result.dossier is not None
    assert result.dossier.root_component == root
    assert {row.role for row in result.dossier.members} == {"terminology", "unresolved_sense"}
    assert all(row.qualification == "proposed" and row.assessment_id is None for row in result.dossier.members)
    assert result.dossier.supported_facets == ()
    assert result.dossier.membership_completeness == "declared_selection"
    assert "operation_version" not in root.model_dump() and "dependencies" not in root.model_dump()
    assert result.dossier.predecessors == (predecessor,)


def test_declared_dossier_refuses_substituted_component_and_changed_passage_closure():
    component, root, predecessor, report, inputs = _predecessor()
    with pytest.raises(ValueError, match="does not resolve"):
        produce_structural_dossier(inputs, root_component=root.model_copy(update={"component_id": "f" * 64}), root=component, retained=((predecessor, {"report": report}),), relationships={})
    changed = inputs.model_copy(update={"passages": (inputs.passages[0].model_copy(update={"text": "term bad"}),)})
    with pytest.raises(ValueError, match="passage differs"):
        produce_structural_dossier(changed, root_component=root, root=component, retained=((predecessor, {"report": report}),), relationships={})
