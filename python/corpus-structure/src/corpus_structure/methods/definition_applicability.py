"""Owned automatic source-backed definition nomination and applicability proposals.

The model classifies each fixed-list usage/passage pair. Its category and confidence
are retained observations, never public eligibility or a calibrated truth estimate.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256
from typing import Self

from pydantic import Field, JsonValue, RootModel, model_validator

from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.methods.contextual_embeddings import (
    E5,
    ContextInput,
    encode_contexts,
)
from corpus_structure.methods.gliner import GlinerInput, GlinerPack, GlinerProfile, GlinerRefused
from corpus_structure.methods.gliner_worker import GlinerWorker, GlinerWorkerError
from corpus_structure.methods.structural_products import definition_applicability
from corpus_structure.methods.structural_retrieval import source_definition_inventory
from corpus_structure.semantic.contextual_storage import enrichment_report
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import (
    DefinitionReading,
    StructuralInput,
    StructuralValue,
)


class DefinitionApplicabilityConfig(StructuralValue):
    inputs: StructuralInput | None = None
    structural_input_digest: str | None = None
    usage_id: str | None = None
    target_ids: tuple[str, ...] = ()
    profile: GlinerProfile | None = None
    unique_target_budget: int = Field(default=10, ge=1, le=256)
    channel_budget: int = Field(default=30, ge=1, le=256)

    @model_validator(mode="after")
    def declared_inputs(self) -> Self:
        if self.inputs is None:
            if (
                self.usage_id is not None
                or self.target_ids
                or self.profile is not None
                or self.structural_input_digest is not None
            ):
                raise ValueError(
                    "an absent automatic definition operation cannot carry partial inputs"
                )
            return self
        if self.profile is None or self.usage_id is None:
            raise ValueError("automatic definition operation needs a declared provider and usage")
        if self.structural_input_digest != self.inputs.identity:
            raise ValueError("automatic definition operation needs its exact frozen input digest")
        passages = {p.passage_id for p in self.inputs.passages}
        if self.usage_id not in passages or self.usage_id in self.target_ids:
            raise ValueError("usage and target passage identities must be distinct")
        if (
            not self.target_ids
            or len(set(self.target_ids)) != len(self.target_ids)
            or not set(self.target_ids) <= passages
        ):
            raise ValueError("target inventory must be nonempty, unique and source-backed")
        if not self.unique_target_budget <= self.channel_budget:
            raise ValueError("candidate budget cannot exceed channel overfetch")
        version = next(
            p.effective_version for p in self.inputs.passages if p.passage_id == self.usage_id
        )
        inventory = source_definition_inventory(
            self.inputs, target_ids=self.target_ids, effective_version=version
        )
        if inventory.inventory_id != self.inputs.inventory_id:
            raise ValueError("automatic definition inventory must be frozen before model execution")
        if len(self.target_ids) + 1 > E5.max_items:
            raise ValueError("automatic definition inventory exceeds owned encoder bound")
        return self


def applicability_pack(prepared) -> GlinerPack:
    """Descriptions and closed labels come from the bound semantic release."""
    vocabulary = next(
        v for v in prepared.vocabularies if v.enum == "StructuralDefinitionReadingOutcomeValue"
    )
    declaration = next(
        r
        for r in prepared.registry_rows
        if r.kind == "enum_definition" and r.name == vocabulary.enum
    )
    members = json.loads(declaration.body)["permissible_values"]
    labels = {
        m.value: members[m.value].get("description") or m.value.replace("_", " ")
        for m in vocabulary.members
    }
    return GlinerPack.from_declaration(
        prepared.release_id,
        {"classifications": [{"task": "applicability", "labels": labels}]},
        version="native-combined-v2",
    )


def pair_input(
    inputs: StructuralInput, usage_id: str, target_id: str, pack: GlinerPack
) -> GlinerInput:
    passages = {p.passage_id: p for p in inputs.passages}
    usage, target = passages[usage_id], passages[target_id]
    text = (
        "SOURCE USAGE (assess the meaning invoked here):\n"
        + usage.text
        + "\nTARGET PASSAGE (classify its applicability to that source usage):\n"
        + target.text
        + "\nQuestion: "
        + inputs.question
        + "\nScope: "
        + inputs.scope
        + "\nUsage scope/version: "
        + usage.scope
        + " / "
        + str(usage.effective_version)
        + "\nTarget scope/version: "
        + target.scope
        + " / "
        + str(target.effective_version)
        + "\nChoose the target's source-grounded relationship, not topical similarity."
    )
    digest = sha256(
        canonical_bytes(
            dict(usage=usage.identity, target=target.identity, text=text, pack=pack.fingerprint)
        )
    ).hexdigest()
    return GlinerInput("definition-pair:" + digest, digest, text)


def decode_applicability(
    raw, *, target_id: str, usage_id: str, allowed: frozenset[str]
) -> DefinitionReading:
    value = raw.get("applicability") if isinstance(raw, dict) else None
    label = value.get("label") if isinstance(value, dict) else value
    if not isinstance(label, str) or label not in allowed:
        raise GlinerRefused("native applicability output has no valid declared category")
    return DefinitionReading.model_validate(
        dict(
            target_id=target_id,
            outcome=label,
            evidence=(usage_id, target_id),
            reason=(
                "Native fixed-list source-pair classification; "
                "independent source support remains unassessed."
            ),
        )
    )


class DefinitionApplicabilityMethod:
    name = "structure.definitions"
    version = "1"
    family = MethodFamily.RESOLVE
    unit_type = TaskUnitType.RUN
    tier = MethodTier.ENCODER
    confidence_source = None
    Config = DefinitionApplicabilityConfig
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    def __init__(self):
        self._worker: GlinerWorker | None = None

    def close(self):
        if self._worker is not None:
            self._worker.close()
        self._worker = None

    def select(self, run, cfg):
        return (
            (
                UnitRef(
                    TaskUnitType.RUN,
                    unit_key="definition:" + cfg.inputs.identity + ":" + cfg.usage_id,
                ),
            )
            if cfg.inputs is not None
            else ()
        )

    def input_digest(self, unit, cfg):
        return Digest(canonical_bytes(cfg.model_dump(mode="json", exclude_none=True)))

    def run(self, units, cfg, ctx):
        if cfg.inputs is None or cfg.profile is None or cfg.usage_id is None:
            raise ValueError("automatic definition task requires complete configured inputs")
        # One short read validates the original complete foreign-source frame. Its
        # snapshot is settled before either owned model starts.
        ctx.check_active()
        ctx.reader.validate_structural_inputs(cfg.inputs)
        ctx.check_active()
        passages = {p.passage_id: p for p in cfg.inputs.passages}
        usage = passages[cfg.usage_id]
        inventory = source_definition_inventory(
            cfg.inputs, target_ids=cfg.target_ids, effective_version=usage.effective_version
        )
        contexts = [
            ContextInput(
                cfg.usage_id,
                "source-passage:" + usage.identity,
                "query",
                usage.text,
                usage.text,
                0,
                len(usage.text),
                parent=usage.parent or "",
            )
        ]
        for target in inventory.targets:
            contexts.append(
                ContextInput(
                    target.target_id,
                    target.source_binding,
                    "document",
                    target.label,
                    target.description,
                    0,
                    len(target.label),
                    parent=target.parent or "",
                    type_name=target.type_name,
                    representation_digest=target.representation_digest,
                )
            )
        encoded = encode_contexts(contexts, E5, check_active=ctx.check_active)
        vectors = {v.object_id: v for v in encoded.vectors}
        candidates = ctx.reader.contextual_candidates(
            occurrence_id=cfg.usage_id,
            query=vectors[cfg.usage_id],
            inventory=inventory,
            target_vectors=tuple(vectors[t.target_id] for t in inventory.targets),
            lexical_query=usage.text,
            dimension=E5.dimension,
            budget=cfg.unique_target_budget,
            channel_budget=cfg.channel_budget,
        )
        retrieval = enrichment_report(
            profiles=(E5,),
            vectors=encoded.vectors,
            inventories=(inventory,),
            candidate_lists=(candidates,),
        )
        pack = applicability_pack(ctx.reader.prepared)
        if self._worker is None:
            self._worker = GlinerWorker(cfg.profile)
        elif self._worker.profile.fingerprint != cfg.profile.fingerprint:
            raise GlinerRefused("one automatic definition owner cannot switch provider profile")
        readings, raw_reports, stages = [], [], []
        targets = tuple(c.target_id for c in candidates.candidates)
        allowed = ctx.reader.prepared.enum_members("StructuralDefinitionReadingOutcomeValue")
        for start in range(0, len(targets), cfg.profile.max_batch):
            selected = targets[start : start + cfg.profile.max_batch]
            requests = tuple(pair_input(cfg.inputs, cfg.usage_id, t, pack) for t in selected)
            ctx.check_active()
            try:
                replies = self._worker.extract(
                    pack,
                    requests,
                    threshold=0.5,
                    overlap_policy="flat",
                    check_active=ctx.check_active,
                )
            except (GlinerRefused, GlinerWorkerError, ValueError, TimeoutError, OSError) as error:
                ctx.check_active()
                stages.append(
                    dict(
                        outcome="failed",
                        targets=selected,
                        error_type=type(error).__name__,
                        error=str(error),
                    )
                )
                if self._worker.closed:
                    remaining = targets[start + len(selected) :]
                    if remaining:
                        stages.append(
                            dict(
                                outcome="not_run",
                                targets=remaining,
                                reason="native owner retired after failure",
                            )
                        )
                    break
                continue
            for target, reply in zip(selected, replies, strict=True):
                raw_reports.append(dict(target_id=target, **asdict(reply)))
                try:
                    reading = decode_applicability(
                        reply.raw, target_id=target, usage_id=cfg.usage_id, allowed=allowed
                    )
                except GlinerRefused as error:
                    stages.append(dict(outcome="failed", targets=(target,), reason=str(error)))
                else:
                    readings.append(reading)
                    stages.append(
                        dict(outcome="succeeded", targets=(target,), category=reading.outcome)
                    )
        ctx.check_active()
        report = definition_applicability(
            cfg.inputs,
            usage_id=cfg.usage_id,
            candidate_list_id=candidates.list_id,
            eligible_targets=inventory.target_ids,
            candidate_targets=targets,
            readings=readings,
        )
        report = report.model_copy(update={"retrieval_report": retrieval})
        detail = dict(
            version="automatic-definition-applicability-1",
            standing="unassessed_model_observations",
            native_options=dict(
                operation="batch_extract",
                threshold=0.5,
                overlap_policy="flat",
                include_spans=True,
                include_confidence=True,
                max_len=None,
            ),
            nomination=dict(outcome="succeeded", candidate_list_id=candidates.list_id),
            classification_stages=stages,
            raw_reports=raw_reports,
            profile=cfg.model_dump(mode="json")["profile"],
            profile_fingerprint=cfg.profile.fingerprint,
            schema_declaration=pack.declaration_json,
            pack_fingerprint=pack.fingerprint,
            encoder_implementation=encoded.implementation,
            encoder_inputs=[asdict(i) for i in encoded.inputs],
        )
        detail = RootModel[dict[str, JsonValue]].model_validate_json(canonical_bytes(detail)).root
        return tuple(
            UnitResult(
                ref=unit.ref,
                outcome=ObservationOutcome.PRODUCED,
                structural_product=report.model_dump(mode="json"),
                parse_detail=detail,
            )
            for unit in units
        )
