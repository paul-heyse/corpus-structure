"""Frozen cross-source pins retain original references and reject widened custody."""

from dataclasses import replace
from decimal import Decimal

import pytest

from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_source_sets import (
    FrozenSourceSet,
    SourceSetEntry,
    read_source_sets,
    source_sets_record,
)
from corpus_structure.semantic.data_product_reference import (
    DataProductMemberReference,
    DataProductReference,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.selected_support import SelectedSupportAcquisition


def entry(*, product="projection:one", source="source:one", member="member:one"):
    return SourceSetEntry.from_semantic_source(
        DataProductMemberReference(DataProductReference(product), member),
        context=SubjectContext(
            "project", "view:one", source, b'{"page":1}', subject_definition="document"
        ),
    )


def test_source_set_keeps_exact_original_reference_and_roundtrips():
    first = entry()
    second = entry(product="projection:two", member="member:two")
    scope = FrozenSourceSet.unqualified("inputs", (second, first))
    encoded = source_sets_record((scope,))
    assert encoded["inputs"]["entries"][0]["product"] == "projection:one"
    assert (
        encoded["inputs"]["entries"][0]["source_reference"]
        == DataProductMemberReference(DataProductReference("projection:one"), "member:one").identity
    )
    assert read_source_sets(encoded)[0].entries == (first, second)
    with pytest.raises(ValueError, match="unique"):
        FrozenSourceSet.unqualified("inputs", (first, first))
    with pytest.raises(ValueError, match="qualified"):
        replace(first, project_id="")
    with pytest.raises(ValueError, match="product/member"):
        replace(first, source_reference="forged")
    with pytest.raises(ValueError, match="canonical"):
        replace(first, analyzed_scope=canonical_bytes([1]))


def test_source_set_normalizes_exact_fraction_and_exponent_scope_without_float_roundtrip():
    first = replace(entry(), analyzed_scope=b'{"coordinate":0.123456789012345678901,"scale":1e+30}')
    encoded = source_sets_record((FrozenSourceSet.unqualified("inputs", (first,)),))
    assert encoded["inputs"]["entries"][0]["analyzed_scope"] == {
        "coordinate": Decimal("0.123456789012345678901"),
        "scale": Decimal("1e30"),
    }
    assert read_source_sets(encoded)[0].entries == (first,)


def selected_entry(
    *,
    product="projection:one",
    member="member:one",
    episode="episode:one",
    use="use:one",
    read="read:one",
    output_member=None,
):
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_source_sets import SelectedSourceSetEntry
    from corpus_structure.semantic.demand_results import CutSelection

    cut = CutSelection(
        json_bytes(
            dict(
                project_id="project",
                demand_id="demand:source",
                read_id=read,
                release_id="release:source",
                runtime_id="runtime:source",
                selection={},
                trust_snapshot={},
                read_snapshot="1:2:",
                frontier_at="2026-11-17T00:00:00Z",
                scope={},
            )
        )
    )
    return SelectedSourceSetEntry.from_selected_header(
        dict(
            product_id=product,
            member_id=member,
            subject="view:one",
            original_source="source:one",
            analyzed_scope={"page": 1},
            subject_definition="document",
            use_id=use,
            derivation_id=episode,
            output_member_id=output_member,
            role="result",
            position=0,
            multiplicity=1,
        ),
        cut,
    )


def test_selected_source_set_groups_cut_once_and_preserves_distinct_proofs():
    first = selected_entry()
    second = selected_entry(
        product="projection:two", member="member:two", episode="episode:two", use="use:two"
    )
    scope = FrozenSourceSet.from_selected("inputs", (first, second))
    encoded = source_sets_record((scope,))
    assert len(encoded["inputs"]["acquisition"]["reads"]) == 1
    assert len(encoded["inputs"]["acquisition"]["reads"][0]["proofs"]) == 2
    assert read_source_sets(encoded)[0] == scope
    other_proof = selected_entry(episode="episode:other", use="use:other")
    both = FrozenSourceSet.from_selected("inputs", (first, other_proof))
    assert len(both.entries) == 1
    assert isinstance(both.acquisition, SelectedSupportAcquisition)
    assert len(both.acquisition.reads[0].proofs) == 2
    with pytest.raises(ValueError, match="repeats a selected proof"):
        FrozenSourceSet.from_selected("inputs", (first, first))


def test_source_set_envelope_is_current_only_and_emitting_member_is_distinct():
    from corpus_structure.semantic.data_operation_source_sets import source_sets_meaning

    whole = selected_entry()
    member = selected_entry(output_member="member:one")
    assert whole.entry == member.entry
    assert whole.proof.output.member_id is None
    assert member.proof.output.member_id == "member:one"
    with pytest.raises(ValueError, match="emitting member"):
        selected_entry(output_member="wrong-member")
    with pytest.raises(ValueError, match="current entries/acquisition envelope"):
        read_source_sets({"inputs": [whole.entry.record()]})
    before = FrozenSourceSet.from_selected("inputs", (whole,))
    after = FrozenSourceSet.from_selected("inputs", (selected_entry(read="read:later"),))
    assert source_sets_record((before,)) != source_sets_record((after,))
    assert source_sets_meaning(source_sets_record((before,))) == source_sets_meaning(
        source_sets_record((after,))
    )


def test_request_identity_keeps_selected_episode_and_excludes_acquisition_cut():
    from corpus_structure.semantic.data_operation_compilation import project_operation_binding
    from corpus_structure.semantic.data_operation_identity import semantic_value
    from corpus_structure.semantic.data_operation_model import (
        BindingExpression,
        BoundRoleMember,
        EffectiveIdentity,
        ResolvedOperationBinding,
        ResolvedRoleBinding,
    )
    from semantic.test_data_operation_bindings import model

    target = model(BindingExpression("scan", roles=("items",)))
    target = replace(
        target, identities=(*target.identities, EffectiveIdentity("urn:op", "recipe", "recipe:one"))
    )

    def request(selected):
        pin, proof = selected.entry, selected.proof
        member = BoundRoleMember(
            pin.product,
            "kind:fixed",
            pin.subject,
            pin.original_source,
            pin.analyzed_scope,
            b"{}",
            (proof.support.derivation_id,),
            b"{}",
            member=pin.member,
            subject_definition=pin.subject_definition,
            support_references=(proof.support,),
            producer_output=proof.output,
        )
        binding = ResolvedOperationBinding(
            "urn:op",
            pin.subject,
            (ResolvedRoleBinding("items", "present", (member,)),),
            canonical_bytes(semantic_value({})),
            "declared",
            b"{}",
            b"{}",
            "execution:test",
            None,
            __import__(
                "corpus_structure.semantic.data_operation_json", fromlist=["json_bytes"]
            ).json_bytes(
                source_sets_record((FrozenSourceSet.from_selected("inputs", (selected,)),))
            ),
            subject_context=SubjectContext(
                pin.project_id,
                pin.subject,
                pin.original_source,
                pin.analyzed_scope,
                subject_definition=pin.subject_definition,
            ),
        )
        return project_operation_binding(target, binding)[0]

    first = request(selected_entry())
    assert first.identity.key == request(selected_entry(read="read:later")).identity.key
    assert (
        first.identity.key
        != request(selected_entry(episode="episode:other", use="use:other")).identity.key
    )
