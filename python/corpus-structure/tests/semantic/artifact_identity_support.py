"""Shared controlled inputs and builders for artifact identity support."""

from typing import Literal

from corpus_structure.semantic.constructions.navigation import (
    artifact_source_labels,
    source_alias_fields,
)
from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import (
    DeclaredArtifactNomination,
    DeclaredArtifactRecord,
    DeclaredPrimaryReference,
    DeclaredSourceArtifactOccurrence,
)


def record(
    identity,
    *,
    work="book",
    code="5.1",
    title=None,
    aliases=(),
    revision=None,
    namespace="chapter5",
    role: Literal["caption", "reference"] = "caption",
):
    label_text = (f" (numbering namespace: {namespace})" if namespace else "") + (
        f" (revision: {revision})" if revision else ""
    )
    numbering_label, revision_label = artifact_source_labels(label_text, 0, "#/texts/" + identity)
    # A pure kernel fixture carries declared addresses without claiming native admission.
    source_product = "product:source:" + identity
    pin = DeclaredStructuralSource(
        source=canonical_bytes([source_product, None]).decode(),
        source_product=source_product,
        subject="native:" + identity,
        subject_definition="original-source-view",
        document=work,
        projection_digest="a" * 64,
        section_pointer="#/groups/0",
        membership="direct",
        project_id="controlled",
        original_source=work,
        analyzed_scope_meaning="{}",
        kind_contract="kind:source",
    )
    primary = DeclaredPrimaryReference(
        product_id="product:navigation:" + identity, member_id="member:artifact:" + identity
    )
    return DeclaredArtifactRecord(
        contribution_id=identity,
        occurrence_id="occurrence:" + identity,
        source_contribution={"pin": pin.model_dump(mode="json", exclude_none=True)},
        primary_node=primary,
        citations=(
            dict(
                source_ref=pin.source,
                passage_id="p:" + identity,
                source_pointer="#/texts/" + identity,
                start=0,
                end=3,
                text="5.1",
            ),
        ),
        artifact=DeclaredSourceArtifactOccurrence(
            source_work=work,
            artifact_kind="table",
            controlled_code=code,
            title=title,
            **source_alias_fields(
                "Table 5.1" + "".join(f' (alias: "{alias}")' for alias in aliases),
                len("Table 5.1"),
                "#/texts/" + identity,
            ),
            occurrence_role=role,
            scope="chapter5",
            source_pointer="#/texts/" + identity,
            dependencies=(source_product,),
            primary_node=primary,
        ),
        numbering=numbering_label,
        revision=revision_label,
    )


def nomination(left, right, ordinal=1):
    return DeclaredArtifactNomination(
        left=left,
        right=right,
        relationship=dict(
            variant="member",
            role="nominations",
            occurrence="scoped:fixture",
            member_id="contribution:source-contribution:" + format(ordinal, "064x"),
        ),
        endpoints=tuple(
            dict(
                role=role,
                record_id=key,
                contribution_id=key,
                origin_source=canonical_bytes(["product:source:" + key, None]).decode(),
                origin_anchor_id="anchor:" + key,
            )
            for role, key in (("attachment", left), ("target", right))
        ),
        primary_node=DeclaredPrimaryReference(
            product_id="product:navigation:" + left, member_id="member:reference:" + left
        ),
        origin_cue=dict(source_pointer="#/texts/" + left, start=0, end=3, text="See"),
    )
