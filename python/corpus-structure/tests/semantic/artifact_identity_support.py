"""Shared controlled inputs and builders for artifact identity support."""

from typing import Literal

from corpus_structure.semantic.artifact_identity import (
    ArtifactNomination,
    ArtifactRecord,
    SourceArtifactOccurrence,
)
from corpus_structure.semantic.constructions.navigation import (
    artifact_source_labels,
    source_alias_fields,
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
    return ArtifactRecord(
        contribution_id=identity,
        occurrence_id="occurrence:" + identity,
        source_contribution={},
        citations=(
            dict(
                source_ref="source:" + identity,
                passage_id="p:" + identity,
                source_pointer="#/texts/" + identity,
                start=0,
                end=3,
                text="5.1",
            ),
        ),
        artifact=SourceArtifactOccurrence(
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
            dependencies=("source:" + identity,),
        ),
        numbering=numbering_label,
        revision=revision_label,
    )


def nomination(left, right, ordinal=1):
    return ArtifactNomination(
        left=left,
        right=right,
        relationship=dict(
            contribution_id="source-contribution:" + format(ordinal, "064x"),
            project_id="controlled",
            run_id=1,
            cut_id=1,
            release_id="release:controlled",
            result_revision=1,
            selected_task_id=1,
            origin_task_id=1,
            runtime_fingerprint="runtime:controlled",
        ),
        endpoints=tuple(
            dict(
                role=role,
                record_id=key,
                contribution_id=key,
                origin_source_view_id=1,
                origin_anchor_id="anchor:" + key,
            )
            for role, key in (("attachment", left), ("target", right))
        ),
        origin_cue=dict(source_pointer="#/texts/" + left, start=0, end=3, text="See"),
    )
