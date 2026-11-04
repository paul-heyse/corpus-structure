"""Finite M1 scoring contracts. Numerical readiness grants no native admission authority.

Feature scores are supervised whole-reading compatibility potentials, never independent
votes, log-likelihood ratios or evidence of scientific truth. Production receives JSON
parameters and evidence identities; fitting labels belong only to the evaluator module.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, StringConstraints, model_validator
from scipy.special import expit

from .identity import canonical_bytes
from .types import PreparedRelease

Nonempty = Annotated[str, StringConstraints(pattern=r"\S")]
Digest = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
Family = Literal["definition", "assertion", "measurement", "table", "formula_context"]


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True, validate_default=True)

    @property
    def digest(self) -> str:
        return sha256(canonical_bytes(self.model_dump(mode="json"))).hexdigest()


class FeatureDefinition(FrozenContract):
    name: Nonempty
    group: Literal["structure", "evidence", "semantics", "transformation", "diagnostics"]


FEATURES = (
    FeatureDefinition(name="present_fraction", group="structure"),
    FeatureDefinition(name="located_fraction", group="evidence"),
    FeatureDefinition(name="exact_anchor_fraction", group="evidence"),
    FeatureDefinition(name="unresolved_fraction", group="semantics"),
    FeatureDefinition(name="classified_fraction", group="semantics"),
    FeatureDefinition(name="changed_fraction", group="transformation"),
    FeatureDefinition(name="alternative_count", group="structure"),
    FeatureDefinition(name="diagnostic_count", group="diagnostics"),
)


class RecordAlgorithm(FrozenContract):
    version: Nonempty = "m1-grouped-reading-logistic-1"
    feature_version: Literal["sealed-record-groups-1"] = "sealed-record-groups-1"
    features: tuple[FeatureDefinition, ...] = FEATURES
    positive_class: Literal[1] = 1
    score_meaning: Literal["whole_reading_compatibility_potential"] = (
        "whole_reading_compatibility_potential"
    )
    solver: Literal["lbfgs"] = "lbfgs"
    l1_ratio: FiniteFloat = 0.0
    inverse_regularization: Annotated[FiniteFloat, Field(gt=0)] = 1.0
    tolerance: Annotated[FiniteFloat, Field(gt=0)] = 1e-8
    max_iterations: Annotated[int, Field(gt=0)] = 1000
    minimum_per_class: Annotated[int, Field(ge=2)] = 2
    scaling: Literal["training-population-standard-deviation-1"] = (
        "training-population-standard-deviation-1"
    )
    weighting: Literal["explicit-positive-sample-weight-no-class-weight-1"] = (
        "explicit-positive-sample-weight-no-class-weight-1"
    )

    @model_validator(mode="after")
    def valid_features(self) -> Self:
        if self.l1_ratio != 0.0:
            raise ValueError("released lbfgs algorithm requires L2 regularization")
        names = tuple(feature.name for feature in self.features)
        known = {feature.name: feature for feature in FEATURES}
        if not names or len(set(names)) != len(names) or any(
            known.get(feature.name) != feature for feature in self.features
        ):
            raise ValueError(
                "features require a unique ordered subset of released grouped features"
            )
        return self

    @property
    def feature_signature(self) -> str:
        return sha256(
            canonical_bytes([self.feature_version, [f.model_dump() for f in self.features]])
        ).hexdigest()


DEFAULT_ALGORITHM = RecordAlgorithm()


class PolicyApplicability(FrozenContract):
    release_id: Nonempty
    family: Family
    subset: Nonempty
    assumptions: Nonempty


class RecordFeatures(FrozenContract):
    record_id: Nonempty
    interpretation_id: Nonempty
    release_id: Nonempty
    family: Family
    feature_signature: Digest
    names: tuple[str, ...]
    values: tuple[FiniteFloat | None, ...]
    unavailable: tuple[str, ...] = ()
    input_digest: Digest

    @model_validator(mode="after")
    def aligned(self) -> Self:
        if len(self.names) != len(self.values) or len(set(self.names)) != len(self.names):
            raise ValueError("feature names and values require one declared order")
        return self


class LinearParameters(FrozenContract):
    feature_signature: Digest
    names: tuple[Nonempty, ...]
    coefficients: tuple[FiniteFloat, ...]
    center: tuple[FiniteFloat, ...]
    scale: tuple[Annotated[FiniteFloat, Field(gt=0)], ...]
    intercept: FiniteFloat
    positive_class: Literal[1] = 1

    @model_validator(mode="after")
    def dimensions(self) -> Self:
        size = len(self.names)
        if not size or len(set(self.names)) != size or any(
            len(values) != size for values in (self.coefficients, self.center, self.scale)
        ):
            raise ValueError("finite parameters must align with unique feature order and scaling")
        return self


class FitDiagnostics(FrozenContract):
    partition: Literal["feature_fit", "final_event_calibration"]
    frame_digest: Digest
    reference_digest: Digest
    coverage_digest: Digest
    provenance: Nonempty
    negative_count: Annotated[int, Field(ge=0)]
    positive_count: Annotated[int, Field(ge=0)]
    converged: bool
    iterations: Annotated[int, Field(ge=0)]
    standing: Literal["fitted", "provisional"]
    reason: Nonempty
    library_version: Nonempty = "scikit-learn-1.9.1"

    @model_validator(mode="after")
    def fitted_support(self) -> Self:
        if self.standing == "fitted" and (
            not self.converged or min(self.negative_count, self.positive_count) < 2
        ):
            raise ValueError("fitted standing requires convergence and both correctness classes")
        return self


class FeatureInstance(FrozenContract):
    algorithm: RecordAlgorithm
    applicability: PolicyApplicability
    parameters: LinearParameters
    fit: FitDiagnostics

    @model_validator(mode="after")
    def compatible(self) -> Self:
        if (
            self.parameters.feature_signature != self.algorithm.feature_signature
            or self.parameters.names != tuple(f.name for f in self.algorithm.features)
            or self.fit.partition != "feature_fit"
            or self.fit.standing != "fitted"
            or self.fit.library_version != "scikit-learn-1.9.1"
            or min(self.fit.negative_count, self.fit.positive_count)
            < self.algorithm.minimum_per_class
        ):
            raise ValueError("feature instance differs from its algorithm or fitted support")
        return self


class FinalEventCalibration(FrozenContract):
    method: Literal["held-out-final-event-sigmoid-1"] = "held-out-final-event-sigmoid-1"
    feature_instance_digest: Digest
    event_procedure: Nonempty
    slope: FiniteFloat
    intercept: FiniteFloat
    fit: FitDiagnostics
    assumptions: Nonempty
    frame_selection: Literal["complete-predeclared-eligible-scored-events"] = (
        "complete-predeclared-eligible-scored-events"
    )
    coverage_digest: Digest

    @model_validator(mode="after")
    def held_out(self) -> Self:
        if (
            self.fit.partition != "final_event_calibration"
            or self.fit.standing != "fitted"
            or self.fit.library_version != "scikit-learn-1.9.1"
        ):
            raise ValueError("calibration requires separately fitted final-event labels")
        return self


class RecordAcceptanceInstance(FrozenContract):
    feature: FeatureInstance
    calibration: FinalEventCalibration | None = None
    threshold: Annotated[FiniteFloat, Field(gt=0, le=1)]
    threshold_procedure: Nonempty
    conditioning_assumptions: Nonempty

    @model_validator(mode="after")
    def frozen_feature(self) -> Self:
        if self.calibration is not None and (
            self.calibration.feature_instance_digest != self.feature.digest
            or self.calibration.fit.frame_digest == self.feature.fit.frame_digest
            or self.calibration.fit.reference_digest == self.feature.fit.reference_digest
            or min(self.calibration.fit.negative_count, self.calibration.fit.positive_count)
            < self.feature.algorithm.minimum_per_class
        ):
            raise ValueError("calibration must bind the frozen feature instance and held-out frame")
        return self


class RecordScore(FrozenContract):
    feature_instance_digest: Digest
    feature_input_digest: Digest
    record_id: Nonempty
    interpretation_id: Nonempty
    compatibility_potential: FiniteFloat
    uncalibrated_probability: Annotated[FiniteFloat, Field(ge=0, le=1)]
    standing: Literal["provisional_whole_reading_score"] = "provisional_whole_reading_score"


class NativeAdmissionProposal(FrozenContract):
    """A request for native validation, deliberately incapable of granting acceptance."""

    instance_digest: Digest
    record_id: Nonempty
    interpretation_id: Nonempty
    final_event_score: FiniteFloat | None
    calibrated_probability: Annotated[FiniteFloat, Field(ge=0, le=1)] | None
    blockers: tuple[str, ...]
    eligible_for_native_validation: bool
    standing: Literal["candidate"] = "candidate"
    required_authority: Literal["native-evaluator-authorized-exact-instance-binding"] = (
        "native-evaluator-authorized-exact-instance-binding"
    )


def _row(record: BaseModel | Mapping[str, Any]) -> dict[str, Any]:
    return record.model_dump(mode="python") if isinstance(record, BaseModel) else dict(record)


def _roles(prepared: PreparedRelease, row: Mapping[str, Any]):
    definition = prepared.index.definitions[row["contract"]]
    if "SemanticRecordFields" not in definition.ancestors:
        raise ValueError("record requires a released family contract")
    props = {p.name: p for p in definition.properties}
    if props["family"].equals_string != row["family"]:
        raise ValueError("record family differs from released contract")
    roles = {k: p for k, p in props.items() if k not in {"family", "occurrence_recipe"}}
    fields = {field["role"]: field for field in row["fields"]}
    if len(fields) != len(row["fields"]) or fields.keys() != roles.keys():
        raise ValueError("record fields differ from complete released role universe")
    return roles, fields


def derive_record_features(
    prepared: PreparedRelease,
    record: BaseModel | Mapping[str, Any],
    *,
    algorithm: RecordAlgorithm = DEFAULT_ALGORITHM,
    diagnostics: Sequence[Mapping[str, Any]] | None = None,
) -> RecordFeatures:
    """Derive grouped signals from a sealed, already source-validated reading.

    Explicit diagnostics must belong to this reading's sealed producer result. None means
    unavailable, never zero. Raw provider confidence is unavailable in sealed records and
    cannot be substituted with shape success or a made-up constant. Native authenticates
    the sealed payload and these input dependencies before any publication.
    """
    row = _row(record)
    _, fields = _roles(prepared, row)
    anchors = row.get("anchors", ())
    n = len(fields)
    counts = {
        "present_fraction": sum(f["state"] == "present" for f in fields.values()) / n,
        "located_fraction": sum(f["evidence_status"] == "available" for f in fields.values()) / n,
        "exact_anchor_fraction": (
            sum(a["precision"] == "exact" for a in anchors) / len(anchors) if anchors else None
        ),
        "unresolved_fraction": sum(f["state"] == "unresolved" for f in fields.values()) / n,
        "classified_fraction": sum(f["kind"] == "classified" for f in fields.values()) / n,
        "changed_fraction": (
            sum(f["kind"] in {"normalized", "derived"} for f in fields.values()) / n
        ),
        "alternative_count": float(sum(len(f.get("alternatives", ())) for f in fields.values())),
        "diagnostic_count": float(len(diagnostics)) if diagnostics is not None else None,
    }
    names = tuple(feature.name for feature in algorithm.features)
    return RecordFeatures(
        record_id=row["record_id"],
        interpretation_id=row["interpretation_id"],
        release_id=prepared.release_id,
        family=row["family"],
        feature_signature=algorithm.feature_signature,
        names=names,
        values=tuple(counts[name] for name in names),
        unavailable=("provider.raw_confidence", *tuple(k for k, v in counts.items() if v is None)),
        input_digest=sha256(canonical_bytes([row, diagnostics])).hexdigest(),
    )


def score_record(
    feature: FeatureInstance, vector: RecordFeatures, *, subset: str
) -> RecordScore:
    applicability, parameters = feature.applicability, feature.parameters
    if (vector.release_id, vector.family, subset) != (
        applicability.release_id, applicability.family, applicability.subset
    ):
        raise ValueError("record is outside exact instance release/family/subset applicability")
    if vector.feature_signature != parameters.feature_signature or vector.names != parameters.names:
        raise ValueError("record feature signature or order differs from fitted instance")
    if any(value is None for value in vector.values):
        raise ValueError("required raw feature is unavailable; imputation is not declared")
    values = tuple(float(value) for value in vector.values if value is not None)
    potential = math.fsum(
        ((value - center) / scale) * coefficient
        for value, center, scale, coefficient in zip(
            values, parameters.center, parameters.scale, parameters.coefficients, strict=True
        )
    ) + parameters.intercept
    if not math.isfinite(potential):
        raise ArithmeticError("nonfinite whole-reading potential")
    return RecordScore(
        feature_instance_digest=feature.digest,
        feature_input_digest=vector.input_digest,
        record_id=vector.record_id,
        interpretation_id=vector.interpretation_id,
        compatibility_potential=potential,
        uncalibrated_probability=float(expit(potential)),
    )


def assess_record_admission(
    prepared: PreparedRelease,
    record: BaseModel | Mapping[str, Any],
    instance: RecordAcceptanceInstance,
    *,
    subset: str,
    final_event_score: float | None,
    event_procedure: str,
) -> NativeAdmissionProposal:
    """Refuse incomplete readings and prepare a native request, never accepted standing.

    The final score is the whole event AFTER any constraints/coupling. This pure function
    cannot authenticate its membership or evaluator authority. Native must match the exact
    instance, completed task/score universe and protected evaluation product independently.
    """
    row = _row(record)
    roles, fields = _roles(prepared, row)
    blockers = []
    app = instance.feature.applicability
    if (prepared.release_id, row["family"], subset) != (app.release_id, app.family, app.subset):
        blockers.append("outside_instance_applicability")
    if row["policy_version"] != instance.feature.algorithm.version:
        blockers.append("algorithm_policy_version_mismatch")
    sets = {e["set_id"]: e for e in row.get("evidence_sets", ())}
    anchors = {a["anchor_id"]: a for a in row.get("anchors", ())}
    for role, field in fields.items():
        role_type = prepared.index.definitions[roles[role].range]
        required = "RequiredRecordField" in role_type.ancestors
        changing = "MeaningChangingRecordField" in role_type.ancestors
        if required and field["state"] != "present":
            blockers.append(f"required_role_not_present:{role}")
        if changing and field["state"] == "unresolved":
            blockers.append(f"unresolved_meaning:{role}")
        used = tuple(field.get("evidence_sets", ()))
        if (required or changing) and (
            field.get("evidence_status") != "available" or not used
        ):
            blockers.append(f"missing_located_evidence:{role}")
        for key in used:
            evidence = sets.get(key)
            if evidence is None or evidence["role"] != role or not evidence["anchors"]:
                blockers.append(f"invalid_evidence_set:{role}")
                continue
            for anchor in evidence["anchors"]:
                piece = anchors.get(anchor)
                if piece is None or piece["precision"] == "unavailable" or (
                    field["kind"] == "literal" and piece["precision"] != "exact"
                ):
                    blockers.append(f"unlocated_field_evidence:{role}")
    probability = None
    calibration = instance.calibration
    if final_event_score is not None and (
        type(final_event_score) not in (float, int) or not math.isfinite(final_event_score)
    ):
        raise ValueError("final-event score must be finite")
    if calibration is None:
        blockers.append("no_final_event_calibration")
    elif event_procedure != calibration.event_procedure:
        blockers.append("final_event_procedure_mismatch")
    elif final_event_score is None:
        blockers.append("missing_final_event_score")
    else:
        value = calibration.slope * final_event_score + calibration.intercept
        if not math.isfinite(value):
            raise ArithmeticError("nonfinite calibrated event predictor")
        probability = float(expit(value))
        if probability < instance.threshold:
            blockers.append("below_calibrated_threshold")
    return NativeAdmissionProposal(
        instance_digest=instance.digest,
        record_id=row["record_id"],
        interpretation_id=row["interpretation_id"],
        final_event_score=final_event_score,
        calibrated_probability=probability,
        blockers=tuple(dict.fromkeys(blockers)),
        eligible_for_native_validation=not blockers,
    )
