"""Discover a source-bound artifact cohort and score explicit private candidate pairs."""

from __future__ import annotations

import json

from pydantic import Field, model_validator

from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.artifact_identity import (
    ArtifactCitation,
    ArtifactIdentityProduct,
    ArtifactNomination,
    ArtifactPairKey,
    ArtifactRecord,
    ArtifactScoringPolicy,
    SourceArtifactOccurrence,
    native_alias_candidates,
    pair_candidates,
    score_pairs,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.structural_products import (
    StructuralInput,
    StructuralProductReport,
    StructuralValue,
)

from .scoped_relations import SourceWorkBinding


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
        citations = []
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
        if not citations:
            continue
        records.append(
            ArtifactRecord(
                contribution_id=row["contribution_id"],
                occurrence_id=row["occurrence_id"],
                artifact=SourceArtifactOccurrence.model_validate(source_python(row["value"])),
                source_contribution=json.loads(canonical_bytes(row)),
                citations=tuple(citations),
            )
        )
    return tuple(records)


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
    input_sources = {s.source_view_id: s for s in inputs.sources}
    ids = {}
    for endpoint in endpoints:
        row = rows.get(endpoint["contribution_id"])
        if row is None or not row["anchors"]:
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
        source = input_sources.get(pin["source_view_id"])
        if source is None or (
            source.native_task_id,
            source.native_product_key,
            source.native_content_digest,
            source.projection_digest,
            source.recipe_digest,
        ) != (
            pin["native_product_task_id"],
            pin["product_key"],
            pin["product_digest"],
            pin["projection_digest"],
            pin["recipe_digest"],
        ):
            raise ValueError("artifact nomination endpoint lies outside selected sources")
        expected_role = "reference" if endpoint["role"] == "attachment" else "caption"
        matches = [
            record.contribution_id
            for record in records
            if record.occurrence_id == row["occurrence_id"]
            and record.artifact.occurrence_role == expected_role
            and any(
                citation.source_ref == source.identity
                and any(
                    anchor["pointer"] == citation.source_pointer
                    and anchor["source_piece"] == citation.text
                    for anchor in row["anchors"]
                )
                for citation in record.citations
            )
        ]
        if len(matches) != 1:
            raise ValueError("artifact nomination endpoint lacks exactly one selected artifact")
        ids[endpoint["role"]] = matches[0]
    left, right = sorted(ids.values())
    if left == right:
        raise ValueError("artifact nomination cannot reference its own occurrence")
    return ArtifactNomination(left=left, right=right, relationship=reference)


class ArtifactIdentityMethod:
    name = "structure.artifact_identity"
    version = "2"
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
        for source in cfg.inputs.sources:
            ctx.check_active()
            binding = bindings.get(source.native_content_digest)
            if binding is None:
                unbound.append(source.source_view_id)
                continue
            frame = ctx.reader.structural_source_frame(cfg.inputs, source.identity)
            records.extend(
                discover_identity_records(frame, cfg.inputs, source.identity, binding.source_work)
            )
            provenance.append(binding.provenance)
        # Same physical occurrence seen through overlapping views is one cohort member.
        cohort = {}
        for record in sorted(records, key=lambda r: r.contribution_id):
            cohort.setdefault(
                (record.occurrence_id, record.artifact.source_work, record.artifact.artifact_kind),
                record,
            )
        selected = tuple(cohort.values())
        nominations = []
        for reference in sorted(cfg.external_nomination_refs, key=lambda ref: ref.contribution_id):
            ctx.check_active()
            payload = ctx.reader.retained_source_contribution(reference)
            nominations.append(retained_artifact_nomination(cfg.inputs, selected, reference, payload))
        alias, _ = native_alias_candidates(selected)
        pairs = pair_candidates(
            selected,
            external_nominations=tuple(nominations),
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
                records=selected,
                pairs=scored,
                native_alias_pairs=tuple(ArtifactPairKey(left=a, right=b) for a, b in alias),
                external_nominations=tuple(nominations),
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
