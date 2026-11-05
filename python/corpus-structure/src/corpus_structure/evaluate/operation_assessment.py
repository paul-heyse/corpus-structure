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
        if any(not getattr(self, field).strip() for field in (
            "unit", "release_id", "guideline_version", "rubric_version", "context_policy",
            "operation_question", "operation_version", "domain",
        )):
            raise ReferenceError("operation frame requires explicit versioned question and context")


def encode_frame(frame: OperationEvaluationFrame, *, captured_coordinates=()) -> dict[str, Any]:
    return dict(protocol=FRAME_PROTOCOL, evaluation_frame=asdict(frame),
                captured_coordinates=list(captured_coordinates), context_dependency_digest=None)


def decode_frame(value: Mapping[str, Any]) -> OperationEvaluationFrame:
    if value.get("protocol") != FRAME_PROTOCOL or set(value) - {
        "protocol", "evaluation_frame", "captured_coordinates", "context_dependency_digest",
        "source_views",
    }:
        raise ReferenceError("unsupported immutable operation frame")
    try:
        raw = dict(value["evaluation_frame"])
        for field in ("anchor_ids", "related_pins", "anchor_scopes", "contribution_ids"):
            raw[field] = tuple(raw.get(field, ()))
        return OperationEvaluationFrame(**raw)
    except (KeyError, TypeError, ValueError) as error:
        raise ReferenceError("invalid immutable operation frame") from error


@dataclass(frozen=True)
class OperationCase:
    """One independent question; alternatives contain exact permitted output fields.

    Anchor IDs come from independent source authoring. A case with an unstated
    source field expects absence; uninspected never implies absence. An output ID
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
    reference_projection: Mapping[str, Any] | None = None
    candidate_selector: Mapping[str, Any] = field(default_factory=dict)
    permissible_anchor_sets: tuple[tuple[str, ...], ...] = ()

    def __post_init__(self):
        if self.judgment not in JUDGMENTS or self.source_state not in {
            "stated", "unstated", "uninspected", "unresolved",
        }:
            raise ReferenceError("unknown operation judgment or source field state")
        if not all((self.case_id, self.facet, self.inspected_scope, self.explanation,
                    self.assessor_provenance)):
            raise ReferenceError("case requires inspected scope, explanation and assessor provenance")
        if self.source_state == "uninspected" and self.judgment != "unassessed":
            raise ReferenceError("uninspected source cannot supply a local truth label")
        if self.source_state == "stated" and self.judgment == "supported" and not self.alternatives:
            raise ReferenceError("stated supported case requires independent expected structure")
        if any(not isinstance(value, Mapping) or not value for value in self.alternatives):
            raise ReferenceError("permissible alternatives require nonempty exact structures")
        if self.reference_projection is not None:
            projection = self.reference_projection
            if not {"protocol", "source_pass_id", "source_frame_id", "source_record_id", "source_field_index",
                    "source_field", "question", "correspondence", "scope"} <= projection.keys() or projection["protocol"] != "exact-field-projection-1":
                raise ReferenceError("reused reference requires versioned exact-question projection")
            if projection["question"] != self.facet or not projection["scope"]:
                raise ReferenceError("old whole-reading labels cannot supply local truth")


def decode_authored(authored: bytes, frame: OperationEvaluationFrame) -> dict[str, Any]:
    if not isinstance(authored, bytes):
        raise TypeError("operation pass must retain exact submitted bytes")
    try:
        payload = json.loads(authored)
        expected = dict(protocol=PROTOCOL, release_id=frame.release_id, unit_ref=frame.unit,
                        guideline=frame.guideline_version, rubric_version=frame.rubric_version,
                        context_policy=frame.context_policy, operation_question=frame.operation_question,
                        operation_version=frame.operation_version, domain=frame.domain,
                        direction=frame.direction)
        if set(payload) - {*expected, "reason", "cases", "adjudication_passes"}:
            raise ReferenceError("unknown operation pass fields")
        if any(payload.get(key) != value for key, value in expected.items()) or not payload["reason"].strip():
            raise ReferenceError("operation pass differs from frozen question/source/rubric")
        cases = []
        for item in payload["cases"]:
            raw = dict(item)
            raw["anchor_ids"] = tuple(raw["anchor_ids"])
            raw["alternatives"] = tuple(raw["alternatives"])
            raw["permissible_anchor_sets"] = tuple(tuple(values) for values in raw.get("permissible_anchor_sets", ()))
            case = OperationCase(**raw)
            if frame.direction == "source_first" and case.contribution_id is not None:
                raise ReferenceError("source-first missing occurrence cannot acquire an output ID")
            if frame.direction == "output_first" and case.contribution_id not in frame.contribution_ids:
                raise ReferenceError("output case is outside frozen contribution population")
            if (set(case.anchor_ids) | {identity for values in case.permissible_anchor_sets for identity in values}) - set(frame.anchor_ids):
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
    return all(key in actual and canonical_bytes(actual[key]) == canonical_bytes(value)
               for key, value in expected.items())


def score_cases(frame: OperationEvaluationFrame, cases: Sequence[OperationCase],
                contributions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    from scipy.optimize import linear_sum_assignment

    unique: dict[str, Mapping[str, Any]] = {}
    for contribution in contributions:
        identity = contribution["contribution_id"]
        sidecars = {"selected_task_id", "origin_task_id", "source", "method", "cut_member"}
        if identity in unique and canonical_bytes({key: value for key, value in unique[identity].items() if key not in sidecars}) != canonical_bytes({key: value for key, value in contribution.items() if key not in sidecars}):
            raise ReferenceError("one contribution identity has conflicting retained payloads")
        unique[identity] = contribution
    selected = [unique[identity] for identity in sorted(unique)]
    if frame.direction == "output_first":
        if set(frame.contribution_ids) - unique.keys():
            raise ReferenceError("frozen output population is absent from prediction capture")
        selected = [unique[identity] for identity in frame.contribution_ids]
    if len({case.case_id for case in cases}) != len(cases):
        raise ReferenceError("assessment repeats an independent case identity")
    candidates_by_case = {
        case.case_id: [value for value in selected
                      if value.get("kind") == case.contribution_kind
                      and _matches(value, case.candidate_selector)
                      and (case.contribution_id is None or value["contribution_id"] == case.contribution_id)
                      and any({anchor["anchor_id"] for anchor in value.get("anchors", ())} == set(anchors)
                              for anchors in (case.anchor_ids, *case.permissible_anchor_sets))]
        for case in cases
    }
    assignments = {}
    # Repeated producer observations retain their IDs, but one physical occurrence
    # supplies at most one answer to one facet. Competing readings share that slot.
    occurrence_groups: dict[bytes, list[Mapping[str, Any]]] = {}
    for value in selected:
        anchors = value.get("anchors", ())
        occurrence = value.get("occurrence_id") or (
            sorted(anchor["anchor_id"] for anchor in anchors) if anchors else value["contribution_id"])
        key = canonical_bytes([value.get("kind"), occurrence])
        occurrence_groups.setdefault(key, []).append(value)
    groups = [occurrence_groups[key] for key in sorted(occurrence_groups)]
    for facet in sorted({case.facet for case in cases}):
        eligible = sorted((case for case in cases if case.facet == facet and
                           case.judgment in {"supported", "ambiguous"} and
                           case.source_state in {"stated", "unresolved"}), key=lambda value: value.case_id)
        if not eligible:
            continue
        # Each reference has an explicit unmatched column. Invalid matches cost more
        # than all unmatched choices, so the objective maximizes exact permitted matches.
        matrix = []
        for case in eligible:
            ids = {value["contribution_id"] for value in candidates_by_case[case.case_id]}
            matrix.append([
                0 if any(value["contribution_id"] in ids and any(_matches(value, option) for option in case.alternatives)
                         for value in group) else len(eligible) + 2 for group in groups
            ] + [1] * len(eligible))
        rows, columns = linear_sum_assignment(matrix)
        for row, column in zip(rows, columns, strict=True):
            if column < len(groups) and matrix[row][column] == 0:
                case = eligible[row]
                ids = {value["contribution_id"] for value in candidates_by_case[case.case_id]}
                assignments[case.case_id] = next(value for value in groups[column]
                    if value["contribution_id"] in ids and any(_matches(value, option) for option in case.alternatives))
    results = []
    for case in sorted(cases, key=lambda value: value.case_id):
        candidates = candidates_by_case[case.case_id]
        matches = [value for value in candidates
                   if any(_matches(value, option) for option in case.alternatives)]
        matched = assignments.get(case.case_id)
        if case.judgment == "unassessed" or case.source_state == "uninspected":
            judgment, category = "unassessed", "uninspected"
        elif case.judgment == "ambiguous" or case.source_state == "unresolved":
            judgment, category = "ambiguous", "permissible_alternatives" if matched else "unresolved"
        elif case.source_state == "unstated":
            judgment = "unsupported" if candidates else "supported"
            category = "spurious" if candidates else "inspected_unstated"
        elif case.judgment == "unsupported":
            judgment, category = "unsupported", case.error_category or "independent_unsupported"
        elif matched is not None:
            judgment, category = "supported", None
        else:
            judgment = "unsupported"
            category = "duplicate_occurrence" if matches else (
                case.error_category or ("wrong_structure" if candidates else "missing_output"))
        results.append(dict(case_id=case.case_id, facet=case.facet, judgment=judgment,
                            source_state=case.source_state, error_category=category,
                            contribution_id=matched["contribution_id"] if matched else case.contribution_id,
                            candidate_ids=[value["contribution_id"] for value in candidates],
                            explanation=case.explanation, reference_projection=case.reference_projection))
    facets = {}
    for facet in sorted({case.facet for case in cases}):
        counts = Counter(value["judgment"] for value in results if value["facet"] == facet)
        facets[facet] = {label: counts[label] for label in JUDGMENTS}
    return dict(direction=frame.direction, grain="operation_case_facet", facets=facets, cases=results,
                prediction_count=len(selected), quality_claim="not_established")


def compare_assessments(baseline: Mapping[str, Any], revised: Mapping[str, Any]) -> dict[str, Any]:
    for key in ("protocol", "set_id", "reference_snapshot", "frame_digest"):
        if baseline.get(key) != revised.get(key):
            raise ReferenceError("operation comparison requires same frozen source/rubric/reference cases")
    a = {(unit["unit_id"], case["case_id"]): case for unit in baseline["units"] for case in unit["cases"]}
    b = {(unit["unit_id"], case["case_id"]): case for unit in revised["units"] for case in unit["cases"]}
    if a.keys() != b.keys():
        raise ReferenceError("changed semantic grain requires explicit correspondence")
    changes: dict[str, list[Any]] = {key: [] for key in (
        "newly_captured", "corrected", "regressed", "newly_spurious", "still_unresolved", "unchanged")}
    for identity in sorted(a):
        old, new = a[identity], b[identity]
        if new["judgment"] in {"ambiguous", "unassessed"}:
            category = "still_unresolved"
        elif old["judgment"] != "supported" and new["judgment"] == "supported":
            category = "newly_captured" if old["error_category"] == "missing_output" else "corrected"
        elif old["judgment"] == "supported" and new["judgment"] == "unsupported":
            category = "newly_spurious" if new["error_category"] == "spurious" else "regressed"
        else:
            category = "unchanged"
        changes[category].append(dict(unit_id=identity[0], case_id=identity[1], baseline=old, revised=new))
    return dict(protocol="source-operation-comparison-1", changes=changes, quality_claim="not_established")


def create_reference_set(conn: Connection, *, project_id: str, source_run_id: int,
                         source_cut_id: int, label: str, legacy_split: str, guideline: str,
                         guideline_text: str, partition: str, sampling: Mapping[str, Any],
                         frames: Mapping[str, OperationEvaluationFrame]) -> dict[str, Any]:
    runs = table("ops.run")
    release_id = conn.scalar(select(runs.c.release_id).where(
        runs.c.id == source_run_id, runs.c.project_id == project_id))
    if release_id is None or partition not in PARTITIONS or legacy_split not in {"dev", "test"}:
        raise ReferenceError("operation reference run/partition/split is invalid")
    require_bound_operation(open_release(conn, release_id), "reference_operation_set")
    by_key = {unit["unit_key"]: unit for unit in source_units(conn, source_run_id)}
    if not frames or set(frames) - by_key.keys():
        raise ReferenceError("operation frame is outside selected source population")
    selected = []
    for key, frame in frames.items():
        if (frame.unit, frame.release_id, frame.guideline_version) != (key, release_id, guideline):
            raise ReferenceError("operation frame differs from source/guideline/release")
        selected.append(dict(unit_key=key, source_view_id=by_key[key]["source_view_id"], frame=encode_frame(frame)))
    metadata = dict(sampling, operation_protocol=PROTOCOL, partition=partition,
                    source_frame_abi=FRAME_PROTOCOL, source_cut_id=source_cut_id,
                    guideline_text=guideline_text,
                    guideline_digest=sha256(guideline_text.encode()).hexdigest())
    result = _call(conn, "SELECT eval.create_operation_reference_set(:p,:r,:l,:s,:g,CAST(:m AS jsonb),CAST(:u AS jsonb))",
                   p=project_id, r=source_run_id, l=label, s=legacy_split, g=guideline,
                   m=_json(metadata), u=_json(selected)).scalar_one()
    return dict(set_id=result, release_id=release_id, units=selected, sampling=metadata)


def author_packet(conn: Connection, unit_id: int) -> dict[str, Any]:
    return _call(conn, "SELECT eval.operation_author_packet(:u)", u=unit_id).scalar_one()


def record_pass(conn: Connection, *, unit_id: int, pass_kind: str, actor: str,
                authored: bytes, frame: OperationEvaluationFrame) -> int:
    unit = _unit(conn, unit_id)
    require_bound_operation(open_release(conn, unit["release_id"]), "reference_operation_pass")
    if decode_frame(unit["context"][0]) != frame:
        raise ReferenceError("operation pass differs from independently frozen frame")
    decode_authored(authored, frame)
    return _call(conn, "SELECT eval.record_operation_reference_pass(:u,:k,:a,:b,CAST(:f AS jsonb))",
                 u=unit_id, k=pass_kind, a=actor, b=authored, f=_json(unit["context"][0])).scalar_one()


def read_pass(conn: Connection, pass_id: int, *, frame_id: int | None = None) -> dict[str, Any]:
    passes, frames = table("eval.reference_pass"), table("eval.reference_frame")
    row = conn.execute(select(passes).where(passes.c.id == pass_id)).mappings().one()
    query = select(frames).where(frames.c.pass_id == pass_id)
    if frame_id is not None:
        query = query.where(frames.c.id == frame_id)
    citation = conn.execute(query.order_by(frames.c.version.desc()).limit(1)).mappings().one()
    unit = _unit(conn, row["unit_id"])
    authored = bytes(row["authored"])
    if sha256(authored).hexdigest() != row["content_digest"] or unit["context"] != [citation["source_frame"]]:
        raise ReferenceError("operation pass digest or frozen frame changed")
    payload = decode_authored(authored, decode_frame(citation["source_frame"]))
    return dict(row, authored=authored, frame_id=citation["id"], payload=payload)


def adjudication_packet(conn: Connection, unit_id: int) -> dict[str, Any]:
    passes = unit_passes(conn, unit_id)
    if not passes["A"] or not passes["B"]:
        raise ReferenceError("operation adjudication requires independent A and B")
    a, b = (read_pass(conn, passes[kind][-1]) for kind in ("A", "B"))
    return dict(source=author_packet(conn, unit_id), adjudication_passes=[a["id"], b["id"]],
                authors=[dict(pass_id=value["id"], actor=value["actor"], authored=value["authored"].decode(),
                              content_digest=value["content_digest"]) for value in (a, b)],
                agreement=dict(equal_cases=canonical_bytes([asdict(case) for case in a["payload"]["cases"]]) ==
                               canonical_bytes([asdict(case) for case in b["payload"]["cases"]])))


def reference_evaluate(conn: Connection, *, project_id: str, run_id: int, set_id: int) -> ReferenceReport:
    from corpus_structure.semantic.contribution_queries import read_source_contributions

    completed = _completed(conn, run_id, project_id)
    prepared = open_release(conn, completed["release_id"])
    require_bound_operation(prepared, "reference_operation_grade")
    sets, units = table("eval.reference_set"), table("eval.reference_unit")
    definition = conn.execute(select(sets).where(sets.c.id == set_id, sets.c.project_id == project_id)).mappings().one()
    if definition["sampling"].get("operation_protocol") != PROTOCOL or definition["release_id"] != prepared.release_id:
        raise ReferenceError("operation evaluation source release differs; correspondence is required")
    selected = conn.execute(select(units).where(units.c.set_id == set_id).order_by(units.c.id)).mappings().all()
    snapshot = _call(conn, "SELECT eval.native_reference_snapshot(:s)", s=set_id).scalar_one()
    if not selected or len(snapshot) != len(selected):
        raise ReferenceError("every operation unit requires adjudicated C, including zero output")
    inventory = read_source_contributions(conn, prepared=prepared, run_id=run_id,
                                         cut_id=completed["cut_id"], limit=10000, include_details=True)
    if inventory.more:
        raise ReferenceError("operation prediction capture exceeds bounded inventory; select a smaller frame")
    frozen = {value["unit_id"]: value for value in snapshot}
    reports = []
    report_views = {report["selected_task_id"]: report["source_view_id"] for report in inventory.reports}
    for unit in selected:
        frame = decode_frame(unit["context"][0])
        reference = read_pass(conn, frozen[unit["id"]]["pass_id"], frame_id=frozen[unit["id"]]["frame_id"])
        operations = [dict(value) for value in inventory.operations
                      if report_views.get(value["selected_task_id"]) == unit["source_view_id"]
                      and value["question"] == frame.operation_question
                      and value["operation_version"] == frame.operation_version]
        operation_keys = {value["operation_key"] for value in operations}
        predictions = [value for value in inventory.contributions
                       if value["pin"]["source_view_id"] == unit["source_view_id"]
                       and value["operation_key"] in operation_keys]
        report = score_cases(frame, reference["payload"]["cases"], predictions)
        reports.append(dict(report, unit_id=unit["id"], source_view_id=unit["source_view_id"],
                            producer_operations=operations,
                            producer_reports=[dict(value) for value in inventory.reports
                                              if value["source_view_id"] == unit["source_view_id"]],
                            prediction_ids=[value["contribution_id"] for value in predictions]))
    result = dict(protocol=EVALUATION_PROTOCOL, set_id=set_id, run_id=run_id, release_id=prepared.release_id,
                  reference_snapshot=snapshot, units=reports, partition=definition["sampling"]["partition"],
                  frame_digest=sha256(canonical_bytes([unit["context"] for unit in selected])).hexdigest(),
                  quality_claim="not_established", population_claim="declared_cases_only")
    identity = _call(conn, "SELECT eval.record_operation_reference_evaluation(:p,:r,:s,CAST(:n AS jsonb),CAST(:v AS jsonb))",
                     p=project_id, r=run_id, s=set_id, n=_json(snapshot), v=_json(result)).scalar_one()
    return ReferenceReport(identity, project_id, run_id, set_id, snapshot, result)


def operation_assessment_native_sql() -> str:
    return Path(__file__).resolve().parents[1].joinpath("semantic/sql/operation_assessment.sql").read_text()


def read_evaluation(conn: Connection, *, project_id: str, evaluation_id: int) -> Mapping[str, Any]:
    evaluations = table("eval.reference_evaluation")
    row = conn.execute(select(evaluations).where(
        evaluations.c.id == evaluation_id, evaluations.c.project_id == project_id)).mappings().one_or_none()
    if row is None or row["result"].get("protocol") != EVALUATION_PROTOCOL:
        raise ReferenceError("unknown immutable operation evaluation in selected project")
    digest = sha256(canonical_bytes(dict(snapshot=row["reference_snapshot"], result=row["result"]))).hexdigest()
    if digest != row["content_digest"]:
        raise ReferenceError("immutable operation evaluation digest differs")
    return row["result"]


def review_export(conn: Connection, *, project_id: str, set_id: int) -> dict[str, Any]:
    return _call(conn, "SELECT eval.operation_review_export(:p,:s)", p=project_id, s=set_id).scalar_one()


def project_reference_field(conn: Connection, *, pass_id: int, frame_id: int,
                            record_id: str, field_index: int, question: str) -> dict[str, Any]:
    """Project an independently authored field, never an old grade/whole-reading label.

    The returned exact field and anchors are evidence for the named question only.
    Calling code must keep the source partition; native submission verifies that
    provenance and refuses a projection into a differently protected cohort.
    """
    from .record_references import read_pass as read_record_pass

    if question not in {"value", "role", "location"} or field_index < 0:
        raise ReferenceError("reference projection supports only exact value, role or location questions")
    source = read_record_pass(conn, pass_id, frame_id=frame_id)
    records = [record for record in source.records if record["record_id"] == record_id]
    if len(records) != 1 or field_index >= len(records[0]["fields"]):
        raise ReferenceError("source reference field is absent or ambiguous")
    record = records[0]
    field = record["fields"][field_index]
    evidence_ids = set(field.get("evidence_sets", ()))
    anchor_ids = {anchor for evidence in record["evidence_sets"]
                  if evidence["set_id"] in evidence_ids for anchor in evidence["anchors"]}
    anchors = [anchor for anchor in record["anchors"] if anchor["anchor_id"] in anchor_ids]
    return dict(protocol="exact-field-projection-1", source_pass_id=pass_id, source_frame_id=frame_id,
                source_record_id=record_id, source_field_index=field_index, source_field=dict(field),
                question=question, correspondence=dict(anchor_ids=sorted(anchor_ids)),
                scope=f"exact independently authored field {question}; no whole-record truth",
                anchors=anchors)
