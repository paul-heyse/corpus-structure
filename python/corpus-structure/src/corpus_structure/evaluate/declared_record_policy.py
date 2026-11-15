"""Protected complete-reading judgments over exact current declared selections.

These DTOs carry retained evidence, not authority. Native custody authenticates the
original selections, independent references and actual grade producer. Feature-fit
labels remain protected and are exposed only through the dedicated fitter capability.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Annotated, Literal, Self

from pydantic import Field, FiniteFloat, model_validator

from corpus_structure.semantic.declared_structural_references import (
    DeclaredProductRef,
    DeclaredStructuralSource,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.record_policy import (
    Digest, Family, FrozenContract, Nonempty, RecordFeatures,
)
from corpus_structure.semantic.record_policy_authority import DdoFittedRecordPolicy, NAMESPACE

Partition = Literal["development", "feature_fit", "final_event_calibration", "final_assessment"]
PROTECTED_NAMESPACE = NAMESPACE + "protected/"


class DdoRecordReferencePass(FrozenContract):
    """Attribution to retained source-only A/B authorship and C adjudication.

    A metadata value cannot establish independence. The selected reader checks the
    actual protected reference bodies, original source cut and exposure history.
    Answers are deliberately absent from a grade's fitter-visible frame.
    """

    reference: DeclaredProductRef
    pass_kind: Literal["A", "B", "C"]
    author: Nonempty
    content_digest: Digest
    question_digest: Digest
    rubric_digest: Digest
    source_cut_id: Nonempty
    exposed_outputs: tuple[DeclaredProductRef, ...] = ()
    adjudicates: tuple[Digest, ...] = ()

    @model_validator(mode="after")
    def source_only_pass(self) -> Self:
        if self.exposed_outputs:
            raise ValueError("source-only record reference cannot have exposed prediction outputs")
        if self.pass_kind in {"A", "B"} and self.adjudicates:
            raise ValueError("independent A/B pass cannot adjudicate another answer")
        if self.pass_kind == "C" and (
            len(self.adjudicates) != 2 or len(set(self.adjudicates)) != 2
        ):
            raise ValueError("C adjudication requires two distinct retained independent answers")
        return self


class DdoRecordOrigin(FrozenContract):
    source: DeclaredStructuralSource
    origin_group: Nonempty
    copied_from: tuple[DeclaredStructuralSource, ...] = ()

    @model_validator(mode="after")
    def unique_origins(self) -> Self:
        if len(set(row.identity for row in self.copied_from)) != len(self.copied_from):
            raise ValueError("record origin repeats a copied source")
        return self


class DdoRecordFinalEvent(FrozenContract):
    """Exact completed producer score; a compatibility potential, never a label."""

    feature_instance_digest: Digest
    feature_input_digest: Digest
    event_procedure: Nonempty
    final_event_score: FiniteFloat
    outcome: Literal["completed"] = "completed"


class DdoRecordGradeEvent(FrozenContract):
    record_id: Nonempty
    interpretation_id: Nonempty
    reading: DeclaredProductRef
    source: DeclaredStructuralSource
    source_release_id: Nonempty
    derivation_id: Nonempty
    reading_recipe: Nonempty
    features: RecordFeatures
    correct: bool
    origin_group: Nonempty
    sample_weight: Annotated[FiniteFloat, Field(gt=0)] = 1.0
    final_event: DdoRecordFinalEvent | None = None

    @model_validator(mode="after")
    def exact_reading(self) -> Self:
        if (self.features.record_id, self.features.interpretation_id, self.features.release_id) != (
            self.record_id, self.interpretation_id, self.source_release_id,
        ):
            raise ValueError("grade features differ from the original scored reading identity")
        if self.reading.context != {
            "project_id": self.source.project_id, "subject": self.source.subject,
            "subject_definition": self.source.subject_definition,
            "original_source": self.source.original_source,
            "analyzed_scope_meaning": self.source.analyzed_scope_meaning,
        }:
            raise ValueError("grade reading differs from its complete source context")
        if self.final_event is not None and self.final_event.feature_input_digest != self.features.input_digest:
            raise ValueError("sealed final event differs from the original feature input")
        return self


class DdoRecordCoverage(FrozenContract):
    """A source opportunity, including absence of output, separate from scored events."""

    source: DeclaredStructuralSource
    outputs: tuple[DeclaredProductRef, ...]
    outcome: Literal["completed", "no_output", "failed"]
    event_ids: tuple[Nonempty, ...]

    @model_validator(mode="after")
    def exact_opportunity(self) -> Self:
        addresses = [(row.product_id, row.member_id) for row in self.outputs]
        if len(set(addresses)) != len(addresses) or len(set(self.event_ids)) != len(self.event_ids):
            raise ValueError("record coverage repeats an output or eligible event")
        if self.outcome != "completed" and self.event_ids:
            raise ValueError("no-output or failed coverage cannot manufacture scored events")
        if self.outcome == "no_output" and self.outputs:
            raise ValueError("no-output coverage cannot contain a prediction product")
        return self


class DdoRecordGradeFrame(FrozenContract):
    partition: Partition
    project_id: Nonempty
    family: Family
    family_contract: Nonempty
    reading_recipe: Nonempty
    subset: Nonempty
    question_digest: Digest
    rubric_digest: Digest
    reference_digest: Digest
    source_cut_id: Nonempty
    prediction_cut_id: Nonempty
    source_release_id: Nonempty
    prediction_release_id: Nonempty
    sources: Annotated[tuple[DeclaredStructuralSource, ...], Field(min_length=1)]
    reference_passes: tuple[DdoRecordReferencePass, DdoRecordReferencePass, DdoRecordReferencePass]
    events: tuple[DdoRecordGradeEvent, ...]
    coverage: Annotated[tuple[DdoRecordCoverage, ...], Field(min_length=1)]
    origin_groups: Annotated[tuple[DdoRecordOrigin, ...], Field(min_length=1)]
    held_out_from: tuple[Digest, ...] = ()

    @model_validator(mode="after")
    def complete_frame(self) -> Self:
        sources = {row.identity: row for row in self.sources}
        if len(sources) != len(self.sources) or any(row.project_id != self.project_id for row in self.sources):
            raise ValueError("grade requires unique sources in its exact project")
        passes = {row.pass_kind: row for row in self.reference_passes}
        if len(passes) != 3 or set(passes) != {"A", "B", "C"}:
            raise ValueError("grade requires exact independent A/B and C adjudication")
        if passes["A"].author == passes["B"].author:
            raise ValueError("A/B record references require distinct independent authors")
        if set(passes["C"].adjudicates) != {passes["A"].content_digest, passes["B"].content_digest}:
            raise ValueError("C does not adjudicate the exact retained A/B answers")
        if any((row.question_digest, row.rubric_digest, row.source_cut_id, row.reference.project_id) != (
            self.question_digest, self.rubric_digest, self.source_cut_id, self.project_id,
        ) for row in self.reference_passes):
            raise ValueError("reference passes differ from the frozen question, rubric or source cut")
        coverage = {row.source.identity: row for row in self.coverage}
        origins = {row.source.identity: row for row in self.origin_groups}
        if (len(coverage) != len(self.coverage) or len(origins) != len(self.origin_groups)
                or set(coverage) != set(sources) or set(origins) != set(sources)):
            raise ValueError("coverage and origins must retain the exact complete source population")
        event_ids = tuple(row.interpretation_id for row in self.events)
        covered_ids = tuple(event for row in self.coverage for event in row.event_ids)
        if len(set(event_ids)) != len(event_ids) or set(event_ids) != set(covered_ids) or len(covered_ids) != len(event_ids):
            raise ValueError("grade events differ from the complete eligible/scored coverage frame")
        for row in self.events:
            source = row.source.identity
            if (source not in sources or row.interpretation_id not in coverage[source].event_ids
                    or row.reading not in coverage[source].outputs
                    or row.origin_group != origins[source].origin_group
                    or (row.features.family, row.source_release_id, row.reading_recipe) != (
                        self.family, self.prediction_release_id, self.reading_recipe)):
                raise ValueError("grade event differs from actual source, output, origin or producer context")
            if self.partition == "final_event_calibration" and row.final_event is None:
                raise ValueError("calibration grade requires every eligible completed final event")
        if len(set(self.held_out_from)) != len(self.held_out_from):
            raise ValueError("grade repeats a held-out frame identity")
        return self


class DdoRecordGrade(FrozenContract):
    version: Literal["record-grade-1"] = "record-grade-1"
    frame: DdoRecordGradeFrame
    frame_canonical_json: Nonempty
    frame_digest: Digest

    @model_validator(mode="after")
    def canonical_frame_custody(self) -> Self:
        content = canonical_bytes(self.frame.model_dump(mode="json"))
        if content.decode() != self.frame_canonical_json or sha256(content).hexdigest() != self.frame_digest:
            raise ValueError("grade frame canonical bytes or digest differ from their typed value")
        return self

    @classmethod
    def from_frame(cls, frame: DdoRecordGradeFrame) -> Self:
        content = canonical_bytes(frame.model_dump(mode="json"))
        return cls(frame=frame, frame_canonical_json=content.decode(), frame_digest=sha256(content).hexdigest())


class DdoProtectedRecordPolicyContracts(FrozenContract):
    """One schema root owns the entire protected nominal namespace."""

    grade: DdoRecordGrade
    fitted: DdoFittedRecordPolicy


def protected_record_policy_kind_declarations():
    from corpus_structure.semantic.data_operation_model import MODEL_VERSION
    from corpus_structure.semantic.nominal_schema_kinds import nominal_schema_kinds
    from corpus_structure.semantic.types import SourceArtifact

    return SourceArtifact("record-policy/protected-kinds.json", canonical_bytes({
        "version": MODEL_VERSION,
        "kinds": [dict(row, universe="evaluator") for row in nominal_schema_kinds(
            DdoProtectedRecordPolicyContracts.model_json_schema(),
            namespace=PROTECTED_NAMESPACE, root_name="DdoProtectedRecordPolicyContracts",
        )],
    }))
