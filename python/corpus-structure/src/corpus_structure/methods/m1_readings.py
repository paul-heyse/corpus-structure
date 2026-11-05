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
    source_dependencies: Literal["source_view_product", "retained_source_result"] = (
        "source_view_product"
    )
    source_dependency_method: Literal["extract.m1_candidates"] = UPSTREAM
    subset: str = Field(default="statistics-m1-source-readings-2", min_length=1)
    feature_instances: tuple[FeatureInstance, ...] = ()
    # Historical reports may predate in-report schema/context retention. An explicitly
    # supplied exact declaration/bounds is verified against their retained digests.
    retained_schema_packs: dict[str, dict[str, Any]] = Field(default_factory=dict)
    retained_context_bounds: dict[str, int] | None = None
    retained_source_tasks: tuple[int, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def historical_dependencies(cls, value):
        if isinstance(value, dict) and value.get("retained_source_tasks"):
            value = dict(value)
            value["source_dependencies"] = "retained_source_result"
        return value

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
        if any(type(task) is not int or task < 1 for task in self.retained_source_tasks) or len(
            set(self.retained_source_tasks)
        ) != len(self.retained_source_tasks):
            raise ValueError("historical source tasks require distinct positive IDs")
        if (self.source_dependencies == "retained_source_result") != bool(
            self.retained_source_tasks
        ):
            raise ValueError("historical source mode requires explicit retained source tasks")
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


def _historical(reader, view, cfg):
    matches, errors = [], []
    for task_id in cfg.retained_source_tasks:
        try:
            matches.append(reader.retained_source_result(view.ref.id, task_id, UPSTREAM))
        except ValueError as error:
            errors.append(f"task {task_id}: {error}")
    if len(matches) != 1:
        raise ValueError(
            "historical source task correspondence is missing or ambiguous: " + "; ".join(errors)
        )
    return matches[0]


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
    version = "3"
    family = MethodFamily.RESOLVE
    unit_type = TaskUnitType.SOURCE_VIEW
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = M1ReadingConfig
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    def select(self, run, cfg):
        if cfg.retained_source_tasks:
            selected = []
            candidates = tuple(view for view in run.reader.source_views() if view.analysis_eligible)
            for task_id in cfg.retained_source_tasks:
                matches, errors = [], []
                for view in candidates:
                    try:
                        run.reader.retained_source_result(view.id, task_id, UPSTREAM)
                        matches.append(view)
                    except ValueError as error:
                        errors.append(str(error))
                if len(matches) != 1:
                    raise ValueError(
                        f"historical task {task_id} has no unique selected source: "
                        + "; ".join(errors)
                    )
                selected.append(matches[0])
            if len({view.id for view in selected}) != len(selected):
                raise ValueError("historical tasks duplicate a current source selection")
            return tuple(UnitRef(TaskUnitType.SOURCE_VIEW, view.id, view.key) for view in selected)
        return tuple(
            UnitRef(TaskUnitType.SOURCE_VIEW, view.id, view.key)
            for view in run.reader.source_views()
            if view.analysis_eligible
        )

    def input_digest(self, unit, cfg):
        view = unit.run.reader.source_view(unit.ref.unit_id)
        if cfg.retained_source_tasks:
            retained = _historical(unit.run.reader, view, cfg)
            packet = dict(
                recipe=cfg.recipe,
                retained_task_id=retained.task_id,
                retained_release_id=retained.release_id,
                retained_result_digest=retained.body_digest,
                retained_source_bindings=retained.source_bindings,
            )
        else:
            packet = dict(recipe=cfg.recipe, upstream=_upstream(unit.run.reader, view))
        return Digest(canonical_bytes(packet))

    def interpretation_request(self, group):
        """No coupling factors are manufactured from independent compatibility scores."""
        return None

    def run(self, units, cfg, ctx):
        results = []
        for unit in units:
            ctx.check_active()
            view = ctx.reader.source_view(unit.ref.unit_id)
            from .contribution_adapter import (
                replay_historical_contributions,
                replay_retained_contributions,
            )

            retained = _historical(ctx.reader, view, cfg) if cfg.retained_source_tasks else None
            upstream = retained.result if retained else _upstream(ctx.reader, view)
            digest = (
                retained.body_digest if retained else sha256(canonical_bytes(upstream)).hexdigest()
            )
            detail = upstream["parse_detail"]
            contribution_batch = (
                replay_historical_contributions(ctx.reader, view, retained)
                if retained
                else replay_retained_contributions(
                    ctx.reader,
                    view,
                    upstream,
                    schema_packs=cfg.retained_schema_packs,
                    context_bounds=cfg.retained_context_bounds,
                )
            )
            # Local attachment questions are inventoried independently of record assembly.
            # No real factor policy currently applies: record the exact unavailable solve,
            # retaining all useful returned products rather than manufacturing probabilities.
            from .local_interpretation import local_question_operation

            local_dependencies = tuple(
                sorted(
                    {
                        dependency
                        for contribution in contribution_batch.contributions
                        for dependency in contribution.get("computation_dependencies", ())
                    }
                    | {"retained-result:" + digest}
                )
            )
            if contribution_batch.contributions:
                local_operation = local_question_operation(
                    question=(
                        "which contextual role or attachment is supported "
                        "for these retained source contributions?"
                    ),
                    contributions=contribution_batch.contributions,
                    dependency_ids=local_dependencies,
                )
                if retained:
                    local_operation.update(
                        retained_task_id=retained.task_id,
                        retained_result_digest=retained.body_digest,
                        retained_source_bindings=retained.source_bindings,
                    )
                contribution_batch = type(contribution_batch)(
                    (*contribution_batch.operations, local_operation),
                    contribution_batch.contributions,
                    contribution_batch.coordinate_texts,
                )
            details: dict[str, Any] = dict(
                recipe=cfg.recipe,
                source_pin=asdict(NativeSourcePin.from_source(native_source_frame(view, ()))),
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
            if retained:
                details["retained_input"] = dict(
                    selected_task_id=retained.selected_task_id,
                    task_id=retained.task_id,
                    run_id=retained.run_id,
                    release_id=retained.release_id,
                    result_digest=retained.body_digest,
                    source_bindings=retained.source_bindings,
                    original_source_pin=detail["source_pin"],
                    preserved_predecessor_records=len(upstream.get("records", ())),
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
            # Historical whole records remain under their original release. This new
            # operation derives local products; it never copies/relabels old records.
            for original in () if retained else upstream.get("records", ()):
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
                                if "local_interpretation" not in operation
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
