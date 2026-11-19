"""Protected complete-reading judgments over exact current declared selections.

These DTOs carry retained evidence, not authority. Native custody authenticates the
original selections, independent references and actual grade producer. Feature-fit
labels remain protected and are exposed only through the dedicated fitter capability.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Annotated, Any, Literal, Self

from pydantic import Field, FiniteFloat, model_validator

from corpus_structure.semantic.declared_structural_references import (
    DeclaredProductRef,
    DeclaredStructuralSource,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.record_policy import (
    Digest,
    Family,
    FeatureInstance,
    FitDiagnostics,
    FrozenContract,
    Nonempty,
    PolicyApplicability,
    RecordAcceptanceInstance,
    RecordAlgorithm,
    RecordFeatures,
    reading_potential,
)
from corpus_structure.semantic.record_policy_authority import (
    NAMESPACE,
    DdoFittedRecordPolicy,
    DdoRecordPolicyApplicability,
)
from corpus_structure.semantic.refusals import SemanticRefusal

Partition = Literal["development", "feature_fit", "final_event_calibration", "final_assessment"]
PROTECTED_NAMESPACE = NAMESPACE + "protected/"


class DdoRecordReferencePass(FrozenContract):
    """Attribution to retained source-only A/B authorship and C adjudication.

    A metadata value cannot establish independence. The selected reader checks the
    actual protected reference bodies, original source cut and exposure history.
    Answers are deliberately absent from a grade's fitter-visible frame.
    """

    reference: DeclaredProductRef
    source: DeclaredStructuralSource
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
            raise SemanticRefusal(
                "source-only record reference cannot have exposed prediction outputs"
            )
        if self.pass_kind in {"A", "B"} and self.adjudicates:
            raise SemanticRefusal("independent A/B pass cannot adjudicate another answer")
        if self.pass_kind == "C" and (
            len(self.adjudicates) != 2 or len(set(self.adjudicates)) != 2
        ):
            raise SemanticRefusal(
                "C adjudication requires two distinct retained independent answers"
            )
        return self


class DdoRecordOrigin(FrozenContract):
    source: DeclaredStructuralSource
    origin_group: Nonempty
    copied_from: tuple[DeclaredStructuralSource, ...] = ()

    @model_validator(mode="after")
    def unique_origins(self) -> Self:
        if len(set(row.identity for row in self.copied_from)) != len(self.copied_from):
            raise SemanticRefusal("record origin repeats a copied source")
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
            self.record_id,
            self.interpretation_id,
            self.source_release_id,
        ):
            raise SemanticRefusal("grade features differ from the original scored reading identity")
        if self.reading.context != {
            "project_id": self.source.project_id,
            "subject": self.source.subject,
            "subject_definition": self.source.subject_definition,
            "original_source": self.source.original_source,
            "analyzed_scope_meaning": self.source.analyzed_scope_meaning,
        }:
            raise SemanticRefusal("grade reading differs from its complete source context")
        if (
            self.final_event is not None
            and self.final_event.feature_input_digest != self.features.input_digest
        ):
            raise SemanticRefusal("sealed final event differs from the original feature input")
        return self


class DdoRecordCoverage(FrozenContract):
    """A source opportunity, including absence of output, separate from scored events."""

    source: DeclaredStructuralSource
    outputs: tuple[DeclaredProductRef, ...]
    outcome: Literal["completed", "no_output", "failed"]
    event_ids: tuple[Nonempty, ...]
    failure_request_id: Nonempty | None = None
    failure_use_id: Nonempty | None = None

    @model_validator(mode="after")
    def exact_opportunity(self) -> Self:
        addresses = [(row.product_id, row.member_id) for row in self.outputs]
        if len(set(addresses)) != len(addresses) or len(set(self.event_ids)) != len(self.event_ids):
            raise SemanticRefusal("record coverage repeats an output or eligible event")
        if self.outcome != "completed" and self.event_ids:
            raise SemanticRefusal("no-output or failed coverage cannot manufacture scored events")
        if (self.outcome == "failed") != (
            self.failure_request_id is not None and self.failure_use_id is not None
        ):
            raise SemanticRefusal(
                "failed source coverage requires its actual native request and selected use"
            )
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
    reference_passes: Annotated[tuple[DdoRecordReferencePass, ...], Field(min_length=3)]
    events: tuple[DdoRecordGradeEvent, ...]
    coverage: Annotated[tuple[DdoRecordCoverage, ...], Field(min_length=1)]
    origin_groups: Annotated[tuple[DdoRecordOrigin, ...], Field(min_length=1)]
    held_out_from: tuple[Digest, ...] = ()

    @model_validator(mode="after")
    def complete_frame(self) -> Self:
        sources = {row.identity: row for row in self.sources}
        if len(sources) != len(self.sources) or any(
            row.project_id != self.project_id for row in self.sources
        ):
            raise SemanticRefusal("grade requires unique sources in its exact project")
        groups = {}
        for row in self.reference_passes:
            groups.setdefault(row.question_digest, []).append(row)
        question_sources = []
        for rows in groups.values():
            passes = {row.pass_kind: row for row in rows}
            if len(rows) != 3 or set(passes) != {"A", "B", "C"}:
                raise SemanticRefusal(
                    "grade requires exact independent A/B and C adjudication for every question"
                )
            if len({(row.reference.product_id, row.reference.member_id) for row in rows}) != 3:
                raise SemanticRefusal("A/B/C references require distinct retained pass identities")
            if set(passes["C"].adjudicates) != {
                passes["A"].content_digest,
                passes["B"].content_digest,
            }:
                raise SemanticRefusal("C does not adjudicate the exact retained A/B answers")
            source = passes["C"].source
            if any(
                (row.rubric_digest, row.source_cut_id, row.reference.project_id, row.source)
                != (
                    self.rubric_digest,
                    self.source_cut_id,
                    self.project_id,
                    source,
                )
                for row in rows
            ):
                raise SemanticRefusal(
                    "reference passes differ from the frozen rubric, source or cut"
                )
            question_sources.append(source)
        if tuple(question_sources) != self.sources:
            raise SemanticRefusal(
                "reference questions differ from the exact ordered source population"
            )
        coverage = {row.source.identity: row for row in self.coverage}
        origins = {row.source.identity: row for row in self.origin_groups}
        if (
            len(coverage) != len(self.coverage)
            or len(origins) != len(self.origin_groups)
            or set(coverage) != set(sources)
            or set(origins) != set(sources)
        ):
            raise SemanticRefusal(
                "coverage and origins must retain the exact complete source population"
            )
        event_ids = tuple(row.interpretation_id for row in self.events)
        covered_ids = tuple(event for row in self.coverage for event in row.event_ids)
        if (
            len(set(event_ids)) != len(event_ids)
            or set(event_ids) != set(covered_ids)
            or len(covered_ids) != len(event_ids)
        ):
            raise SemanticRefusal(
                "grade events differ from the complete eligible/scored coverage frame"
            )
        for row in self.events:
            source = row.source.identity
            if (
                source not in sources
                or row.interpretation_id not in coverage[source].event_ids
                or row.reading not in coverage[source].outputs
                or row.origin_group != origins[source].origin_group
                or (row.features.family, row.reading_recipe) != (self.family, self.reading_recipe)
            ):
                raise SemanticRefusal(
                    "grade event differs from actual source, output, origin or producer context"
                )
            if self.partition == "final_event_calibration" and row.final_event is None:
                raise SemanticRefusal(
                    "calibration grade requires every eligible completed final event"
                )
        if len(set(self.held_out_from)) != len(self.held_out_from):
            raise SemanticRefusal("grade repeats a held-out frame identity")
        return self


class DdoRecordGrade(FrozenContract):
    version: Literal["record-grade-1"] = "record-grade-1"
    frame: DdoRecordGradeFrame
    frame_canonical_json: Nonempty
    frame_digest: Digest

    @model_validator(mode="after")
    def canonical_frame_custody(self) -> Self:
        content = canonical_bytes(self.frame.model_dump(mode="json"))
        if (
            content.decode() != self.frame_canonical_json
            or sha256(content).hexdigest() != self.frame_digest
        ):
            raise SemanticRefusal(
                "grade frame canonical bytes or digest differ from their typed value"
            )
        return self

    @classmethod
    def from_selected_body(cls, body: dict) -> Self:
        """Check an exact tagged selected-body projection against captured frame text.

        This path requires preserved semantic number meaning. The separate native
        fitter wrapper owns restoration of its lossy JSONB projection after native
        authentication; that value must not pass through this stricter path.
        """
        from corpus_structure.semantic.data_operation_values import semantic_value

        frame = DdoRecordGradeFrame.model_validate_json(body["frame_canonical_json"])
        original = frame.model_dump(mode="json")
        if semantic_value(original) != semantic_value(body["frame"]):
            raise SemanticRefusal(
                "projected grade frame differs from authenticated captured frame meaning"
            )
        return cls.model_validate_json(canonical_bytes({**body, "frame": original}))

    @classmethod
    def from_frame(cls, frame: DdoRecordGradeFrame) -> Self:
        content = canonical_bytes(frame.model_dump(mode="json"))
        return cls(
            frame=frame,
            frame_canonical_json=content.decode(),
            frame_digest=sha256(content).hexdigest(),
        )


def _canonical_json_value(content: str):
    import json

    value = json.loads(content)
    if canonical_bytes(value).decode() != content:
        raise SemanticRefusal("protected record payload must retain its exact canonical JSON")
    return value


class DdoRecordReferenceQuestion(FrozenContract):
    """Source-only frozen source, region, coordinate and rubric before predictions."""

    project_id: Nonempty
    partition: Partition
    family: Family
    family_contract: Nonempty
    reading_recipe: Nonempty
    subset: Nonempty
    source: DeclaredStructuralSource
    source_release_id: Nonempty
    source_cut_id: Nonempty
    source_cut_canonical_json: Nonempty
    frame_canonical_json: Nonempty
    coordinate_texts_canonical_json: Nonempty
    rubric: Nonempty
    origin_group: Nonempty
    copied_from: tuple[DeclaredStructuralSource, ...] = ()
    held_out_from: tuple[Digest, ...] = ()
    sample_weight: Annotated[FiniteFloat, Field(gt=0)] = 1.0

    @property
    def rubric_digest(self) -> str:
        return sha256(canonical_bytes(self.rubric)).hexdigest()

    @model_validator(mode="after")
    def frozen_source_question(self) -> Self:
        from corpus_structure.semantic.demand_results import CutSelection

        cut = CutSelection(self.source_cut_canonical_json.encode())
        if (cut.identity, cut.record["project_id"], cut.record["release_id"]) != (
            self.source_cut_id,
            self.project_id,
            self.source_release_id,
        ) or self.source.project_id != self.project_id:
            raise SemanticRefusal(
                "record question differs from its exact acquired original source cut"
            )
        frame = _canonical_json_value(self.frame_canonical_json)
        coordinates = _canonical_json_value(self.coordinate_texts_canonical_json)
        if not isinstance(frame, dict) or not isinstance(coordinates, list):
            raise SemanticRefusal(
                "record question requires its complete source frame and coordinate list"
            )
        pin = self.source.model_dump(mode="json", exclude_none=True)
        if frame.get("pin") != pin or frame.get("release_id") != self.source_release_id:
            raise SemanticRefusal("record question frame differs from its actual original source")
        for related in frame.get("related_pins", ()):
            DeclaredStructuralSource.model_validate(related)
        if len(set(self.held_out_from)) != len(self.held_out_from):
            raise SemanticRefusal("record question repeats a held-out frame identity")
        return self


class DdoRecordReference(FrozenContract):
    version: Literal["source-only-record-reference-1"] = "source-only-record-reference-1"
    question: DdoRecordReferenceQuestion
    pass_kind: Literal["A", "B", "C"]
    author: Nonempty
    records_canonical_json: Nonempty
    exposed_outputs: tuple[DeclaredProductRef, ...] = ()
    adjudicates: tuple[Digest, ...] = ()

    @model_validator(mode="after")
    def source_only_reading(self) -> Self:
        rows = _canonical_json_value(self.records_canonical_json)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise SemanticRefusal(
                "record reference requires the exact complete independently authored record sequence"
            )
        if self.exposed_outputs:
            raise SemanticRefusal("source-only record references cannot expose prediction outputs")
        if self.pass_kind in {"A", "B"} and self.adjudicates:
            raise SemanticRefusal("independent A/B pass cannot adjudicate another answer")
        if self.pass_kind == "C" and (
            len(self.adjudicates) != 2 or len(set(self.adjudicates)) != 2
        ):
            raise SemanticRefusal("C requires its exact two independent retained answer digests")
        return self


class DdoRecordReferencePopulation(FrozenContract):
    """One genuine independently retained A/B/C pass over a frozen ordered population."""

    version: Literal["source-only-record-reference-population-1"] = (
        "source-only-record-reference-population-1"
    )
    pass_kind: Literal["A", "B", "C"]
    references: Annotated[tuple[DdoRecordReference, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def exact_ordered_population(self) -> Self:
        first = self.references[0].question
        sources = [row.question.source.identity for row in self.references]
        if len(set(sources)) != len(sources) or any(
            row.pass_kind != self.pass_kind for row in self.references
        ):
            raise SemanticRefusal(
                "record reference pass requires its unique ordered source population"
            )
        expected = (
            first.project_id,
            first.partition,
            first.family,
            first.family_contract,
            first.reading_recipe,
            first.subset,
            first.source_cut_id,
            first.source_release_id,
            first.rubric,
        )
        for row in self.references:
            question = row.question
            if (
                question.project_id,
                question.partition,
                question.family,
                question.family_contract,
                question.reading_recipe,
                question.subset,
                question.source_cut_id,
                question.source_release_id,
                question.rubric,
            ) != expected:
                raise SemanticRefusal(
                    "record reference population changes its frozen family, source cut or rubric"
                )
        return self


class DdoRecordReferencePopulationA(DdoRecordReferencePopulation):
    pass_kind: Literal["A"]


class DdoRecordReferencePopulationB(DdoRecordReferencePopulation):
    pass_kind: Literal["B"]


class DdoRecordReferencePopulationC(DdoRecordReferencePopulation):
    pass_kind: Literal["C"]


class DdoRecordPredictionSelection(FrozenContract):
    source: DeclaredStructuralSource
    outcome: Literal["completed", "no_output", "failed"]
    request_id: Nonempty
    obligation_id: Nonempty
    derivation_id: Nonempty | None = None
    use_id: Nonempty
    project_id: Nonempty
    demand_id: Nonempty
    read_id: Nonempty
    product_id: Nonempty | None = None
    expected_cut: Nonempty
    cut_canonical_json: Nonempty

    @model_validator(mode="after")
    def exact_outcome(self) -> Self:
        if self.outcome == "completed" and (self.product_id is None or self.derivation_id is None):
            raise SemanticRefusal(
                "completed prediction requires its actual product and producing episode"
            )
        if self.outcome != "completed" and self.product_id is not None:
            raise SemanticRefusal("absent/failed prediction cannot invent an output product")
        return self


class DdoRecordGradeSpecification(FrozenContract):
    prediction_selections: Annotated[tuple[DdoRecordPredictionSelection, ...], Field(min_length=1)]
    algorithm: RecordAlgorithm


class DdoRecordGradeSelection(FrozenContract):
    """Exact evaluator-acquired selected grade, reacquired by the fitter principal."""

    project_id: Nonempty
    demand_id: Nonempty
    read_id: Nonempty
    use_id: Nonempty
    derivation_id: Nonempty
    product_id: Nonempty
    expected_cut: Nonempty
    cut_canonical_json: Nonempty
    frame_digest: Digest


class DdoRecordFeatureFitRequest(FrozenContract):
    selection: DdoRecordGradeSelection
    algorithm: RecordAlgorithm
    assumptions: Nonempty


class DdoRecordFitSpecification(FrozenContract):
    calibration_selection: DdoRecordGradeSelection
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
        frame_digest=grade.frame_digest,
        reference_digest=frame.reference_digest,
        coverage_digest=sha256(
            canonical_bytes([row.model_dump(mode="json") for row in frame.coverage])
        ).hexdigest(),
        event_ids=tuple(row.interpretation_id for row in frame.events),
        provenance="declared-selected-complete-record-grade-1",
        assumptions=assumptions,
    )


def _fit_feature_value(grade: DdoRecordGrade, *, algorithm: RecordAlgorithm, assumptions: str):
    """Pure numerical step; the caller authenticates the grade using the fit capability."""
    from .record_fitting import FeatureFitObservation, WholeReadingLabel, fit_whole_reading_features

    frame = grade.frame
    if frame.partition != "feature_fit":
        raise SemanticRefusal("feature fitting requires the distinct feature_fit partition")
    observations = tuple(
        FeatureFitObservation(
            features=row.features,
            label=WholeReadingLabel(
                event_id=row.interpretation_id,
                origin_group=row.origin_group,
                correct=row.correct,
                sample_weight=row.sample_weight,
            ),
        )
        for row in frame.events
    )
    return fit_whole_reading_features(
        observations,
        algorithm=algorithm,
        applicability=PolicyApplicability(
            release_id=frame.prediction_release_id,
            family=frame.family,
            subset=frame.subset,
            assumptions=assumptions,
        ),
        frame=_fitting_frame(grade, assumptions),
    )


def reacquire_record_feature_grade(
    connection, selection: DdoRecordGradeSelection
) -> DdoRecordGrade:
    """Use the actual restricted native fitter capability; never a general read fallback."""
    from corpus_structure.semantic.demand_results import CutSelection
    from corpus_structure.semantic.record_policy_native import read_selected_feature_fit_frame

    cut = CutSelection(selection.cut_canonical_json.encode())
    if (cut.identity, cut.record["project_id"], cut.record["demand_id"], cut.record["read_id"]) != (
        selection.expected_cut,
        selection.project_id,
        selection.demand_id,
        selection.read_id,
    ):
        raise SemanticRefusal("fitter selection differs from the original acquired cut bytes")
    values = selection.model_dump(mode="python", exclude={"cut_canonical_json"})
    result = read_selected_feature_fit_frame(
        connection, variant="record-feature-grade", cut=cut, **values
    )
    if (result["product_id"], result["derivation_id"]) != (
        selection.product_id,
        selection.derivation_id,
    ):
        raise SemanticRefusal(
            "native fitter result differs from selected grade product or derivation"
        )
    grade = DdoRecordGrade.model_validate_json(canonical_bytes(result["frame"]))
    if (grade.frame.partition, grade.frame.project_id, grade.frame_digest) != (
        "feature_fit",
        selection.project_id,
        selection.frame_digest,
    ):
        raise SemanticRefusal("native fitter result differs from exact feature-fit frame")
    return grade


def fit_record_feature_frame(
    connection, selection: DdoRecordGradeSelection, *, algorithm: RecordAlgorithm, assumptions: str
):
    """Fit preliminary parameters through the dedicated actual fitter connection.

    The returned parameters may be authored into the real reading policy so that a
    separate calibration population can be produced. They grant no admission authority;
    final fitting recomputes the exact frozen instance from the same immutable grade.
    """
    if not assumptions.strip():
        raise SemanticRefusal("feature fitting requires explicit conditioning assumptions")
    grade = reacquire_record_feature_grade(connection, selection)
    return _fit_feature_value(grade, algorithm=algorithm, assumptions=assumptions)


def fit_declared_record_policy(
    feature_grade: DdoRecordGrade,
    calibration_grade: DdoRecordGrade,
    specification: DdoRecordFitSpecification,
) -> DeclaredRecordPolicyFitOutcome:
    """Pure exact-instance recomputation and separately held-out event calibration.

    The acquired family port authenticates the selected grade bodies first. This
    function does not grant native authority merely from the possession of DTOs.
    Original release identities remain attribution; calibration may use a later
    compatible release with the same consumed family contract and reading recipe.
    """
    from .record_fitting import (
        FinalEventObservation,
        WholeReadingLabel,
        fit_final_event_calibration,
    )

    first, second = feature_grade.frame, calibration_grade.frame
    if (first.partition, second.partition) != ("feature_fit", "final_event_calibration"):
        raise SemanticRefusal(
            "feature-fit and final-event calibration require separate declared partitions"
        )
    expected = (
        specification.applicability.project_id,
        specification.family_contract,
        specification.reading_recipe,
    )
    if any(
        (frame.project_id, frame.family_contract, frame.reading_recipe) != expected
        for frame in (first, second)
    ):
        raise SemanticRefusal(
            "fitting frames differ from the exact project, consumed family contract or reading recipe"
        )
    if (first.family, first.subset, first.rubric_digest) != (
        second.family,
        second.subset,
        second.rubric_digest,
    ):
        raise SemanticRefusal("calibration changes the declared family, subset or grading rubric")
    if (
        feature_grade.frame_digest == calibration_grade.frame_digest
        or first.reference_digest == second.reference_digest
        or feature_grade.frame_digest not in second.held_out_from
    ):
        raise SemanticRefusal(
            "calibration requires a separately held-out frozen frame and reference"
        )
    groups = [{row.origin_group for row in frame.origin_groups} for frame in (first, second)]
    origins = [
        {
            source.original_source
            for row in frame.origin_groups
            for source in (
                row.source,
                *row.copied_from,
            )
        }
        for frame in (first, second)
    ]
    if groups[0] & groups[1] or origins[0] & origins[1]:
        raise SemanticRefusal(
            "calibration shares a declared origin group or known copied source with feature fitting"
        )
    feature = specification.frozen_feature
    fitted = _fit_feature_value(
        feature_grade, algorithm=feature.algorithm, assumptions=specification.assumptions
    )
    if fitted.instance is None:
        return DeclaredRecordPolicyFitOutcome((fitted.diagnostics,))
    if canonical_bytes(fitted.instance.model_dump(mode="json")) != canonical_bytes(
        feature.model_dump(mode="json")
    ):
        raise SemanticRefusal(
            "frozen feature instance differs from actual immutable feature-fit recomputation"
        )
    observations = []
    for row in second.events:
        event = row.final_event
        if event is None or (event.feature_instance_digest, event.event_procedure) != (
            feature.digest,
            specification.event_procedure,
        ):
            raise SemanticRefusal(
                "calibration event differs from actual frozen predictor or event procedure"
            )
        vector = row.features
        if (
            vector.names != feature.parameters.names
            or vector.feature_signature != feature.parameters.feature_signature
            or any(value is None for value in vector.values)
        ):
            raise SemanticRefusal("calibration features differ from the frozen ordered predictor")
        potential = reading_potential(
            feature.parameters, tuple(value for value in vector.values if value is not None)
        )
        if event.final_event_score != potential:
            raise SemanticRefusal(
                "calibration sealed score differs from the actual frozen predictor"
            )
        observations.append(
            FinalEventObservation(
                feature_instance_digest=feature.digest,
                event_procedure=event.event_procedure,
                final_event_score=event.final_event_score,
                label=WholeReadingLabel(
                    event_id=row.interpretation_id,
                    origin_group=row.origin_group,
                    correct=row.correct,
                    sample_weight=row.sample_weight,
                ),
            )
        )
    calibration = fit_final_event_calibration(
        observations,
        feature=feature,
        frame=_fitting_frame(calibration_grade, specification.assumptions),
        event_procedure=specification.event_procedure,
    )
    diagnostics = (fitted.diagnostics, calibration.diagnostics)
    if calibration.calibration is None:
        return DeclaredRecordPolicyFitOutcome(diagnostics)
    instance = RecordAcceptanceInstance(
        feature=feature,
        calibration=calibration.calibration,
        threshold=specification.threshold,
        threshold_procedure=specification.threshold_procedure,
        conditioning_assumptions=specification.assumptions,
    )
    from corpus_structure.semantic.data_operation_values import semantic_value

    basis = sha256(
        canonical_bytes(
            semantic_value(
                [
                    feature_grade.frame_digest,
                    calibration_grade.frame_digest,
                    specification.model_dump(mode="json"),
                ]
            )
        )
    ).hexdigest()
    return DeclaredRecordPolicyFitOutcome(
        diagnostics,
        DdoFittedRecordPolicy.from_instance(
            instance,
            family_contract=specification.family_contract,
            reading_recipe=specification.reading_recipe,
            judgment_basis_digest=basis,
            applicability=specification.applicability,
        ),
    )


class DdoProtectedRecordPolicyContracts(FrozenContract):
    """One schema root owns the entire protected nominal namespace."""

    grade: DdoRecordGrade
    fitted: DdoFittedRecordPolicy
    specification: DdoRecordFitSpecification
    reference_a: DdoRecordReferencePopulationA
    reference_b: DdoRecordReferencePopulationB
    adjudication: DdoRecordReferencePopulationC
    grading: DdoRecordGradeSpecification
    preliminary: DdoRecordFeatureFitRequest


def protected_record_policy_kind_declarations():
    from corpus_structure.semantic.data_operation_version import MODEL_VERSION
    from corpus_structure.semantic.nominal_schema_kinds import nominal_schema_kinds
    from corpus_structure.semantic.types import SourceArtifact

    return SourceArtifact(
        "record-policy/protected-kinds.json",
        canonical_bytes(
            {
                "version": MODEL_VERSION,
                "kinds": [
                    dict(row, universe="evaluator")
                    for row in nominal_schema_kinds(
                        DdoProtectedRecordPolicyContracts.model_json_schema(),
                        namespace=PROTECTED_NAMESPACE,
                        root_name="DdoProtectedRecordPolicyContracts",
                    )
                ],
            }
        ),
    )


def execute_fit_profile(receiver, feature_grade, calibration_grade, specification):
    result = fit_declared_record_policy(
        DdoRecordGrade.model_validate_json(canonical_bytes(feature_grade)),
        DdoRecordGrade.model_validate_json(canonical_bytes(calibration_grade)),
        DdoRecordFitSpecification.model_validate_json(canonical_bytes(specification)),
    )
    if result.fitted is None:
        raise SemanticRefusal("provisional numerical fit cannot produce a fitted policy")
    return result.fitted.model_dump(mode="json")


def _record_cpu_inputs(
    input_basis: list, *, scalar_roles: tuple[str, ...], set_roles: tuple[str, ...] = ()
):
    from corpus_structure.semantic.data_operation_cpu_basis import cpu_basis_values

    grouped, _ = cpu_basis_values(input_basis, scalar_roles=scalar_roles, set_roles=set_roles)
    return grouped, {
        **{name: grouped[name][0].body for name in scalar_roles},
        **{name: [row.body for row in grouped[name]] for name in set_roles},
    }


def _record_cpu_basis(port, binding, values):
    from corpus_structure.semantic.data_operation_cpu_basis import cpu_input_basis_from_binding

    roles = {role.name: role for role in port.operation.roles if role.direction == "input"}
    bodies = {
        name: (
            (values[role.parameter or name],)
            if role.collection == "scalar"
            else tuple(values[role.parameter or name])
        )
        for name, role in roles.items()
    }
    recipe = next(
        identity.key
        for identity in port.model.identities
        if identity.owner == port.operation.semantic_id and identity.domain == "recipe"
    )
    return cpu_input_basis_from_binding(recipe, binding, bodies)


def execute_fit_kernel(input_basis: list, *, check_active) -> dict:
    from corpus_structure.semantic.data_operation_cpu_basis import cpu_authority_reply
    from corpus_structure.semantic.data_operation_json import json_bytes

    _basis, values = _record_cpu_inputs(
        input_basis, scalar_roles=("feature_grade", "calibration_grade", "specification")
    )
    check_active()
    result = fit_declared_record_policy(
        DdoRecordGrade.model_validate_json(json_bytes(values["feature_grade"])),
        DdoRecordGrade.model_validate_json(json_bytes(values["calibration_grade"])),
        DdoRecordFitSpecification.model_validate_json(json_bytes(values["specification"])),
    )
    check_active()
    return cpu_authority_reply(
        input_basis,
        {
            "fitted": result.fitted.model_dump(mode="python") if result.fitted else None,
            "diagnostics": [row.model_dump(mode="python") for row in result.diagnostics],
        },
    )


def _bound_scalar(binding, role):
    if binding is None or not binding.sufficient or binding.subject_context is None:
        raise SemanticRefusal(
            "record-policy computation requires its sufficient exact native binding"
        )
    selected = [value for value in binding.roles if value.role == role and value.state == "present"]
    if len(selected) != 1 or len(selected[0].members) != 1:
        raise SemanticRefusal("record-policy computation requires one exact scalar input")
    member = selected[0].members[0]
    if member.multiplicity != 1 or member.member is not None:
        raise SemanticRefusal("record-policy grade requires its whole original protected product")
    return member


@dataclass
class RecordPolicyFitPlan:
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        import inspect

        from corpus_structure.semantic.data_operation_prepared_call import PreparedCallResult
        from corpus_structure.semantic.data_operation_support import ComputationalSupportReference

        check_active()
        if execution_owner.fitter_engine is None:
            raise SemanticRefusal(
                "record-policy fitting requires its separately acquired fitter engine"
            )
        feature_member = _bound_scalar(binding, "feature_grade")
        calibration_member = _bound_scalar(binding, "calibration_grade")
        specification = DdoRecordFitSpecification.model_validate_json(
            canonical_bytes(arguments.arguments["specification"])
        )
        selection = specification.feature_selection
        if (
            selection.project_id != binding.subject_context.project_id
            or selection.product_id != feature_member.product
            or not any(
                isinstance(ref, ComputationalSupportReference)
                and ref.derivation_id == selection.derivation_id
                for ref in feature_member.support_references
            )
            or not calibration_member.support_episodes
            or specification.calibration_selection.product_id != calibration_member.product
            or specification.calibration_selection.derivation_id
            not in calibration_member.support_episodes
        ):
            raise SemanticRefusal("fitting selection differs from actual protected grade support")
        with execution_owner.fitter_engine.begin() as connection:
            grade = reacquire_record_feature_grade(connection, selection)
        if canonical_bytes(grade.model_dump(mode="json")) != canonical_bytes(
            arguments.arguments["feature_grade"]
        ):
            raise SemanticRefusal(
                "restricted fitter grade differs from the actual selected input body"
            )
        with execution_owner.engine.begin() as connection:
            calibration = reacquire_selected_record_grade(
                connection, specification.calibration_selection
            )
        if canonical_bytes(calibration.model_dump(mode="json")) != canonical_bytes(
            arguments.arguments["calibration_grade"]
        ):
            raise SemanticRefusal(
                "evaluator calibration grade differs from its actual selected input body"
            )
        signature = inspect.signature(execute_fit_kernel, eval_str=True)
        input_basis = _record_cpu_basis(self.port, binding, arguments.arguments)
        bound = signature.bind(input_basis=input_basis, check_active=check_active)
        reply = yield from self.port.plan_cpu_reply(
            execute_fit_kernel,
            bound,
            record_policy_operation_sources(),
            execution_owner=execution_owner,
            check_active=check_active,
        )
        from corpus_structure.semantic.data_operation_cpu_basis import cpu_authority_value

        result = cpu_authority_value(reply.content, expected_basis=input_basis)
        evidence = canonical_bytes(reply.execution_receipt.record())
        if result["fitted"] is None:
            return PreparedCallResult(
                None,
                cpu_execution_evidence=evidence,
                outcome="empty",
                cpu_execution_reply=reply.content,
            )
        return PreparedCallResult(
            result["fitted"], cpu_execution_evidence=evidence, cpu_execution_reply=reply.content
        )


def record_policy_inputs(bundle):
    """Current source-only question extents, without the retired evaluator model."""
    from pathlib import Path

    import yaml

    from corpus_structure.semantic.reading_resolution_products import reading_resolution_inputs
    from corpus_structure.semantic.types import SourceArtifact, SourceBundle

    bundle = reading_resolution_inputs(bundle)
    name, root = "data_operation_record_policy_scope", "data_operation_record_policy_scope_root"
    content = (
        Path(__file__).parents[1] / "model/semantic/data-operation-record-policy.yaml"
    ).read_bytes()
    existing = {source.name: source.content for source in bundle.sources}
    if name in existing:
        if existing[name] != content:
            raise ValueError("record policy source scope differs from its acquired current owner")
        return bundle
    if root in existing:
        raise ValueError("record policy source scope uses its reserved root")
    return SourceBundle(
        root,
        (
            *bundle.sources,
            SourceArtifact(name, content),
            SourceArtifact(
                root,
                yaml.safe_dump(
                    {
                        "id": "urn:corpus:record-policy-scope-root",
                        "name": root,
                        "imports": [bundle.root, name],
                    }
                ).encode(),
            ),
        ),
    )


def record_policy_computation_assets():
    from pathlib import Path

    from corpus_structure.semantic.python_module_projection import admitted_operation_module_meaning
    from corpus_structure.semantic.record_policy import READING_NUMERICS
    from corpus_structure.semantic.types import SourceArtifact

    root = Path(__file__).parents[1]
    paths = (
        "methods/declared_record_policy.py",
        "evaluate/declared_record_policy.py",
        "evaluate/record_alignment.py",
        "evaluate/record_fitting.py",
        "semantic/record_policy.py",
        "semantic/record_contracts.py",
        "semantic/record_policy_authority.py",
        "semantic/declared_structural_references.py",
        "semantic/data_operation_prepared_call.py",
        "semantic/data_operation_cpu_basis.py",
    )
    return SourceArtifact(
        "record-policy/computation-assets",
        canonical_bytes(
            {
                "version": "declared-complete-record-policy-1",
                "scope_schema": (root / "model/semantic/data-operation-record-policy.yaml")
                .read_bytes()
                .hex(),
                "numerical_policy": READING_NUMERICS.model_dump(mode="json"),
                "protected_schema": DdoProtectedRecordPolicyContracts.model_json_schema(),
                "files": [
                    (name, admitted_operation_module_meaning((root / name).read_bytes()).hex())
                    for name in paths
                ],
            }
        ),
    )


def record_policy_operation_sources():
    from pathlib import Path

    from corpus_structure.semantic.python_operation_sources import (
        PythonSource,
        PythonSourceCollection,
    )

    root = Path(__file__).parents[1]
    paths = ("methods/declared_record_policy.py", "evaluate/declared_record_policy.py")
    return PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                (root / name).read_bytes(),
                str((root / name).resolve()),
            )
            for name in paths
        ),
        boundary_contracts=(record_policy_computation_assets(),),
    )


def acquire_fit_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.declared_record_policy import RecordPolicyFit
    from corpus_structure.semantic.data_operation_ports import PortRefusal
    from corpus_structure.semantic.data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if (
        selected.semantic_id != "record_policy.fit"
        or selected.effects
        or selected.capabilities.prepared_factory is None
        or selected.capabilities.prepared_factory.entrypoint
        != "corpus_structure.methods.declared_record_policy.RecordPolicyFit.acquire_port"
    ):
        raise PortRefusal("record-policy fit requires its exact pure derivation and factory")
    receiver = RecordPolicyFit()
    plan = RecordPolicyFitPlan()
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.evaluate.declared_record_policy.RecordPolicyFitPlan.plan",
        authorize,
        (record_policy_computation_assets(),),
        record_policy_operation_sources(),
        functions=(
            (
                "corpus_structure.evaluate.declared_record_policy.execute_fit_kernel",
                execute_fit_kernel,
            ),
        ),
        retain_cpu_reply=True,
    )
    plan.port = port
    return port


def _record_frame(content):
    from .record_alignment import RecordEvaluationFrame

    value = _canonical_json_value(content)
    expected = {
        "unit",
        "release_id",
        "guideline_version",
        "reference_policy_version",
        "prediction_policy_version",
        "pin",
        "anchor_ids",
        "related_pins",
        "anchor_scopes",
    }
    if set(value) != expected:
        raise SemanticRefusal("record question requires its exact complete source-frame fields")
    return RecordEvaluationFrame(
        unit=value["unit"],
        release_id=value["release_id"],
        guideline_version=value["guideline_version"],
        reference_policy_version=value["reference_policy_version"],
        prediction_policy_version=value["prediction_policy_version"],
        pin=value["pin"],
        anchor_ids=frozenset(value["anchor_ids"]),
        related_pins=tuple(value["related_pins"]),
        anchor_scopes=tuple(value["anchor_scopes"]),
    )


def grade_complete_record_values(
    references: tuple[DdoRecordReference, DdoRecordReference, DdoRecordReference],
    predictions: dict | None,
    specification: DdoRecordGradeSpecification,
    *,
    reference_prepared,
    prediction_prepared,
    reference_model,
    prediction_model,
    reference_addresses: tuple[DeclaredProductRef, ...],
    prediction_address: DeclaredProductRef | None,
    prediction_derivation: str | None,
    prediction_recipe: str,
    prediction_outcome: Literal["completed", "no_output", "failed"] = "completed",
    failure_request_id: str | None = None,
    failure_use_id: str | None = None,
    check_active=lambda: None,
) -> DdoRecordGrade:
    """Pure complete-family grading after actual selections/source custody are acquired.

    Reference and prediction domain schemas and original identities remain separate.
    This function produces no native authority and never treats selected-case field
    equality as full-reading correctness. No-output opportunities remain in coverage.
    """
    import json
    from dataclasses import replace

    from corpus_structure.semantic.declared_candidate_products import candidate_member_values
    from corpus_structure.semantic.reading_resolution_products import (
        reading_diagnostics,
        resolved_reading_events,
    )
    from corpus_structure.semantic.record_contracts import record_family_contract
    from corpus_structure.semantic.record_policy import derive_record_features

    from .record_alignment import RecordSide, prepare_reference_alignment

    check_active()
    if len(reference_addresses) != 3:
        raise SemanticRefusal(
            "record grade requires three exact independently retained pass addresses"
        )
    passes = {
        row.pass_kind: (row, address)
        for row, address in zip(references, reference_addresses, strict=True)
    }
    if set(passes) != {"A", "B", "C"}:
        raise SemanticRefusal("record grading requires independent A/B and C adjudication")
    question = passes["C"][0].question
    if any(row.question != question for row in references):
        raise SemanticRefusal("record references differ from the same frozen source-only question")
    if (
        question.source_release_id != reference_prepared.release_id
        or prediction_recipe != question.reading_recipe
        or specification.prediction_selections[0].project_id != question.project_id
    ):
        raise SemanticRefusal(
            "record grade differs from actual source release, project or producing reading recipe"
        )
    if set(passes["C"][0].adjudicates) != {passes["A"][0].digest, passes["B"][0].digest}:
        raise SemanticRefusal("adjudication does not retain the actual independent A/B answers")
    reference_frame = _record_frame(question.frame_canonical_json)
    coordinates = tuple(_canonical_json_value(question.coordinate_texts_canonical_json))
    reference_rows = {}
    reference_stages = {}
    for kind, (reference, _) in passes.items():
        rows = tuple(
            reference_prepared.validate_json("SourceRecord", canonical_bytes(row)).model_dump(
                mode="python", exclude_unset=True
            )
            for row in _canonical_json_value(reference.records_canonical_json)
        )
        if any(row["family"] != question.family for row in rows):
            raise SemanticRefusal(
                "independent reference contains a record outside its declared family"
            )
        reference_stages[kind] = prepare_reference_alignment(
            RecordSide(reference_frame, rows),
            reference_prepared,
            model=reference_model,
            coordinate_texts=coordinates,
        )
        reference_rows[kind] = rows
    if predictions is not None and predictions["source_pin"] != question.source.model_dump(
        mode="json", exclude_none=True
    ):
        raise SemanticRefusal(
            "prediction source differs from the original frozen source-only question"
        )
    if predictions is not None and predictions["inspection_outcome"] not in {"produced", "empty"}:
        raise SemanticRefusal("record grade requires its complete completed prediction carrier")
    candidates = (
        tuple(
            prediction_prepared.validate_json("SourceRecord", canonical_bytes(row)).model_dump(
                mode="python", exclude_unset=True
            )
            for row in candidate_member_values(predictions, candidate_type="record")
            if row["family"] == question.family
        )
        if predictions is not None
        else ()
    )
    for actual_model, rows in (
        (reference_model, reference_rows["C"]),
        (prediction_model, candidates),
    ):
        for row in rows:
            if record_family_contract(actual_model, row["contract"]) != question.family_contract:
                raise SemanticRefusal(
                    "record family semantics differ from the frozen consumed contract"
                )
    prediction_frame = replace(reference_frame, release_id=prediction_prepared.release_id)
    pins = (reference_frame.pin, *reference_frame.related_pins)
    correspondence = tuple(
        {"reference_pin": pin, "prediction_pin": pin, "physical_digest": pin["projection_digest"]}
        for pin in pins
    )
    if predictions is None and prediction_outcome == "completed":
        raise SemanticRefusal("completed source grading requires its actual prediction carrier")
    details = json.loads(predictions["diagnostics_json"]) if predictions is not None else {}
    sealed = resolved_reading_events(predictions) if predictions is not None else ()
    events = []
    for row in candidates:
        check_active()
        if predictions is None or prediction_address is None or prediction_derivation is None:
            raise SemanticRefusal(
                "scored record requires its actual prediction carrier and producing episode"
            )
        correct = reference_stages["C"].whole_reading_correct(
            row,
            prediction_prepared=prediction_prepared,
            prediction_model=prediction_model,
            prediction_frame=prediction_frame,
            prediction_coordinate_texts=predictions["coordinate_texts"],
            correspondence=correspondence,
        )
        diagnostics = reading_diagnostics(row, details.get("producer_diagnostics", details))
        selected = [
            event
            for event in sealed
            if (event["record_id"], event["interpretation_id"])
            == (row["record_id"], row["interpretation_id"])
        ]
        final_event = None
        if len(selected) != 1:
            raise SemanticRefusal(
                "record grade requires every candidate's unique retained producer event"
            )
        retained = selected[0]
        if retained["outcome"] == "completed":
            diagnostics = retained.get("feature_diagnostics", retained["diagnostics"])
        features = derive_record_features(
            prediction_prepared, row, algorithm=specification.algorithm, diagnostics=diagnostics
        )
        if retained["outcome"] == "completed":
            final_event = DdoRecordFinalEvent(
                feature_instance_digest=retained["feature_instance_digest"],
                feature_input_digest=retained["feature_input_digest"],
                event_procedure=retained["event_procedure"],
                final_event_score=retained["final_event_score"],
            )
        events.append(
            DdoRecordGradeEvent(
                record_id=row["record_id"],
                interpretation_id=row["interpretation_id"],
                reading=prediction_address,
                source=question.source,
                source_release_id=prediction_prepared.release_id,
                derivation_id=prediction_derivation,
                reading_recipe=prediction_recipe,
                features=features,
                correct=correct,
                origin_group=question.origin_group,
                sample_weight=question.sample_weight,
                final_event=final_event,
            )
        )
    metadata = tuple(
        DdoRecordReferencePass(
            reference=address,
            source=question.source,
            pass_kind=row.pass_kind,
            author=row.author,
            content_digest=row.digest,
            question_digest=question.digest,
            rubric_digest=question.rubric_digest,
            source_cut_id=question.source_cut_id,
            adjudicates=row.adjudicates,
        )
        for row, address in zip(references, reference_addresses, strict=True)
    )
    return DdoRecordGrade.from_frame(
        DdoRecordGradeFrame(
            partition=question.partition,
            project_id=question.project_id,
            family=question.family,
            family_contract=question.family_contract,
            reading_recipe=question.reading_recipe,
            subset=question.subset,
            question_digest=question.digest,
            rubric_digest=question.rubric_digest,
            reference_digest=passes["C"][0].digest,
            source_cut_id=question.source_cut_id,
            prediction_cut_id=specification.prediction_selections[0].expected_cut,
            source_release_id=reference_prepared.release_id,
            prediction_release_id=prediction_prepared.release_id,
            sources=(question.source,),
            reference_passes=metadata,
            events=tuple(events),
            coverage=(
                DdoRecordCoverage(
                    source=question.source,
                    outputs=(prediction_address,) if prediction_address is not None else (),
                    outcome=("completed" if events else "no_output")
                    if predictions is not None
                    else prediction_outcome,
                    event_ids=tuple(row.interpretation_id for row in events),
                    failure_request_id=failure_request_id,
                    failure_use_id=failure_use_id,
                ),
            ),
            origin_groups=(
                DdoRecordOrigin(
                    source=question.source,
                    origin_group=question.origin_group,
                    copied_from=question.copied_from,
                ),
            ),
            held_out_from=question.held_out_from,
        )
    )


def _selected_body(index, product, member=None):
    from corpus_structure.semantic.data_operation_values import decode_semantic_value

    row = (
        index.mapping("kb.data_product", ("id",)).get(product)
        if member is None
        else index.mapping("kb.data_product_member", ("product_id", "member_id")).get(
            (product, member)
        )
    )
    if row is None:
        raise SemanticRefusal("record-policy input is outside the exact selected native closure")
    return row, decode_semantic_value(row["canonical_body" if member is None else "body"])


def _check_source_coordinates(
    prepared, source_values, coordinates, anchors=(), *, source_cache=None
):
    """Authenticate actual retained native coordinates, refusing missing recognition custody."""
    import re

    from corpus_structure.semantic.source_products import FrozenNativeSource

    source_cache = {} if source_cache is None else source_cache
    sources = {}
    for pin, body in source_values:
        key = canonical_bytes(pin)
        cache_key = prepared.release_id, key
        if cache_key not in source_cache:
            source_cache[cache_key] = FrozenNativeSource.acquire(prepared, body).view
        sources[key] = source_cache[cache_key]

    for coordinate in coordinates:
        view = sources.get(canonical_bytes(coordinate["pin"]))
        if view is None:
            raise SemanticRefusal("record coordinate is outside the frozen original source closure")
        value = view.value
        space, pointer = coordinate["space"], coordinate["pointer"]
        if space == "captured_recognition":
            raise SemanticRefusal(
                "captured recognition grading requires its separately admitted observation product"
            )
        nodes = view.context_items_by_ref
        cell = re.fullmatch(
            r"(#/tables/(?:0|[1-9][0-9]*))/data/table_cells/(0|[1-9][0-9]*)", pointer
        )
        node = nodes.get(cell[1] if cell else pointer)
        if node is None:
            raise SemanticRefusal(
                "record coordinate names an item outside the selected native source"
            )
        if cell:
            cells = node.get("data", {}).get("table_cells", ())
            if int(cell[2]) >= len(cells):
                raise SemanticRefusal("record coordinate cell is outside the selected native table")
            node = cells[int(cell[2])]
        if space == "selected_projection":
            actual = value["text"]
        elif space in {"native", "recognized_text"}:
            actual = node.get("text")
        else:
            raise SemanticRefusal("model context cannot authenticate record grading evidence")
        if coordinate["text"] != actual:
            raise SemanticRefusal(
                "record coordinate text differs from actual retained source bytes"
            )
    for anchor in anchors:
        if anchor["space"] == "captured_recognition":
            raise SemanticRefusal(
                "captured recognition grading requires its separately admitted observation product"
            )
        if anchor["space"] != "selected_projection" or anchor["precision"] != "exact":
            continue
        view = sources.get(canonical_bytes(anchor["pin"]))
        cell = re.fullmatch(
            r"(#/tables/(?:0|[1-9][0-9]*))/data/table_cells/(0|[1-9][0-9]*)", anchor["pointer"]
        )
        pointer, cell_index = (cell[1], int(cell[2])) if cell else (anchor["pointer"], None)
        piece = (
            None if view is None else view.containing_piece(pointer, anchor["start"], anchor["end"])
        )
        if (
            piece is None
            or not anchor["start"] < anchor["end"]
            or not (
                piece.get("source_field") == "cell_text" and piece.get("cell_index") == cell_index
                if cell_index is not None
                else piece.get("source_field") in {"text", "orig"}
            )
        ):
            raise SemanticRefusal(
                "selected projection grading extent crosses synthetic or another source item"
            )


def _authenticate_question_sources(connection, prepared, questions, *, source_cache=None):
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_model import json_context_meaning
    from corpus_structure.semantic.demand_results import CutSelection, selected_record_index

    cut = CutSelection(questions[0].source_cut_canonical_json.encode())
    if any(question.source_cut_canonical_json.encode() != cut.content for question in questions):
        raise SemanticRefusal("record source population changes its exact frozen native source cut")
    source_cache = {} if source_cache is None else source_cache
    by_pin, question_pins = {}, []
    with selected_record_index(
        connection,
        cut.record["demand_id"],
        project_id=questions[0].project_id,
        scope=cut.record["scope"],
        read_id=cut.record["read_id"],
        expected_cut=cut.identity,
    ) as (_, index):
        for question in questions:
            frame = _record_frame(question.frame_canonical_json)
            pins = (frame.pin, *frame.related_pins)
            question_pins.append(pins)
            for pin in pins:
                key = canonical_bytes(pin)
                if key in by_pin:
                    continue
                source = DeclaredStructuralSource.model_validate(pin)
                row, body = _selected_body(index, source.source_product, source.source_member)
                if (
                    row["kind_contract"],
                    row["subject"],
                    row["subject_definition"],
                    row["original_source"],
                    json_context_meaning(json_bytes(row["analyzed_scope"])).decode(),
                ) != (
                    source.kind_contract,
                    source.subject,
                    source.subject_definition,
                    source.original_source,
                    source.analyzed_scope_meaning,
                ):
                    raise SemanticRefusal(
                        "record question source differs from actual selected native identity/context"
                    )
                coordinate = body["source"]
                if (
                    coordinate["document"],
                    coordinate["projection"],
                    coordinate["section_pointer"],
                    coordinate["membership"],
                ) != (
                    source.document,
                    source.projection_digest,
                    source.section_pointer,
                    source.membership,
                ):
                    raise SemanticRefusal(
                        "record source coordinate differs from its retained native body"
                    )
                by_pin[key] = (pin, body)
    result = []
    for question, pins in zip(questions, question_pins, strict=True):
        values = tuple(by_pin[canonical_bytes(pin)] for pin in pins)
        _check_source_coordinates(
            prepared,
            values,
            _canonical_json_value(question.coordinate_texts_canonical_json),
            source_cache=source_cache,
        )
        result.append(values)
    return tuple(result)


def execute_grade_profile(
    receiver, sources, reference_a, reference_b, adjudication, prediction, specification
):
    if receiver.execute is None:
        raise ValueError(
            "record grading requires its acquired current source and release resources"
        )
    return receiver.execute(
        sources, reference_a, reference_b, adjudication, prediction, specification
    )


def grade_complete_record_population_values(
    populations,
    predictions,
    specification,
    *,
    reference_prepared,
    reference_model,
    prediction_prepared,
    prediction_models,
    reference_addresses,
    prediction_addresses,
    prediction_recipes,
    cut_release_id,
    check_active=lambda: None,
):
    """Grade exactly the ordered predeclared source census, without acceptance filtering."""
    if tuple(row.pass_kind for row in populations) != ("A", "B", "C"):
        raise SemanticRefusal("record grade requires its ordered authentic A/B/C pass populations")
    questions = tuple(row.question for row in populations[2].references)
    if any(
        tuple(row.question for row in population.references) != questions
        for population in populations
    ):
        raise SemanticRefusal(
            "A/B/C passes differ from the same exact ordered question/source population"
        )
    count = len(questions)
    if any(
        len(items) != count
        for items in (
            predictions,
            specification.prediction_selections,
            prediction_prepared,
            prediction_models,
            prediction_addresses,
            prediction_recipes,
        )
    ):
        raise SemanticRefusal(
            "grade requires exact all-of reference/source/prediction population coverage"
        )
    if len({selection.expected_cut for selection in specification.prediction_selections}) != 1:
        raise SemanticRefusal(
            "record prediction population must retain one exact frozen selection cut"
        )
    frames = []
    for position, question in enumerate(questions):
        check_active()
        selection = specification.prediction_selections[position]
        if selection.source != question.source:
            raise SemanticRefusal(
                "prediction population changes the original ordered source questions"
            )
        unit_specification = specification.model_copy(
            update={"prediction_selections": (selection,)}
        )
        grade = grade_complete_record_values(
            tuple(population.references[position] for population in populations),
            predictions[position],
            unit_specification,
            reference_prepared=reference_prepared,
            reference_model=reference_model,
            prediction_prepared=prediction_prepared[position],
            prediction_model=prediction_models[position],
            reference_addresses=reference_addresses,
            prediction_address=prediction_addresses[position],
            prediction_derivation=selection.derivation_id,
            prediction_recipe=prediction_recipes[position],
            prediction_outcome=selection.outcome,
            failure_request_id=selection.request_id if selection.outcome == "failed" else None,
            failure_use_id=selection.use_id if selection.outcome == "failed" else None,
            check_active=check_active,
        )
        frames.append(grade.frame)
    first = frames[0]
    if any(frame.held_out_from != first.held_out_from for frame in frames):
        raise SemanticRefusal("record source population changes its predeclared held-out basis")
    return DdoRecordGrade.from_frame(
        DdoRecordGradeFrame(
            **{
                name: getattr(first, name)
                for name in (
                    "partition",
                    "project_id",
                    "family",
                    "family_contract",
                    "reading_recipe",
                    "subset",
                    "rubric_digest",
                    "source_cut_id",
                    "prediction_cut_id",
                    "source_release_id",
                    "held_out_from",
                )
            },
            prediction_release_id=cut_release_id,
            question_digest=sha256(
                canonical_bytes([frame.question_digest for frame in frames])
            ).hexdigest(),
            reference_digest=sha256(
                canonical_bytes([frame.reference_digest for frame in frames])
            ).hexdigest(),
            sources=tuple(source for frame in frames for source in frame.sources),
            reference_passes=tuple(
                reference for frame in frames for reference in frame.reference_passes
            ),
            events=tuple(event for frame in frames for event in frame.events),
            coverage=tuple(coverage for frame in frames for coverage in frame.coverage),
            origin_groups=tuple(origin for frame in frames for origin in frame.origin_groups),
        )
    )


def execute_grade_kernel(input_basis: list, metadata: dict, *, prepared, check_active) -> dict:
    from corpus_structure.semantic.cpu_execution import hydrate_capsule
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.data_operation_cpu_basis import cpu_authority_reply
    from corpus_structure.semantic.data_operation_json import json_bytes

    basis, values = _record_cpu_inputs(
        input_basis,
        scalar_roles=("reference_a", "reference_b", "adjudication", "specification"),
        set_roles=("sources", "prediction"),
    )
    populations = tuple(
        DdoRecordReferencePopulation.model_validate_json(json_bytes(values[name]))
        for name in ("reference_a", "reference_b", "adjudication")
    )
    captured = {prepared.release_id: prepared}
    for release_id, content in metadata["historical_capsules"].items():
        historical = hydrate_capsule(bytes.fromhex(content))
        if historical.release_id != release_id or release_id in captured:
            raise SemanticRefusal(
                "captured grading archive differs from its original release identity"
            )
        captured[release_id] = historical
    reference_prepared = captured[metadata["reference_release_id"]]
    archives = tuple(captured[release_id] for release_id in metadata["prediction_release_ids"])
    checked = DdoRecordGradeSpecification.model_validate_json(json_bytes(values["specification"]))
    by_product = {role.product_id: role.body for role in basis["prediction"]}
    if set(by_product) != {
        address["product_id"] for address in metadata["bound_prediction_addresses"]
    }:
        raise SemanticRefusal("record CPU predictions differ from their actual selected addresses")
    result = grade_complete_record_population_values(
        populations,
        tuple(by_product.get(selection.product_id) for selection in checked.prediction_selections),
        checked,
        reference_prepared=reference_prepared,
        reference_model=bound_data_operation_model(reference_prepared),
        prediction_prepared=archives,
        prediction_models=tuple(bound_data_operation_model(item) for item in archives),
        reference_addresses=tuple(
            DeclaredProductRef.model_validate_json(canonical_bytes(value))
            for value in metadata["reference_addresses"]
        ),
        prediction_addresses=tuple(
            DeclaredProductRef.model_validate_json(canonical_bytes(value))
            if value is not None
            else None
            for value in metadata["prediction_addresses"]
        ),
        prediction_recipes=tuple(metadata["prediction_recipes"]),
        cut_release_id=metadata["cut_release_id"],
        check_active=check_active,
    )
    return cpu_authority_reply(input_basis, result.model_dump(mode="python"))


def _bound_source_members(binding):
    if binding is None or not binding.sufficient or binding.subject_context is None:
        raise SemanticRefusal("record grading requires its sufficient exact native binding")
    roles = [role for role in binding.roles if role.role == "sources" and role.state == "present"]
    if len(roles) != 1 or not roles[0].members:
        raise SemanticRefusal(
            "record grading requires every actual primary and related source input"
        )
    members = roles[0].members
    if any(member.multiplicity != 1 for member in members) or len(
        {(member.product, member.member) for member in members}
    ) != len(members):
        raise SemanticRefusal(
            "record source population repeats or multiplies an original source address"
        )
    return members


def _verify_declared_sources(source_values, members, bodies, *, project):
    """Native source roles retain the same actual sources that the reference cut authenticated."""
    from corpus_structure.semantic.data_operation_values import semantic_value

    expected = {}
    for values in source_values:
        for raw_pin, body in values:
            pin = DeclaredStructuralSource.model_validate(raw_pin)
            key = (pin.source_product, pin.source_member)
            previous = expected.setdefault(key, (pin, body))
            if previous != (pin, body):
                raise SemanticRefusal(
                    "record question assigns conflicting source meaning to one actual address"
                )
    if len(members) != len(bodies) or {
        (member.product, member.member) for member in members
    } != set(expected):
        raise SemanticRefusal(
            "declared sources differ from the exact primary and related consumed source closure"
        )
    for member, body in zip(members, bodies, strict=True):
        pin, actual = expected[(member.product, member.member)]
        address = DeclaredProductRef.from_bound(member, project=project)
        if (
            address.kind_contract,
            address.project_id,
            address.subject,
            address.subject_definition,
            address.original_source,
            address.analyzed_scope_meaning,
        ) != (
            pin.kind_contract,
            pin.project_id,
            pin.subject,
            pin.subject_definition,
            pin.original_source,
            pin.analyzed_scope_meaning,
        ) or semantic_value(body) != semantic_value(actual):
            raise SemanticRefusal(
                "declared source body/context differs from its authenticated selected source"
            )


def _bound_prediction_members(binding):
    if binding is None or not binding.sufficient or binding.subject_context is None:
        raise SemanticRefusal("record grading requires its sufficient exact native binding")
    roles = [role for role in binding.roles if role.role == "prediction"]
    if len(roles) != 1 or roles[0].state not in {"present", "known-absent"}:
        raise SemanticRefusal("record prediction population is unknown or unavailable")
    members = roles[0].members
    if any(member.member is not None or member.multiplicity != 1 for member in members):
        raise SemanticRefusal("record grading requires whole actual prediction carriers")
    if len({member.product for member in members}) != len(members):
        raise SemanticRefusal("record prediction population repeats a carrier identity")
    return members


@dataclass
class RecordPolicyGradePlan:
    prepared: Any
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        import inspect

        from corpus_structure.semantic.cpu_execution import release_capsule
        from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
        from corpus_structure.semantic.data_operation_json import json_bytes
        from corpus_structure.semantic.data_operation_model import json_context_meaning
        from corpus_structure.semantic.demand_results import CutSelection, selected_record_index
        from corpus_structure.semantic.reading_resolution_products import reading_recipe_identity
        from corpus_structure.semantic.releases import open_release

        check_active()
        context = binding.subject_context if binding is not None else None
        if context is None or context.original_source is not None:
            raise SemanticRefusal(
                "record grading requires its exact project knowledge-universe context"
            )
        values = arguments.arguments
        populations = tuple(
            DdoRecordReferencePopulation.model_validate_json(canonical_bytes(values[name]))
            for name in ("reference_a", "reference_b", "adjudication")
        )
        reference_members = tuple(
            _bound_scalar(binding, name) for name in ("reference_a", "reference_b", "adjudication")
        )
        source_members = _bound_source_members(binding)
        prediction_members = _bound_prediction_members(binding)
        specification = DdoRecordGradeSpecification.model_validate_json(
            canonical_bytes(values["specification"])
        )
        questions = tuple(row.question for row in populations[2].references)
        if any(
            tuple(row.question for row in population.references) != questions
            for population in populations
        ) or tuple(selection.source for selection in specification.prediction_selections) != tuple(
            question.source for question in questions
        ):
            raise SemanticRefusal(
                "record grade requires exact all-of ordered reference/source/prediction questions"
            )
        if len(prediction_members) != len(values["prediction"]):
            raise SemanticRefusal("record prediction bodies differ from actual bound population")
        bound_predictions = {
            member.product: (member, body)
            for member, body in zip(prediction_members, values["prediction"], strict=True)
        }
        completed = {
            selection.product_id
            for selection in specification.prediction_selections
            if selection.outcome == "completed"
        }
        if completed != set(bound_predictions):
            raise SemanticRefusal(
                "bound prediction carriers differ from exact complete predeclared population"
            )
        cuts = tuple(
            CutSelection(selection.cut_canonical_json.encode())
            for selection in specification.prediction_selections
        )
        cut = cuts[0]
        if any(selected.content != cut.content for selected in cuts):
            raise SemanticRefusal(
                "record prediction population changes its exact frozen native cut"
            )
        for selection in specification.prediction_selections:
            if (
                cut.identity,
                cut.record["demand_id"],
                cut.record["read_id"],
                cut.record["project_id"],
            ) != (
                selection.expected_cut,
                selection.demand_id,
                selection.read_id,
                selection.project_id,
            ) or selection.project_id != context.project_id:
                raise SemanticRefusal(
                    "record prediction selection differs from its exact acquired native cut"
                )
        archives, addresses, recipes = [], [], []
        historical = {}
        loaded_releases = {}
        source_cache = {}

        def acquire_release(connection, release_id):
            if release_id not in loaded_releases:
                loaded_releases[release_id] = open_release(connection, release_id)
            return loaded_releases[release_id]

        def capture(prepared):
            if (
                prepared.release_id != self.prepared.release_id
                and prepared.release_id not in historical
            ):
                historical[prepared.release_id] = release_capsule(prepared).hex()
            return prepared.release_id

        with execution_owner.engine.begin() as connection:
            reference_prepared = acquire_release(connection, questions[0].source_release_id)
            reference_release_id = capture(reference_prepared)
            sources_by_question = _authenticate_question_sources(
                connection, reference_prepared, questions, source_cache=source_cache
            )
            _verify_declared_sources(
                sources_by_question, source_members, values["sources"], project=context.project_id
            )
            with selected_record_index(
                connection,
                cut.record["demand_id"],
                project_id=context.project_id,
                scope=cut.record["scope"],
                read_id=cut.record["read_id"],
                expected_cut=cut.identity,
                capture_frontier=True,
            ) as (_, index):
                uses = {row["use_id"]: row for row in index.frontier_rows("uses")}
                obligations = {
                    row["obligation_id"]: row for row in index.frontier_rows("obligations")
                }
                for question, selection, source_values in zip(
                    questions, specification.prediction_selections, sources_by_question, strict=True
                ):
                    check_active()
                    use = uses.get(selection.use_id)
                    obligation = obligations.get(selection.obligation_id)
                    if (
                        use is None
                        or obligation is None
                        or use["obligation_id"] != selection.obligation_id
                        or use["request_id"] != selection.request_id
                        or obligation["operation_id"] != "resolve.m1_readings/declared"
                        or (
                            obligation["subject"],
                            obligation["original_source"],
                            json_context_meaning(json_bytes(obligation["analyzed_scope"])).decode(),
                        )
                        != (
                            question.source.subject,
                            question.source.original_source,
                            question.source.analyzed_scope_meaning,
                        )
                    ):
                        raise SemanticRefusal(
                            "record prediction lacks its exact current native source/request/use selection"
                        )
                    if selection.outcome != "completed":
                        state = "failed" if selection.outcome == "failed" else "empty"
                        fate = "failed" if selection.outcome == "failed" else "known-absent"
                        if use["completion_state"] != state or use["fate"] != fate:
                            raise SemanticRefusal(
                                "absent/failed prediction is unknown, unavailable or not actually completed"
                            )
                        prepared = acquire_release(connection, cut.record["release_id"])
                        archives.append(capture(prepared))
                        addresses.append(None)
                        recipes.append(
                            reading_recipe_identity(bound_data_operation_model(prepared))
                        )
                        continue
                    member, passed_body = bound_predictions[selection.product_id]
                    if (
                        selection.derivation_id not in member.support_episodes
                        or use["derivation_id"] != selection.derivation_id
                        or use["completion_state"] != "success"
                        or use["fate"] not in {"fulfilled", "attached"}
                    ):
                        raise SemanticRefusal(
                            "record prediction lacks valid completed selected producing support"
                        )
                    _, actual = _selected_body(index, selection.product_id)
                    if canonical_bytes(actual) != canonical_bytes(passed_body):
                        raise SemanticRefusal(
                            "record prediction differs from its actual selected carrier body"
                        )
                    episode = index.mapping("ops.data_derivation", ("id",)).get(
                        selection.derivation_id
                    )
                    outputs = tuple(
                        index.rows_for(
                            "ops.data_derivation_output",
                            derivation_id=selection.derivation_id,
                            product_id=selection.product_id,
                        )
                    )
                    if (
                        episode is None
                        or not outputs
                        or episode["request_id"] != selection.request_id
                    ):
                        raise SemanticRefusal(
                            "record prediction lacks its exact actual producing episode/output"
                        )
                    prepared = acquire_release(connection, episode["release_id"])
                    recipe = reading_recipe_identity(bound_data_operation_model(prepared))
                    if episode["recipe"] != recipe:
                        raise SemanticRefusal(
                            "record prediction recipe differs from its actual admitted producer"
                        )
                    records = [
                        packet["body"]
                        for packet in actual["members"]
                        if packet["body"]["candidate_type"] == "record"
                    ]
                    _check_source_coordinates(
                        prepared,
                        source_values,
                        actual["coordinate_texts"],
                        [anchor for row in records for anchor in row["anchors"]],
                        source_cache=source_cache,
                    )
                    archives.append(capture(prepared))
                    addresses.append(
                        DeclaredProductRef.from_bound(
                            member, project=context.project_id
                        ).model_dump(mode="json")
                    )
                    recipes.append(recipe)
            metadata = dict(
                reference_release_id=reference_release_id,
                prediction_release_ids=archives,
                historical_capsules=historical,
                reference_addresses=[
                    DeclaredProductRef.from_bound(member, project=context.project_id).model_dump(
                        mode="json"
                    )
                    for member in reference_members
                ],
                prediction_addresses=addresses,
                prediction_recipes=recipes,
                cut_release_id=cut.record["release_id"],
                bound_prediction_addresses=[
                    DeclaredProductRef.from_bound(member, project=context.project_id).model_dump(
                        mode="json"
                    )
                    for member in prediction_members
                ],
            )
        signature = inspect.signature(execute_grade_kernel, eval_str=True)
        bound = signature.bind(
            input_basis=_record_cpu_basis(self.port, binding, values),
            metadata=metadata,
            prepared=self.prepared,
            check_active=check_active,
        )
        return (
            yield from self.port.plan_cpu(
                execute_grade_kernel,
                bound,
                record_policy_operation_sources(),
                prepared_release_id=self.prepared.release_id,
                execution_owner=execution_owner,
                check_active=check_active,
            )
        )


def acquire_grade_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.declared_record_policy import RecordPolicyGrade
    from corpus_structure.semantic.data_operation_ports import PortRefusal
    from corpus_structure.semantic.data_operation_prepared_call import PreparedOriginalCallPort
    from corpus_structure.semantic.record_policy_authority import GRADE_FACTORY, GRADE_OPERATION

    selected = model.operation(operation)
    if (
        selected.semantic_id != GRADE_OPERATION
        or selected.effects
        or selected.capabilities.prepared_factory is None
        or selected.capabilities.prepared_factory.entrypoint != GRADE_FACTORY
    ):
        raise PortRefusal("record grade requires its exact protected pure derivation/factory")
    receiver = RecordPolicyGrade(None)
    plan = RecordPolicyGradePlan(prepared)
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.evaluate.declared_record_policy.RecordPolicyGradePlan.plan",
        authorize,
        (record_policy_computation_assets(),),
        record_policy_operation_sources(),
        functions=(
            (
                "corpus_structure.evaluate.declared_record_policy.execute_grade_kernel",
                execute_grade_kernel,
            ),
        ),
        requires_prepared_schema=True,
        retain_cpu_reply=True,
    )
    plan.port = port
    return port


def reacquire_selected_record_grade(
    connection, selection: DdoRecordGradeSelection
) -> DdoRecordGrade:
    """Evaluator-authorized exact grade selection, separate from the fitter-only read."""
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.demand_results import CutSelection, selected_record_index
    from corpus_structure.semantic.native_definition_projection import (
        read_native_definition_projection,
    )
    from corpus_structure.semantic.record_policy_authority import (
        GRADE_FACTORY,
        GRADE_KIND,
        GRADE_OPERATION,
    )
    from corpus_structure.semantic.releases import open_release

    cut = CutSelection(selection.cut_canonical_json.encode())
    if (cut.identity, cut.record["project_id"], cut.record["demand_id"], cut.record["read_id"]) != (
        selection.expected_cut,
        selection.project_id,
        selection.demand_id,
        selection.read_id,
    ):
        raise SemanticRefusal("grade selection differs from original acquired native cut bytes")
    with selected_record_index(
        connection,
        selection.demand_id,
        project_id=selection.project_id,
        scope=cut.record["scope"],
        read_id=selection.read_id,
        expected_cut=cut.identity,
    ) as (_, index):
        row, body = _selected_body(index, selection.product_id)
        episode = index.mapping("ops.data_derivation", ("id",)).get(selection.derivation_id)
        use = index.mapping("ops.demand_use", ("id",)).get(selection.use_id)
        outputs = [
            edge
            for edge in index.rows("ops.data_derivation_output")
            if (
                edge["derivation_id"],
                edge["product_id"],
                edge["role"],
                edge["member_id"],
                edge["multiplicity"],
            )
            == (selection.derivation_id, selection.product_id, "grade", None, 1)
        ]
        if (
            episode is None
            or use is None
            or use["derivation_id"] != selection.derivation_id
            or len(outputs) != 1
        ):
            raise SemanticRefusal(
                "selected protected grade lacks its exact producing episode/use/output"
            )
        prepared = open_release(connection, episode["release_id"])
        model = bound_data_operation_model(prepared)
        operation = model.operation(GRADE_OPERATION)
        request = index.mapping("ops.data_request", ("id",)).get(episode["request_id"])
        recipe = next(
            item.key
            for item in model.identities
            if item.domain == "recipe" and item.owner == GRADE_OPERATION
        )
        if (
            request is None
            or request["operation_id"] != GRADE_OPERATION
            or episode["recipe"] != recipe
            or operation.effects
            or operation.capabilities.prepared_factory is None
            or operation.capabilities.prepared_factory.entrypoint != GRADE_FACTORY
        ):
            raise SemanticRefusal(
                "protected grade differs from its actual captured grading operation/factory"
            )
        contracts = {
            kind["kind_contract"]
            for kind in read_native_definition_projection(prepared)["kinds"]
            if kind["kind"] == GRADE_KIND and kind["universe"] == "evaluator"
        }
        if row["kind_contract"] not in contracts:
            raise SemanticRefusal("selected grade lacks its actual protected nominal kind")
        grade = DdoRecordGrade.from_selected_body(body)
        if (
            grade.frame_digest != selection.frame_digest
            or grade.frame.project_id != selection.project_id
        ):
            raise SemanticRefusal(
                "selected grade differs from exact immutable frame digest or project"
            )
        return grade


def author_record_policy_inputs(engine, prepared, *, request):
    """Retain current source-only reference/specification facts; never authored grades."""
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.data_operation_values import decode_semantic_value
    from corpus_structure.semantic.native_definition_projection import (
        read_native_definition_projection,
    )
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.serve.interpretation_authoring import author_interpretations

    from .record_alignment import RecordSide, align_records

    if request.targets not in {
        ("record_policy.grade",),
        ("record_policy.fit",),
        ("record_policy.fit", "record_policy.authorize"),
    }:
        raise SemanticRefusal("protected record authoring requires its exact grade or fit target")
    supported = {
        PROTECTED_NAMESPACE + name: cls
        for name, cls in (
            ("DdoRecordReferencePopulationA", DdoRecordReferencePopulationA),
            ("DdoRecordReferencePopulationB", DdoRecordReferencePopulationB),
            ("DdoRecordReferencePopulationC", DdoRecordReferencePopulationC),
            ("DdoRecordGradeSpecification", DdoRecordGradeSpecification),
            ("DdoRecordFitSpecification", DdoRecordFitSpecification),
        )
    }
    contracts = {
        row["kind_contract"]: supported[row["kind"]]
        for row in read_native_definition_projection(prepared)["kinds"]
        if row["kind"] in supported and row["universe"] == "evaluator"
    }
    populations: dict[tuple[str, str, str], list[DdoRecordReference]] = {}
    for selected in request.original_sources.values():
        reference = selected.reference
        cls = contracts.get(reference.get("kind_contract"))
        if reference.get("kind") != "authored-fact" or cls is None:
            raise SemanticRefusal(
                "protected record authoring accepts only source-only references and exact specifications"
            )
        value = cls.model_validate_json(
            canonical_bytes(decode_semantic_value(reference["meaning_body"]))
        )
        if isinstance(value, DdoRecordReferencePopulation):
            questions = tuple(row.question for row in value.references)
            if questions[0].project_id != request.project_id:
                raise SemanticRefusal("record reference belongs to another project")
            key = (
                questions[0].project_id,
                questions[0].source_release_id,
                questions[0].source_cut_canonical_json,
            )
            populations.setdefault(key, []).extend(value.references)
    # One invocation pins one transaction. Identical exact cuts share their
    # authenticated selected index; no authority survives this authoring call.
    if populations:
        with engine.begin() as connection:
            for (_, release_id, _), references in populations.items():
                original = open_release(connection, release_id)
                questions = tuple(reference.question for reference in references)
                sources = _authenticate_question_sources(connection, original, questions)
                for reference, question, source_values in zip(
                    references, questions, sources, strict=True
                ):
                    rows = tuple(
                        original.validate_json("SourceRecord", canonical_bytes(row)).model_dump(
                            mode="python", exclude_unset=True
                        )
                        for row in _canonical_json_value(reference.records_canonical_json)
                    )
                    frame = _record_frame(question.frame_canonical_json)
                    from dataclasses import replace

                    comparison = replace(
                        frame, prediction_policy_version=frame.reference_policy_version
                    )
                    coordinates = _canonical_json_value(question.coordinate_texts_canonical_json)
                    _check_source_coordinates(
                        original,
                        source_values,
                        coordinates,
                        [anchor for row in rows for anchor in row["anchors"]],
                    )
                    align_records(
                        RecordSide(comparison, rows),
                        RecordSide(comparison, rows),
                        original,
                        model=bound_data_operation_model(original),
                        prediction_model=bound_data_operation_model(original),
                        coordinate_texts=coordinates,
                    )
    return author_interpretations(engine, prepared, request=request)


def prepare_record_feature_policy(connection, request: DdoRecordFeatureFitRequest):
    """Restricted preliminary fit and a genuine current authored reading policy value.

    This is not a protected fit producer and grants no native policy authority.
    The final declared fit recomputes the same immutable feature instance before
    calibrating actual independently held-out producer events.
    """
    from corpus_structure.semantic.observations import source_value
    from corpus_structure.semantic.reading_resolution_products import (
        RECIPE,
        DeclaredReadingFeatureInstance,
    )

    grade = reacquire_record_feature_grade(connection, request.selection)
    fitted = _fit_feature_value(grade, algorithm=request.algorithm, assumptions=request.assumptions)
    policy = None
    if fitted.instance is not None:
        checked = DeclaredReadingFeatureInstance(
            feature=fitted.instance,
            family_contract=grade.frame.family_contract,
            reading_recipe=grade.frame.reading_recipe,
        )
        policy = {
            "version": "reading-feature-policy-2",
            "recipe": RECIPE,
            "subset": grade.frame.subset,
            "feature_instances": source_value([checked.model_dump(mode="json")]),
        }
    return {
        "selection": request.selection.model_dump(mode="json"),
        "fit": fitted.model_dump(mode="json"),
        "reading_policy": policy,
    }
