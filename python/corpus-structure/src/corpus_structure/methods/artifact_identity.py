"""Discover a source-bound artifact cohort and score explicit private candidate pairs."""

from __future__ import annotations

import json

from pydantic import Field, model_validator

from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.artifact_identity import (
    ArtifactCitation,
    ArtifactIdentityProduct,
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
    external_pairs: tuple[tuple[str, str], ...] = ()
    exclusions: tuple[tuple[str, str], ...] = ()

    @model_validator(mode="after")
    def closure(self):
        if self.inputs is None:
            if (
                self.structural_input_digest
                or self.policy
                or self.work_bindings
                or self.external_pairs
                or self.exclusions
            ):
                raise ValueError("partial artifact identity config")
        elif self.structural_input_digest != self.inputs.identity or self.policy is None:
            raise ValueError("artifact identity requires exact sources and declared model policy")
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
                citations=tuple(citations),
            )
        )
    return tuple(records)


class ArtifactIdentityMethod:
    name = "structure.artifact_identity"
    version = "1"
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
        pairs = pair_candidates(
            selected,
            external_pairs=cfg.external_pairs,
            title_threshold=cfg.title_threshold,
            exclusions=cfg.exclusions,
        )
        alias = native_alias_candidates(selected)
        # Native array blocking is an independently retained generator arm.
        selected_pairs = {(p.left, p.right): p for p in pairs}
        for endpoints in alias:
            if endpoints not in selected_pairs:
                extra = pair_candidates(
                    selected, external_pairs=(endpoints,), exclusions=cfg.exclusions
                )
                selected_pairs[endpoints] = next(p for p in extra if (p.left, p.right) == endpoints)
            p = selected_pairs[endpoints]
            selected_pairs[endpoints] = p.model_copy(
                update={
                    "candidate_routes": tuple(
                        dict.fromkeys((*p.candidate_routes, "native_alias_array"))
                    )
                }
            )
        scored = score_pairs(
            selected, tuple(selected_pairs[k] for k in sorted(selected_pairs)), cfg.policy
        )
        report = StructuralProductReport(
            kind="artifact_identity",
            inputs=cfg.inputs,
            artifact_identity=ArtifactIdentityProduct(
                records=selected,
                pairs=scored,
                native_alias_pairs=tuple(ArtifactPairKey(left=a, right=b) for a, b in alias),
                policy=cfg.policy,
                source_mapping_provenance=tuple(sorted(set(provenance))),
                unbound_source_ids=tuple(unbound),
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
