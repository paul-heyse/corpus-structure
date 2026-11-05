"""Recompute reading interpretation/scores over retained CPU extraction products.

Changing finite feature parameters does not change or repeat the upstream model operation.
This method has no evaluator credentials, calibration labels or publication authority.
"""

import json
from dataclasses import asdict
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from corpus_structure.core.method import CoverageDraft, Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.record_contracts import interpretation_identity
from corpus_structure.semantic.record_policy import (
    FeatureInstance,
    derive_record_features,
    score_record,
)
from corpus_structure.semantic.source_contexts import NativeSourcePin

from .record_readings import interpret_candidate_readings

METHOD = "resolve.m1_readings"
UPSTREAM = "extract.m1_candidates"
RECIPE = "retained-m1-reading-resolution-1"
EVENT_PROCEDURE = "independent-complete-reading-logistic-1"


class M1ReadingConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    recipe: Literal["retained-m1-reading-resolution-1"] = RECIPE
    source_dependencies: Literal["source_view_product"] = "source_view_product"
    source_dependency_method: Literal["extract.m1_candidates"] = UPSTREAM
    subset: str = Field(default="statistics-m1-source-readings-2", min_length=1)
    feature_instances: tuple[FeatureInstance, ...] = ()
    # Historical reports may predate in-report schema/context retention. An explicitly
    # supplied exact declaration/bounds is verified against their retained digests.
    retained_schema_packs: dict[str, dict[str, Any]] = Field(default_factory=dict)
    retained_context_bounds: dict[str, int] | None = None

    @field_validator("feature_instances", mode="before")
    @classmethod
    def finite_json_instances(cls, value):
        return tuple(
            item
            if isinstance(item, FeatureInstance)
            else FeatureInstance.model_validate_json(json.dumps(item))
            for item in value
        )

    @model_validator(mode="after")
    def unambiguous_instances(self):
        keys = [
            (i.applicability.release_id, i.applicability.family, i.applicability.subset)
            for i in self.feature_instances
        ]
        if len(set(keys)) != len(keys):
            raise ValueError(
                "reading resolution has multiple feature instances for one applicability"
            )
        return self


def _upstream(reader, view):
    result = reader.source_result(view.ref.id, UPSTREAM)
    if result is None:
        raise ValueError("required upstream M1 candidate operation has no source result")
    if result["parse_detail"].get("source_pin") != asdict(
        NativeSourcePin.from_source(native_source_frame(view, ()))
    ):
        raise ValueError("upstream M1 candidate source binding differs")
    return result


def reading_diagnostics(row, details):
    """Select exact group diagnostics once even when the decoder repeats a group."""
    group_ids = {d for d in row["computation_dependencies"] if d.startswith("native-group:")}
    unique = {}
    for report in details.get("reports", ()):
        for diagnostic in report.get("diagnostics", ()):
            if diagnostic.get("group_dependency") in group_ids:
                key = canonical_bytes({k: v for k, v in diagnostic.items() if k != "group"})
                unique.setdefault(key, diagnostic)
    return list(unique.values())


class M1Readings:
    name = METHOD
    version = "2"
    family = MethodFamily.RESOLVE
    unit_type = TaskUnitType.SOURCE_VIEW
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = M1ReadingConfig
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    def select(self, run, cfg):
        return tuple(
            UnitRef(TaskUnitType.SOURCE_VIEW, view.id, view.key)
            for view in run.reader.source_views()
            if view.analysis_eligible
        )

    def input_digest(self, unit, cfg):
        view = unit.run.reader.source_view(unit.ref.unit_id)
        return Digest(
            canonical_bytes(dict(recipe=cfg.recipe, upstream=_upstream(unit.run.reader, view)))
        )

    def interpretation_request(self, group):
        """No coupling factors are manufactured from independent compatibility scores."""
        return None

    def run(self, units, cfg, ctx):
        results = []
        for unit in units:
            ctx.check_active()
            view = ctx.reader.source_view(unit.ref.unit_id)
            upstream = _upstream(ctx.reader, view)
            digest = sha256(canonical_bytes(upstream)).hexdigest()
            detail = upstream["parse_detail"]
            from .contribution_adapter import replay_retained_contributions

            contribution_batch = replay_retained_contributions(
                ctx.reader,
                view,
                upstream,
                schema_packs=cfg.retained_schema_packs,
                context_bounds=cfg.retained_context_bounds,
            )
            details: dict[str, Any] = dict(
                recipe=cfg.recipe,
                source_pin=detail["source_pin"],
                raw_candidate_result=dict(
                    method=UPSTREAM,
                    outcome=upstream["outcome"],
                    input_hash=upstream["input_hash"],
                    configuration_hash=upstream["configuration_hash"],
                    dependency_digest=digest,
                ),
                model_observations=detail.get("model_observations", []),
                record_policy_events=[],
                record_interpretation=[],
                standing="private_candidates",
            )
            if upstream["outcome"] == "failed":
                results.append(
                    UnitResult(
                        ref=unit.ref,
                        outcome=ObservationOutcome.PRODUCED
                        if contribution_batch.contributions
                        else ObservationOutcome.FAILED,
                        error=None
                        if contribution_batch.contributions
                        else "required upstream M1 candidate operation failed",
                        parse_detail=details,
                        contributions=contribution_batch.contributions,
                        contribution_operations=contribution_batch.operations,
                        contribution_coordinate_texts=contribution_batch.coordinate_texts,
                        coverage=(
                            CoverageDraft(
                                family="retained_contribution_recovery",
                                scope=view.ref.section_pointer,
                                outcome="failed",
                                reason="upstream failed; earlier returned parts remain private",
                            ),
                        ),
                    )
                )
                continue
            records, events = [], []
            for original in upstream.get("records", ()):
                ctx.check_active()
                row = ctx.reader.prepared.validate_json(
                    "SourceRecord", canonical_bytes(original)
                ).model_dump(mode="python", exclude_unset=True)
                if row["standing"] != "candidate":
                    raise ValueError("reading resolution requires private upstream candidates")
                instance = next(
                    (
                        i
                        for i in cfg.feature_instances
                        if (
                            i.applicability.release_id,
                            i.applicability.family,
                            i.applicability.subset,
                        )
                        == (ctx.reader.prepared.release_id, row["family"], cfg.subset)
                    ),
                    None,
                )
                row["computation_dependencies"] = tuple(
                    sorted(
                        {
                            *row["computation_dependencies"],
                            "reading-recipe:" + cfg.recipe,
                            "raw-candidate-result:" + digest,
                            *(("record-feature-instance:" + instance.digest,) if instance else ()),
                        }
                    )
                )
                row["interpretation_id"] = interpretation_identity(row)
                event: dict[str, Any] = dict(
                    record_id=row["record_id"],
                    interpretation_id=row["interpretation_id"],
                    feature_instance_digest=instance.digest if instance else None,
                    feature_input_digest=None,
                    event_procedure=EVENT_PROCEDURE,
                    final_event_score=None,
                    outcome="not_run",
                    diagnostics=["applicable fitted feature instance unavailable"],
                )
                if instance is not None:
                    diagnostics = reading_diagnostics(row, detail)
                    vector = derive_record_features(
                        ctx.reader.prepared,
                        row,
                        algorithm=instance.algorithm,
                        diagnostics=diagnostics,
                    )
                    event["feature_input_digest"] = vector.input_digest
                    event["feature_diagnostics"] = diagnostics
                    event["feature_input_canonical_json"] = canonical_bytes(
                        [row, diagnostics]
                    ).decode()
                    try:
                        score = score_record(instance, vector, subset=cfg.subset)
                        event.update(
                            final_event_score=score.compatibility_potential,
                            outcome="completed",
                            diagnostics=diagnostics,
                            score=score.model_dump(mode="json"),
                        )
                    except (ValueError, ArithmeticError) as error:
                        event.update(outcome="limited", diagnostics=[str(error)])
                events.append(event)
                records.append(row)
            details["record_policy_events"] = events
            details["record_interpretation"] = interpret_candidate_readings(
                records, request_factory=self.interpretation_request
            )
            details["seal"] = sha256(canonical_bytes(details)).hexdigest()
            ctx.check_active()
            results.append(
                UnitResult(
                    ref=unit.ref,
                    outcome=ObservationOutcome.PRODUCED
                    if records or contribution_batch.contributions
                    else ObservationOutcome.EMPTY,
                    records=tuple(records),
                    contributions=contribution_batch.contributions,
                    contribution_operations=contribution_batch.operations,
                    contribution_coordinate_texts=contribution_batch.coordinate_texts,
                    parse_detail=details,
                    coverage=(
                        CoverageDraft(
                            family="retained_contribution_recovery",
                            scope=view.ref.section_pointer,
                            outcome="partial"
                            if any(
                                operation["outcome"]
                                in {"unsupported", "limited", "failed", "not_run"}
                                for operation in contribution_batch.operations
                            )
                            else "complete",
                            reason="retained report recovery; unavailable inputs are explicit",
                        ),
                        CoverageDraft(
                            family="reading_resolution",
                            scope=view.ref.section_pointer,
                            outcome="complete",
                            reason=(
                                "retained candidates resolved; "
                                "scoring/coupling outcomes retained separately"
                            ),
                        ),
                    ),
                )
            )
        return tuple(results)
