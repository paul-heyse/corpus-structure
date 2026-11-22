"""Retained source joins supply assessable private membership with full endpoint custody."""

import json

import pytest
from pydantic import ValidationError

from corpus_structure.methods.dossier_contributions import derive_declared_contribution_members
from corpus_structure.methods.structural_products import select_dossier
from corpus_structure.semantic.declared_structural_references import DeclaredContributionRef
from corpus_structure.semantic.native_source_view import thaw_native
from semantic.dossier_contributions_support import source_fixture as source_fixture
from semantic.dossier_semantic_states_support import component_reference, components, retained


def test_source_join_enters_dossier_with_both_endpoint_citations_and_no_borrowed_support():
    inputs, ref, payload = source_fixture()
    payload["public_assertions"] = [
        dict(assessment_id="source-geometry-is-not-meaning", statement="quote")
    ]
    members = derive_declared_contribution_members(inputs, ref, payload)
    assert len(members) == 1
    member = members[0]
    assert member.role == "relationship" and member.qualification == "proposed"
    assert member.assessment_id is None and member.scope.startswith(
        inputs.sources[0].identity + ":"
    )
    assert member.contribution_citations is not None
    assert member.computation_dependencies is not None
    assert {c.span.text for c in member.contribution_citations} == {"50", "Probability %"}
    assert set(member.computation_dependencies) >= {
        r["contribution_id"] for r in payload["contributions"]
    }
    assert member.sense == "unresolved"
    # Current dossier products require an actual selected root component; a source
    # geometry join alone cannot invent the missing root or its semantic support.
    with pytest.raises(ValidationError, match="root_component"):
        select_dossier(
            inputs,
            root_id="corpus",
            members=members,
            contribution_predecessors=(ref,),
            member_budget=1,
        )


@pytest.mark.parametrize("field", ["run_id", "origin_task_id", "selected_task_id"])
def test_reference_forbids_loose_identifiers(field):
    _, ref, _ = source_fixture()
    with pytest.raises(ValidationError):
        DeclaredContributionRef.model_validate({**ref.model_dump(), field: "1"})
    with pytest.raises(ValidationError):
        DeclaredContributionRef.model_validate({**ref.model_dump(), "supported": True})


@pytest.mark.parametrize("corruption", ["identity", "endpoint", "source", "citation", "passage"])
def test_source_membership_rejects_forged_closure(corruption):
    inputs, ref, payload = source_fixture()
    payload = thaw_native(payload)
    if corruption == "identity":
        payload["contributions"][0]["disposition"] = "forged"
    elif corruption == "endpoint":
        payload["contributions"] = [
            r for r in payload["contributions"] if r["contribution_id"] == ref.contribution_id
        ]
    elif corruption == "source":
        inputs = inputs.model_copy(
            update=dict(
                sources=(inputs.sources[0].model_copy(update=dict(projection_digest="d" * 64)),)
            )
        )
    elif corruption == "citation":
        payload["sources"][0]["projection"]["text"] = "!" * len(
            payload["sources"][0]["projection"]["text"]
        )
    else:
        inputs = inputs.model_copy(
            update=dict(
                passages=(
                    inputs.passages[0].model_copy(
                        update=dict(text="!" * len(inputs.passages[0].text))
                    ),
                )
            )
        )
    with pytest.raises(ValueError):
        derive_declared_contribution_members(inputs, ref, payload)


def replay_aliases(inputs, reference, member):
    """Change literal detached labels while keeping governed original-source meaning."""
    passage = inputs.passages[0].model_copy(update=dict(passage_id="replay-passage"))
    changed_inputs = inputs.model_copy(update=dict(passages=(*inputs.passages, passage)))
    changed_ref = reference.model_copy(
        update=dict(
            product_id="unadmitted:replayed-source-joins",
            contribution_id="source-contribution:" + "f" * 64,
        )
    )
    citations = tuple(
        citation.model_copy(
            update=dict(
                contribution_id="source-contribution:" + str(i) * 64,
                span=citation.span.model_copy(update=dict(passage_id=passage.passage_id)),
            )
        )
        for i, citation in enumerate(member.contribution_citations)
    )
    changed_member = type(member).model_validate(
        {
            **member.model_dump(),
            "member_id": "literal:replayed-member",
            "contribution_ref": changed_ref,
            "relation_product_id": changed_ref.contribution_id,
            "citation": citations[0].span,
            "passage_id": passage.passage_id,
            "contribution_citations": citations,
            "computation_dependencies": (
                changed_ref.contribution_id,
                *(c.contribution_id for c in citations),
            ),
        }
    )
    return changed_inputs, changed_ref, changed_member


def test_public_source_membership_identity_excludes_execution_custody_aliases():
    from methods.declared_primary_fixture import profiles

    from corpus_structure.methods.structural_products import dossier_root
    from corpus_structure.semantic.data_operation_model import json_context_meaning
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.original_documents import original_document_subject
    from corpus_structure.semantic.source_products import FrozenNativeSource, source_subject
    from corpus_structure.semantic.structural_admission import (
        structural_claim_id,
        structural_statement,
    )

    inputs, reference, payload = source_fixture()
    initial = derive_declared_contribution_members(inputs, reference, payload)[0]
    assert initial.contribution_citations is not None
    selected = next(
        row
        for row in payload["contributions"]
        if row["contribution_id"] == reference.contribution_id
    )
    target = next(
        endpoint["contribution_id"]
        for endpoint in selected["endpoints"]
        if endpoint["role"] == "target"
    )
    target_citation = next(
        citation
        for citation in initial.contribution_citations
        if citation.contribution_id == target
    )
    upstream = components(inputs, span=target_citation.span)
    inputs, predecessor, root_payload = retained(upstream)
    component = next(
        c for c in upstream.definition_components.components if c.interpretation == "unresolved"
    )
    root = component_reference(upstream, component)
    assert dossier_root(root, ((predecessor, root_payload),)) == component
    member = derive_declared_contribution_members(inputs, reference, payload, root=component)[0]
    assert member.contribution_citations is not None
    original = select_dossier(
        inputs,
        root_id=component.component_id,
        root_component=root,
        members=(member,),
        predecessors=(predecessor,),
        contribution_predecessors=(reference,),
    )
    changed_inputs, changed_ref, changed_member = replay_aliases(inputs, reference, member)
    changed = select_dossier(
        changed_inputs,
        root_id=component.component_id,
        root_component=root,
        members=(changed_member,),
        predecessors=(predecessor,),
        contribution_predecessors=(changed_ref,),
    )
    assert original.dossier is not None
    assert changed_member.contribution_citations is not None
    before, after = structural_statement(original), structural_statement(changed)
    assert original.product_id != changed.product_id
    assert before == after and structural_claim_id(before) == structural_claim_id(after)
    public_member = before["dossier"]["members"][0]
    assert public_member["sense"] == before["dossier"]["root"] == component.component_id
    assert public_member["qualification"] == "proposed"
    assert member.assessment_id is None and original.dossier.supported_facets == ()
    assert not {"contribution_ref", "computation_dependencies"} & public_member.keys()
    assert len(public_member["endpoint_citations"]) == 2
    assert {c["passage"]["text"] for c in public_member["endpoint_citations"]} == {
        "50",
        "Probability %",
    }
    assert all(set(c) == {"source_pointer", "passage"} for c in public_member["endpoint_citations"])
    assert all(
        '"' + name + '"' not in json.dumps(before)
        for name in (
            "run_id",
            "cut_id",
            "release_id",
            "result_revision",
            "source_view_id",
            "native_task_id",
            "selected_task_id",
            "origin_task_id",
            "runtime_fingerprint",
        )
    )
    # A changed source-qualified region remains part of public membership meaning.
    moved = changed_member.model_copy(update=dict(scope=changed_member.scope + "/other-region"))
    different = select_dossier(
        changed_inputs,
        root_id=component.component_id,
        root_component=root,
        members=(moved,),
        predecessors=(predecessor,),
        contribution_predecessors=(changed_ref,),
    )
    assert structural_claim_id(structural_statement(different)) != structural_claim_id(before)

    # The same exact table projection in another original is a distinct source.
    native = thaw_native(payload["sources"][0]["projection"])
    native["source"].update(
        document="unadmitted:other-original",
        document_subject=original_document_subject("unadmitted:other-original"),
    )
    selected = FrozenNativeSource.acquire(profiles()[0].prepared, native)
    coordinate = selected.value["source"]
    source = inputs.sources[0]
    other = DeclaredStructuralSource(
        source=canonical_bytes(["unadmitted:other-source", None]).decode(),
        source_product="unadmitted:other-source",
        kind_contract=source.kind_contract,
        project_id=source.project_id,
        subject=source_subject(coordinate),
        subject_definition=source.subject_definition,
        original_source=coordinate["document"],
        document=coordinate["document"],
        projection_digest=coordinate["projection"],
        section_pointer=coordinate["section_pointer"],
        membership=coordinate["membership"],
        analyzed_scope_meaning=json_context_meaning(
            canonical_bytes(dict(source=coordinate, selectors=selected.value["selectors"]))
        ).decode(),
    )
    other_passage = changed_inputs.passages[-1].model_copy(update=dict(source_ref=other.identity))
    other_inputs = changed_inputs.model_copy(
        update=dict(sources=(*inputs.sources, other), passages=(*inputs.passages, other_passage))
    )
    other_ref = changed_ref.model_copy(
        update=dict(
            product_id="unadmitted:other-source-joins",
            contribution_id="source-contribution:" + "e" * 64,
            subject=other.subject,
            original_source=other.original_source,
            analyzed_scope_meaning=other.analyzed_scope_meaning,
        )
    )
    other_citations = tuple(
        citation.model_copy(
            update=dict(
                source_ref=other.identity, contribution_id="source-contribution:" + str(i + 2) * 64
            )
        )
        for i, citation in enumerate(changed_member.contribution_citations)
    )
    other_member = changed_member.model_copy(
        update=dict(
            member_id="literal:other-source-member",
            contribution_ref=other_ref,
            relation_product_id=other_ref.contribution_id,
            contribution_citations=other_citations,
            computation_dependencies=(
                other_ref.contribution_id,
                *(citation.contribution_id for citation in other_citations),
            ),
        )
    )
    different_source = select_dossier(
        other_inputs,
        root_id=component.component_id,
        root_component=root,
        members=(other_member,),
        predecessors=(predecessor,),
        contribution_predecessors=(other_ref,),
    )
    assert structural_claim_id(structural_statement(different_source)) != structural_claim_id(
        before
    )
