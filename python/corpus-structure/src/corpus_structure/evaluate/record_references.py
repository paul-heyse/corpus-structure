"""Five-family references on the existing protected evaluator/pass/grade authority.

Source answers never enter a producer request. This module does not fit a model, assign
credible origins, author labels, or grant production acceptance to reference readings.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, select

from corpus_structure.semantic.contracts import require_bound_operation
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.types import PreparedRelease, SourceArtifact, SourceBundle

from .record_alignment import (
    COMPARISON_POLICY,
    FAMILIES,
    TIERS,
    RecordEvaluationFrame,
    RecordSide,
    align_records,
)
from .semantic import ReferenceError, ReferenceReport, _call, _completed, _json, _unit, unit_passes
from .semantic_alignment import TierCounts

PROTOCOL = "source-record-reference-1"
FRAME_PROTOCOL = "source-record-frame-1"
EVALUATION_PROTOCOL = "source-record-evaluation-1"
PARTITIONS = ("development", "feature_fit", "final_event_calibration", "final_assessment")


def reference_inputs(bundle: SourceBundle, *, model_content: bytes | None = None) -> SourceBundle:
    """Explicitly archive the reference product schema alongside the effective release.

    Call after observation_inputs; no reference answers are read or packaged. The abstract
    source-product ancestor fences these types from knowledge graph realization.
    """
    if not any(source.name == "record_policy" for source in bundle.sources):
        from corpus_structure.semantic.record_policy_products import record_policy_inputs

        bundle = record_policy_inputs(bundle)
    content = (
        (Path(__file__).resolve().parents[1] / "model/semantic/record-references.yaml").read_bytes()
        if model_content is None
        else model_content
    )
    if any(
        source.name in {"record_references", "record-reference-root"} for source in bundle.sources
    ):
        raise ReferenceError("record reference module already supplied")
    root = canonical_bytes(
        dict(
            id="https://corpus-structure.dev/semantic/record-reference-root",
            name="record_reference_root",
            imports=[bundle.root, "record_references"],
        )
    )
    return SourceBundle(
        "record-reference-root",
        (
            *bundle.sources,
            SourceArtifact("record_references", content),
            SourceArtifact("record-reference-root", root),
        ),
    )


def encode_frame(
    frame: RecordEvaluationFrame,
    *,
    captured_coordinates: Sequence[Mapping[str, Any]] = (),
    context_dependency_digest: str | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = dict(asdict(frame))
    value["anchor_ids"] = sorted(frame.anchor_ids)
    value["related_pins"] = list(frame.related_pins)
    return dict(
        protocol=FRAME_PROTOCOL,
        evaluation_frame=value,
        captured_coordinates=list(captured_coordinates),
        context_dependency_digest=context_dependency_digest,
    )


def decode_frame(value: Mapping[str, Any]) -> RecordEvaluationFrame:
    if (
        set(value)
        - {
            "protocol",
            "evaluation_frame",
            "captured_coordinates",
            "context_dependency_digest",
            "source_views",
        }
        or value.get("protocol") != FRAME_PROTOCOL
    ):
        raise ReferenceError("unsupported immutable record reference frame")
    raw = dict(value["evaluation_frame"])
    raw["anchor_ids"] = frozenset(raw["anchor_ids"])
    raw["related_pins"] = tuple(raw.get("related_pins", ()))
    raw["anchor_scopes"] = tuple(raw.get("anchor_scopes", ()))
    return RecordEvaluationFrame(**raw)


def align_independent_references(
    a: RecordSide,
    b: RecordSide,
    prepared: PreparedRelease,
    *,
    coordinate_texts: Sequence[Mapping[str, Any]] = (),
):
    """Compare two independent readings under reference acceptance, retaining source identity.

    Only comparison expectations change. Frozen production policy, authored records,
    bytes, standings and interpretation IDs remain unchanged.
    """
    if a.frame != b.frame:
        raise ReferenceError(
            "independent agreement requires the same frozen source/guideline frame"
        )
    comparison = replace(a.frame, prediction_policy_version=a.frame.reference_policy_version)
    return align_records(
        RecordSide(comparison, a.records),
        RecordSide(comparison, b.records),
        prepared,
        coordinate_texts=coordinate_texts,
    )


def decode_authored(
    prepared: PreparedRelease,
    authored: bytes,
    frame: RecordEvaluationFrame,
    *,
    coordinate_texts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate exact independent bytes, without manufacturing producer acceptance."""
    if not isinstance(authored, bytes):
        raise TypeError("authored reference must retain exact submitted bytes")
    payload = prepared.validate_json("ReferenceRecordBatch", authored).model_dump(mode="python")
    expected = (
        PROTOCOL,
        prepared.release_id,
        frame.unit,
        frame.guideline_version,
        frame.reference_policy_version,
        frame.prediction_policy_version,
    )
    actual = tuple(
        payload[key]
        for key in (
            "protocol",
            "release_id",
            "unit_ref",
            "guideline",
            "reference_policy_version",
            "prediction_policy_version",
        )
    )
    if actual != expected or not payload["reason"].strip():
        raise ReferenceError("independent reading differs from frozen guideline/release/frame")
    side = RecordSide(frame, payload["records"])
    align_independent_references(side, side, prepared, coordinate_texts=coordinate_texts)
    return payload


def _coordinates(conn, prepared, unit, records):
    from corpus_structure.semantic.records import authenticated_source_record_coordinates

    return authenticated_source_record_coordinates(
        conn,
        prepared,
        run_id=unit["source_run_id"],
        source_view_id=unit["source_view_id"],
        source=unit["context"][0]["evaluation_frame"]["pin"]["source"],
        records=records,
    )


@dataclass(frozen=True)
class StoredRecordReferencePass:
    id: int
    unit_id: int
    release_id: str
    pass_kind: str
    actor: str
    authored: bytes
    content_digest: str
    frame_id: int
    frame: RecordEvaluationFrame
    records: tuple[Mapping[str, Any], ...]
    reason: str


def record_pass(
    conn: Connection,
    *,
    unit_id: int,
    pass_kind: str,
    actor: str,
    authored: bytes,
    frame: RecordEvaluationFrame,
) -> int:
    if not isinstance(authored, bytes):
        raise TypeError("authored reference must retain exact submitted bytes")
    unit = _unit(conn, unit_id)
    prepared = open_release(conn, unit["release_id"])
    require_bound_operation(prepared, "reference_record_pass")
    if frame.unit != unit["unit_key"] or frame.pin.get("source_view_id") != unit["source_view_id"]:
        raise ReferenceError("record reference frame differs from independently sampled unit")
    payload = prepared.validate_json("ReferenceRecordBatch", authored).model_dump(mode="python")
    if decode_frame(unit["context"][0]) != frame:
        raise ReferenceError("author frame differs from source-only frozen unit")
    contexts = _coordinates(conn, prepared, unit, payload["records"])
    decode_authored(prepared, authored, frame, coordinate_texts=contexts)
    return _call(
        conn,
        "SELECT eval.record_source_record_reference_pass(:u,:k,:a,:b,CAST(:f AS jsonb))",
        u=unit_id,
        k=pass_kind,
        a=actor,
        b=authored,
        f=_json(unit["context"][0]),
    ).scalar_one()


def read_pass(
    conn: Connection, pass_id: int, *, frame_id: int | None = None
) -> StoredRecordReferencePass:
    passes, frames = table("eval.reference_pass"), table("eval.reference_frame")
    row = conn.execute(select(passes).where(passes.c.id == pass_id)).mappings().one()
    query = select(frames).where(frames.c.pass_id == pass_id)
    if frame_id is not None:
        query = query.where(frames.c.id == frame_id)
    citation = conn.execute(query.order_by(frames.c.version.desc()).limit(1)).mappings().one()
    unit = _unit(conn, row["unit_id"])
    authored = bytes(row["authored"])
    if sha256(authored).hexdigest() != row["content_digest"]:
        raise ReferenceError("immutable authored record reference digest differs")
    prepared = open_release(conn, unit["release_id"])
    if unit["context"] != [citation["source_frame"]]:
        raise ReferenceError("retained record pass differs from independently frozen unit frame")
    frame = decode_frame(citation["source_frame"])
    if (citation["source_view_id"], citation["projection_digest"]) != (
        unit["source_view_id"],
        frame.pin["projection_digest"],
    ) or frame.unit != unit["unit_key"]:
        raise ReferenceError("immutable reference frame differs from selected reference unit")
    raw = prepared.validate_json("ReferenceRecordBatch", authored).model_dump(mode="python")
    contexts = _coordinates(conn, prepared, unit, raw["records"])
    payload = decode_authored(prepared, authored, frame, coordinate_texts=contexts)
    return StoredRecordReferencePass(
        pass_id,
        unit["id"],
        prepared.release_id,
        row["pass_kind"],
        row["actor"],
        authored,
        row["content_digest"],
        citation["id"],
        frame,
        tuple(payload["records"]),
        payload["reason"],
    )


def agreement(conn: Connection, unit_id: int) -> dict[str, Any]:
    passes = unit_passes(conn, unit_id)
    if not passes["A"] or not passes["B"]:
        raise ReferenceError("record agreement requires independent A and B")
    a, b = (read_pass(conn, passes[kind][-1]) for kind in ("A", "B"))
    if a.actor == b.actor:
        raise ReferenceError("record A and B require independently identified authors")
    unit = _unit(conn, unit_id)
    prepared = open_release(conn, unit["release_id"])
    contexts = _coordinates(conn, prepared, unit, (*a.records, *b.records))
    return dict(
        unit_id=unit_id,
        comparison_scope="independent_reference_authors",
        frozen_prediction_policy_version=a.frame.prediction_policy_version,
        pass_a=a.id,
        pass_b=b.id,
        a_to_b=align_independent_references(
            RecordSide(a.frame, a.records),
            RecordSide(b.frame, b.records),
            prepared,
            coordinate_texts=contexts,
        ).as_dict(),
        b_to_a=align_independent_references(
            RecordSide(b.frame, b.records),
            RecordSide(a.frame, a.records),
            prepared,
            coordinate_texts=contexts,
        ).as_dict(),
    )


def prediction_records(
    projection,
    *,
    source: str,
    release_id: str,
    realization_id: str,
    source_view_id: int,
    prepared_index=None,
    selected_tasks=None,
    report_method_names: Mapping[int, str] | None = None,
):
    """Consume only an admitted completed SourceRecordProjection, retaining report outcomes.

    Private interpretation IDs remain immutable; assertion lowering links are not part of
    reconstruction. Empty, failed and unsupported reports remain explicit diagnostics.
    """
    if (projection.release_id, projection.realization_id) != (release_id, realization_id):
        raise ReferenceError("prediction projection differs from the frozen completed result")
    from corpus_structure.semantic.record_projection import (
        index_record_projection,
        reconstruct_record,
    )

    index = prepared_index
    if index is None:
        index = getattr(projection, "record_index", None)
    if index is None:
        index = index_record_projection(projection.rows)
    if selected_tasks is None:
        selected_tasks = tuple(
            task
            for task, view in projection.report_source_view_ids.items()
            if view == source_view_id
        )
    # A resolver is authoritative for this source even when it produced no records.
    # Falling back after failure/empty would turn upstream diagnostics into predictions.
    methods = report_method_names or getattr(projection, "report_method_names", {})
    selected_tasks = tuple(selected_tasks)
    resolver_tasks = tuple(
        task for task in selected_tasks if methods.get(task) == "resolve.m1_readings"
    )
    raw_tasks = tuple(
        task for task in selected_tasks if methods.get(task) == "extract.m1_candidates"
    )
    selected_tasks = resolver_tasks or raw_tasks or selected_tasks
    selected = [dict(row) for task in selected_tasks for row in index.reports_by_task.get(task, ())]
    if any(row["source"] != source for row in selected):
        raise ReferenceError("completed prediction changed the frozen logical source alias")
    memberships = [
        (row["selected_task_id"], row["record_id"], row["interpretation_id"])
        for task in selected_tasks
        for row in index.members_by_task.get(task, ())
    ]
    if len(memberships) != len(set(memberships)):
        raise ReferenceError(
            "completed publication repeats a record interpretation within one report"
        )
    # One persisted root may have several legitimate producer-report provenance links.
    identities = sorted(
        {(record_id, interpretation_id) for _, record_id, interpretation_id in memberships}
    )
    records: list[dict[str, Any]] = []
    for identity in identities:
        record = reconstruct_record(index, *identity)
        admissions = index.rows_for(*identity, "record_admission")
        if len(admissions) != 1 or admissions[0]["decision"] not in {
            "candidate",
            "accepted",
            "unresolved",
            "rejected",
        }:
            raise ReferenceError("completed record has no unique native admission standing")
        # SourceRecord remains sealed and candidate. Only the detached evaluation view
        # adopts the native overlay; standing does not participate in interpretation ID.
        records.append(dict(record, standing=admissions[0]["decision"]))
    record_rows = tuple(records)
    if any(row["pin"]["source"] != source for row in record_rows):
        raise ReferenceError("completed public record membership crosses source units")
    return record_rows, tuple(selected)


def report_payload(value: Any) -> Any:
    """Released reports omit undefined ratios; exact zero denominators remain explicit."""
    if isinstance(value, Mapping):
        return {
            key: report_payload(item)
            for key, item in value.items()
            if not (key in {"precision", "recall", "f1"} and item is None)
        }
    if isinstance(value, (list, tuple)):
        return [report_payload(item) for item in value]
    return value


def reference_evaluate(
    conn: Connection,
    *,
    project_id: str,
    run_id: int,
    set_id: int,
    policy_fit: Mapping[str, Any] | None = None,
) -> ReferenceReport:
    completed = _completed(conn, run_id, project_id)
    sets, units = table("eval.reference_set"), table("eval.reference_unit")
    definition = (
        conn.execute(select(sets).where(sets.c.id == set_id, sets.c.project_id == project_id))
        .mappings()
        .one()
    )
    if definition["release_id"] != completed["release_id"]:
        raise ReferenceError("record references and completed publication have different releases")
    if definition["sampling"].get("record_protocol") != PROTOCOL:
        raise ReferenceError("reference set does not declare the record protocol")
    prepared = open_release(conn, completed["release_id"])
    require_bound_operation(prepared, "reference_record_grade")
    selected_units = (
        conn.execute(select(units).where(units.c.set_id == set_id).order_by(units.c.id))
        .mappings()
        .all()
    )
    snapshot = _call(conn, "SELECT eval.native_reference_snapshot(:s)", s=set_id).scalar_one()
    if not selected_units or len(snapshot) != len(selected_units):
        raise ReferenceError(
            "every eligible record unit requires adjudicated C, including empty units"
        )
    from corpus_structure.semantic.record_queries import read_completed_record_projection

    projection = read_completed_record_projection(
        conn,
        run_id=run_id,
        project_id=project_id,
        source_view_ids=tuple(unit["source_view_id"] for unit in selected_units),
    )
    snapshots = {value["unit_id"]: value for value in snapshot}
    reports = []
    prepared_index = projection.record_index
    tasks_by_view: dict[int, list[int]] = {}
    report_method_names: dict[int, str] = {}
    task, cut_task = table("ops.task"), table("ops.cut_task")
    config, method = table("ops.method_config"), table("ops.method")
    # Read method authority from the immutable selected cut, not from producer strings.
    # Include selected tasks without record reports so a failed resolver cannot trigger
    # fallback to an upstream raw report.
    task_rows = conn.execute(
        select(task.c.id, task.c.unit_id, method.c.name)
        .select_from(
            task.join(cut_task, cut_task.c.task_id == task.c.id)
            .join(config, config.c.id == task.c.method_config_id)
            .join(method, method.c.id == config.c.method_id)
        )
        .where(cut_task.c.cut_id == projection.cut_id, task.c.unit_type == "source_view")
        .order_by(task.c.id)
    )
    for task_id, view, name in task_rows:
        tasks_by_view.setdefault(view, []).append(task_id)
        report_method_names[task_id] = name
    populations = {value["unit_key"]: value for value in definition["sampling"]["eligible_units"]}
    for unit in selected_units:
        frozen = snapshots[unit["id"]]
        reference = read_pass(conn, frozen["pass_id"], frame_id=frozen["frame_id"])
        prediction, outcomes = prediction_records(
            projection,
            source=reference.frame.pin["source"],
            source_view_id=unit["source_view_id"],
            release_id=prepared.release_id,
            realization_id=completed["output_realization_id"],
            prepared_index=prepared_index,
            selected_tasks=tasks_by_view.get(unit["source_view_id"], ()),
            report_method_names=report_method_names,
        )
        bound = _unit(conn, unit["id"])
        contexts = _coordinates(conn, prepared, bound, (*reference.records, *prediction))
        aligned = align_records(
            RecordSide(reference.frame, reference.records),
            RecordSide(reference.frame, prediction),
            prepared,
            coordinate_texts=contexts,
        ).as_dict()
        aligned["producer_reports"] = list(outcomes)
        aligned["origin_group"] = populations[unit["unit_key"]]["origin_group"]
        aligned["gap_evidence"] = _call(
            conn,
            "SELECT eval.source_record_gap_evidence(:r,:u,:p,:f)",
            r=run_id,
            u=unit["id"],
            p=frozen["pass_id"],
            f=frozen["frame_id"],
        ).scalar_one()
        reports.append(aligned)
    tiers = {
        tier: TierCounts(
            *(
                sum(unit["tiers"][tier][key] for unit in reports)
                for key in ("reference", "prediction", "matched")
            )
        ).as_dict()
        for tier in TIERS
    }
    families = {
        family: {
            tier: TierCounts(
                *(
                    sum(unit["families"][family][tier][key] for unit in reports)
                    for key in ("reference", "prediction", "matched")
                )
            ).as_dict()
            for tier in TIERS
        }
        for family in FAMILIES
    }
    result = dict(
        protocol=EVALUATION_PROTOCOL,
        release_id=prepared.release_id,
        output_realization_id=completed["output_realization_id"],
        family="source_records",
        comparison_policy=COMPARISON_POLICY,
        grain="accepted_source_record_occurrence",
        tiers=tiers,
        families=families,
        units=reports,
        reference_units_scored=len(reports),
        partition=definition["sampling"]["partition"],
        sampling_digest=_call(
            conn,
            "SELECT encode(sha256(convert_to(sampling::text,'UTF8')),'hex') "
            "FROM eval.reference_set WHERE id=:s",
            s=set_id,
        ).scalar_one(),
        quality_claim="not_established",
    )
    if policy_fit is not None:
        require_bound_operation(prepared, "reference_record_calibrate")
        result["policy_fit"] = dict(policy_fit)
    result = report_payload(result)
    prepared.validate_json("ReferenceRecordEvaluationReport", _json(result))
    identity = _call(
        conn,
        "SELECT eval.record_source_record_reference_evaluation(:p,:r,:s,"
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


def assign_origin(
    conn: Connection,
    *,
    project_id: str,
    origin_group: str,
    partition: str,
    source_uris: Sequence[str],
    provenance: Mapping[str, Any],
) -> None:
    """Explicit credible common origins; chapters never imply independent origin groups."""
    if partition not in PARTITIONS:
        raise ReferenceError("unknown record reference partition")
    _call(
        conn,
        "SELECT eval.assign_record_reference_origin(:p,:g,:t,CAST(:u AS jsonb),CAST(:v AS jsonb))",
        p=project_id,
        g=origin_group,
        t=partition,
        u=_json(source_uris),
        v=_json(provenance),
    )


def source_units(conn: Connection, source_run_id: int) -> tuple[dict[str, Any], ...]:
    """Source-selected pool only; no agent packet, prediction or producer-output filter.

    The set-creation native owner locks and snapshots membership. This read supplies
    source-only authoring inputs; it is not itself a frozen historical population.
    """
    views, membership = table("kb.source_view"), table("ops.run_source_view")
    return tuple(
        dict(row)
        for row in conn.execute(
            select(
                views.c.id.label("source_view_id"),
                views.c.key.label("unit_key"),
                views.c.projection_digest,
                views.c.document_id,
            )
            .join(membership, membership.c.source_view_id == views.c.id)
            .where(membership.c.run_id == source_run_id)
            .order_by(membership.c.position, views.c.id)
        ).mappings()
    )


def source_binding(
    conn: Connection, *, source_run_id: int, source_view_id: int, source_cut_id: int | None = None
) -> str:
    """Freeze actual source-only task/report metadata, never derive aliases from records."""
    return _call(
        conn,
        "SELECT eval.record_reference_source_binding(:r,:v,:c)",
        r=source_run_id,
        v=source_view_id,
        c=source_cut_id,
    ).scalar_one()


def create_reference_set(
    conn: Connection,
    *,
    project_id: str,
    source_run_id: int,
    label: str,
    legacy_split: str,
    guideline: str,
    guideline_text: str,
    partition: str,
    unit_keys: Sequence[str],
    sampling: Mapping[str, Any],
    frames: Mapping[str, RecordEvaluationFrame],
    reference_policy_version: str,
    prediction_policy_version: str,
    captured_coordinates: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    context_dependency_digests: Mapping[str, str] | None = None,
    source_cut_id: int | None = None,
) -> dict[str, Any]:
    """Freeze an independent sample, preserving the historical document split meaning.

    Origin membership is assigned explicitly before this call. This operation records no
    inference about source-group sufficiency and never samples from producer predictions.
    Caller declares seed, strata, inclusion probabilities, provenance and challenge cohort.
    """
    runs = table("ops.run")
    source = (
        conn.execute(
            select(runs).where(runs.c.id == source_run_id, runs.c.project_id == project_id)
        )
        .mappings()
        .one()
    )
    prepared = open_release(conn, source["release_id"])
    require_bound_operation(prepared, "reference_record_set")
    if legacy_split not in {"dev", "test"} or partition not in PARTITIONS:
        raise ReferenceError(
            "record partition and historical document split are distinct contracts"
        )
    if not unit_keys or len(set(unit_keys)) != len(unit_keys):
        raise ReferenceError("reference sample requires unique eligible source units")
    required = {"seed", "strata", "inclusion_probabilities", "provenance", "cohort"}
    if not required <= set(sampling):
        raise ReferenceError(
            "sampling requires seed, strata, inclusion probabilities, provenance and cohort"
        )
    probabilities = sampling["inclusion_probabilities"]
    if set(probabilities) != set(unit_keys) or any(
        isinstance(value, bool) or not isinstance(value, (float, int)) or not 0 < value <= 1
        for value in probabilities.values()
    ):
        raise ReferenceError(
            "every sampled eligible unit requires its declared inclusion probability"
        )
    by_key = {unit["unit_key"]: unit for unit in source_units(conn, source_run_id)}
    if set(unit_keys) - by_key.keys():
        raise ReferenceError("independent reference sample is outside the completed source cut")
    if set(frames) != set(unit_keys):
        raise ReferenceError(
            "every independent sample unit requires its predeclared source-only frame"
        )
    selected = [
        dict(
            source_view_id=by_key[key]["source_view_id"],
            unit_key=key,
            frame=encode_frame(
                frames[key],
                captured_coordinates=(captured_coordinates or {}).get(key, ()),
                context_dependency_digest=(context_dependency_digests or {}).get(key),
            ),
        )
        for key in unit_keys
    ]
    metadata = dict(
        sampling,
        record_protocol=PROTOCOL,
        partition=partition,
        reference_policy_version=reference_policy_version,
        prediction_policy_version=prediction_policy_version,
        population_claim="declared_source_origins_only",
        source_frame_abi=FRAME_PROTOCOL,
        source_cut_id=source_cut_id,
        guideline_text=guideline_text,
        guideline_digest=sha256(guideline_text.encode()).hexdigest(),
    )
    identity = _call(
        conn,
        "SELECT eval.create_source_record_reference_set(:p,:r,:l,:s,:g,"
        "CAST(:m AS jsonb),CAST(:u AS jsonb))",
        p=project_id,
        r=source_run_id,
        l=label,
        s=legacy_split,
        g=guideline,
        m=_json(metadata),
        u=_json(selected),
    ).scalar_one()
    return dict(
        set_id=identity,
        sampling=metadata,
        units=selected,
        release_id=prepared.release_id,
        source_run_id=source_run_id,
    )


def read_fitting_references(conn: Connection, set_id: int) -> tuple[dict[str, Any], ...]:
    """Restricted fitter credentials call a protected feature-fit-only native capability.

    No Python partition filter and no evaluator connection fallback exists here.
    """
    rows = _call(conn, "SELECT eval.read_record_fitting_references(:s)", s=set_id).scalar_one()
    return tuple(rows)


def author_packet(conn: Connection, unit_id: int) -> dict[str, Any]:
    """Independent source-only A/B input, protected by the actual evaluator capability."""
    return _call(conn, "SELECT eval.source_record_author_packet(:u)", u=unit_id).scalar_one()


def adjudication_packet(conn: Connection, unit_id: int) -> dict[str, Any]:
    """C retains the independently submitted A/B bytes and disagreement linkage.

    This is a separate input boundary from author_packet; it contains no producer output.
    """
    passes = unit_passes(conn, unit_id)
    if not passes["A"] or not passes["B"]:
        raise ReferenceError("adjudication requires independently retained A and B")
    a, b = (read_pass(conn, passes[kind][-1]) for kind in ("A", "B"))
    if a.actor == b.actor:
        raise ReferenceError("adjudication requires independently identified authors")
    return dict(
        source=author_packet(conn, unit_id),
        adjudication_passes=(a.id, b.id),
        authors=tuple(
            dict(
                pass_id=value.id,
                actor=value.actor,
                authored=value.authored,
                content_digest=value.content_digest,
            )
            for value in (a, b)
        ),
        disagreement=agreement(conn, unit_id),
    )
