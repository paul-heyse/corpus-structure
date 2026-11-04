"""Protected finite-frame policy fitting through the existing evaluator store.

Only this evaluator operation joins source-only adjudication to immutable producer
candidates. Production receives fitted parameters and evaluation identities, never labels.
A finite converged fit is not a quality or population-generalization claim.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from sqlalchemy import Connection, select

from corpus_structure.semantic.contracts import require_bound_operation
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.record_policy import (
    Family,
    FeatureInstance,
    PolicyApplicability,
    RecordAcceptanceInstance,
    RecordAlgorithm,
    derive_record_features,
    score_record,
)
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.types import PreparedRelease

from .record_alignment import RecordSide, align_records
from .record_fitting import (
    FeatureFitObservation,
    FinalEventObservation,
    FittingFrame,
    WholeReadingLabel,
    fit_final_event_calibration,
    fit_whole_reading_features,
)
from .record_references import decode_frame, reference_evaluate
from .semantic import ReferenceError, ReferenceReport, _call

EVENT_PROCEDURE = "independent-complete-reading-logistic-1"


@dataclass(frozen=True)
class PolicyFitOutcome:
    """Insufficient support remains provisional and creates no production authority."""

    diagnostics: Mapping[str, Any]
    report: ReferenceReport | None = None


def _digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def whole_reading_correct(
    prepared: PreparedRelease,
    candidate: Mapping[str, Any],
    reference_records: Sequence[Mapping[str, Any]],
    frame,
    *,
    coordinate_texts: Sequence[Mapping[str, Any]],
    reference_prepared: PreparedRelease | None = None,
    prediction_frame=None,
    prediction_coordinate_texts: Sequence[Mapping[str, Any]] | None = None,
    correspondence: Sequence[Mapping[str, Any]] | None = None,
) -> bool:
    """Apply the same full-reading semantics without changing sealed standing or IDs.

    An accepted comparison copy exists only in this private evaluator calculation. It
    does not enter a producer result, public projection or admission decision.
    """
    reference_prepared = reference_prepared or prepared
    prediction_frame = prediction_frame or frame
    options = dict(
        coordinate_texts=coordinate_texts,
        prediction_prepared=prepared,
        prediction_coordinate_texts=prediction_coordinate_texts,
        correspondence=correspondence,
    )
    # Validate source/frame/policy even when the candidate cannot be accepted.
    align_records(
        RecordSide(frame, reference_records),
        RecordSide(prediction_frame, (candidate,)),
        reference_prepared,
        **options,
    )
    comparison = dict(candidate, standing="accepted")
    try:
        aligned = align_records(
            RecordSide(frame, reference_records),
            RecordSide(prediction_frame, (comparison,)),
            reference_prepared,
            **options,
        )
    except ValueError:
        # The original candidate was valid; accepted-only completeness/precision
        # requirements can legitimately make this full reading incorrect.
        return False
    if correspondence is not None:
        return any(
            value["prediction_record_id"] == candidate["record_id"] and "full" in value["tiers"]
            for value in aligned.match_bindings
        )
    return candidate["record_id"] in aligned.matches["full"]


def _diagnostics(record: Mapping[str, Any], detail: Mapping[str, Any]) -> list[dict[str, Any]]:
    # One shared producer recipe retains first exact diagnostics for a native group.
    from corpus_structure.methods.m1_readings import reading_diagnostics

    return reading_diagnostics(record, detail)


def fit_record_policy(
    conn: Connection,
    *,
    project_id: str,
    run_id: int,
    set_id: int,
    family: Family,
    subset: str,
    assumptions: str,
    algorithm: RecordAlgorithm | None = None,
    feature_evaluation_id: int | None = None,
    threshold: float = 0.99,
    threshold_procedure: str = "predeclared-fixed-whole-reading-probability-1",
) -> PolicyFitOutcome:
    """Fit features, or separately calibrate every eligible sealed final event.

    The native frame authenticates the completed cut, selected views, actual source
    origins and latest adjudicated snapshot before labels reach numerical code. No
    accepted-only score selection or producer-authored correctness input is accepted.
    """
    if not subset.strip() or not assumptions.strip():
        raise ReferenceError("policy fitting requires explicit subset and conditioning assumptions")
    kind = "feature_fit" if feature_evaluation_id is None else "final_event_calibration"
    raw = _call(
        conn,
        "SELECT eval.record_policy_prediction_frame(:p,:r,:s,:f,:k)",
        p=project_id,
        r=run_id,
        s=set_id,
        f=family,
        k=kind,
    ).scalar_one()
    prepared = open_release(conn, raw["release_id"])
    reference_prepared = open_release(conn, raw.get("reference_release_id", raw["release_id"]))
    require_bound_operation(prepared, "reference_record_calibrate")
    feature = None
    feature_evaluation_digest = None
    if feature_evaluation_id is not None:
        evaluations = table("eval.reference_evaluation")
        previous = (
            conn.execute(select(evaluations).where(evaluations.c.id == feature_evaluation_id))
            .mappings()
            .one()
        )
        product = previous["result"].get("policy_fit", {})
        if product.get("kind") != "feature_fit":
            raise ReferenceError("calibration requires an immutable protected feature-fit product")
        feature = FeatureInstance.model_validate_json(json.dumps(product["feature_instance"]))
        feature_evaluation_digest = previous["content_digest"]
        if algorithm is not None and algorithm != feature.algorithm:
            raise ReferenceError("calibration cannot change the frozen feature algorithm")
        if (prepared.release_id, family, subset) != (
            feature.applicability.release_id,
            feature.applicability.family,
            feature.applicability.subset,
        ):
            raise ReferenceError("calibration differs from frozen feature applicability")
        algorithm = feature.algorithm
    algorithm = algorithm or RecordAlgorithm()
    observations = []
    final_observations = []
    members: list[dict[str, Any]] = []
    coverage = []
    from .record_references import _coordinates, _prediction_coordinates
    from .semantic import _unit

    for unit in raw["units"]:
        frame = decode_frame(unit["source_frame"])
        prediction_frame = decode_frame(unit.get("prediction_frame", unit["source_frame"]))
        coverage.append(
            {
                "unit_id": unit["unit_id"],
                "source_view_id": unit["source_view_id"],
                "reports": [
                    {
                        "selected_task_id": report["selected_task_id"],
                        "outcome": report["outcome"],
                        "records": len(report["records"]),
                    }
                    for report in unit["reports"]
                ],
            }
        )
        reference = tuple(
            reference_prepared.validate_json("SourceRecord", canonical_bytes(record)).model_dump(
                mode="python", exclude_unset=True
            )
            for record in unit["reference_records"]
        )
        reports = tuple(
            (
                report,
                tuple(
                    prepared.validate_json("SourceRecord", canonical_bytes(record)).model_dump(
                        mode="python", exclude_unset=True
                    )
                    for record in report["records"]
                ),
            )
            for report in unit["reports"]
        )
        bound_unit = _unit(conn, unit["unit_id"])
        candidates = tuple(record for _, records in reports for record in records)
        coordinates = _coordinates(conn, reference_prepared, bound_unit, reference)
        prediction_coordinates = _prediction_coordinates(
            conn, prepared, run_id, prediction_frame, candidates
        )
        for report, records in reports:
            detail = source_python(report["parse_detail"]) if report["parse_detail"] else {}
            for record in records:
                correct = whole_reading_correct(
                    prepared,
                    record,
                    reference,
                    frame,
                    coordinate_texts=coordinates,
                    reference_prepared=reference_prepared,
                    prediction_frame=prediction_frame,
                    prediction_coordinate_texts=prediction_coordinates,
                    correspondence=unit.get("correspondence"),
                )
                label = WholeReadingLabel(
                    event_id=record["interpretation_id"],
                    origin_group=unit["origin_group"],
                    correct=correct,
                )
                diagnostics = _diagnostics(record, detail)
                vector = derive_record_features(
                    prepared, record, algorithm=algorithm, diagnostics=diagnostics
                )
                score = 0.0
                if feature is not None:
                    events = [
                        event
                        for event in detail.get("record_policy_events", ())
                        if (event.get("record_id"), event.get("interpretation_id"))
                        == (record["record_id"], record["interpretation_id"])
                        and event.get("feature_instance_digest") == feature.digest
                    ]
                    if len(events) != 1 or events[0].get("outcome") != "completed":
                        raise ReferenceError(
                            "calibration requires every candidate's unique completed event"
                        )
                    event = events[0]
                    # The sealed diagnostics participate in the exact score input. They
                    # remain diagnostics, never labels or synthetic independent votes.
                    diagnostics = event["diagnostics"]
                    vector = derive_record_features(
                        prepared, record, algorithm=algorithm, diagnostics=diagnostics
                    )
                    if event["feature_input_digest"] != vector.input_digest:
                        raise ReferenceError("sealed final event has different feature input")
                    if event["event_procedure"] != EVENT_PROCEDURE:
                        raise ReferenceError("unsupported final-event interpretation procedure")
                    score = event["final_event_score"]
                    expected_score = score_record(
                        feature, vector, subset=subset
                    ).compatibility_potential
                    if not math.isclose(score, expected_score, rel_tol=1e-12, abs_tol=1e-12):
                        raise ReferenceError(
                            "sealed final event differs from released feature scorer"
                        )
                    final_observations.append(
                        FinalEventObservation(
                            feature_instance_digest=feature.digest,
                            event_procedure=EVENT_PROCEDURE,
                            final_event_score=score,
                            label=label,
                        )
                    )
                else:
                    observations.append(FeatureFitObservation(features=vector, label=label))
                members.append(
                    dict(
                        record_id=record["record_id"],
                        interpretation_id=record["interpretation_id"],
                        selected_task_id=report["selected_task_id"],
                        source=report["source"],
                        feature_input_digest=vector.input_digest,
                        score=score,
                        correct=correct,
                    )
                )
    if not members:
        raise ReferenceError(
            "policy fit has no candidate events; no-output coverage is retained separately"
        )
    frame = FittingFrame(
        frame_digest=_digest(raw),
        reference_digest=raw["reference_digest"],
        coverage_digest=_digest(coverage),
        event_ids=tuple(member["interpretation_id"] for member in members),
        provenance=f"protected-evaluator:set:{set_id}:run:{run_id}:{kind}",
        assumptions=assumptions,
    )
    instance = None
    if feature is None:
        fitted = fit_whole_reading_features(
            observations,
            algorithm=algorithm,
            applicability=PolicyApplicability(
                release_id=prepared.release_id,
                family=family,
                subset=subset,
                assumptions=assumptions,
            ),
            frame=frame,
        )
        if fitted.instance is None:
            return PolicyFitOutcome(fitted.diagnostics.model_dump(mode="json"))
        feature = fitted.instance
        diagnostics = fitted.diagnostics
    else:
        fitted_calibration = fit_final_event_calibration(
            final_observations, feature=feature, frame=frame, event_procedure=EVENT_PROCEDURE
        )
        if fitted_calibration.calibration is None:
            return PolicyFitOutcome(fitted_calibration.diagnostics.model_dump(mode="json"))
        diagnostics = fitted_calibration.diagnostics
        instance = RecordAcceptanceInstance(
            feature=feature,
            calibration=fitted_calibration.calibration,
            threshold=threshold,
            threshold_procedure=threshold_procedure,
            conditioning_assumptions=assumptions,
        )
    feature_payload = feature.model_dump(mode="json")
    product: dict[str, Any] = dict(
        protocol="source-record-policy-fit-1",
        kind=kind,
        family=family,
        subset=subset,
        feature_instance=feature_payload,
        feature_instance_digest=feature.digest,
        feature_canonical_json=canonical_bytes(feature_payload).decode(),
        event_procedure=EVENT_PROCEDURE,
        event_frame_digest=_digest(members),
        event_frame_canonical_json=canonical_bytes(members).decode(),
        event_members=members,
        coverage_digest=frame.coverage_digest,
        assumptions=assumptions,
    )
    if instance is not None:
        if feature_evaluation_id is None or feature_evaluation_digest is None:
            raise ReferenceError("calibration export has no protected feature-fit authority")
        product.update(
            acceptance_instance=instance.model_dump(mode="json"),
            instance_digest=instance.digest,
            instance_canonical_json=canonical_bytes(instance.model_dump(mode="json")).decode(),
            feature_evaluation_id=feature_evaluation_id,
            feature_evaluation_digest=feature_evaluation_digest,
        )
    prepared.validate_json("RecordPolicyCalibrationProduct", canonical_bytes(product))
    report = reference_evaluate(
        conn, project_id=project_id, run_id=run_id, set_id=set_id, policy_fit=product
    )
    return PolicyFitOutcome(diagnostics.model_dump(mode="json"), report)
