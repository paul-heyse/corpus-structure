"""Dossier target membership preserves exact native addresses and private standing."""

import pytest

from corpus_structure.methods.structural_products import produce_structural_dossier
from corpus_structure.semantic.declared_structural_references import (
    DeclaredComponentRef,
    DeclaredStructuralRef,
    DeclaredStructuralSource,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import (
    DeclaredDefinitionComponentsProduct,
    DeclaredDefinitionComponentsReport,
    DeclaredStructuralInput,
    DeclaredStructuralInputPin,
    StructuralPassage,
    declared_definition_component,
)
from semantic.definition_component_members_support import unadmitted_component_members


def _predecessor():
    reference = DeclaredStructuralSource(
        source=canonical_bytes(["source:actual", "member:actual"]).decode(),
        subject="document:actual",
        document="document:actual",
        projection_digest="a" * 64,
        section_pointer="/",
        membership="descendants",
        project_id="project",
        original_source="document:actual",
        analyzed_scope_meaning='{"scope":"selected"}',
        source_product="source:actual",
        source_member="member:actual",
        kind_contract="kind:source",
        subject_definition="original-source-view",
    )
    passage = StructuralPassage(
        passage_id="definition",
        source_ref=reference.identity,
        start=0,
        end=8,
        text="term def",
        scope="selected",
    )
    component = declared_definition_component(
        term=dict(passage_id="definition", start=0, end=4, text="term"),
        content=dict(passage_id="definition", start=5, end=8, text="def"),
        interpretation="unresolved",
        basis="unqualified",
        scope="selected",
        evidence=("definition",),
        reason="Independent selected candidate remains unresolved.",
    )
    pin = DeclaredStructuralInputPin(
        product_id="source:actual",
        member_id="member:actual",
        reference=reference.source,
        kind_contract="kind:source",
        project_id="project",
        subject=reference.subject,
        subject_definition=reference.subject_definition,
        original_source=reference.original_source,
        analyzed_scope_meaning=reference.analyzed_scope_meaning,
    )
    report = DeclaredDefinitionComponentsReport(
        inputs=DeclaredStructuralInput(
            question="Read the retained definition.",
            scope="selected",
            inventory_id="inventory",
            policy_id="policy",
            sources=(reference,),
            passages=(passage,),
            dependencies=("primary:actual",),
        ),
        members=unadmitted_component_members((component,)),
        definition_components=DeclaredDefinitionComponentsProduct(
            stages=(
                dict(
                    passage_id="definition",
                    operation="attachment",
                    outcome="succeeded",
                    reason="The independently authored unresolved component is retained for dossier selection.",
                ),
            ),
        ),
        sources_input=(pin,),
    )
    address = dict(
        product_id="native:component-report",
        kind_contract="kind:components",
        project_id="project",
        subject=reference.subject,
        subject_definition=reference.subject_definition,
        original_source=reference.original_source,
        analyzed_scope_meaning=reference.analyzed_scope_meaning,
        structural_id=report.product_id,
    )
    root = DeclaredComponentRef(**address, component_id=component.component_id)
    predecessor = DeclaredStructuralRef(**address)
    inputs = report.inputs.model_copy(
        update={"dependencies": ("native:component-report", report.product_id, "primary:actual")}
    )
    return component, root, predecessor, report, inputs


def test_declared_dossier_uses_real_root_report_and_preserves_proposed_membership():
    component, root, predecessor, report, inputs = _predecessor()
    result = produce_structural_dossier(
        inputs,
        root_component=root,
        root=component,
        retained=((predecessor, {"report": report}),),
        relationships={},
    )
    assert result.dossier is not None
    assert result.dossier.root_component == root
    assert {row.role for row in result.dossier.members} == {"terminology", "unresolved_sense"}
    assert all(
        row.qualification == "proposed" and row.assessment_id is None
        for row in result.dossier.members
    )
    assert result.dossier.supported_facets == ()
    assert result.dossier.membership_completeness == "declared_selection"
    assert "operation_version" not in root.model_dump() and "dependencies" not in root.model_dump()
    assert result.dossier.predecessors == (predecessor,)


def test_declared_dossier_refuses_substituted_component_and_changed_passage_closure():
    component, root, predecessor, report, inputs = _predecessor()
    with pytest.raises(ValueError, match="does not resolve"):
        produce_structural_dossier(
            inputs,
            root_component=root.model_copy(update={"component_id": "f" * 64}),
            root=component,
            retained=((predecessor, {"report": report}),),
            relationships={},
        )
    changed = inputs.model_copy(
        update={"passages": (inputs.passages[0].model_copy(update={"text": "term bad"}),)}
    )
    with pytest.raises(ValueError, match="passage differs"):
        produce_structural_dossier(
            changed,
            root_component=root,
            root=component,
            retained=((predecessor, {"report": report}),),
            relationships={},
        )


def _prepared_dossier_role(role, *, member, multiplicity=1):
    from corpus_structure.semantic.data_operation_model import (
        BoundRoleMember,
        ResolvedRoleBinding,
        SubjectContext,
    )
    from corpus_structure.semantic.dossier_products import PreparedDossierInputs
    from corpus_structure.semantic.types import PreparedRelease

    # This control exercises the binding gate. Release schema interpretation is
    # covered by the dossier producer and native journey, and is not entered here.
    prepared = PreparedRelease(
        release_id="release:binding-control",
        manifest=b"{}",
        definitions=(),
        vocabularies=(),
        registry_rows=(),
        queries=(),
        artifacts=(),
        required_capabilities=(),
        diagnostics=(),
        _adapters=(),
    )
    bound = BoundRoleMember(
        product="product:actual-source",
        kind_contract="kind:actual-source",
        subject="view:actual",
        original_source="document:actual",
        analyzed_scope=b"{}",
        coverage=b"{}",
        support_episodes=(),
        support_evidence=b"{}",
        subject_definition="original-source-view",
        support_references=(),
        member=member,
        multiplicity=multiplicity,
    )
    return PreparedDossierInputs(
        prepared=prepared,
        roles=(ResolvedRoleBinding(role, "present", (bound,)),),
        context=SubjectContext(
            "project",
            "view:actual",
            "document:actual",
            b"{}",
            subject_definition="original-source-view",
        ),
        check_active=lambda: None,
    ), bound


def test_dossier_keeps_actual_selected_source_member_and_unit_multiplicity():
    inputs, source = _prepared_dossier_role("sources", member="selected:section")
    assert inputs.members("sources") == (source,)
    assert inputs.members("sources")[0].member == "selected:section"
    repeated, _ = _prepared_dossier_role("sources", member="selected:section", multiplicity=2)
    with pytest.raises(ValueError, match="whole native inventories"):
        repeated.members("sources")


@pytest.mark.parametrize(
    "role",
    ["components", "definitions", "comparisons", "candidates", "relationships", "admissions"],
)
def test_dossier_report_roles_still_require_whole_native_inventories(role):
    selected, _ = _prepared_dossier_role(role, member="selected:report-fragment")
    with pytest.raises(ValueError, match="whole native inventories"):
        selected.members(role)
    whole, report = _prepared_dossier_role(role, member=None)
    assert whole.members(role) == (report,)


def _run_bound_dossier(monkeypatch, *, changed_pin=None):
    from dataclasses import replace
    from types import SimpleNamespace

    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_model import (
        ResolvedRoleBinding,
        json_context_meaning,
    )
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource

    component, _, predecessor, report, _ = _predecessor()
    (source,) = report.inputs.sources
    (pin,) = report.sources_input
    meaning = json_context_meaning(json_bytes({"scope": "selected"})).decode()
    source = source.model_copy(update={"analyzed_scope_meaning": meaning})
    pin = pin.model_copy(update={"analyzed_scope_meaning": meaning})
    report = report.model_copy(
        update={
            "sources_input": (pin,),
            "inputs": report.inputs.model_copy(
                update={
                    "sources": (source,),
                    "passages": tuple(
                        passage.model_copy(update={"source_ref": source.identity})
                        for passage in report.inputs.passages
                    ),
                }
            ),
        }
    )
    selected, bound = _prepared_dossier_role("sources", member=pin.member_id)
    source_member = replace(
        bound,
        product=pin.product_id,
        kind_contract=pin.kind_contract,
        subject=pin.subject,
        subject_definition=pin.subject_definition,
        original_source=pin.original_source,
        analyzed_scope=json_bytes({"scope": "selected"}),
    )
    # A derived report keeps its own declared nominal context. Its source pin
    # remains the exact original-source-view context acquired by native support.
    output = replace(
        source_member,
        product=predecessor.product_id,
        member=None,
        kind_contract=predecessor.kind_contract,
        subject_definition="actual-focus-source",
    )
    members = {"sources": (source_member,), "components": (output,)}
    selected = replace(
        selected,
        roles=tuple(
            ResolvedRoleBinding(role, "present", members.get(role, ()))
            for role in (
                "sources",
                "components",
                "definitions",
                "comparisons",
                "candidates",
                "relationships",
                "admissions",
            )
        ),
    )
    frame = SimpleNamespace(
        pin=SimpleNamespace(
            source_key=source.source, values=lambda: source.model_dump(exclude_none=True)
        ),
        text="term def",
        selected_ranges=((0, 8),),
    )
    # This is a pure dossier consumer control; native acquisition and its proofs
    # remain the responsibility of the actual structural journey.
    monkeypatch.setattr(DeclaredNativeFrameSource, "acquire", lambda *args, **kw: frame)
    if changed_pin is not None:
        report = report.model_copy(update={"sources_input": (pin.model_copy(update=changed_pin),)})
    return (
        selected.run(
            ({},),
            report.model_dump(mode="json"),
            (),
            (),
            (),
            (),
            (),
            component_id=component.component_id,
            candidate_selections="[]",
            comparison_selections="[]",
            extra_passages="[]",
            question="Read exact retained root",
            scope="selected",
            inventory_id="inventory",
            policy_id="policy",
            member_budget=12,
            representation_policy="supported-facet-greedy-1",
        ),
        pin,
        output,
    )


def test_dossier_authenticates_source_pins_without_relabelling_derived_output_context(monkeypatch):
    from pydantic import ValidationError

    from corpus_structure.semantic.structural_products import DeclaredDossierReport

    raw, source_pin, output = _run_bound_dossier(monkeypatch)
    report = DeclaredDossierReport.model_validate(raw)
    (source,) = report.inputs.sources
    assert source.source == source_pin.reference
    assert source.source_product == source_pin.product_id
    assert source.source_member == source_pin.member_id
    assert source.kind_contract == source_pin.kind_contract
    assert source.analyzed_scope_meaning == source_pin.analyzed_scope_meaning
    assert "sources_input" not in raw
    with pytest.raises(ValidationError, match="sources_input"):
        DeclaredDossierReport.model_validate({**raw, "sources_input": [source_pin.model_dump()]})
    assert report.components_input == {"variant": "product", "role": "components"}
    assert report.dossier.root_component.product_id == output.product
    assert report.dossier.root_component.member_id is None
    assert report.dossier.root_component.subject_definition == "actual-focus-source"
    assert report.dossier.predecessors[0].subject_definition == "actual-focus-source"
    absolute = report.dossier.root_component.model_dump(exclude={"component_id", "structural_id"})
    absolute["reference"] = canonical_bytes([output.product, None]).decode()
    with pytest.raises(ValidationError, match="components_input"):
        DeclaredDossierReport.model_validate({**raw, "components_input": absolute})


@pytest.mark.parametrize(
    "field,value",
    [
        ("product_id", "source:other"),
        ("member_id", "member:other"),
        ("kind_contract", "kind:other"),
        ("project_id", "project:other"),
        ("subject", "subject:other"),
        ("subject_definition", "actual-focus-source"),
        ("original_source", "document:other"),
        ("analyzed_scope_meaning", '{"scope":"other"}'),
        ("reference", '["source:other","member:other"]'),
    ],
)
def test_dossier_refuses_each_source_pin_custody_or_context_substitution(monkeypatch, field, value):
    with pytest.raises(ValueError, match="exact bound native source inputs"):
        _run_bound_dossier(monkeypatch, changed_pin={field: value})
