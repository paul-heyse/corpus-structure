"""Discover a source-bound artifact cohort and score explicit private candidate pairs."""

from __future__ import annotations

import json
from collections import defaultdict

from corpus_structure.semantic.artifact_identity import (
    ArtifactAliasSpan,
    ArtifactCitation,
    ArtifactDeclaredEndpoint,
    ArtifactDeclaredRelationship,
    ArtifactNomination,
    ArtifactNominationEndpoint,
    ArtifactRecord,
    ArtifactReferenceDesignator,
    SourceArtifactOccurrence,
    normalized_code,
)
from corpus_structure.semantic.contributions import occurrence_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.structural_products import (
    DeclaredArtifactNomination,
    DeclaredArtifactRecord,
)


def identity_records[Record: (ArtifactRecord, DeclaredArtifactRecord)](
    frame,
    inputs,
    source_ref,
    rows,
    index,
    *,
    artifact_type=SourceArtifactOccurrence,
    reference_type=ArtifactReferenceDesignator,
    record_type: type[Record],
    primary_reference=lambda reference: reference,
) -> tuple[Record, ...]:
    """Source-bound artifact assembly shared by native and sealed address owners."""
    from .witnessed_source_links import retained_artifact_fields

    pieces = json.loads(frame.native_context)["pieces"]
    passages = tuple(p for p in inputs.passages if p.source_ref == source_ref)
    records = []
    for row in rows:
        if row["semantic_type"] != "structural.artifact":
            continue
        artifact = artifact_type.model_validate(source_python(row["value"]))
        citations = []
        labels = None
        named_target = None
        primary_node = None
        for anchor in row["anchors"]:
            for piece in pieces:
                pointer = piece.get("item_ref", "")
                if piece.get("cell_index") is not None:
                    pointer += "/data/table_cells/" + str(piece["cell_index"])
                if pointer != anchor["pointer"] or piece.get("kind") != "native_text":
                    continue
                start = piece["start"] + anchor["start"]
                end = piece["start"] + anchor["end"]
                for passage in passages:
                    if (
                        passage.start <= start < end <= passage.end
                        and passage.text[start - passage.start : end - passage.start]
                        == anchor["source_piece"]
                    ):
                        matches = [
                            fact
                            for fact in (
                                *index.select("artifact_mention", pointer),
                                *index.select("artifact_reference", pointer),
                            )
                            if fact.span("subject") == (start, end)
                        ]
                        if len(matches) != 1:
                            raise ValueError(
                                "artifact occurrence lacks one exact primary source designator"
                            )
                        (fact,) = matches
                        _, labels, _ = retained_artifact_fields(fact, piece["start"])
                        primary_node = primary_reference(fact.reference)
                        explicit = [
                            fact
                            for fact in index.select("artifact_explicit_reference", pointer)
                            if fact.span("subject") == (start, end)
                            and fact.payload["artifact_kind"] == artifact.artifact_kind
                        ]
                        if len(explicit) > 1:
                            raise ValueError(
                                "artifact reference has ambiguous primary target declarations"
                            )
                        if explicit and artifact.occurrence_role == "reference":
                            (target,) = explicit
                            lo, hi = target.span("cue")
                            if passage.start <= lo < hi <= passage.end:
                                named_target = reference_type(
                                    target_code=target.payload["designator"],
                                    target_numbering=target.payload["numbering_namespace"],
                                    cue=ArtifactAliasSpan(
                                        source_pointer=pointer,
                                        start=lo - piece["start"],
                                        end=hi - piece["start"],
                                        text=target.text("cue"),
                                    ),
                                    primary_node=primary_reference(target.reference),
                                )
                        citations.append(
                            ArtifactCitation(
                                source_ref=source_ref,
                                passage_id=passage.passage_id,
                                source_pointer=pointer,
                                start=start,
                                end=end,
                                text=anchor["source_piece"],
                            )
                        )
        if labels is None:
            continue
        records.append(
            record_type(
                contribution_id=row["contribution_id"],
                occurrence_id=row["occurrence_id"],
                artifact=artifact,
                source_contribution=json.loads(canonical_bytes(row)),
                citations=tuple(citations),
                numbering=labels[0],
                revision=labels[1],
                explicit_reference=named_target,
                primary_node=primary_node,
            )
        )
    return tuple(records)


def artifact_cohort[Record: (ArtifactRecord, DeclaredArtifactRecord)](
    records: list[Record],
) -> tuple[Record, ...]:
    cohort: dict[tuple[str, str, str], Record] = {}
    for record in sorted(records, key=lambda r: r.contribution_id):
        key = (record.occurrence_id, record.artifact.source_work, record.artifact.artifact_kind)
        previous = cohort.setdefault(key, record)
        if previous is not record:
            if (previous.numbering, previous.revision) != (record.numbering, record.revision):
                raise ValueError("overlapping artifact views disagree on native source labels")
            cohort[key] = previous.model_copy(
                update={
                    "citations": tuple(dict.fromkeys((*previous.citations, *record.citations))),
                    "explicit_reference": previous.explicit_reference or record.explicit_reference,
                }
            )
    return tuple(cohort.values())


def declared_artifact_relationships(
    records,
    inputs,
    indexes,
    *,
    endpoint_type=ArtifactDeclaredEndpoint,
    relationship_type=ArtifactDeclaredRelationship,
    primary_reference=lambda reference: reference,
):
    """Resolve retained navigation facts through their actual nominal reference owner."""
    passages = {passage.passage_id: passage for passage in inputs.passages}
    captions = defaultdict(list)
    declarations = []
    for record in records:
        work, kind = record.artifact.source_work, record.artifact.artifact_kind
        work_citations = []
        for citation in record.citations:
            passage = passages[citation.passage_id]
            index = indexes[citation.source_ref]

            def source_facts(kind, index=index, citation=citation, passage=passage):
                return [
                    fact
                    for fact in index.select(kind, citation.source_pointer)
                    if fact.span("subject") == (citation.start, citation.end)
                    and passage.start <= fact.span("cue")[0] < fact.span("cue")[1] <= passage.end
                ]

            for fact in source_facts("artifact_work"):
                if fact.payload["work"] == work:
                    lo, hi = fact.span("cue")
                    work_citations.append(
                        (
                            citation.model_copy(
                                update={"start": lo, "end": hi, "text": fact.text("cue")}
                            ),
                            primary_reference(fact.reference),
                        )
                    )
            for fact in source_facts("artifact_relation"):
                relation_kind = fact.payload["relation_kind"]
                if (relation_kind == "reference") != (
                    record.artifact.occurrence_role == "reference"
                ) or fact.payload["artifact_kind"] != kind:
                    continue
                lo, hi = fact.span("cue")
                declarations.append(
                    (
                        record,
                        relation_kind,
                        citation.model_copy(
                            update={"start": lo, "end": hi, "text": fact.text("cue")}
                        ),
                        (
                            fact.payload.get("work", work),
                            kind,
                            fact.payload["numbering_namespace"],
                            fact.payload["designator"].lower(),
                        ),
                        fact.payload.get("revision"),
                        primary_reference(fact.reference),
                    )
                )
        if record.artifact.occurrence_role == "caption":
            captions[
                work, kind, record.numbering.value, normalized_code(record.artifact.controlled_code)
            ].append((record, tuple(work_citations)))
    output = []
    for source, kind, origin, key, revision, primary_node in declarations:
        targets = []
        cross_work = key[0] != source.artifact.source_work
        for target, work_cues in captions[key]:
            if (
                target.occurrence_id == source.occurrence_id
                or (cross_work and not work_cues)
                or (revision is not None and target.revision.value != revision)
                or (
                    kind == "supersedes"
                    and (
                        source.revision.value is None
                        or revision is None
                        or source.revision.value == revision
                    )
                )
            ):
                continue
            marker, marker_node = work_cues[0] if cross_work else (None, None)
            citation = (
                next(
                    c
                    for c in target.citations
                    if c.source_ref == marker.source_ref and c.passage_id == marker.passage_id
                )
                if marker
                else target.citations[0]
            )
            targets.append(
                endpoint_type(
                    record_id=target.contribution_id,
                    citation=citation,
                    work_cue=marker,
                    work_primary_node=marker_node,
                )
            )
        output.append(
            relationship_type(
                kind=kind,
                source_id=source.contribution_id,
                origin=origin,
                primary_node=primary_node,
                targets=tuple(targets),
                outcome="no_compatible_candidate"
                if not targets
                else "witnessed_candidate"
                if len(targets) == 1
                else "ambiguous",
            )
        )
    return tuple(dict.fromkeys(output))


def artifact_nomination[Nomination: (ArtifactNomination, DeclaredArtifactNomination)](
    inputs,
    records,
    reference,
    contributions,
    *,
    sources,
    source_key,
    navigation_for,
    origin_fields,
    endpoint_type=ArtifactNominationEndpoint,
    nomination_type: type[Nomination],
    primary_reference=lambda reference: reference,
) -> Nomination:
    """Join original source origins through their actual nominal address owner."""
    if reference.contribution_id not in inputs.dependencies:
        raise ValueError("artifact nomination outside declared dependencies")
    rows = {row["contribution_id"]: row for row in contributions}
    relation = rows.get(reference.contribution_id)
    if (
        relation is None
        or relation["semantic_type"] != "structural.scoped_attachment"
        or source_python(relation["value"])["relation"] != "artifact_reference_target"
    ):
        raise ValueError("artifact nomination requires a retained reference-target relationship")
    endpoints = relation.get("endpoints", ())
    if len(endpoints) != 2 or {e["role"] for e in endpoints} != {"attachment", "target"}:
        raise ValueError("artifact nomination requires two role-bound endpoints")
    matched = {}
    cue = None
    cue_node = None
    for endpoint in endpoints:
        row = rows.get(endpoint["contribution_id"])
        if row is None or len(row["anchors"]) != 1:
            raise ValueError("artifact nomination endpoint lacks retained source evidence")
        if not (
            row["semantic_type"] == "structural.artifact"
            or (
                row["semantic_type"] == "structural.located_participant"
                and source_python(row["value"])["role"] == "artifact_reference"
            )
        ):
            raise ValueError("artifact nomination endpoint has an incompatible source role")
        pin = row["pin"]
        source = sources.get(source_key(pin))
        anchor = row["anchors"][0]
        if (
            source is None
            or source["pin"] != pin
            or anchor["pin"] != pin
            or anchor["space"] != "native"
            or anchor["precision"] != "exact"
            or occurrence_identity([anchor]) != row["occurrence_id"]
        ):
            raise ValueError("artifact nomination endpoint lacks its exact origin source pin")
        projection = source["projection"]
        origins = [
            piece
            for piece in projection["pieces"]
            if piece.get("kind") == "native_text"
            and piece.get("cell_index") is None
            and piece["item_ref"] == anchor["pointer"]
            and piece["start"]
            <= piece["start"] + anchor["start"]
            < piece["start"] + anchor["end"]
            <= piece["end"]
            and projection["text"][
                piece["start"] + anchor["start"] : piece["start"] + anchor["end"]
            ]
            == anchor["source_piece"]
        ]
        if len(origins) != 1:
            raise ValueError("artifact nomination endpoint differs from its exact origin text")
        expected_role = "reference" if endpoint["role"] == "attachment" else "caption"
        matches = [
            record
            for record in records
            if record.occurrence_id == row["occurrence_id"]
            and record.artifact.occurrence_role == expected_role
        ]
        if len(matches) != 1:
            raise ValueError("artifact nomination endpoint lacks exactly one selected artifact")
        if expected_role == "reference":
            start = origins[0]["start"]
            candidates = [
                record
                for record in navigation_for(pin).select("artifact_reference", anchor["pointer"])
                if record.span("subject") == (start + anchor["start"], start + anchor["end"])
            ]
            if len(candidates) != 1 or candidates[0].span("cue") is None:
                raise ValueError("artifact reference lacks exact retained primary cue support")
            (candidate,) = candidates
            cue_node = primary_reference(candidate.reference)
            lo, hi = candidate.span("cue")
            cue = ArtifactAliasSpan(
                source_pointer=anchor["pointer"],
                start=lo - start,
                end=hi - start,
                text=projection["text"][lo:hi],
            )
        matched[endpoint["role"]] = endpoint_type(
            role=endpoint["role"],
            record_id=matches[0].contribution_id,
            contribution_id=row["contribution_id"],
            **origin_fields(pin),
            origin_anchor_id=anchor["anchor_id"],
        )
    directed = (matched["attachment"], matched["target"])
    left, right = sorted(e.record_id for e in directed)
    assert cue is not None
    return nomination_type(
        left=left,
        right=right,
        relationship=reference,
        endpoints=directed,
        origin_cue=cue,
        primary_node=cue_node,
    )


# Exact historical verifier identity; no execution capability is retained.
SEALED_ARTIFACT_NAME = "structure.artifact_identity"
SEALED_ARTIFACT_VERSION = "5"
