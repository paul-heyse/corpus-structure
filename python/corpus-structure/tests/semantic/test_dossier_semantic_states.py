"""Current dossier roots, identities and facet credit preserve literal reading states."""

from corpus_structure.methods.structural_products import (
    derive_dossier_members,
    dossier_root,
    select_dossier,
)
from corpus_structure.semantic.structural_admission import structural_claim_id, structural_statement
from semantic.dossier_semantic_states_support import (
    applicability,
    component_reference,
    components,
    retained,
)


def test_component_interpretations_share_citation_without_collapsing_or_false_definition_credit():
    upstream = components()
    value, reference, payload = retained(upstream)
    members, facets = derive_dossier_members(value, ((reference, payload),))
    assert len(members) == 6 and len({m.member_id for m in members}) == 6
    assert {(m.role, m.definition_interpretation) for m in members} == {
        ("terminology", "definition"),
        ("definition", "definition"),
        ("terminology", "explanation"),
        ("usage", "explanation"),
        ("terminology", "unresolved"),
        ("unresolved_sense", "unresolved"),
    }
    assert all(
        m.qualification == "proposed" and m.assessment_id is None
        for m in members
        if m.definition_interpretation == "unresolved"
    )
    assert {f.kind for f in facets} == {
        "terminology:definition:hello",
        "definition:definition:hello",
        "terminology:explanation:hello",
        "usage:explanation:hello",
    }
    assert not any(
        f.kind.startswith("definition:") and f.definition_interpretation != "definition"
        for f in facets
    )
    # Each distinct interpretation supplies its own selected root. Sharing a
    # citation does not make these three component meanings the same root sense.
    interpretations, claims = set(), set()
    for component in upstream.definition_components.components:
        root = component_reference(upstream, component)
        assert dossier_root(root, ((reference, payload),)) == component
        rooted_members, rooted_facets = derive_dossier_members(
            value, ((reference, payload),), root=component
        )
        public = structural_statement(
            select_dossier(
                value,
                root_id=component.component_id,
                root_component=root,
                members=rooted_members,
                supported_facets=rooted_facets,
                predecessors=(reference,),
            )
        )
        assert public["dossier"]["root"] == component.component_id
        assert all(m["sense"] == component.component_id for m in public["dossier"]["members"])
        interpretations.update(m["definition_interpretation"] for m in public["dossier"]["members"])
        claims.add(structural_claim_id(public))
    assert interpretations == {"definition", "explanation", "unresolved"}
    assert len(claims) == 3


def test_same_content_preserves_every_applicability_outcome_and_facet():
    component_report, alternatives = applicability()
    root_inputs, root_predecessor, root_payload = retained(component_report)
    supplied = tuple(retained(report) for report in alternatives)
    dependencies = [dependency for inputs, _, _ in supplied for dependency in inputs.dependencies]
    value = root_inputs.model_copy(
        update=dict(
            dependencies=tuple(
                dict.fromkeys(
                    (*dependencies, component_report.product_id, root_predecessor.product_id)
                )
            )
        )
    )
    retained_reports = tuple((reference, payload) for _, reference, payload in supplied)
    members, facets = derive_dossier_members(value, retained_reports)
    states = {m.applicability_outcome: m for m in members if m.applicability_outcome is not None}
    assert {state: m.role for state, m in states.items()} == {
        "applicable_definition": "definition",
        "applicable_explanation": "usage",
        "mention": "usage",
        "example": "usage",
        "incompatible": "relationship",
        "unresolved": "unresolved_sense",
    }
    assert len({m.member_id for m in states.values()}) == 6
    assert len({report.product_id for report in alternatives}) == 6
    assert states["applicable_explanation"].definition_interpretation == "explanation"
    assert {f.applicability_outcome for f in facets if f.applicability_outcome} == set(states)
    assert {f.applicability_outcome for f in facets if f.kind.startswith("definition:")} == {
        "applicable_definition"
    }
    claims = set()
    for upstream, (_, reference, payload) in zip(alternatives, supplied, strict=True):
        reading = upstream.definition.readings[0]
        root = component_reference(component_report, reading.component)
        assert dossier_root(root, ((root_predecessor, root_payload),)) == reading.component
        rooted_members, _ = derive_dossier_members(
            value, ((reference, payload),), root=reading.component
        )
        (member,) = [m for m in rooted_members if m.applicability_outcome is not None]
        report = select_dossier(
            value,
            root_id=reading.component.component_id,
            root_component=root,
            members=(member,),
            predecessors=(root_predecessor, reference),
        )
        public = structural_statement(report)
        assert public["dossier"]["members"][0]["applicability_outcome"] == reading.outcome
        assert public["dossier"]["members"][0]["sense"] == reading.component.component_id
        claims.add(structural_claim_id(public))
    assert len(claims) == 6
