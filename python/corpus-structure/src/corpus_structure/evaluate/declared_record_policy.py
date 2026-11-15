"""Protected complete-reading judgments over exact current declared selections.

These DTOs carry retained evidence, not authority. Native custody authenticates the
original selections, independent references and actual grade producer. Feature-fit
labels remain protected and are exposed only through the dedicated fitter capability.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Annotated, Literal, Self

from pydantic import Field, FiniteFloat, model_validator

from corpus_structure.semantic.declared_structural_references import (
    DeclaredProductRef,
    DeclaredStructuralSource,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.record_policy import (
    Digest, Family, FeatureInstance, FitDiagnostics, FrozenContract, Nonempty,
    PolicyApplicability, RecordAcceptanceInstance, RecordAlgorithm, RecordFeatures, reading_potential,
)
from corpus_structure.semantic.record_policy_authority import (
    DdoFittedRecordPolicy, DdoRecordPolicyApplicability, NAMESPACE,
)

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
        pass_addresses = {(row.reference.product_id, row.reference.member_id) for row in self.reference_passes}
        if len(pass_addresses) != 3:
            raise ValueError("A/B/C references require distinct retained pass identities")
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


class DdoRecordGradeSelection(FrozenContract):
    """Exact evaluator-acquired selected grade, reacquired by the fitter principal."""

    project_id: Nonempty
    demand_id: Nonempty
    read_id: Nonempty
    use_id: Nonempty
    derivation_id: Nonempty
    product_id: Nonempty
    expected_cut: Nonempty
    frame_digest: Digest


class DdoRecordFitSpecification(FrozenContract):
    feature_selection: DdoRecordGradeSelection
    frozen_feature: FeatureInstance
    applicability: DdoRecordPolicyApplicability
    family_contract: Nonempty
    reading_recipe: Nonempty
    event_procedure: Nonempty
    assumptions: Nonempty
    threshold: Annotated[FiniteFloat, Field(gt=0, le=1)]
    threshold_procedure: Nonempty


@dataclass(frozen=True)
class DeclaredRecordPolicyFitOutcome:
    diagnostics: tuple[FitDiagnostics, ...]
    fitted: DdoFittedRecordPolicy | None = None


def _fitting_frame(grade: DdoRecordGrade, assumptions: str):
    from .record_fitting import FittingFrame

    frame = grade.frame
    return FittingFrame(
        frame_digest=grade.frame_digest, reference_digest=frame.reference_digest,
        coverage_digest=sha256(canonical_bytes([
            row.model_dump(mode="json") for row in frame.coverage
        ])).hexdigest(),
        event_ids=tuple(row.interpretation_id for row in frame.events),
        provenance="declared-selected-complete-record-grade-1", assumptions=assumptions,
    )


def _fit_feature_value(grade: DdoRecordGrade, *, algorithm: RecordAlgorithm, assumptions: str):
    """Pure numerical step; the caller authenticates the grade using the fit capability."""
    from .record_fitting import FeatureFitObservation, WholeReadingLabel, fit_whole_reading_features

    frame = grade.frame
    if frame.partition != "feature_fit":
        raise ValueError("feature fitting requires the distinct feature_fit partition")
    observations = tuple(FeatureFitObservation(
        features=row.features, label=WholeReadingLabel(
            event_id=row.interpretation_id, origin_group=row.origin_group,
            correct=row.correct, sample_weight=row.sample_weight,
        ),
    ) for row in frame.events)
    return fit_whole_reading_features(
        observations, algorithm=algorithm,
        applicability=PolicyApplicability(
            release_id=frame.prediction_release_id, family=frame.family,
            subset=frame.subset, assumptions=assumptions,
        ),
        frame=_fitting_frame(grade, assumptions),
    )


def reacquire_record_feature_grade(connection, selection: DdoRecordGradeSelection) -> DdoRecordGrade:
    """Use the actual restricted native fitter capability; never a general read fallback."""
    from corpus_structure.semantic.record_policy_native import read_record_feature_fit_frame

    result = read_record_feature_fit_frame(connection, **selection.model_dump(mode="python"))
    if (result["product_id"], result["derivation_id"]) != (selection.product_id, selection.derivation_id):
        raise ValueError("native fitter result differs from selected grade product or derivation")
    grade = DdoRecordGrade.model_validate_json(canonical_bytes(result["frame"]))
    if (grade.frame.partition, grade.frame.project_id, grade.frame_digest) != (
        "feature_fit", selection.project_id, selection.frame_digest,
    ):
        raise ValueError("native fitter result differs from exact feature-fit frame")
    return grade


def fit_record_feature_frame(connection, selection: DdoRecordGradeSelection, *, algorithm: RecordAlgorithm, assumptions: str):
    """Fit preliminary parameters through the dedicated actual fitter connection.

    The returned parameters may be authored into the real reading policy so that a
    separate calibration population can be produced. They grant no admission authority;
    final fitting recomputes the exact frozen instance from the same immutable grade.
    """
    if not assumptions.strip():
        raise ValueError("feature fitting requires explicit conditioning assumptions")
    grade = reacquire_record_feature_grade(connection, selection)
    return _fit_feature_value(grade, algorithm=algorithm, assumptions=assumptions)


def fit_declared_record_policy(
    feature_grade: DdoRecordGrade, calibration_grade: DdoRecordGrade,
    specification: DdoRecordFitSpecification,
) -> DeclaredRecordPolicyFitOutcome:
    """Pure exact-instance recomputation and separately held-out event calibration.

    The acquired family port authenticates the selected grade bodies first. This
    function does not grant native authority merely from the possession of DTOs.
    Original release identities remain attribution; calibration may use a later
    compatible release with the same consumed family contract and reading recipe.
    """
    from .record_fitting import FinalEventObservation, WholeReadingLabel, fit_final_event_calibration

    first, second = feature_grade.frame, calibration_grade.frame
    if (first.partition, second.partition) != ("feature_fit", "final_event_calibration"):
        raise ValueError("feature-fit and final-event calibration require separate declared partitions")
    expected = (specification.applicability.project_id, specification.family_contract, specification.reading_recipe)
    if any((frame.project_id, frame.family_contract, frame.reading_recipe) != expected for frame in (first, second)):
        raise ValueError("fitting frames differ from the exact project, consumed family contract or reading recipe")
    if (first.family, first.subset, first.rubric_digest) != (second.family, second.subset, second.rubric_digest):
        raise ValueError("calibration changes the declared family, subset or grading rubric")
    if (feature_grade.frame_digest == calibration_grade.frame_digest
            or first.reference_digest == second.reference_digest
            or feature_grade.frame_digest not in second.held_out_from):
        raise ValueError("calibration requires a separately held-out frozen frame and reference")
    groups = [{row.origin_group for row in frame.origin_groups} for frame in (first, second)]
    origins = [{source.original_source for row in frame.origin_groups for source in (
        row.source, *row.copied_from,
    )} for frame in (first, second)]
    if groups[0] & groups[1] or origins[0] & origins[1]:
        raise ValueError("calibration shares a declared origin group or known copied source with feature fitting")
    feature = specification.frozen_feature
    fitted = _fit_feature_value(feature_grade, algorithm=feature.algorithm, assumptions=specification.assumptions)
    if fitted.instance is None:
        return DeclaredRecordPolicyFitOutcome((fitted.diagnostics,))
    if canonical_bytes(fitted.instance.model_dump(mode="json")) != canonical_bytes(feature.model_dump(mode="json")):
        raise ValueError("frozen feature instance differs from actual immutable feature-fit recomputation")
    observations = []
    for row in second.events:
        event = row.final_event
        if event is None or (event.feature_instance_digest, event.event_procedure) != (
            feature.digest, specification.event_procedure,
        ):
            raise ValueError("calibration event differs from actual frozen predictor or event procedure")
        vector = row.features
        if (vector.names != feature.parameters.names
                or vector.feature_signature != feature.parameters.feature_signature
                or any(value is None for value in vector.values)):
            raise ValueError("calibration features differ from the frozen ordered predictor")
        potential = reading_potential(feature.parameters, tuple(value for value in vector.values if value is not None))
        if event.final_event_score != potential:
            raise ValueError("calibration sealed score differs from the actual frozen predictor")
        observations.append(FinalEventObservation(
            feature_instance_digest=feature.digest, event_procedure=event.event_procedure,
            final_event_score=event.final_event_score, label=WholeReadingLabel(
                event_id=row.interpretation_id, origin_group=row.origin_group,
                correct=row.correct, sample_weight=row.sample_weight,
            ),
        ))
    calibration = fit_final_event_calibration(
        observations, feature=feature, frame=_fitting_frame(calibration_grade, specification.assumptions),
        event_procedure=specification.event_procedure,
    )
    diagnostics = (fitted.diagnostics, calibration.diagnostics)
    if calibration.calibration is None:
        return DeclaredRecordPolicyFitOutcome(diagnostics)
    instance = RecordAcceptanceInstance(
        feature=feature, calibration=calibration.calibration, threshold=specification.threshold,
        threshold_procedure=specification.threshold_procedure,
        conditioning_assumptions=specification.assumptions,
    )
    basis = sha256(canonical_bytes([
        feature_grade.frame_digest, calibration_grade.frame_digest,
        specification.model_dump(mode="json"),
    ])).hexdigest()
    return DeclaredRecordPolicyFitOutcome(diagnostics, DdoFittedRecordPolicy.from_instance(
        instance, family_contract=specification.family_contract,
        reading_recipe=specification.reading_recipe, judgment_basis_digest=basis,
        applicability=specification.applicability,
    ))


class DdoProtectedRecordPolicyContracts(FrozenContract):
    """One schema root owns the entire protected nominal namespace."""

    grade: DdoRecordGrade
    fitted: DdoFittedRecordPolicy
    specification: DdoRecordFitSpecification


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
