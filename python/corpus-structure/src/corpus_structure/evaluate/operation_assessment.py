"""Protected, source-first operation references and deterministic local assessment.

The existing eval set/unit/pass/frame/evaluation store owns custody. These products
do not supply whole-reading labels, fitted probabilities, or publication authority.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, select

from corpus_structure.semantic.contracts import require_bound_operation
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.releases import open_release

from .record_references import PARTITIONS, source_units
from .semantic import ReferenceError, ReferenceReport, _call, _completed, _json, _unit, unit_passes

PROTOCOL = "source-operation-reference-1"
FRAME_PROTOCOL = "source-operation-frame-1"
EVALUATION_PROTOCOL = "source-operation-evaluation-1"
JUDGMENTS = ("supported", "unsupported", "ambiguous", "unassessed")


@dataclass(frozen=True)
class OperationEvaluationFrame:
    unit: str
    release_id: str
    guideline_version: str
    rubric_version: str
    context_policy: str
    operation_question: str
    operation_version: str
    domain: str
    direction: str
    pin: Mapping[str, Any]
    anchor_ids: tuple[str, ...] = ()
    related_pins: tuple[Mapping[str, Any], ...] = ()
    anchor_scopes: tuple[Mapping[str, Any], ...] = ()
    contribution_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if self.direction not in {"source_first", "output_first"}:
            raise ReferenceError("operation direction must be source_first or output_first")
        if self.direction == "source_first" and self.contribution_ids:
            raise ReferenceError("source-first selection cannot depend on emitted contributions")
        if self.direction == "output_first" and not self.contribution_ids:
            raise ReferenceError("output-first frame requires its frozen selected contribution IDs")
        for values in (self.anchor_ids, self.contribution_ids):
            if len(values) != len(set(values)):
                raise ReferenceError("operation frame repeats an identity")
        if any(
            not getattr(self, field).strip()
            for field in (
                "unit",
                "release_id",
                "guideline_version",
                "rubric_version",
                "context_policy",
                "operation_question",
                "operation_version",
                "domain",
            )
        ):
            raise ReferenceError("operation frame requires explicit versioned question and context")


@dataclass(frozen=True)
class OperationSourceOpportunity:
    """Independent native source scope, retained even when token alignment fails."""

    opportunity_id: str
    source_view_id: int
    start: int
    end: int
    facet: str
    source_state: str

    def __post_init__(self):
        if (
            not self.opportunity_id.strip()
            or not self.facet.strip()
            or any(type(v) is not int for v in (self.source_view_id, self.start, self.end))
            or self.source_view_id <= 0
            or not 0 <= self.start < self.end
        ):
            raise ReferenceError("opportunity requires a named exact native source scope")
        if self.source_state not in {
            "stated",
            "unstated",
            "inapplicable",
            "unresolved",
            "uninspected",
        }:
            raise ReferenceError("unsupported source opportunity state")


@dataclass(frozen=True, kw_only=True)
class OperationEvaluationFrameV2(OperationEvaluationFrame):
    source_group: str
    partition: str
    inspected_scope: str
    opportunities: tuple[OperationSourceOpportunity, ...]
    exposure_history: tuple[str, ...] = ()

    def __post_init__(self):
        super().__post_init__()
        if (
            not self.source_group.strip()
            or not self.inspected_scope.strip()
            or self.partition not in PARTITIONS
        ):
            raise ReferenceError(
                "operation frame requires source group, inspected scope and partition"
            )
        if not self.opportunities or len({v.opportunity_id for v in self.opportunities}) != len(
            self.opportunities
        ):
            raise ReferenceError("operation frame requires distinct source opportunities")
        views = {
            self.pin.get("source_view_id"),
            *(p.get("source_view_id") for p in self.related_pins),
        }
        if any(v.source_view_id not in views for v in self.opportunities):
            raise ReferenceError("source opportunity is outside frozen source pins")
        if self.exposure_history and self.partition in {
            "final_event_calibration",
            "final_assessment",
        }:
            raise ReferenceError("exposed source cannot supply a fresh held-out frame")


def encode_frame(frame: OperationEvaluationFrame, *, captured_coordinates=()) -> dict[str, Any]:
    return dict(
        protocol="source-operation-frame-2"
        if isinstance(frame, OperationEvaluationFrameV2)
        else FRAME_PROTOCOL,
        evaluation_frame=asdict(frame),
        captured_coordinates=list(captured_coordinates),
        context_dependency_digest=None,
    )


def decode_frame(value: Mapping[str, Any]) -> OperationEvaluationFrame:
    if value.get("protocol") not in {FRAME_PROTOCOL, "source-operation-frame-2"} or set(value) - {
        "protocol",
        "evaluation_frame",
        "captured_coordinates",
        "context_dependency_digest",
        "source_views",
    }:
        raise ReferenceError("unsupported immutable operation frame")
    try:
        raw = dict(value["evaluation_frame"])
        for field in ("anchor_ids", "related_pins", "anchor_scopes", "contribution_ids"):
            raw[field] = tuple(raw.get(field, ()))
        if value["protocol"] == "source-operation-frame-2":
            raw["opportunities"] = tuple(
                OperationSourceOpportunity(**v) for v in raw.get("opportunities", ())
            )
            raw["exposure_history"] = tuple(raw.get("exposure_history", ()))
            return OperationEvaluationFrameV2(**raw)
        return OperationEvaluationFrame(**raw)
    except (KeyError, TypeError, ValueError) as error:
        raise ReferenceError("invalid immutable operation frame") from error


@dataclass(frozen=True)
class OperationCase:
    """One independent question; alternatives contain exact permitted output fields.

    Anchor IDs come from independent source authoring. A case with an unstated
    source field requires explicit state capture; uninspected never implies absence. An output ID
    exists only for output-first cases. Explanation and provenance are mandatory.
    """

    case_id: str
    facet: str
    anchor_ids: tuple[str, ...]
    inspected_scope: str
    source_state: str
    judgment: str
    alternatives: tuple[Mapping[str, Any], ...]
    explanation: str
    assessor_provenance: Mapping[str, Any]
    contribution_kind: str = "proposal"
    contribution_id: str | None = None
    error_category: str | None = None
    candidate_selector: Mapping[str, Any] = field(default_factory=dict)
    permissible_anchor_sets: tuple[tuple[str, ...], ...] = ()
    expectation_mode: str = "structure"
    anchor_endpoint_role: str | None = None

    def __post_init__(self):
        if self.judgment not in JUDGMENTS or self.source_state not in {
            "stated",
            "unstated",
            "uninspected",
            "unresolved",
        }:
            raise ReferenceError("unknown operation judgment or source field state")
        if self.expectation_mode not in {"structure", "absence_detection"}:
            raise ReferenceError(
                "operation expectation must declare structure or absence_detection"
            )
        if self.anchor_endpoint_role is not None and (
            self.contribution_kind not in {"proposal", "relation"}
            or not isinstance(self.anchor_endpoint_role, str)
            or not self.anchor_endpoint_role.strip()
        ):
            raise ReferenceError(
                "endpoint anchored assessment requires a proposal or relation and a declared role"
            )
        if not all(
            (
                self.case_id,
                self.facet,
                self.inspected_scope,
                self.explanation,
                self.assessor_provenance,
            )
        ):
            raise ReferenceError(
                "case requires inspected scope, explanation and assessor provenance"
            )
        if self.source_state == "uninspected" and self.judgment != "unassessed":
            raise ReferenceError("uninspected source cannot supply a local truth label")
        if self.source_state == "stated" and self.judgment == "supported" and not self.alternatives:
            raise ReferenceError("stated supported case requires independent expected structure")
        if any(not isinstance(value, Mapping) or not value for value in self.alternatives):
            raise ReferenceError("permissible alternatives require nonempty exact structures")


def decode_authored(authored: bytes, frame: OperationEvaluationFrame) -> dict[str, Any]:
    if not isinstance(authored, bytes):
        raise TypeError("operation pass must retain exact submitted bytes")
    try:
        payload = json.loads(authored)
        expected = dict(
            protocol=PROTOCOL,
            release_id=frame.release_id,
            unit_ref=frame.unit,
            guideline=frame.guideline_version,
            rubric_version=frame.rubric_version,
            context_policy=frame.context_policy,
            operation_question=frame.operation_question,
            operation_version=frame.operation_version,
            domain=frame.domain,
            direction=frame.direction,
        )
        if set(payload) - {*expected, "reason", "cases", "adjudication_passes"}:
            raise ReferenceError("unknown operation pass fields")
        if (
            any(payload.get(key) != value for key, value in expected.items())
            or not payload["reason"].strip()
        ):
            raise ReferenceError("operation pass differs from frozen question/source/rubric")
        cases = []
        for item in payload["cases"]:
            raw = dict(item)
            raw["anchor_ids"] = tuple(raw["anchor_ids"])
            raw["alternatives"] = tuple(raw["alternatives"])
            raw["permissible_anchor_sets"] = tuple(
                tuple(values) for values in raw.get("permissible_anchor_sets", ())
            )
            case = OperationCase(**raw)
            if frame.direction == "source_first" and case.contribution_id is not None:
                raise ReferenceError("source-first missing occurrence cannot acquire an output ID")
            if (
                frame.direction == "output_first"
                and case.contribution_id not in frame.contribution_ids
            ):
                raise ReferenceError("output case is outside frozen contribution population")
            endpoint_anchors = {
                identity
                for option in case.alternatives
                for endpoint in option.get("endpoint_semantics", ())
                for identity in endpoint["anchor_ids"]
            }
            if (
                set(case.anchor_ids)
                | endpoint_anchors
                | {identity for values in case.permissible_anchor_sets for identity in values}
            ) - set(frame.anchor_ids):
                raise ReferenceError("case anchors are outside independently frozen source scope")
            cases.append(case)
        if len({case.case_id for case in cases}) != len(cases):
            raise ReferenceError("operation reference repeats a case identity")
        payload["cases"] = cases
        return payload
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise ReferenceError("invalid operation reference pass") from error


def _matches(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    """Partial object equality is rubric-declared; sequences retain order and membership."""
    for key, value in expected.items():
        if key not in actual:
            return False
        if key == "endpoint_semantics":
            endpoints = actual[key]
            if len(endpoints) != len(value) or any(
                a["role"] != b["role"]
                or a["anchor_ids"] != b["anchor_ids"]
                or not _matches(a["fields"], b.get("fields", {}))
                for a, b in zip(endpoints, value, strict=True)
            ):
                return False
        elif canonical_bytes(actual[key]) != canonical_bytes(value):
            return False
    return True


def _literal_product(value: Mapping[str, Any]) -> Mapping[str, Any]:
    anchors = value.get("anchors", ())
    value = dict(value, source_anchor_ids=[anchor["anchor_id"] for anchor in anchors])
    if value.get("anchor_role") == "inspection_subject":
        return value
    if anchors and all(
        anchor.get("precision") == "exact" and "source_piece" in anchor for anchor in anchors
    ):
        return dict(value, source_pieces=[anchor["source_piece"] for anchor in anchors])
    return value


def _interpretation_product(
    row: Mapping[str, Any], closure: Mapping[str, Mapping[str, Any]]
) -> Mapping[str, Any]:
    """Expose independently judgeable fields without comparing model probabilities."""
    from corpus_structure.semantic.observations import source_python

    result = source_python(row["value"])
    scope = result["assessed_scope"]
    if scope["pin"] != row["pin"]:
        raise ReferenceError("interpretation result differs from its assessed source pin")
    fields = {
        "interpretation_question_key": result["question_key"],
        "interpretation_answer_kind": result["answer_kind"],
        "interpretation_state": result["state"],
        "interpretation_selected_keys": result["selected_keys"],
        "interpretation_projection_extent": scope["projection_extent"],
    }
    members = [closure.get(identity) for identity in row.get("members", ())]
    if (
        result["answer_kind"] in {"text", "number", "date"}
        and result["state"] == "proposed"
        and len(members) == 1
        and (member := members[0]) is not None
        and member["semantic_type"] == "source_occurrence"
        and member["operation_key"] == row["operation_key"]
        and member["pin"] == row["pin"]
        and (anchors := member.get("anchors"))
        and all(a["space"] == "native" and a["precision"] == "exact" for a in anchors)
    ):
        fields["interpretation_literal_pieces"] = [a["source_piece"] for a in anchors]
        fields["interpretation_literal_anchors"] = [
            {key: a[key] for key in ("pointer", "start", "end")} for a in anchors
        ]
        if result.get("normalization") == "native_proposal":
            fields["interpretation_normalized_value"] = result["native_answer"][
                result["answer_kind"]
            ]
    return dict(row, **fields)


def _comparison_product(
    value: Mapping[str, Any], closure: Mapping[str, Mapping[str, Any]]
) -> Mapping[str, Any]:
    value = _literal_product(value)
    if value.get("semantic_type", "").startswith("interpretation."):
        return _interpretation_product(value, closure)
    if value.get("kind") not in {"proposal", "relation"} or (
        value.get("kind") == "proposal" and not value.get("endpoints")
    ):
        return value
    endpoints = []
    for endpoint in value.get("endpoints", ()):
        target = closure.get(endpoint["contribution_id"])
        if target is None:
            raise ReferenceError("endpoint assessment requires complete selected endpoint closure")
        endpoints.append(
            dict(
                role=endpoint["role"],
                anchor_ids=[a["anchor_id"] for a in target.get("anchors", ())],
                fields=_literal_product(target),
            )
        )
    value = dict(value, endpoint_semantics=endpoints)
    if value.get("semantic_type") == "definition.defining_text_attachment":
        endpoints_by_role = {endpoint["role"]: endpoint["anchor_ids"] for endpoint in endpoints}
        if len(endpoints) == 2 and endpoints_by_role.keys() == {"term", "defining_text"}:
            value.update(
                attachment_head=endpoints_by_role["term"],
                attachment_tail=endpoints_by_role["defining_text"],
                attachment_direction=[endpoint["role"] for endpoint in endpoints],
            )
    return value


def _case_anchors(case: OperationCase, value: Mapping[str, Any]) -> set[str]:
    if case.anchor_endpoint_role is None:
        return {anchor["anchor_id"] for anchor in value.get("anchors", ())}
    endpoints = [
        endpoint
        for endpoint in value.get("endpoint_semantics", ())
        if endpoint["role"] == case.anchor_endpoint_role
    ]
    return set(endpoints[0]["anchor_ids"]) if len(endpoints) == 1 else set()


def score_cases(
    frame: OperationEvaluationFrame,
    cases: Sequence[OperationCase],
    contributions: Sequence[Mapping[str, Any]],
    *,
    endpoint_closure: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    from scipy.optimize import linear_sum_assignment

    unique: dict[str, Mapping[str, Any]] = {}
    observed = set()
    missing_observation_lineage = 0
    for contribution in contributions:
        identity = contribution["contribution_id"]
        if frame.direction == "output_first" and identity not in frame.contribution_ids:
            continue
        if contribution.get("origin_task_id") is None:
            missing_observation_lineage += 1
        else:
            observed.add((contribution["origin_task_id"], identity))
        sidecars = {
            "selected_task_id",
            "origin_task_id",
            "source",
            "method",
            "cut_member",
            "task_status",
            "source_view_id",
            "task_id",
            "position",
        }
        if identity in unique and canonical_bytes(
            {key: value for key, value in unique[identity].items() if key not in sidecars}
        ) != canonical_bytes(
            {key: value for key, value in contribution.items() if key not in sidecars}
        ):
            raise ReferenceError("one contribution identity has conflicting retained payloads")
        unique[identity] = contribution
    closure = dict(unique)
    for value in endpoint_closure or ():
        closure[value["contribution_id"]] = value
    selected = [_comparison_product(unique[identity], closure) for identity in sorted(unique)]
    if frame.direction == "output_first":
        if set(frame.contribution_ids) - unique.keys():
            raise ReferenceError("frozen output population is absent from prediction capture")
        selected = [
            _comparison_product(unique[identity], closure) for identity in frame.contribution_ids
        ]
    if len({case.case_id for case in cases}) != len(cases):
        raise ReferenceError("assessment repeats an independent case identity")
    candidates_by_case = {
        case.case_id: [
            value
            for value in selected
            if value.get("kind") == case.contribution_kind
            and _matches(value, case.candidate_selector)
            and (case.contribution_id is None or value["contribution_id"] == case.contribution_id)
            and any(
                _case_anchors(case, value) == set(anchors)
                for anchors in (case.anchor_ids, *case.permissible_anchor_sets)
            )
        ]
        for case in cases
    }
    assignments = {}
    # Source-first quantity counts physical occurrences. Output-first correctness
    # assesses each frozen emitted ID, including distinct observations of one occurrence.
    occurrence_groups: dict[bytes, list[Mapping[str, Any]]] = {}
    for value in selected:
        if frame.direction == "output_first":
            key = canonical_bytes(["contribution", value["contribution_id"]])
            occurrence_groups.setdefault(key, []).append(value)
            continue
        anchors = value.get("anchors", ())
        occurrence = value.get("occurrence_id") or (
            sorted(anchor["anchor_id"] for anchor in anchors)
            if anchors
            else value["contribution_id"]
        )
        if value.get("kind") == "relation" or (
            value.get("kind") == "proposal" and not anchors and value.get("endpoints")
        ):
            occurrence = [
                [endpoint["role"], endpoint["anchor_ids"]]
                for endpoint in value.get("endpoint_semantics", ())
            ]
        key = canonical_bytes([value.get("kind"), occurrence])
        occurrence_groups.setdefault(key, []).append(value)
    groups = [occurrence_groups[key] for key in sorted(occurrence_groups)]
    for facet in sorted({case.facet for case in cases}):
        eligible = sorted(
            (
                case
                for case in cases
                if case.facet == facet
                and case.judgment in {"supported", "ambiguous"}
                and case.source_state in {"stated", "unstated", "unresolved"}
            ),
            key=lambda value: value.case_id,
        )
        if not eligible:
            continue
        # Each reference has an explicit unmatched column. Invalid matches cost more
        # than all unmatched choices, so the objective maximizes exact permitted matches.
        matrix = []
        for case in eligible:
            ids = {value["contribution_id"] for value in candidates_by_case[case.case_id]}
            matrix.append(
                [
                    0
                    if any(
                        value["contribution_id"] in ids
                        and any(_matches(value, option) for option in case.alternatives)
                        for value in group
                    )
                    else len(eligible) + 2
                    for group in groups
                ]
                + [1] * len(eligible)
            )
        rows, columns = linear_sum_assignment(matrix)
        for row, column in zip(rows, columns, strict=True):
            if column < len(groups) and matrix[row][column] == 0:
                case = eligible[row]
                ids = {value["contribution_id"] for value in candidates_by_case[case.case_id]}
                assignments[case.case_id] = next(
                    value
                    for value in groups[column]
                    if value["contribution_id"] in ids
                    and any(_matches(value, option) for option in case.alternatives)
                )
    results: list[dict[str, Any]] = []
    for case in sorted(cases, key=lambda value: value.case_id):
        candidates = candidates_by_case[case.case_id]
        matches = [
            value
            for value in candidates
            if any(_matches(value, option) for option in case.alternatives)
        ]
        matched = assignments.get(case.case_id)
        if case.judgment == "unassessed" or case.source_state == "uninspected":
            judgment, category = "unassessed", "uninspected"
        elif case.judgment == "ambiguous" or case.source_state == "unresolved":
            judgment, category = (
                "ambiguous",
                "permissible_alternatives" if matched else "unresolved",
            )
        elif case.source_state == "unstated" and case.expectation_mode == "absence_detection":
            judgment = "unsupported" if candidates else "supported"
            category = "spurious" if candidates else "inspected_unstated"
        elif case.judgment == "unsupported":
            judgment, category = "unsupported", case.error_category or "independent_unsupported"
        elif matched is not None:
            judgment, category = "supported", None
        else:
            judgment = "unsupported"
            category = (
                "duplicate_occurrence"
                if matches
                else (
                    case.error_category or ("wrong_structure" if candidates else "missing_output")
                )
            )
        results.append(
            dict(
                case_id=case.case_id,
                facet=case.facet,
                judgment=judgment,
                source_state=case.source_state,
                error_category=category,
                expectation_mode=case.expectation_mode,
                capture_outcome=(
                    "true_negative"
                    if category == "inspected_unstated"
                    else "captured_structure"
                    if matched is not None and judgment == "supported"
                    else "not_captured"
                ),
                contribution_id=matched["contribution_id"] if matched else case.contribution_id,
                candidate_ids=[value["contribution_id"] for value in candidates],
                explanation=case.explanation,
            )
        )
    facets = {}
    for facet in sorted({case.facet for case in cases}):
        counts = Counter(
            value["judgment"]
            for value in results
            if value["facet"] == facet and value["expectation_mode"] == "structure"
        )
        facets[facet] = {label: counts[label] for label in JUDGMENTS}
    detection_facets = {
        facet: {
            label: sum(
                value["facet"] == facet
                and value["judgment"] == label
                and value["expectation_mode"] == "absence_detection"
                for value in results
            )
            for label in JUDGMENTS
        }
        for facet in facets
    }
    source_coverage = None
    if isinstance(frame, OperationEvaluationFrameV2):
        # IDs join independently frozen opportunities to cases, never to a
        # surviving token/candidate population. Missing references stay visible.
        by_case = {value["case_id"]: value for value in results}
        opportunities = []
        for opportunity in frame.opportunities:
            assessed = by_case.get(opportunity.opportunity_id)
            if assessed is not None and assessed["facet"] != opportunity.facet:
                raise ReferenceError("reference facet differs from frozen source opportunity")
            status = (
                "not_assessed_by_output_frame"
                if frame.direction == "output_first"
                else "reference_missing"
                if assessed is None
                else "unassessed"
                if assessed["judgment"] == "unassessed"
                else "permissible_alternative"
                if assessed["error_category"] == "permissible_alternatives"
                else "unresolved"
                if assessed["judgment"] == "ambiguous"
                else assessed["capture_outcome"]
            )
            opportunities.append(
                dict(
                    **asdict(opportunity),
                    assessment_status=status,
                    case_id=assessed["case_id"] if assessed is not None else None,
                    judgment=assessed["judgment"] if assessed is not None else "unassessed",
                    error_category=assessed["error_category"] if assessed is not None else None,
                )
            )
        source_coverage = dict(
            grain="frozen_source_opportunity",
            opportunities=opportunities,
            opportunity_count=len(opportunities),
            status_counts=dict(Counter(v["assessment_status"] for v in opportunities)),
            unmatched_reference_case_ids=sorted(
                set(by_case) - {o.opportunity_id for o in frame.opportunities}
            ),
        )
    return dict(
        **({"source_coverage": source_coverage} if source_coverage is not None else {}),
        direction=frame.direction,
        grain="operation_case_facet",
        facets=facets,
        cases=results,
        absence_detection_facets=detection_facets,
        prediction_count=len(selected),
        prediction_count_grain="unique_semantic_contribution_product",
        producer_observation_count=len(observed) if not missing_observation_lineage else None,
        producer_observation_count_grain="unique_origin_task_and_contribution_id",
        missing_producer_observation_lineage=missing_observation_lineage,
        quality_claim="not_established",
    )


def compare_assessments(baseline: Mapping[str, Any], revised: Mapping[str, Any]) -> dict[str, Any]:
    for key in ("protocol", "set_id", "reference_snapshot", "frame_digest"):
        if baseline.get(key) != revised.get(key):
            raise ReferenceError(
                "operation comparison requires same frozen source/rubric/reference cases"
            )
    a = {
        (unit["unit_id"], case["case_id"]): case
        for unit in baseline["units"]
        for case in unit["cases"]
    }
    b = {
        (unit["unit_id"], case["case_id"]): case
        for unit in revised["units"]
        for case in unit["cases"]
    }
    if a.keys() != b.keys():
        raise ReferenceError("changed semantic grain requires explicit correspondence")
    changes: dict[str, list[Any]] = {
        key: []
        for key in (
            "newly_captured",
            "corrected",
            "regressed",
            "newly_spurious",
            "still_unresolved",
            "unchanged",
        )
    }
    for identity in sorted(a):
        old, new = a[identity], b[identity]
        if new["judgment"] in {"ambiguous", "unassessed"}:
            category = "still_unresolved"
        elif old["judgment"] != "supported" and new["judgment"] == "supported":
            category = (
                "newly_captured" if old["error_category"] == "missing_output" else "corrected"
            )
        elif old["judgment"] == "supported" and new["judgment"] == "unsupported":
            category = "newly_spurious" if new["error_category"] == "spurious" else "regressed"
        else:
            category = "unchanged"
        changes[category].append(
            dict(unit_id=identity[0], case_id=identity[1], baseline=old, revised=new)
        )
    return dict(
        protocol="source-operation-comparison-1", changes=changes, quality_claim="not_established"
    )


def create_reference_set(
    conn: Connection,
    *,
    project_id: str,
    source_run_id: int,
    source_cut_id: int,
    label: str,
    legacy_split: str,
    guideline: str,
    guideline_text: str,
    partition: str,
    sampling: Mapping[str, Any],
    frames: Mapping[str, OperationEvaluationFrame],
) -> dict[str, Any]:
    runs = table("ops.run")
    release_id = conn.scalar(
        select(runs.c.release_id).where(runs.c.id == source_run_id, runs.c.project_id == project_id)
    )
    if release_id is None or partition not in PARTITIONS or legacy_split not in {"dev", "test"}:
        raise ReferenceError("operation reference run/partition/split is invalid")
    require_bound_operation(open_release(conn, release_id), "reference_operation_set")
    by_key = {unit["unit_key"]: unit for unit in source_units(conn, source_run_id)}
    if not frames or set(frames) - by_key.keys():
        raise ReferenceError("operation frame is outside selected source population")
    selected: list[dict[str, Any]] = []
    for key, frame in frames.items():
        if (frame.unit, frame.release_id, frame.guideline_version) != (key, release_id, guideline):
            raise ReferenceError("operation frame differs from source/guideline/release")
        selected.append(
            dict(
                unit_key=key,
                source_view_id=by_key[key]["source_view_id"],
                frame=encode_frame(frame),
            )
        )
    abis = {unit["frame"]["protocol"] for unit in selected}
    if len(abis) != 1:
        raise ReferenceError("one reference set requires one source frame ABI")
    if any(
        isinstance(frame, OperationEvaluationFrameV2) and frame.partition != partition
        for frame in frames.values()
    ):
        raise ReferenceError("frame partition differs from reference set")
    metadata = dict(
        sampling,
        operation_protocol=PROTOCOL,
        partition=partition,
        source_frame_abi=next(iter(abis)),
        source_cut_id=source_cut_id,
        guideline_text=guideline_text,
        guideline_digest=sha256(guideline_text.encode()).hexdigest(),
    )
    result = _call(
        conn,
        "SELECT eval.create_operation_reference_set(:p,:r,:l,:s,:g,"
        "CAST(:m AS jsonb),CAST(:u AS jsonb))",
        p=project_id,
        r=source_run_id,
        l=label,
        s=legacy_split,
        g=guideline,
        m=_json(metadata),
        u=_json(selected),
    ).scalar_one()
    return dict(set_id=result, release_id=release_id, units=selected, sampling=metadata)


def author_packet(conn: Connection, unit_id: int) -> dict[str, Any]:
    return _call(conn, "SELECT eval.operation_author_packet(:u)", u=unit_id).scalar_one()


def record_pass(
    conn: Connection,
    *,
    unit_id: int,
    pass_kind: str,
    actor: str,
    authored: bytes,
    frame: OperationEvaluationFrame,
) -> int:
    unit = _unit(conn, unit_id)
    require_bound_operation(open_release(conn, unit["release_id"]), "reference_operation_pass")
    if decode_frame(unit["context"][0]) != frame:
        raise ReferenceError("operation pass differs from independently frozen frame")
    decode_authored(authored, frame)
    return _call(
        conn,
        "SELECT eval.record_operation_reference_pass(:u,:k,:a,:b,CAST(:f AS jsonb))",
        u=unit_id,
        k=pass_kind,
        a=actor,
        b=authored,
        f=_json(unit["context"][0]),
    ).scalar_one()


def read_pass(conn: Connection, pass_id: int, *, frame_id: int | None = None) -> dict[str, Any]:
    passes, frames = table("eval.reference_pass"), table("eval.reference_frame")
    row = conn.execute(select(passes).where(passes.c.id == pass_id)).mappings().one()
    query = select(frames).where(frames.c.pass_id == pass_id)
    if frame_id is not None:
        query = query.where(frames.c.id == frame_id)
    citation = conn.execute(query.order_by(frames.c.version.desc()).limit(1)).mappings().one()
    unit = _unit(conn, row["unit_id"])
    authored = bytes(row["authored"])
    if sha256(authored).hexdigest() != row["content_digest"] or unit["context"] != [
        citation["source_frame"]
    ]:
        raise ReferenceError("operation pass digest or frozen frame changed")
    payload = decode_authored(authored, decode_frame(citation["source_frame"]))
    return dict(row, authored=authored, frame_id=citation["id"], payload=payload)


def adjudication_packet(conn: Connection, unit_id: int) -> dict[str, Any]:
    passes = unit_passes(conn, unit_id)
    if not passes["A"] or not passes["B"]:
        raise ReferenceError("operation adjudication requires independent A and B")
    a, b = (read_pass(conn, passes[kind][-1]) for kind in ("A", "B"))
    return dict(
        source=author_packet(conn, unit_id),
        adjudication_passes=[a["id"], b["id"]],
        authors=[
            dict(
                pass_id=value["id"],
                actor=value["actor"],
                authored=value["authored"].decode(),
                content_digest=value["content_digest"],
            )
            for value in (a, b)
        ],
        agreement=dict(
            equal_cases=canonical_bytes([asdict(case) for case in a["payload"]["cases"]])
            == canonical_bytes([asdict(case) for case in b["payload"]["cases"]])
        ),
    )


def reference_evaluate(
    conn: Connection, *, project_id: str, run_id: int, set_id: int
) -> ReferenceReport:
    from corpus_structure.semantic.contribution_queries import read_source_contributions
    from corpus_structure.semantic.interpretation_questions import declared_families
    from corpus_structure.semantic.observations import source_python

    completed = _completed(conn, run_id, project_id)
    prepared = open_release(conn, completed["release_id"])
    require_bound_operation(prepared, "reference_operation_grade")
    sets, units = table("eval.reference_set"), table("eval.reference_unit")
    definition = (
        conn.execute(select(sets).where(sets.c.id == set_id, sets.c.project_id == project_id))
        .mappings()
        .one()
    )
    if (
        definition["sampling"].get("operation_protocol") != PROTOCOL
        or definition["release_id"] != prepared.release_id
    ):
        raise ReferenceError(
            "operation evaluation source release differs; correspondence is required"
        )
    selected = (
        conn.execute(select(units).where(units.c.set_id == set_id).order_by(units.c.id))
        .mappings()
        .all()
    )
    run_views = {unit["source_view_id"] for unit in source_units(conn, run_id)}
    missing = {unit["source_view_id"] for unit in selected} - run_views
    if missing:
        raise ReferenceError(
            "operation evaluation lacks frozen source views in the prediction run: "
            + ", ".join(str(view) for view in sorted(missing))
        )
    snapshot = _call(conn, "SELECT eval.native_reference_snapshot(:s)", s=set_id).scalar_one()
    if not selected or len(snapshot) != len(selected):
        raise ReferenceError("every operation unit requires adjudicated C, including zero output")
    frozen = {value["unit_id"]: value for value in snapshot}
    interpretation_questions = declared_families(prepared.registry_rows)
    reports = []
    for unit in selected:
        frame = decode_frame(unit["context"][0])
        reference = read_pass(
            conn, frozen[unit["id"]]["pass_id"], frame_id=frozen[unit["id"]]["frame_id"]
        )
        inventory = read_source_contributions(
            conn,
            prepared=prepared,
            run_id=run_id,
            source_view_id=unit["source_view_id"],
            cut_id=completed["cut_id"],
            limit=10000,
        )
        if inventory.more:
            raise ReferenceError("operation summary capture exceeds bounded source inventory")
        report_views = {
            report["selected_task_id"]: report["source_view_id"] for report in inventory.reports
        }
        operations = [
            dict(value)
            for value in inventory.operations
            if report_views.get(value["selected_task_id"]) == unit["source_view_id"]
            and value["question"] == frame.operation_question
            and value["operation_version"] == frame.operation_version
        ]
        operation_keys = {value["operation_key"] for value in operations}
        assessed_extents = (
            {
                (item.start, item.end)
                for item in frame.opportunities
                if item.source_view_id == unit["source_view_id"]
            }
            if (
                isinstance(frame, OperationEvaluationFrameV2)
                and frame.direction == "source_first"
                and frame.operation_question in interpretation_questions
                and not frame.anchor_ids
                and not frame.anchor_scopes
            )
            else set()
        )
        endpoint_roles = tuple(
            sorted(
                {
                    case.anchor_endpoint_role
                    for case in reference["payload"]["cases"]
                    if case.anchor_endpoint_role is not None
                }
            )
        )
        captured = read_source_contributions(
            conn,
            prepared=prepared,
            run_id=run_id,
            source_view_id=unit["source_view_id"],
            cut_id=completed["cut_id"],
            limit=10000,
            include_details=True,
            operation_keys=tuple(sorted(operation_keys)),
            anchor_ids=frame.anchor_ids
            if frame.direction == "source_first" and not assessed_extents
            else None,
            anchor_scopes=frame.anchor_scopes
            if frame.direction == "source_first" and not assessed_extents
            else None,
            anchor_endpoint_roles=endpoint_roles,
            contribution_ids=frame.contribution_ids if frame.direction == "output_first" else None,
        )
        if captured.more:
            raise ReferenceError(
                "operation selected contribution capture exceeds bounded source inventory"
            )
        predictions = list(captured.contributions)
        if assessed_extents:
            predictions = [
                row
                for row in predictions
                if row["semantic_type"] == f"interpretation.{frame.operation_question}"
                and tuple(source_python(row["value"])["assessed_scope"]["projection_extent"])
                in assessed_extents
            ]
        if frame.rubric_version == "nce12-attachment-role-direction-scope-2":
            selected_attachments = [
                {"task_id": value["origin_task_id"], "contribution_id": value["contribution_id"]}
                for value in predictions
                if value["semantic_type"] == "definition.defining_text_attachment"
            ]
            scopes = dict(
                _call(
                    conn,
                    """
                    SELECT selection.contribution_id,
                     eval.defining_text_event_scope(selection.task_id,selection.contribution_id)
                    FROM jsonb_to_recordset(CAST(:rows AS jsonb))
                     selection(task_id bigint,contribution_id text)
                    """,
                    rows=_json(selected_attachments),
                ).all()
            )
            if any(scope is None for scope in scopes.values()):
                raise ReferenceError("selected defining-text attachment lacks native section scope")
            predictions = [
                dict(value, attachment_scope=scopes[value["contribution_id"]])
                if value["contribution_id"] in scopes
                else value
                for value in predictions
            ]
        prediction_ids = {value["contribution_id"] for value in predictions}
        endpoint_ids = {
            endpoint["contribution_id"]
            for value in predictions
            for endpoint in value.get("endpoints", ())
        } | {
            identity
            for value in predictions
            if value["semantic_type"].startswith("interpretation.")
            for identity in value.get("members", ())
        }
        endpoint_ids -= prediction_ids
        endpoints = (
            read_source_contributions(
                conn,
                prepared=prepared,
                run_id=run_id,
                source_view_id=unit["source_view_id"],
                cut_id=completed["cut_id"],
                limit=10000,
                include_details=True,
                contribution_ids=tuple(sorted(endpoint_ids)),
            )
            if endpoint_ids
            else None
        )
        if endpoints is not None and endpoints.more:
            raise ReferenceError("operation endpoint closure exceeds bounded source inventory")
        closure = (*predictions, *(endpoints.contributions if endpoints is not None else ()))
        report = score_cases(
            frame, reference["payload"]["cases"], predictions, endpoint_closure=closure
        )
        reports.append(
            dict(
                report,
                unit_id=unit["id"],
                source_view_id=unit["source_view_id"],
                producer_operations=operations,
                producer_reports=[
                    dict(value)
                    for value in inventory.reports
                    if value["source_view_id"] == unit["source_view_id"]
                ],
                prediction_ids=[value["contribution_id"] for value in predictions],
            )
        )
    result = dict(
        protocol=EVALUATION_PROTOCOL,
        set_id=set_id,
        run_id=run_id,
        release_id=prepared.release_id,
        reference_snapshot=snapshot,
        units=reports,
        partition=definition["sampling"]["partition"],
        frame_digest=sha256(canonical_bytes([unit["context"] for unit in selected])).hexdigest(),
        quality_claim="not_established",
        population_claim="declared_cases_only",
    )
    identity = _call(
        conn,
        "SELECT eval.record_operation_reference_evaluation(:p,:r,:s,"
        "CAST(:n AS jsonb),CAST(:v AS jsonb))",
        p=project_id,
        r=run_id,
        s=set_id,
        n=_json(snapshot),
        v=_json(result),
    ).scalar_one()
    return ReferenceReport(
        id=identity,
        project_id=project_id,
        run_id=run_id,
        set_id=set_id,
        reference_snapshot=snapshot,
        result=result,
    )


def operation_assessment_native_sql() -> str:
    return (
        Path(__file__)
        .resolve()
        .parents[1]
        .joinpath("semantic/sql/operation_assessment.sql")
        .read_text()
    )


def read_evaluation(conn: Connection, *, project_id: str, evaluation_id: int) -> Mapping[str, Any]:
    evaluations = table("eval.reference_evaluation")
    row = (
        conn.execute(
            select(evaluations).where(
                evaluations.c.id == evaluation_id, evaluations.c.project_id == project_id
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None or row["result"].get("protocol") != EVALUATION_PROTOCOL:
        raise ReferenceError("unknown immutable operation evaluation in selected project")
    digest = sha256(
        canonical_bytes(dict(snapshot=row["reference_snapshot"], result=row["result"]))
    ).hexdigest()
    if digest != row["content_digest"]:
        raise ReferenceError("immutable operation evaluation digest differs")
    return row["result"]


def review_export(conn: Connection, *, project_id: str, set_id: int) -> dict[str, Any]:
    return _call(
        conn, "SELECT eval.operation_review_export(:p,:s)", p=project_id, s=set_id
    ).scalar_one()
