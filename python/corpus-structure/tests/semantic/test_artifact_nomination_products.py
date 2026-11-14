"""Current source-addressed artifact nominations retain exact physical endpoints."""

from types import SimpleNamespace

import pytest

from corpus_structure.methods.artifact_identity import artifact_nomination
from corpus_structure.semantic.constructions.navigation import NavigationRecord
from corpus_structure.semantic.contributions import contribution_identity, occurrence_identity
from corpus_structure.semantic.data_product_reference import DataProductReference, member_reference
from corpus_structure.semantic.declared_structural_references import DeclaredContributionRef
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.record_contracts import anchor_identity
from corpus_structure.semantic.structural_products import (
    DeclaredArtifactNomination,
    DeclaredArtifactNominationEndpoint,
    DeclaredPrimaryReference,
)


def nomination_case():
    text = "see Table 2.1. Table 2.1."
    pin = dict(
        format="declared-native-source-v1",
        source='["product:source",null]',
        source_product="product:source",
        subject="native:source",
        original_source="book",
        document="book",
        projection_digest="a" * 64,
        section_pointer="#/groups/0",
        membership="direct",
        project_id="p",
        analyzed_scope_meaning="{}",
        kind_contract="kind:source",
    )
    first, second = text.index("Table"), text.rindex("Table")
    pieces = [
        dict(kind="native_text", item_ref="#/texts/0", start=0, end=second),
        dict(kind="native_text", item_ref="#/texts/1", start=second, end=len(text)),
    ]
    rows, records = [], []
    for role, pointer, start, piece_start in (
        ("reference", "#/texts/0", first, 0),
        ("caption", "#/texts/1", second, second),
    ):
        anchor = dict(
            pin=pin,
            pointer=pointer,
            space="native",
            precision="exact",
            start=start - piece_start,
            end=start - piece_start + len("Table 2.1"),
            source_piece="Table 2.1",
        )
        anchor["anchor_id"] = anchor_identity(anchor)
        occurrence = occurrence_identity((anchor,))
        row = dict(
            semantic_type="structural.located_participant",
            pin=pin,
            anchors=(anchor,),
            occurrence_id=occurrence,
            value=source_value({"role": "artifact_reference"}),
        )
        row["contribution_id"] = contribution_identity(row)
        rows.append(row)
        records.append(
            SimpleNamespace(
                contribution_id="actual-artifact:" + role,
                occurrence_id=occurrence,
                artifact=SimpleNamespace(occurrence_role=role),
            )
        )
    relation = dict(
        semantic_type="structural.scoped_attachment",
        value=source_value({"relation": "artifact_reference_target"}),
        endpoints=tuple(
            dict(role=role, contribution_id=row["contribution_id"])
            for role, row in zip(("attachment", "target"), rows, strict=True)
        ),
    )
    relation["contribution_id"] = contribution_identity(relation)
    reference = DeclaredContributionRef(
        product_id="product:scoped",
        kind_contract="kind:scoped",
        project_id="p",
        subject="native:source",
        original_source="book",
        analyzed_scope_meaning="{}",
        contribution_id=relation["contribution_id"],
    )
    occurrences = {
        "subject": {"extents": [dict(start=first, end=first + len("Table 2.1"), text="Table 2.1")]},
        "cue": {"extents": [dict(start=0, end=3, text="see")]},
    }
    navigation = NavigationRecord(
        member_reference(DataProductReference("product:navigation"), "member:reference"),
        {
            "pointer": "#/texts/0",
            "roles": [
                {"role": "subject", "occurrences": ["subject"]},
                {"role": "cue", "occurrences": ["cue"]},
            ],
        },
        occurrences,
    )
    sources = {pin["source"]: {"pin": pin, "projection": {"text": text, "pieces": pieces}}}
    inputs = SimpleNamespace(dependencies=(reference.contribution_id,))
    return inputs, records, reference, (*rows, relation), sources, navigation


def project(case):
    inputs, records, reference, rows, sources, navigation = case
    return artifact_nomination(
        inputs,
        records,
        reference,
        rows,
        sources=sources,
        source_key=lambda pin: pin["source"],
        navigation_for=lambda pin: SimpleNamespace(
            select=lambda kind, pointer: (
                (navigation,) if kind == "artifact_reference" and pointer == "#/texts/0" else ()
            )
        ),
        origin_fields=lambda pin: {"origin_source": pin["source"]},
        endpoint_type=DeclaredArtifactNominationEndpoint,
        nomination_type=DeclaredArtifactNomination,
        primary_reference=lambda reference: DeclaredPrimaryReference.model_validate(
            reference.values()
        ),
    )


def test_native_artifact_nomination_keeps_directed_origins_cue_and_real_semantic_reference():
    result = project(nomination_case())
    assert result.endpoints[0].role == "attachment" and result.endpoints[1].role == "target"
    assert (
        result.origin_cue.text == "see" and result.primary_node.product_id == "product:navigation"
    )
    assert all(endpoint.origin_source == '["product:source",null]' for endpoint in result.endpoints)
    assert result.relationship.product_id == "product:scoped"
    assert b"source_view_id" not in canonical_bytes(result.model_dump(mode="json"))
    assert b"task_id" not in canonical_bytes(result.model_dump(mode="json"))


def test_native_artifact_nomination_refuses_changed_origin_pin_and_unselected_endpoint():
    case = nomination_case()
    case[4]['["product:source",null]']["pin"] = {
        **case[4]['["product:source",null]']["pin"],
        "document": "foreign",
    }
    with pytest.raises(ValueError, match="exact origin source pin"):
        project(case)
    inputs, records, reference, rows, sources, navigation = nomination_case()
    with pytest.raises(ValueError, match="exactly one selected artifact"):
        project((inputs, records[:1], reference, rows, sources, navigation))
