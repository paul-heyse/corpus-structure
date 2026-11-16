"""Exact side custody, directed roles and native composition parity."""

from dataclasses import replace

import pytest

from corpus_structure.methods.structural_products import derive_dossier_members
from corpus_structure.semantic.structural_products import (
    DeclaredStructuralProductReport,
    declared_definition_component,
    read_structural_product_report,
)
from semantic.dossier_comparison_bindings_support import (
    fixture as fixture,
)
from semantic.dossier_comparison_bindings_support import (
    side_inputs as side_inputs,
)
from semantic.dossier_comparison_bindings_support import (
    span as span,
)


def derive(value, root, root_ref, reference, payload, selected, relationships):
    return derive_dossier_members(
        value,
        ((reference, payload),),
        root=root,
        root_ref=root_ref,
        comparison_selections=selected,
        relationships=relationships,
    )


def binding(member):
    result = member.comparison_binding
    assert result is not None
    return result


def test_side_binding_keeps_opposite_context_and_requires_own_membership():
    value, root, root_ref, reference, payload, selected, relationships = fixture()
    members, facets = derive(value, root, root_ref, reference, payload, selected[:1], relationships)
    assert {(m.role, m.citation.text) for m in members} == {
        ("relationship", "Apply measure except in test runs."),
        ("exception", "except in test runs"),
    }
    assert {binding(m).side for m in members} == {"left"}
    assert {binding(m).opposite_citation.text for m in members} == {"Measure is a control rule."}
    assert {f.assessment_id for f in facets} == {"exact-comparison-grade"}
    assert [f.assessment_scope for f in facets] == ["comparison_statement"]
    assert {m.qualification for m in members} == {"proposed"}
    both, _ = derive(value, root, root_ref, reference, payload, selected, relationships)
    assert {(binding(m).side, m.role) for m in both} == {
        ("left", "relationship"),
        ("left", "exception"),
        ("right", "relationship"),
    }
    assert {m.member_id for m in members} < {m.member_id for m in both}


@pytest.mark.parametrize("failure", ["scope", "version", "target_custody", "source", "occurrence"])
def test_comparison_qualification_rejects_substitution(failure):
    value, root, root_ref, reference, payload, selected, relationships = fixture()
    from corpus_structure.semantic.declared_structural_references import DeclaredRelationshipRef

    relationship_ref = selected[0].relationship_ref
    assert isinstance(relationship_ref, DeclaredRelationshipRef)
    relationship = relationships[relationship_ref]
    binding = relationship.binding
    match = "exact scoped root relationship"
    if failure == "scope":
        binding = replace(binding, decision=replace(binding.decision, scope="other"))
    elif failure == "version":
        binding = replace(binding, decision=replace(binding.decision, effective_version="R1"))
    elif failure == "target_custody":
        from corpus_structure.semantic.contextual_retrieval import target_representation

        carrier = binding.representations[0]
        changed = target_representation(
            carrier.target_id,
            "wrong-exact-root",
            carrier.label,
            carrier.description,
            type_name=carrier.type_name,
            scope=carrier.scope,
            effective_version=carrier.effective_version,
        )
        binding = replace(binding, representations=(changed,))
        match = "exact native root component"
    elif failure == "source":
        binding = replace(binding, source_pin={**binding.source_pin, "source_product": "another"})
    else:
        anchor = binding.anchors[0]
        binding = replace(
            binding, anchors=({**anchor, "start": anchor["start"] + 1, "end": anchor["end"] + 1},)
        )
        match = "actual native source text"
    relationships[relationship_ref] = replace(relationship, binding=binding)
    with pytest.raises(ValueError, match=match):
        derive(value, root, root_ref, reference, payload, selected[:1], relationships)


def test_comparison_root_witness_cannot_bind_another_focus_in_the_same_passage():
    from corpus_structure.methods.structural_products import _comparison_member_roles

    value, root, root_ref, reference, payload, selected, relationships = fixture()
    report = read_structural_product_report(payload["report"])
    assert report.comparison is not None
    left = next(p for p in value.passages if p.passage_id == report.comparison.left_id)
    report = report.model_copy(
        update={
            "comparison": report.comparison.model_copy(update={"left_focus": span(left, "Apply")})
        }
    )
    with pytest.raises(ValueError, match="outside the exact comparison focus"):
        tuple(
            _comparison_member_roles(
                reference,
                report,
                selected[:1],
                relationships,
                root_ref,
                root,
                require_focus=True,
            )
        )


def test_comparison_conflict_requires_exact_applicability_and_both_authored_readings():
    from corpus_structure.methods.structural_products import _comparison_member_roles
    from corpus_structure.semantic.structural_products import (
        ApplicabilityPremise,
        DeclaredDefinitionProduct,
        DeclaredStructuralDefinitionReading,
    )

    value, root, root_ref, reference, payload, selected, relationships = fixture(exception=False)
    report = read_structural_product_report(payload["report"])
    assert report.comparison is not None
    left, right = value.passages
    left_focus, right_focus = span(left, "Apply measure"), span(right, "Measure is a control rule")
    located_usage = span(left, "measure")
    usage = left.model_copy(
        update={
            "passage_id": "exact-usage",
            "start": located_usage.start,
            "end": located_usage.end,
            "text": located_usage.text,
        }
    )
    report = report.model_copy(
        update={
            "comparison": report.comparison.model_copy(
                update={
                    "left_focus": left_focus,
                    "right_focus": right_focus,
                    "applicability": "co_applicable",
                }
            )
        }
    )
    premise = DeclaredStructuralProductReport(
        kind="definition_applicability",
        inputs=value.model_copy(
            update={
                "passages": (*value.passages, usage),
                "dependencies": tuple(
                    dict.fromkeys(
                        (
                            *value.dependencies,
                            root.component_id,
                            root_ref.product_id,
                            selected[0].relationship_ref.edge_id,
                        )
                    )
                ),
            }
        ),
        definition=DeclaredDefinitionProduct(
            usage_id=usage.passage_id,
            candidate_list_id="candidate-list",
            eligible_targets=(root.component_id,),
            candidate_targets=(root.component_id,),
            readings=(
                DeclaredStructuralDefinitionReading(
                    target_id=root.component_id,
                    component_ref=root_ref,
                    link_ref=selected[0].relationship_ref,
                    component=root,
                    outcome="applicable_definition",
                    evidence=(left.passage_id,),
                    premises=tuple(
                        ApplicabilityPremise(
                            dimension=dimension,
                            state="compatible",
                            evidence=(left.passage_id,),
                            reason="Exact scoped fixture.",
                        )
                        for dimension in (
                            "sense",
                            "scope",
                            "parent",
                            "parameterization",
                            "convention",
                            "version",
                        )
                    ),
                    reason="Source witnesses this exact relation.",
                ),
            ),
        ),
    )
    premise_ref = reference.model_copy(
        update={"product_id": "unadmitted:applicability", "structural_id": premise.product_id}
    )
    text = f'"{left_focus.text}" contradicts "{right_focus.text}".'
    proof = left.model_copy(
        update={
            "passage_id": "authored-contradiction",
            "start": 0,
            "end": len(text),
            "text": text,
        }
    )
    choice = selected[0].model_copy(
        update={
            "applicability_ref": premise_ref,
            "conflict_passage_id": proof.passage_id,
        }
    )

    def roles(witness):
        return tuple(
            _comparison_member_roles(
                reference,
                report,
                (choice,),
                relationships,
                root_ref,
                root,
                require_focus=True,
                applicability_reports={premise_ref: premise},
                dossier_passages={proof.passage_id: witness},
            )
        )

    conflict, relationship = roles(proof)
    assert conflict[0] == "conflict" and relationship[0] == "relationship"
    assert conflict[2].conflict_evidence is not None
    assert conflict[2].conflict_evidence.text == text
    with pytest.raises(ValueError, match="explicit contradiction"):
        roles(proof.model_copy(update={"text": text.replace("contradicts", "discusses")}))


def test_revision_requires_original_successor_and_direction():
    from semantic.structural_formal_support import formal_reading_sets
    from semantic.structural_products_support import input_from_passages

    left_text = "Apply measure. Measure is a control rule.\nClause rules.\nRevision R2 supersedes revision R1."
    right_text = "Measure is a control rule.\nClause rules.\nRevision R1."
    value = input_from_passages(
        (
            dict(
                passage_id="a",
                document="same-original",
                text=left_text,
                start=0,
                scope="rules",
                effective_version="R2",
                parent="rules",
            ),
            dict(
                passage_id="b",
                document="same-original",
                text=right_text,
                start=len(left_text) + 1,
                scope="rules",
                effective_version="R1",
                parent="rules",
            ),
        ),
        scope="rules",
    )
    value, root, root_ref, reference, payload, selected, relationships = fixture(
        value, exception=False, root_on_left=True, primary_layers=formal_reading_sets(value)
    )
    members, _ = derive(value, root, root_ref, reference, payload, selected[:1], relationships)
    assert [(m.role, m.citation.text) for m in members if m.role == "revision"] == [
        ("revision", "Revision R2 supersedes revision R1.")
    ]


def test_typed_source_dependency_keeps_both_endpoints_outside_computational_dependencies():
    from corpus_structure.methods.dossier_contributions import derive_declared_contribution_members
    from corpus_structure.semantic.contributions import contribution_identity
    from corpus_structure.semantic.observations import source_python, source_value
    from semantic.dossier_contributions_support import source_fixture

    value, ref, payload = source_fixture()
    (passage,) = value.passages
    passage = passage.model_copy(update={"effective_version": "R2"})
    initial = derive_declared_contribution_members(value, ref, payload)[0]
    assert initial.contribution_citations is not None
    citations = {c.span.text: c.span for c in initial.contribution_citations}
    root = declared_definition_component(
        term=citations["Probability %"],
        content=citations["50"],
        scope=passage.scope,
        effective_version="R2",
        interpretation="definition",
        basis="matched_cue",
        evidence=(passage.passage_id,),
        reason="Controlled endpoint fixture.",
    )
    attachment = next(c for c in payload["contributions"] if c["kind"] == "relation")
    meaning = source_python(attachment["value"])
    attachment["value"] = source_value({**meaning, "relation": "depends_on"})
    attachment["component"].update(
        attachment_kind="depends_on",
        scope=passage.scope,
        effective_version="R2",
    )
    attachment["contribution_id"] = contribution_identity(attachment)
    ref = ref.model_copy(update={"contribution_id": attachment["contribution_id"]})
    value = value.model_copy(
        update={"passages": (passage,), "dependencies": (ref.contribution_id,)}
    )
    (member,) = derive_declared_contribution_members(value, ref, payload, root=root)
    dependency = member.semantic_dependency
    assert dependency is not None and dependency.relation == "depends_on"
    assert [c.span.text for c in dependency.dependent] == ["50"]
    assert [c.span.text for c in dependency.prerequisite] == ["Probability %"]
    assert member.computation_dependencies and "depends_on" not in member.computation_dependencies
