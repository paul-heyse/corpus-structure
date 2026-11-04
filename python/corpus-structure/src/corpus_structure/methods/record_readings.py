"""Retained reading alternatives and the private bounded-interpreter integration seam.

Factor policies supply actual model inputs; extraction confidence is not a calibrated
potential. The independent candidate baseline remains available without such a policy.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.record_interpretation import (
    InterpretationRequest,
    MentionIdentityTypeRelation,
    TableHeaderRowCellUnitNote,
    ValuePropertyReferentCondition,
    interpret_records,
)


def _digest(value: Any) -> str:
    return sha256(canonical_bytes(_sealed_value(value))).hexdigest()


def _sealed_value(value):
    """Keep hard-zero and failed numerical inputs reconstructible in strict JSON."""
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite_float": repr(value)}
    if isinstance(value, dict):
        return {key: _sealed_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sealed_value(item) for item in value]
    return value


@dataclass(frozen=True)
class RetainedReadingGroup:
    """Complete alternatives for one actual occurrence; no cross-field Cartesian join.

    A request factory owns the semantic mapping onto one of the three templates,
    including genuine local/new identity proposals and all meaning-changing qualifiers.
    Absence of an applicable mapping or real factor policy returns None.
    """

    record_id: str
    family: str
    readings: tuple[Mapping[str, Any], ...]
    dependencies: tuple[str, ...]
    input_digest: str


def retained_reading_groups(
    records: Sequence[Mapping[str, Any]],
) -> tuple[RetainedReadingGroup, ...]:
    grouped: dict[str, dict[str, Mapping[str, Any]]] = {}
    for row in records:
        if row["standing"] != "candidate":
            raise ValueError("bounded interpretation consumes private candidate readings only")
        readings = grouped.setdefault(row["record_id"], {})
        identity = row["interpretation_id"]
        if identity in readings and readings[identity] != row:
            raise ValueError("conflicting retained reading identity")
        readings[identity] = row
    result = []
    for identity, by_reading in sorted(grouped.items()):
        readings = tuple(by_reading[key] for key in sorted(by_reading))
        if len({row["family"] for row in readings}) != 1:
            raise ValueError("one occurrence cannot have multiple released families")
        dependencies = tuple(
            sorted(
                {dependency for row in readings for dependency in row["computation_dependencies"]}
            )
        )
        result.append(
            RetainedReadingGroup(
                identity,
                readings[0]["family"],
                readings,
                dependencies,
                _digest(readings),
            )
        )
    return tuple(result)


def interpret_candidate_readings(
    records: Sequence[Mapping[str, Any]],
    *,
    request_factory: Callable[[RetainedReadingGroup], InterpretationRequest | None] | None = None,
) -> list[dict[str, Any]]:
    """Seal genuine retained inputs and actual pure results, without changing standing.

    Required dependencies include consumed/rejected observations, retrieval outcomes,
    model/context/selection recipes and policy inputs already attached to the records.
    Factories must add their factor, ontology and policy dependencies rather than replace
    these. A score/normalization is never synthesized when a factory is unavailable.
    """
    results = []
    for group in retained_reading_groups(records):
        row: dict[str, Any] = dict(
            record_id=group.record_id,
            family=group.family,
            interpretation_ids=[reading["interpretation_id"] for reading in group.readings],
            retained_input_digest=group.input_digest,
            dependencies=list(group.dependencies),
            independent_baseline="retained_complete_readings",
            coupling_enabled=False,
            probability_standing="not_computed",
        )
        request = request_factory(group) if request_factory else None
        if request is None:
            row.update(
                outcome="not_run", reason="applicable real factor/identity policy unavailable"
            )
        else:
            if not isinstance(
                request.template,
                (
                    ValuePropertyReferentCondition,
                    MentionIdentityTypeRelation,
                    TableHeaderRowCellUnitNote,
                ),
            ):
                raise ValueError("unsupported bounded reading template")
            if {event.key for event in request.events} != set(row["interpretation_ids"]):
                raise ValueError("interpretation events differ from retained complete readings")
            if request.selection.scope_id != group.record_id:
                raise ValueError("interpretation scope differs from retained occurrence")
            if not set(group.dependencies) <= {
                dependency.key for dependency in request.dependencies
            }:
                raise ValueError("interpretation omits retained computation dependencies")
            request_row = _sealed_value(asdict(request))
            result = _sealed_value(asdict(interpret_records(request)))
            row.update(
                request=request_row,
                request_digest=_digest(request_row),
                result=result,
                result_digest=_digest(result),
                outcome=result["outcome"],
                probability_standing=result["probability_standing"],
                reason=(
                    "private comparison only; production coupling awaits paired benefit evidence"
                ),
            )
        row["seal"] = _digest(row)
        results.append(row)
    return results


def native_model_observations(
    report, *, context, family: str, context_index: int
) -> list[dict[str, Any]]:
    """Project only actually returned native scores, retaining raw attachment/position data.

    No absent score gets a default. These observations share checkpoint/head/context and
    decoder dependencies; repeated windows do not become independent evidence.
    """
    from .record_assembly import native_group_identity

    observations = {}
    for group_index, group in enumerate(report.raw.get(family, ())):
        for field, output in group.items():
            if field == "confidence":
                confidence, raw = output, output
            elif isinstance(output, dict) and "confidence" in output:
                confidence, raw = output["confidence"], output
            else:
                continue
            row = dict(
                family=family,
                context_index=context_index,
                group_index=group_index,
                field=field,
                confidence=confidence,
                raw_output=raw,
                score_kind="native_group_confidence"
                if field == "confidence"
                else "native_field_confidence",
                score_standing="uncalibrated_decoder_output",
                source_view_id=context.primary.source_view_id,
                context_digest=context.dependency_digest,
                pack=report.pack,
                profile=report.profile,
                computation=report.computation,
                raw_report_digest=_digest(report.raw),
                group_dependency=native_group_identity(report, group_index, group),
                dependence_group=_digest([report.profile, context.primary.unit_ref, report.pack]),
                dependence_groups=dict(
                    checkpoint=report.profile,
                    passage=context.primary.unit_ref,
                    context=context.dependency_digest,
                    decoder=report.pack,
                ),
            )
            key = _digest({k: v for k, v in row.items() if k != "group_index"})
            if key in observations:
                observations[key]["group_indices"].append(group_index)
            else:
                row["group_indices"] = [group_index]
                row["observation_digest"] = key
                observations[key] = row
    return list(observations.values())
