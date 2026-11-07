"""Discover a source-bound artifact cohort and score explicit private candidate pairs."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Literal

from pydantic import Field, model_validator

from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.artifact_identity import (
    ArtifactAliasSpan,
    ArtifactCitation,
    ArtifactDeclaredEndpoint,
    ArtifactDeclaredRelationship,
    ArtifactIdentityProduct,
    ArtifactNomination,
    ArtifactNominationEndpoint,
    ArtifactPairKey,
    ArtifactRecord,
    ArtifactScoringPolicy,
    SourceArtifactOccurrence,
    artifact_reference_resolutions,
    artifact_route_counts,
    artifact_source_labels,
    explicit_artifact_reference,
    native_alias_candidates,
    normalized_code,
    pair_candidates,
    score_pairs,
)
from corpus_structure.semantic.contributions import occurrence_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.structural_products import (
    StructuralInput,
    StructuralProductReport,
    StructuralValue,
)

from .scoped_relations import ARTIFACT_REFERENCE_CUE, SourceWorkBinding


class ArtifactIdentityConfig(StructuralValue):
    inputs: StructuralInput | None = None
    structural_input_digest: str | None = None
    work_bindings: tuple[SourceWorkBinding, ...] = ()
    policy: ArtifactScoringPolicy | None = None
    title_threshold: float = Field(default=70, ge=0, le=100)
    external_nomination_refs: tuple[RetainedContributionRef, ...] = ()
    exclusions: tuple[tuple[str, str], ...] = ()
    known_anchor_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def closure(self):
        if self.inputs is None:
            if (
                self.structural_input_digest
                or self.policy
                or self.work_bindings
                or self.external_nomination_refs
                or self.exclusions
                or self.known_anchor_ids
            ):
                raise ValueError("partial artifact identity config")
        elif self.structural_input_digest != self.inputs.identity or self.policy is None:
            raise ValueError("artifact identity requires exact sources and declared model policy")
        nomination_ids = {r.contribution_id for r in self.external_nomination_refs}
        if len(nomination_ids) != len(self.external_nomination_refs) or (
            self.inputs is not None and not nomination_ids <= set(self.inputs.dependencies)
        ):
            raise ValueError("external nomination requires distinct declared dependencies")
        if len(set(self.known_anchor_ids)) != len(self.known_anchor_ids):
            raise ValueError("known artifact anchors repeat")
        if len({b.native_content_digest for b in self.work_bindings}) != len(self.work_bindings):
            raise ValueError("source-work mappings repeat")
        return self


def discover_identity_records(frame, inputs, source_ref, source_work):
    from .scoped_relations import discover_relations

    rows = discover_relations(frame, source_work=source_work)["contributions"]
    pieces = json.loads(frame.native_context)["pieces"]
    passages = tuple(p for p in inputs.passages if p.source_ref == source_ref)
    records = []
    for row in rows:
        if row["semantic_type"] != "structural.artifact":
            continue
        artifact = SourceArtifactOccurrence.model_validate(source_python(row["value"]))
        citations = []
        labels = None
        named_target = None
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
                        raw = frame.text[piece["start"] : piece["end"]]
                        labels = artifact_source_labels(raw, anchor["end"], pointer)
                        explicit = explicit_artifact_reference(
                            raw, anchor["start"], anchor["end"], pointer, artifact
                        )
                        if (
                            explicit is not None
                            and passage.start <= piece["start"] + explicit.cue.start
                            and piece["start"] + explicit.cue.end <= passage.end
                        ):
                            named_target = explicit
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
            ArtifactRecord(
                contribution_id=row["contribution_id"],
                occurrence_id=row["occurrence_id"],
                artifact=artifact,
                source_contribution=json.loads(canonical_bytes(row)),
                citations=tuple(citations),
                numbering=labels[0],
                revision=labels[1],
                explicit_reference=named_target,
            )
        )
    return tuple(records)


def artifact_cohort(records: list[ArtifactRecord]) -> tuple[ArtifactRecord, ...]:
    cohort: dict[tuple[str, str, str], ArtifactRecord] = {}
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


_RELATION_LABEL = re.compile(r"[ \t]+\((?:numbering namespace|revision):[ \t]*[A-Za-z0-9_.-]+\)")
_WORK_CUE = re.compile(r"[ \t]+\(work:[ \t]*([A-Za-z0-9][A-Za-z0-9_.-]*)\)")
_ARTIFACT_RELATION = re.compile(
    r"[ \t]+\((cites|same lineage as|supersedes)[ \t]+(Table|Figure|Theorem|Section)[ \t]+"
    r"([A-Za-z]?[0-9]+(?:[.-][0-9]+)*[A-Za-z]?)[ \t]+in numbering namespace[ \t]+"
    r"([A-Za-z0-9][A-Za-z0-9_.-]*)(?:[ \t]+of work[ \t]+([A-Za-z0-9][A-Za-z0-9_.-]*))?"
    r"(?:[ \t]+revision[ \t]+([A-Za-z0-9][A-Za-z0-9_.-]*))?\)"
)
_RELATION_KINDS: dict[str, Literal["reference", "same_lineage", "supersedes"]] = {
    "cites": "reference",
    "same lineage as": "same_lineage",
    "supersedes": "supersedes",
}


def artifact_declared_relationships(records, inputs, frames):
    """Resolve explicit bounded artifact declarations without inferring lineage from labels."""
    passages = {p.passage_id: p for p in inputs.passages}
    piece_bounds = {
        (source, p["item_ref"], p["start"]): p["end"]
        for source, frame in frames.items()
        for p in json.loads(frame.native_context)["pieces"]
        if p.get("kind") == "native_text" and p.get("cell_index") is None
    }
    captions = defaultdict(list)
    declarations = []
    for record in records:
        work, kind = record.artifact.source_work, record.artifact.artifact_kind
        work_citations = []
        anchor_end = record.source_contribution["anchors"][0]["end"]
        for citation in record.citations:
            frame = frames[citation.source_ref]
            passage = passages[citation.passage_id]
            bound = min(
                passage.end,
                piece_bounds[
                    citation.source_ref,
                    citation.source_pointer,
                    citation.end - anchor_end,
                ],
            )
            cursor = citation.end
            while label := _RELATION_LABEL.match(frame.text, cursor, bound):
                cursor = label.end()
            if marker := _WORK_CUE.match(frame.text, cursor, bound):
                cursor = marker.end()
                if marker[1] == work:
                    work_citations.append(
                        citation.model_copy(
                            update={
                                "start": marker.start(),
                                "end": cursor,
                                "text": marker[0],
                            }
                        )
                    )
            while relation := _ARTIFACT_RELATION.match(frame.text, cursor, bound):
                cursor = relation.end()
                relation_kind = _RELATION_KINDS[relation[1]]
                if (relation_kind == "reference") != (
                    record.artifact.occurrence_role == "reference"
                ):
                    continue
                if relation[2].lower() != kind:
                    continue
                declarations.append(
                    (
                        record,
                        relation_kind,
                        citation.model_copy(
                            update={
                                "start": relation.start(),
                                "end": cursor,
                                "text": relation[0],
                            }
                        ),
                        (relation[5] or work, kind, relation[4], relation[3].lower()),
                        relation[6],
                    )
                )
        if record.artifact.occurrence_role == "caption":
            captions[
                work, kind, record.numbering.value, normalized_code(record.artifact.controlled_code)
            ].append((record, tuple(work_citations)))
    output = []
    for source, kind, origin, key, revision in declarations:
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
            marker = work_cues[0] if cross_work else None
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
                ArtifactDeclaredEndpoint(
                    record_id=target.contribution_id,
                    citation=citation,
                    work_cue=marker,
                )
            )
        output.append(
            ArtifactDeclaredRelationship(
                kind=kind,
                source_id=source.contribution_id,
                origin=origin,
                targets=tuple(targets),
                outcome="no_compatible_candidate"
                if not targets
                else "witnessed_candidate"
                if len(targets) == 1
                else "ambiguous",
            )
        )
    return tuple(dict.fromkeys(output))


def retained_artifact_nomination(inputs, records, reference, payload) -> ArtifactNomination:
    """Bind one genuine retained reference relationship to its exact cohort endpoints."""
    if reference.contribution_id not in inputs.dependencies:
        raise ValueError("artifact nomination outside declared dependencies")
    rows = {row["contribution_id"]: row for row in payload["contributions"]}
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
    matched: dict[str, ArtifactNominationEndpoint] = {}
    cue = None
    source_views = {view["source_view_id"]: view for view in payload["sources"]}
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
        source = source_views.get(pin["source_view_id"])
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
            match = ARTIFACT_REFERENCE_CUE.search(
                projection["text"][start : start + anchor["start"]]
            )
            if match is None:
                raise ValueError("artifact reference lacks the exact local cross-reference cue")
            literal = match[0].rstrip()
            cue = ArtifactAliasSpan(
                source_pointer=anchor["pointer"],
                start=match.start(),
                end=match.start() + len(literal),
                text=literal,
            )
        matched[endpoint["role"]] = ArtifactNominationEndpoint(
            role=endpoint["role"],
            record_id=matches[0].contribution_id,
            contribution_id=row["contribution_id"],
            origin_source_view_id=pin["source_view_id"],
            origin_anchor_id=anchor["anchor_id"],
        )
    directed = (matched["attachment"], matched["target"])
    left, right = sorted(e.record_id for e in directed)
    assert cue is not None
    return ArtifactNomination(
        left=left, right=right, relationship=reference, endpoints=directed, origin_cue=cue
    )


class ArtifactIdentityMethod:
    name = "structure.artifact_identity"
    version = "4"
    family = MethodFamily.CONSOLIDATE
    unit_type = TaskUnitType.RUN
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = ArtifactIdentityConfig
    resources = Resources()

    def select(self, run, cfg):
        return (UnitRef(TaskUnitType.RUN, unit_key=cfg.inputs.identity),) if cfg.inputs else ()

    def input_digest(self, unit, cfg):
        return Digest(canonical_bytes(cfg.model_dump(mode="json")))

    def run(self, units, cfg, ctx):
        if cfg.inputs is None or cfg.policy is None:
            raise ValueError("artifact identity inputs absent")
        bindings = {b.native_content_digest: b for b in cfg.work_bindings}
        records = []
        unbound = []
        provenance = []
        frames = {}
        for source in cfg.inputs.sources:
            ctx.check_active()
            binding = bindings.get(source.native_content_digest)
            if binding is None:
                unbound.append(source.source_view_id)
                continue
            frame = ctx.reader.structural_source_frame(cfg.inputs, source.identity)
            frames[source.identity] = frame
            records.extend(
                discover_identity_records(frame, cfg.inputs, source.identity, binding.source_work)
            )
            provenance.append(binding.provenance)
        selected = artifact_cohort(records)
        nominations = []
        for reference in sorted(cfg.external_nomination_refs, key=lambda ref: ref.contribution_id):
            ctx.check_active()
            payload = ctx.reader.retained_source_contribution(reference)
            nominations.append(
                retained_artifact_nomination(cfg.inputs, selected, reference, payload)
            )
        alias, _ = native_alias_candidates(selected)
        explicit_references = artifact_reference_resolutions(selected)
        declarations = (
            artifact_declared_relationships(selected, cfg.inputs, frames)
            if self.version == "4"
            else None
        )
        pairs = pair_candidates(
            selected,
            external_nominations=tuple(nominations),
            declared_relationships=declarations or (),
            explicit_references=explicit_references,
            native_alias_pairs=alias,
            title_threshold=cfg.title_threshold,
            exclusions=cfg.exclusions,
            known_anchor_ids=cfg.known_anchor_ids,
        )
        scored = score_pairs(selected, pairs, cfg.policy)
        report = StructuralProductReport(
            kind="artifact_identity",
            inputs=cfg.inputs,
            artifact_identity=ArtifactIdentityProduct(
                protocol="artifact-identity-4"
                if declarations is not None
                else "artifact-identity-3",
                records=selected,
                pairs=scored,
                native_alias_pairs=tuple(ArtifactPairKey(left=a, right=b) for a, b in alias),
                external_nominations=tuple(nominations),
                explicit_references=explicit_references,
                declared_relationships=declarations,
                route_counts=artifact_route_counts(scored),
                policy=cfg.policy,
                source_mapping_provenance=tuple(sorted(set(provenance))),
                unbound_source_ids=tuple(unbound),
                known_anchor_ids=tuple(sorted(cfg.known_anchor_ids)),
            ),
        )
        return tuple(
            UnitResult(
                ref=u.ref,
                outcome=ObservationOutcome.PRODUCED,
                structural_product=report.model_dump(mode="json"),
            )
            for u in units
        )
