"""Run-bound source operations over the trusted semantic physical model.

Database sequence IDs locate rows only. Reproducible source observations bind the immutable
release, method input and source item; task attempts and sequence IDs do not enter their keys.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from pydantic import BaseModel, JsonValue
from sqlalchemy import Connection, func, insert, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from corpus_structure.core.evidence import RenditionContent
from corpus_structure.core.method import (
    MeasurementView,
    Method,
    ObservationReading,
    RunRendition,
    SourceObservationReference,
    UnitResult,
)
from corpus_structure.core.vocab import ObservationKind, ObservationOutcome, RunKind, TaskUnitType

from .identity import canonical_bytes
from .metadata import table
from .operation_results import ClaimedTask, CompletionResult, HeldProgress, HoldDecision
from .types import PreparedRelease


class OperationConflict(ValueError):
    """Immutable input identity changed or a task/pass fence was lost."""


@dataclass(frozen=True)
class OperationBinding:
    release_id: str
    input_realization_id: str
    input_revision: int
    dependencies: bytes

    def __post_init__(self) -> None:
        import json

        if not self.release_id or not self.input_realization_id or self.input_revision < 0:
            raise ValueError("operation requires release, realization and nonnegative revision")
        if canonical_bytes(json.loads(self.dependencies)) != self.dependencies:
            raise ValueError("dependencies must be canonical immutable JSON bytes")

    @property
    def dependency_digest(self) -> str:
        return sha256(self.dependencies).hexdigest()


def create_run(
    conn: Connection,
    *,
    project_id: str,
    binding: OperationBinding,
    kind: str,
    options: Mapping[str, Any],
    code_commit: str,
    guideline: str = "",
    phase: int = 0,
) -> int:
    import json

    try:
        return conn.execute(
            text("SELECT ops.create_run(:p,:r,:z,:v,:d,:k,:phase,CAST(:opts AS jsonb),:g,:commit)"),
            dict(
                p=project_id,
                r=binding.release_id,
                z=binding.input_realization_id,
                v=binding.input_revision,
                d=binding.dependencies,
                k=kind,
                phase=phase,
                opts=json.dumps(options),
                g=guideline,
                commit=code_commit,
            ),
        ).scalar_one()
    except Exception as exc:
        if getattr(getattr(exc, "orig", None), "sqlstate", None) == "P0004":
            raise OperationConflict("input realization changed before run creation") from exc
        raise


def start_run(conn: Connection, run_id: int) -> int:
    """Start a source run through guarded DML; an exact running replay is harmless."""
    try:
        return conn.execute(text("SELECT ops.start_source_run(:run)"), {"run": run_id}).scalar_one()
    except Exception as exc:
        if getattr(getattr(exc, "orig", None), "sqlstate", None) == "P0004":
            raise OperationConflict("run no longer accepts source execution") from exc
        raise


def binding_of(conn: Connection, run_id: int) -> OperationBinding:
    r = table("ops.run")
    row = conn.execute(select(r).where(r.c.id == run_id)).mappings().one()
    return OperationBinding(
        row["release_id"],
        row["input_realization_id"],
        row["input_revision"],
        bytes(row["dependencies"]),
    )


@dataclass(frozen=True)
class OperationDescriptor:
    name: str
    version: str
    family: str
    tier: str
    unit_type: TaskUnitType
    Config: type[BaseModel]
    confidence_source: str | None = None


def record_method(
    conn: Connection,
    method: Any,
    name: str,
    params: Mapping[str, Any],
    config_hash: str,
    *,
    prepared: PreparedRelease | None = None,
) -> int:
    from .contracts import require_bound_operation

    if prepared is not None:
        require_bound_operation(prepared, "configure_method")
    m = table("ops.method")
    c = table("ops.method_config")
    values = dict(
        name=method.name,
        version=method.version,
        unit_type=str(method.unit_type) if hasattr(method, "unit_type") else None,
        configuration_schema_digest=sha256(
            canonical_bytes(method.Config.model_json_schema())
        ).hexdigest()
        if hasattr(method, "Config")
        else None,
        family=str(method.family),
        tier=str(method.tier),
        confidence_source=str(method.confidence_source)
        if method.confidence_source is not None
        else None,
    )
    conn.execute(pg_insert(m).values(**values).on_conflict_do_nothing())
    declared = (
        conn.execute(select(m).where(m.c.name == method.name, m.c.version == method.version))
        .mappings()
        .one()
    )
    if any(
        declared[k] != value
        for k, value in values.items()
        if not (k in {"unit_type", "configuration_schema_digest"} and declared[k] is None)
    ):
        raise OperationConflict("operation version denotes another method contract")
    mid = declared["id"]
    conn.execute(
        pg_insert(c)
        .values(method_id=mid, name=name, params=dict(params), config_hash=config_hash)
        .on_conflict_do_nothing()
    )
    row = (
        conn.execute(select(c).where(c.c.method_id == mid, c.c.config_hash == config_hash))
        .mappings()
        .one()
    )
    if row["params"] != dict(params):
        raise OperationConflict("configuration hash denotes different parameters")
    return row["id"]


def create_task(
    conn: Connection,
    *,
    run_id: int,
    config_id: int,
    stage: str,
    unit_type: str,
    input_hash: str,
    unit_id: int | None = None,
    unit_key: str | None = None,
    packet_hash: str | None = None,
    agent: bool = False,
    fresh: bool = False,
    trigger: Mapping[str, Any] | None = None,
    skip_reason: str | None = None,
) -> int:
    r = table("ops.run")
    run = (
        conn.execute(text("SELECT * FROM ops.lock_execution_run(:run,'schedule')"), {"run": run_id})
        .mappings()
        .one()
    )
    if run["sealed"] or run["status"] not in {"created", "running"}:
        raise OperationConflict("run no longer accepts tasks")
    t = table("ops.task")
    old_run = r.alias("origin_run")
    twin = (
        None
        if fresh or skip_reason is not None
        else conn.execute(
            select(t.c.id)
            .join(old_run, t.c.run_id == old_run.c.id)
            .where(
                t.c.method_config_id == config_id,
                t.c.input_hash == input_hash,
                t.c.status.in_(["done", "empty"]),
                t.c.unit_type == unit_type,
                t.c.unit_id.is_not_distinct_from(unit_id),
                t.c.unit_key.is_not_distinct_from(unit_key),
                t.c.packet_hash.is_not_distinct_from(packet_hash),
                old_run.c.project_id == run["project_id"],
                old_run.c.release_id == run["release_id"],
                old_run.c.input_realization_id == run["input_realization_id"],
                old_run.c.input_revision == run["input_revision"],
                old_run.c.dependency_digest == run["dependency_digest"],
            )
            .order_by(t.c.id)
            .limit(1)
        ).scalar_one_or_none()
    )
    task_id = conn.execute(
        insert(t)
        .values(
            run_id=run_id,
            release_id=run["release_id"],
            stage=stage,
            unit_type=unit_type,
            unit_id=unit_id,
            unit_key=unit_key,
            method_config_id=config_id,
            input_hash=input_hash,
            packet_hash=packet_hash,
            reused_task_id=twin,
            **({"trigger": dict(trigger)} if trigger is not None else {}),
            reason=skip_reason,
            status="skipped"
            if skip_reason is not None
            else "reused"
            if twin is not None
            else ("awaiting_agent" if agent else "pending"),
            attempt=0,
            cost={},
            priority=0,
            created_at=func.clock_timestamp(),
            finished_at=func.clock_timestamp()
            if twin is not None or skip_reason is not None
            else None,
        )
        .returning(t.c.id)
    ).scalar_one()
    if twin is not None:
        build = table("ops.rendition_build")
        rr = table("ops.run_rendition")
        for item in conn.execute(
            select(build.c.document_id, build.c.rendition_id).where(build.c.task_id == twin)
        ):
            conn.execute(
                pg_insert(rr)
                .values(run_id=run_id, document_id=item.document_id, rendition_id=item.rendition_id)
                .on_conflict_do_nothing()
            )
    return task_id


def claim_tasks(
    conn: Connection,
    *,
    run_id: int,
    config_id: int,
    holder: str,
    limit: int = 1,
    agent: bool = False,
) -> tuple[ClaimedTask, ...]:
    if limit < 1:
        raise ValueError("positive claim limit required")
    if not isinstance(holder, str) or not holder:
        raise ValueError("nonempty claim holder required")
    rows = conn.execute(
        text("SELECT * FROM ops.claim_tasks(:run,:config,:holder,:limit,:agent)"),
        {"run": run_id, "config": config_id, "holder": holder, "limit": limit, "agent": agent},
    ).mappings()
    from corpus_structure.core.vocab import TaskUnitType

    return tuple(
        ClaimedTask(
            task_id=row["id"],
            run_id=row["run_id"],
            release_id=row["release_id"],
            method_config_id=row["method_config_id"],
            unit_type=TaskUnitType(row["unit_type"]),
            unit_id=row["unit_id"],
            unit_key=row["unit_key"],
            packet_hash=row["packet_hash"],
            attempt=row["attempt"],
            holder=row["claimed_by"],
            deadline=row["lease_until"],
            invocation_key=row["invocation_key"],
            held_progress=HeldProgress.model_validate(
                row["error"]["semantic_proposal_first_result"]
            )
            if row["error"] and "semantic_proposal_first_result" in row["error"]
            else None,
        )
        for row in rows
    )


def observation_key(
    binding: OperationBinding, input_hash: str, definition: str, item_key: str, invocation_key: str
) -> str:
    return (
        "observation:"
        + sha256(
            canonical_bytes(
                [
                    binding.release_id,
                    binding.dependency_digest,
                    input_hash,
                    definition,
                    item_key,
                    invocation_key,
                ]
            )
        ).hexdigest()
    )


def complete_task(
    conn: Connection,
    *,
    task_id: int,
    attempt: int,
    holder: str,
    prepared: PreparedRelease,
    observations: Sequence[Mapping[str, Any]],
    outcome: str = "done",
    error: Mapping[str, Any] | None = None,
    envelope: Mapping[str, Any] | None = None,
) -> CompletionResult:
    """Validate the bound producer envelope, then atomically fence and append source results."""
    from .contracts import require_bound_operation

    require_bound_operation(prepared, "complete")
    if outcome not in {"done", "empty", "failed"}:
        raise ValueError("invalid terminal outcome")
    if (outcome == "done") != bool(observations):
        raise ValueError("terminal outcome contradicts observations")
    if (outcome == "failed") != bool(error):
        raise ValueError("failure requires explicit error")
    t = table("ops.task")
    task = conn.execute(select(t).where(t.c.id == task_id)).mappings().one()
    binding = binding_of(conn, task["run_id"])
    if prepared.release_id != binding.release_id:
        raise OperationConflict("wrong producer release")
    rows = []
    for ordinal, raw in enumerate(observations):
        data = dict(raw)
        definition = data.pop("payload_definition")
        item = data.pop("item_key")
        payload = prepared.validate_python(definition, data.pop("payload")).model_dump(mode="json")
        if data.get("rendition_id") is None and task["unit_type"] == "segment":
            segments = table("kb.segment")
            data["rendition_id"] = conn.execute(
                select(segments.c.rendition_id).where(segments.c.id == task["unit_id"])
            ).scalar_one()
            data.setdefault("segment_id", task["unit_id"])
        elif data.get("rendition_id") is None and task["unit_type"] == "rendition":
            data["rendition_id"] = task["unit_id"]
        if task["unit_type"] == "source_view":
            if data.get("source_view_id") not in (None, task["unit_id"]) or any(
                data.get(field) is not None for field in ("rendition_id", "segment_id", "span_id")
            ):
                raise OperationConflict("source-view observation differs from its task unit")
            data["source_view_id"] = task["unit_id"]
        supplied_key = data.pop("observation_key", None)
        if definition == "SourceObservation" and supplied_key != payload["observation_key"]:
            raise OperationConflict("source observation identity differs from bound report")
        rows.append(
            dict(
                data,
                ordinal=ordinal,
                payload_definition=definition,
                payload=payload,
                observation_key=supplied_key
                or observation_key(
                    binding, task["input_hash"], definition, item, task["invocation_key"]
                ),
            )
        )
    import json

    try:
        result = conn.execute(
            text(
                "SELECT ops.complete_task(:task,:attempt,:holder,CAST(:rows AS "
                "jsonb),:outcome,CAST(:error AS jsonb),CAST(:envelope AS jsonb))::text"
            ),
            dict(
                task=task_id,
                attempt=attempt,
                holder=holder,
                rows=json.dumps(rows),
                outcome=outcome,
                error=json.dumps(error),
                envelope=json.dumps(envelope) if envelope is not None else None,
            ),
        ).scalar_one()
    except Exception as exc:
        if getattr(getattr(exc, "orig", None), "sqlstate", None) in {"P0004", "55000"}:
            raise OperationConflict("task attempt lost or run sealed") from exc
        raise
    completion = CompletionResult.model_validate_json(result, strict=True)
    from .operation_results import validate_result_dimension

    validate_result_dimension(
        prepared, "complete", "protocol", completion.receipt.protocol, field="receipt.protocol"
    )
    validate_result_dimension(
        prepared, "complete", "transaction", completion.transaction, field="transaction"
    )
    return completion


def seal_cut(conn: Connection, run_id: int, name: str, *, final: bool = False) -> int:
    return conn.execute(
        text("SELECT ops.capture_cut(:run,:name,:final)"), dict(run=run_id, name=name, final=final)
    ).scalar_one()


def cut_observations(conn: Connection, cut_id: int) -> list[dict[str, Any]]:
    o = table("kb.observation")
    c = table("ops.cut_task")
    return [
        dict(row)
        for row in conn.execute(
            select(o)
            .join(c, o.c.task_id == c.c.origin_task_id)
            .where(c.c.cut_id == cut_id)
            .distinct()
            .order_by(o.c.observation_key)
        ).mappings()
    ]


def register_document(
    conn: Connection,
    *,
    project_id: str,
    source_uri: str,
    original_path: str,
    original: bytes,
    mime: str,
    title: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    prepared: PreparedRelease | None = None,
) -> int:
    from .contracts import require_bound_operation

    if prepared is not None:
        require_bound_operation(prepared, "register_document")
    from pathlib import Path

    if Path(original_path).read_bytes() != original:
        raise OperationConflict("retained original bytes differ from registered source")
    content_hash = sha256(original).hexdigest()
    from corpus_structure.core.evidence import document_key

    key = document_key(project_id, source_uri, content_hash)
    t = table("kb.document")
    values = dict(
        project_id=project_id,
        key=key,
        source_uri=source_uri,
        content_hash=content_hash,
        original_path=original_path,
        mime=mime,
        title=title,
        meta=dict(metadata or {}),
    )
    conn.execute(pg_insert(t).values(**values).on_conflict_do_nothing())
    row = (
        conn.execute(select(t).where(t.c.project_id == project_id, t.c.key == key)).mappings().one()
    )
    if any(row[k] != v for k, v in values.items()):
        raise OperationConflict("source identity denotes another source descriptor")
    conn.execute(
        text("SELECT ops.retain_source_artifact(:document,:original)"),
        dict(document=row["id"], original=original),
    )
    return row["id"]


class SourceReadRefused(OperationConflict):
    """An owned source-read failure with an explicit modeled outcome."""

    def __init__(self, outcome: str, reason: str):
        self.outcome = outcome
        super().__init__(reason)


def _source_read_outcome(prepared: PreparedRelease | None, operation: str, outcome: str) -> None:
    from .operation_results import validate_result_dimension
    from .outcomes import CODE_OUTCOME_DOMAINS

    if prepared is not None:
        validate_result_dimension(prepared, operation, "outcome", outcome, field="outcome")
    elif outcome not in CODE_OUTCOME_DOMAINS["read"]:
        raise ValueError("source-read outcome is outside the supported base protocol")


def read_original(
    conn: Connection, document_id: int, *, prepared: PreparedRelease | None = None
) -> bytes:
    """Translate a verified original payload or a modeled missing/invalid read refusal."""
    from pathlib import Path

    t = table("kb.document")
    row = conn.execute(select(t).where(t.c.id == document_id)).mappings().one_or_none()
    if row is None:
        _source_read_outcome(prepared, "read_original", "missing")
        raise SourceReadRefused("missing", "retained original document is missing")
    artifact = table("kb.source_artifact")
    retained = conn.execute(
        select(artifact.c.content).where(artifact.c.artifact_digest == row["content_hash"])
    ).scalar_one_or_none()
    if retained is not None:
        data = bytes(retained)
        if sha256(data).hexdigest() != row["content_hash"]:
            _source_read_outcome(prepared, "read_original", "invalid")
            raise SourceReadRefused("invalid", "retained original artifact is corrupt")
        _source_read_outcome(prepared, "read_original", "source_ready")
        return data
    try:
        data = Path(row["original_path"]).read_bytes()
    except FileNotFoundError as exc:
        _source_read_outcome(prepared, "read_original", "missing")
        raise SourceReadRefused("missing", "retained original file is missing") from exc
    if sha256(data).hexdigest() != row["content_hash"]:
        _source_read_outcome(prepared, "read_original", "invalid")
        raise SourceReadRefused("invalid", "retained original content changed")
    _source_read_outcome(prepared, "read_original", "source_ready")
    return data


def store_rendition(
    conn: Connection,
    *,
    run_id: int,
    document_id: int,
    content: RenditionContent,
    task_id: int,
    config_id: int,
    parse_detail: Mapping[str, Any],
    text_layout: Mapping[str, Any] | None = None,
    prepared: PreparedRelease | None = None,
) -> int:
    """Preserve physical content sharing separately from method build provenance."""
    from .contracts import require_database_operation

    require_database_operation(conn, binding_of(conn, run_id).release_id, "store_rendition")
    if text_layout is not None:
        from .text_layouts import load_text_layouts

        if prepared is None or not load_text_layouts(text_layout, content, prepared, config_id):
            raise OperationConflict("token artifact requires its admitted source release")
    payload = content.model_dump(mode="json")
    from corpus_structure.core.evidence import content_digest, rendition_key, segment_key

    digest = content_digest(content)
    d = table("kb.document")
    source = conn.execute(select(d.c.key).where(d.c.id == document_id)).scalar_one()
    key = rendition_key(source, digest)
    t = table("kb.rendition")
    values = dict(
        document_id=document_id,
        key=key,
        content_digest=digest,
        canonical_text=content.canonical_text,
        content=payload,
        parse_status=str(content.parse_status),
    )
    conn.execute(pg_insert(t).values(**values).on_conflict_do_nothing())
    row = conn.execute(select(t).where(t.c.key == key)).mappings().one()
    if any(row[k] != v for k, v in values.items()):
        raise OperationConflict("rendition identity denotes different content")
    rendition_id = row["id"]
    st = table("kb.segment")
    counter = [0]

    def put(segment: Any, parent: str | None = None) -> None:
        skey = segment_key(key, segment.kind, segment.start, segment.end)
        conn.execute(
            pg_insert(st)
            .values(
                rendition_id=rendition_id,
                segment_key=skey,
                parent_key=parent,
                kind=str(segment.kind),
                ordinal=counter[0],
                start_offset=segment.start,
                end_offset=segment.end,
                attrs=dict(segment.attrs),
                parse_status=str(segment.parse_status),
                parse_reason=segment.parse_reason,
            )
            .on_conflict_do_nothing()
        )
        counter[0] += 1
        for child in segment.children:
            put(child, skey)

    put(content.document)
    b = table("ops.rendition_build")
    build = dict(
        document_id=document_id,
        method_config_id=config_id,
        rendition_id=rendition_id,
        task_id=task_id,
        parse_detail=dict(parse_detail),
        text_layout=dict(text_layout) if text_layout is not None else None,
    )
    conn.execute(pg_insert(b).values(**build).on_conflict_do_nothing())
    stored_build = conn.execute(select(b).where(b.c.task_id == task_id)).mappings().one()
    if any(stored_build[k] != v for k, v in build.items()):
        raise OperationConflict("rendition build artifact differs on retry")
    tasks = table("ops.task")
    current_hash = conn.execute(
        select(tasks.c.input_hash).where(tasks.c.id == task_id)
    ).scalar_one()
    previous = (
        conn.execute(
            select(b.c.rendition_id)
            .join(tasks, b.c.task_id == tasks.c.id)
            .where(
                b.c.document_id == document_id,
                b.c.method_config_id == config_id,
                tasks.c.input_hash == current_hash,
            )
        )
        .scalars()
        .all()
    )
    if any(value != rendition_id for value in previous):
        raise OperationConflict("deterministic rendition build changed content")
    rr = table("ops.run_rendition")
    conn.execute(
        pg_insert(rr)
        .values(run_id=run_id, document_id=document_id, rendition_id=rendition_id)
        .on_conflict_do_nothing()
    )
    chosen = conn.execute(
        select(rr.c.rendition_id).where(rr.c.run_id == run_id, rr.c.document_id == document_id)
    ).scalar_one()
    if chosen != rendition_id:
        raise OperationConflict("run already selected another source rendition")
    return rendition_id


def read_rendition(
    conn: Connection, rendition_id: int, *, prepared: PreparedRelease | None = None
) -> RenditionContent:
    """Translate a typed rendition payload or an explicit modeled source-read refusal."""
    from pydantic import ValidationError

    from corpus_structure.core.evidence import RenditionContent

    t = table("kb.rendition")
    payload = conn.execute(select(t.c.content).where(t.c.id == rendition_id)).scalar_one_or_none()
    if payload is None:
        _source_read_outcome(prepared, "read_rendition", "missing")
        raise SourceReadRefused("missing", "retained rendition is missing")
    try:
        content = RenditionContent.model_validate(payload)
    except ValidationError as exc:
        _source_read_outcome(prepared, "read_rendition", "invalid")
        raise SourceReadRefused("invalid", "retained rendition content is invalid") from exc
    _source_read_outcome(prepared, "read_rendition", "source_ready")
    return content


def complete_unit_result(
    conn: Connection,
    *,
    task_id: int,
    attempt: int,
    holder: str,
    prepared: PreparedRelease,
    result: UnitResult,
    method: Method[Any] | OperationDescriptor,
    configuration_hash: str,
    source: str,
) -> CompletionResult:
    """The actual recognizer terminal boundary: binding, source storage and one native fence."""
    from .contracts import require_bound_operation

    require_bound_operation(prepared, "complete_unit")
    from .observations import bind_result, source_python

    task_table = table("ops.task")
    initial = conn.execute(select(task_table).where(task_table.c.id == task_id)).mappings().one()
    conn.execute(
        text("SELECT * FROM ops.lock_execution_run(:run,'complete_unit')"),
        {"run": initial["run_id"]},
    ).one()
    task = (
        conn.execute(select(task_table).where(task_table.c.id == task_id).with_for_update())
        .mappings()
        .one()
    )
    if task["attempt"] != attempt or task["claimed_by"] != holder:
        raise OperationConflict("recognizer attempt lost")
    bound = bind_result(
        prepared,
        source=source,
        method=method.name,
        operation_version=method.version,
        configuration_hash=configuration_hash,
        input_hash=task["input_hash"],
        invocation_key=task["invocation_key"],
        result=result,
        method_confidence_source=str(method.confidence_source)
        if method.confidence_source is not None
        else None,
    )
    envelope = bound.model_dump(mode="python")
    items = envelope.pop("observations", [])
    rendition_id = None
    if result.rendition is not None and task["status"] == "running":
        if result.ref.unit_id is None:
            raise ValueError("ingest result requires document id")
        from .text_layouts import freeze_text_layouts

        rendition_id = store_rendition(
            conn,
            run_id=task["run_id"],
            document_id=result.ref.unit_id,
            content=result.rendition,
            task_id=task_id,
            config_id=task["method_config_id"],
            parse_detail=result.parse_detail or {},
            prepared=prepared,
            text_layout=freeze_text_layouts(
                result.text_layouts, result.rendition, prepared, task["method_config_id"]
            ),
        )
    elif result.rendition is not None:
        builds = table("ops.rendition_build")
        from .text_layouts import freeze_text_layouts

        previous_build = (
            conn.execute(select(builds).where(builds.c.task_id == task_id)).mappings().one()
        )
        rendition_id = previous_build["rendition_id"]
        artifact = freeze_text_layouts(
            result.text_layouts, result.rendition, prepared, task["method_config_id"]
        )
        if previous_build["text_layout"] != artifact or previous_build["parse_detail"] != dict(
            result.parse_detail or {}
        ):
            raise OperationConflict("terminal rendition build artifact differs")
        if read_rendition(conn, rendition_id, prepared=prepared) != result.rendition:
            raise OperationConflict("terminal rendition result differs from published content")
    if result.native_products:
        from .pdf_contracts import store_pdf_product

        for product in result.native_products:
            store_pdf_product(
                conn, task_id=task_id, attempt=attempt, holder=holder, product=product
            )
    if result.integrated_products:
        from .pdf_integrated import store_integrated_pdf_product

        for product in result.integrated_products:
            store_integrated_pdf_product(
                conn, task_id=task_id, attempt=attempt, holder=holder, product=product
            )
    if result.source_views:
        from .source_views import store_source_view

        for position, draft in enumerate(result.source_views):
            store_source_view(
                conn,
                run_id=task["run_id"],
                task_id=task_id,
                attempt=attempt,
                holder=holder,
                draft=draft,
                position=position,
            )
    rows = []
    for item in items:
        rid = item.get("rendition_id", rendition_id)
        span_id = None
        if rid is not None and item.get("span_start") is not None:
            st = table("kb.span")
            vals = dict(
                rendition_id=rid,
                start_offset=item["span_start"],
                end_offset=item["span_end"],
                segment_id=item.get("segment_id"),
            )
            conn.execute(pg_insert(st).values(**vals).on_conflict_do_nothing())
            span_id = conn.execute(
                select(st.c.id).where(
                    st.c.rendition_id == rid,
                    st.c.start_offset == item["span_start"],
                    st.c.end_offset == item["span_end"],
                )
            ).scalar_one()
        rows.append(
            dict(
                payload_definition="SourceObservation",
                item_key=item["item_key"],
                observation_key=item["observation_key"],
                payload=item,
                kind=item["family"],
                rendition_id=rid,
                source_view_id=item.get("source_view_id"),
                segment_id=item.get("segment_id"),
                span_id=span_id,
                score=source_python(item["score"]) if item.get("score") is not None else None,
                outcome=item["outcome"],
            )
        )
    outcome = {"produced": "done", "empty": "empty", "failed": "failed"}[result.outcome.value]
    # Rendition-only ingestion is a successful read without extracted assertions. The operation
    # envelope preserves that distinction; native completion still uses empty observations.
    ids = complete_task(
        conn,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        prepared=prepared,
        observations=rows,
        outcome=outcome,
        error={"message": result.error} if result.error else None,
        envelope=envelope,
    )
    return ids


@dataclass(frozen=True)
class BoundRunView:
    run_id: int
    kind: RunKind
    phase: int
    reference_run_id: int | None
    binding: OperationBinding
    prepared: PreparedRelease
    options: Mapping[str, JsonValue]
    reader: BoundReader


@dataclass(frozen=True)
class SourceObservationView:
    id: int
    task_id: int
    kind: ObservationKind
    rendition_id: int | None
    segment_id: int | None
    span_id: int | None
    payload: Mapping[str, JsonValue]
    payload_hash: str
    score: float | None
    outcome: ObservationOutcome
    observation_key: str
    release_id: str
    input_refs: tuple[SourceObservationReference, ...] = ()
    source_view_id: int | None = None
    native_pointer: str | None = None
    projected_span: tuple[int, int] | None = None
    recognized_span: tuple[int, int] | None = None


class BoundReader:
    """Run-scoped source reader; never consults an active project pointer.

    Retained-read mode preserves source custody without admitting analytical preparation.
    Its callers still require the archived read operation and database read privileges.
    """

    def __init__(
        self,
        conn: Connection,
        run_id: int,
        prepared: PreparedRelease,
        cut_id: int | None = None,
        *,
        analysis: bool = True,
    ):
        self.conn, self.run_id, self.prepared, self.cut_id = conn, run_id, prepared, cut_id
        self._analysis_enabled = analysis
        import json

        from .contracts import EXECUTION_COMPILER_VERSION, execution_payload

        payload = execution_payload(prepared)
        self._source_contract = None
        self._source_inputs = {}
        self.math_readings_batch = None
        self.source_tasks: dict[int, int] = {}
        if (
            analysis
            and payload is not None
            and json.loads(payload)["inputs"]["compiler_version"] == EXECUTION_COMPILER_VERSION
        ):
            from .analysis_contracts import bind_analysis_family

            self._source_contract = bind_analysis_family(prepared, "source")

    def pdf_contract(self):
        from .pdf_contracts import pdf_context_for_release

        return pdf_context_for_release(self.conn, self.prepared).boundary

    def source_views(self):
        cached = getattr(self, "_native_view_refs", None)
        if cached is not None:
            return cached
        from .source_views import selected_source_views

        selected = tuple(
            v for v in selected_source_views(self.conn, self.run_id) if v.analysis_eligible
        )
        run = table("ops.run")
        options = self.conn.execute(
            select(run.c.options).where(run.c.id == self.run_id)
        ).scalar_one()
        scope = options.get("scope")
        if not isinstance(scope, dict) or scope.get("kind") != "native_sections":
            self._native_view_refs = selected
            return selected
        boundary = self.pdf_contract()
        scope = boundary.validate_json(
            "PdfNativeSourceScope", __import__("json").dumps(scope)
        ).model_dump(mode="json")
        from .source_views import scope_source_views

        self._native_view_refs = scope_source_views(self.conn, selected, scope)
        return self._native_view_refs

    def source_view(self, source_view_id: int):
        from .source_views import load_source_view, selected_source_views

        if source_view_id not in {r.id for r in selected_source_views(self.conn, self.run_id)}:
            raise OperationConflict("source view is outside bound run")
        cache = getattr(self, "_native_views", None)
        if cache is None:
            cache = {}
            self._native_views = cache
        if source_view_id not in cache:
            cache[source_view_id] = load_source_view(
                self.conn, source_view_id, analysis=self._analysis_enabled
            )
        return cache[source_view_id]

    def ancestor_source_views(self, source_view_id: int):
        from .source_views import selected_source_views

        source = self.source_view(source_view_id)
        ancestors = {a["self_ref"] for a in source.ancestors}
        selected = selected_source_views(self.conn, self.run_id)
        return tuple(
            v
            for v in selected
            if v.native_product == source.ref.native_product and v.section_pointer in ancestors
        )

    def native_document(self, reference):
        import json

        from .pdf_contracts import PreparedPdfProduct, pdf_context_for_task

        identity = table("ops.pdf_product")
        product, build, artifact = (
            table("ops.pdf_selected_product"),
            table("ops.source_build"),
            table("kb.source_artifact"),
        )
        row = (
            self.conn.execute(
                select(
                    product.c.payload,
                    product.c.contract_digest,
                    product.c.schema_digest,
                    product.c.recipe_digest,
                    identity.c.kind.label("product_kind"),
                    build.c.artifact_digest.label("original_digest"),
                )
                .join(
                    identity,
                    (identity.c.task_id == product.c.task_id)
                    & (identity.c.product_key == product.c.product_key),
                )
                .join(build, build.c.task_id == product.c.task_id)
                .where(
                    product.c.task_id == reference.task_id,
                    product.c.product_key == reference.product_key,
                    product.c.content_digest == reference.content_digest,
                )
            )
            .mappings()
            .one()
        )
        from .source_views import selected_source_views

        # Custody is bound to selected pins or a claimed input, before analysis-unit filtering.
        permitted = any(
            view.native_product == reference
            for view in selected_source_views(self.conn, self.run_id)
        )
        if self.source_tasks:
            task, config, run, document = (
                table("ops.task"),
                table("ops.method_config"),
                table("ops.run"),
                table("kb.document"),
            )
            declared = self.conn.execute(
                select(config.c.params, document.c.content_hash, document.c.project_id)
                .join(task, task.c.method_config_id == config.c.id)
                .join(document, document.c.id == task.c.unit_id)
                .where(
                    task.c.id.in_(tuple(self.source_tasks.values())),
                    task.c.run_id == self.run_id,
                    task.c.unit_type == "document",
                    task.c.status == "running",
                )
            ).mappings()
            project = self.conn.execute(
                select(run.c.project_id).where(run.c.id == self.run_id)
            ).scalar_one()
            producer_project = self.conn.execute(
                select(run.c.project_id)
                .join(task, task.c.run_id == run.c.id)
                .where(task.c.id == reference.task_id)
            ).scalar_one()
            claims = list(declared)
            for item in claims:
                if (
                    item["params"].get("integrated_product") == reference.values()
                    and row["product_kind"] != "integrated"
                ):
                    raise OperationConflict(
                        "integrated input role requires an integrated PDF product"
                    )
                if (
                    item["params"].get("native_product") == reference.values()
                    and row["product_kind"] != "native"
                ):
                    raise OperationConflict("native input role requires a native PDF product")
            permitted = permitted or any(
                (
                    item["params"].get("native_product") == reference.values()
                    or item["params"].get("integrated_product") == reference.values()
                )
                and item["content_hash"] == row["original_digest"]
                and item["project_id"] == project == producer_project
                for item in claims
            )
        if not permitted:
            raise OperationConflict(
                "whole-native read requires a selected source view or exact claimed "
                "method input pin"
            )
        context = pdf_context_for_task(self.conn, reference.task_id)
        if row["contract_digest"] != context.contract_digest:
            raise OperationConflict("native product archived contract differs")
        from .pdf_contracts import pdf_context_for_release

        if (
            row["schema_digest"]
            != pdf_context_for_release(self.conn, self.prepared).native_schema_digest
        ):
            raise OperationConflict("native adoption consumer does not admit producer schema")
        context.execution.require_operation("publish_native_document")
        contents = dict(
            self.conn.execute(
                select(artifact.c.artifact_digest, artifact.c.content).where(
                    artifact.c.artifact_digest.in_(
                        [row["original_digest"], row["schema_digest"], row["recipe_digest"]]
                    )
                )
            ).all()
        )
        payload = bytes(row["payload"])
        values = json.loads(payload)
        if values.get("kind") == "integrated":
            payload = canonical_bytes(values["content"])
        return PreparedPdfProduct(
            payload,
            bytes(contents[row["original_digest"]]),
            bytes(contents[row["schema_digest"]]),
            bytes(contents[row["recipe_digest"]]),
            row["contract_digest"],
        )

    def native_product_reference(self, document_id: int, product_key: str, digest: str):
        from .product_reference import ProductReference

        if document_id not in self.source_tasks:
            raise OperationConflict("native product requires real claimed source task")
        return ProductReference(self.source_tasks[document_id], product_key, digest)

    def pdf_context(self):
        from .pdf_contracts import pdf_context_for_task

        if not self.source_tasks:
            raise OperationConflict("PDF preparation requires a bound source task")
        context = getattr(self, "_pdf_context", None)
        if context is None:
            context = pdf_context_for_task(self.conn, next(iter(self.source_tasks.values())))
            self._pdf_context = context
        return context

    def prepare_integrated_pdf_product(
        self, payload, original, recipe_bytes, *, artifacts=(), native_schema=None
    ):
        from .pdf_integrated import prepare_integrated_pdf_product

        return prepare_integrated_pdf_product(
            payload,
            original,
            recipe_bytes,
            artifacts=artifacts,
            native_schema=native_schema,
            context=self.pdf_context(),
        )

    def prepare_pdf_product(self, payload, original, schema_bytes, recipe_bytes):
        from .pdf_contracts import pdf_context_for_task, prepare_pdf_product

        if not self.source_tasks:
            raise OperationConflict("native preparation requires bound source task")
        context = getattr(self, "_pdf_context", None)
        if context is None:
            context = pdf_context_for_task(self.conn, next(iter(self.source_tasks.values())))
            self._pdf_context = context
        return prepare_pdf_product(payload, original, schema_bytes, recipe_bytes, context=context)

    def renditions(self) -> Sequence[RunRendition]:
        from corpus_structure.core.method import RunRendition

        rr, d, r = table("ops.run_rendition"), table("kb.document"), table("kb.rendition")
        q = (
            select(d.c.id, d.c.key, r.c.id.label("rendition_id"), r.c.key.label("rendition_key"))
            .join_from(rr, d, rr.c.document_id == d.c.id)
            .join(r, rr.c.rendition_id == r.c.id)
            .where(rr.c.run_id == self.run_id)
            .order_by(d.c.key)
        )
        return [
            RunRendition(row.id, row.key, row.rendition_id, row.rendition_key)
            for row in self.conn.execute(q)
        ]

    def content(self, rendition_id: int) -> RenditionContent:
        if not self._analysis_enabled:
            raise OperationConflict("retained source reader cannot prepare analytical inputs")
        if self._source_contract is not None:
            self._source_inputs[rendition_id] = self._source_contract.prepare(
                release=self.prepared.release_id,
                rendition=rendition_id,
                profile=self.prepared.execution_model_id,
            )
        return read_rendition(self.conn, rendition_id, prepared=self.prepared)

    def original(self, document_id: int) -> bytes:
        """Read retained source bytes only within this reader's run/project binding."""
        document, run = table("kb.document"), table("ops.run")
        permitted = self.conn.execute(
            select(document.c.id)
            .join_from(document, run, document.c.project_id == run.c.project_id)
            .where(
                document.c.id == document_id,
                run.c.id == self.run_id,
                run.c.release_id == self.prepared.release_id,
            )
        ).scalar_one_or_none()
        if permitted is None:
            raise OperationConflict("original source is outside the bound run/project")
        return read_original(self.conn, document_id, prepared=self.prepared)

    def bind_source_tasks(self, tasks: Mapping[int, int]) -> None:
        """Bind one claimed batch; task identity never comes from a fabricated placeholder."""
        if any(document < 1 or task < 1 for document, task in tasks.items()):
            raise ValueError("source task binding requires real document/task identities")
        self.source_tasks = dict(tasks)

    def segments(self, rendition_id: int) -> Mapping[str, int]:
        s = table("kb.segment")
        return {
            row.segment_key: row.id
            for row in self.conn.execute(
                select(s.c.segment_key, s.c.id).where(s.c.rendition_id == rendition_id)
            )
        }

    def source_observations(self, source_view_id: int, method: str, kind: ObservationKind):
        self.source_view(source_view_id)
        return self._observations(source_view_id, method, kind, native=True)

    def observations(
        self, rendition_id: int, method: str, kind: ObservationKind
    ) -> Sequence[ObservationReading]:
        return self._observations(rendition_id, method, kind, native=False)

    def _observations(self, source_id: int, method: str, kind: ObservationKind, *, native: bool):
        from corpus_structure.core.method import payload_hash
        from corpus_structure.core.vocab import ObservationKind, ObservationOutcome

        from .observations import source_python

        o, t, c, m = (
            table("kb.observation"),
            table("ops.task"),
            table("ops.method_config"),
            table("ops.method"),
        )
        q = (
            select(o)
            .select_from(t)
            .join(o, o.c.task_id == func.coalesce(t.c.reused_task_id, t.c.id))
            .join(c, t.c.method_config_id == c.c.id)
            .join(m, c.c.method_id == m.c.id)
            .where(
                t.c.run_id == self.run_id,
                (o.c.source_view_id == source_id if native else o.c.rendition_id == source_id),
                m.c.name == method,
                o.c.kind == str(kind),
            )
            .order_by(o.c.ordinal)
        )
        if self.cut_id is not None:
            cut = table("ops.cut_task")
            q = q.join(cut, cut.c.origin_task_id == o.c.task_id).where(cut.c.cut_id == self.cut_id)
        out = []
        for row in self.conn.execute(q).mappings():
            payload = (
                source_python(row["payload"]["payload"])
                if row["payload_definition"] == "SourceObservation"
                else row["payload"]
            )
            # ObservationView is the recognizer's pure source representation. Domain boundary
            # interpretation stays in PreparedRelease, not the legacy payload-schema registry.
            out.append(
                SourceObservationView(
                    row["id"],
                    row["task_id"],
                    ObservationKind(row["kind"]),
                    row["rendition_id"],
                    row["segment_id"],
                    row["span_id"],
                    payload,
                    payload_hash(payload),
                    float(row["score"]) if row["score"] is not None else None,
                    ObservationOutcome(row["outcome"]),
                    row["observation_key"],
                    row["release_id"],
                    tuple(
                        SourceObservationReference(ref["observation_key"], ref["role"])
                        for ref in row["payload"].get("inputs", ())
                    ),
                    row["source_view_id"],
                    row["payload"].get("native_pointer"),
                    (
                        (row["payload"]["projected_start"], row["payload"]["projected_end"])
                        if row["payload"].get("projected_start") is not None
                        else None
                    ),
                    (
                        (row["payload"]["recognized_start"], row["payload"]["recognized_end"])
                        if row["payload"].get("recognized_start") is not None
                        else None
                    ),
                )
            )
        return out

    def source_view_coverage(self, source_view_id: int, method: str):
        from corpus_structure.core.method import CoverageDraft, SourceCoverageReading

        source = self.source_view(source_view_id)
        task, result, config, producer = map(
            table, ("ops.task", "ops.task_result", "ops.method_config", "ops.method")
        )
        query = (
            select(result)
            .select_from(task)
            .join(result, result.c.task_id == func.coalesce(task.c.reused_task_id, task.c.id))
            .join(config, task.c.method_config_id == config.c.id)
            .join(producer, producer.c.id == config.c.method_id)
            .where(
                task.c.run_id == self.run_id,
                task.c.unit_type == "source_view",
                task.c.unit_id == source_view_id,
                producer.c.name == method,
            )
        )
        if self.cut_id is not None:
            cut = table("ops.cut_task")
            query = query.join(cut, cut.c.origin_task_id == result.c.task_id).where(
                cut.c.cut_id == self.cut_id
            )
        return tuple(
            SourceCoverageReading(
                CoverageDraft(**item),
                row["task_id"],
                row["release_id"],
                position,
                0,
                len(source.text),
            )
            for row in self.conn.execute(query).mappings()
            for position, item in enumerate(row["body"].get("coverage", ()))
            if item["family"] == method
        )

    def source_coverage(self, rendition_id: int, method: str):
        """Read immutable source coverage through this run's effective task origins."""
        from corpus_structure.core.method import CoverageDraft, SourceCoverageReading

        task, result, config, producer = map(
            table, ("ops.task", "ops.task_result", "ops.method_config", "ops.method")
        )
        rendition = table("kb.rendition")
        query = (
            select(
                result.c.body,
                result.c.task_id,
                result.c.release_id,
                rendition.c.key,
                func.length(rendition.c.canonical_text).label("source_length"),
            )
            .select_from(task)
            .join(result, result.c.task_id == func.coalesce(task.c.reused_task_id, task.c.id))
            .join(config, task.c.method_config_id == config.c.id)
            .join(producer, config.c.method_id == producer.c.id)
            .join(rendition, rendition.c.id == task.c.unit_id)
            .where(
                task.c.run_id == self.run_id,
                task.c.unit_type == "rendition",
                task.c.unit_id == rendition_id,
                producer.c.name == method,
            )
            .order_by(result.c.task_id)
        )
        if self.cut_id is not None:
            cut = table("ops.cut_task")
            query = query.join(cut, cut.c.origin_task_id == result.c.task_id).where(
                cut.c.cut_id == self.cut_id
            )
        segment = table("kb.segment")
        extents = {
            row.segment_key: (row.start_offset, row.end_offset)
            for row in self.conn.execute(
                select(segment.c.segment_key, segment.c.start_offset, segment.c.end_offset).where(
                    segment.c.rendition_id == rendition_id
                )
            )
        }
        out = []
        for row in self.conn.execute(query).mappings():
            for position, item in enumerate(row["body"].get("coverage", ())):
                if item.get("family") != method:
                    continue
                bounds = (
                    (0, row["source_length"])
                    if item["scope"] == row["key"]
                    else extents.get(item["scope"], (None, None))
                )
                out.append(
                    SourceCoverageReading(
                        CoverageDraft(**item), row["task_id"], row["release_id"], position, *bounds
                    )
                )
        return tuple(out)

    def measurements(self, method: str, metric: str) -> Sequence[MeasurementView]:
        from corpus_structure.core.method import MeasurementView
        from corpus_structure.core.vocab import MeasurementScope

        t, c, m, v = (
            table("ops.task"),
            table("ops.method_config"),
            table("ops.method"),
            table("ops.measurement"),
        )
        q = (
            select(v)
            .select_from(t)
            .join(v, v.c.task_id == func.coalesce(t.c.reused_task_id, t.c.id))
            .join(c, t.c.method_config_id == c.c.id)
            .join(m, c.c.method_id == m.c.id)
            .where(t.c.run_id == self.run_id, m.c.name == method, v.c.metric == metric)
        )
        return [
            MeasurementView(
                row["id"],
                row["task_id"],
                row["metric"],
                MeasurementScope(row["scope_type"]),
                row["scope_id"],
                row["scope_key"],
                float(row["value"]) if row["value"] is not None else None,
                row["detail"],
            )
            for row in self.conn.execute(q).mappings()
        ]

    def guideline(self) -> str:
        r = table("ops.run")
        return self.conn.execute(select(r.c.guideline).where(r.c.id == self.run_id)).scalar_one()

    def artifact(self, artifact_hash: str) -> bytes:
        for artifact in self.prepared.artifacts:
            if artifact.digest == artifact_hash:
                return artifact.content
        raise LookupError("artifact does not belong to the run release")

    def connection(self) -> AbstractContextManager[Connection]:
        from contextlib import nullcontext

        return nullcontext(self.conn)


def run_view(
    conn: Connection, run_id: int, prepared: PreparedRelease, *, cut_id: int | None = None
) -> BoundRunView:
    from corpus_structure.core.vocab import RunKind

    r = table("ops.run")
    row = conn.execute(select(r).where(r.c.id == run_id)).mappings().one()
    binding = binding_of(conn, run_id)
    if binding.release_id != prepared.release_id:
        raise OperationConflict("reader release differs from run")
    return BoundRunView(
        run_id,
        RunKind(row["kind"]),
        row["phase"],
        None,
        binding,
        prepared,
        row["options"],
        BoundReader(conn, run_id, prepared, cut_id),
    )


def end_source_run(
    conn: Connection, run_id: int, *, failure: Mapping[str, JsonValue] | None = None
) -> int:
    import json

    return conn.execute(
        text("SELECT ops.end_source_run(:run,CAST(:failure AS jsonb))"),
        {"run": run_id, "failure": json.dumps(failure) if failure is not None else None},
    ).scalar_one()


def lock_input_snapshot(conn: Connection, run_id: int) -> None:
    """Fence packet input reads until this queue/serve transaction ends; no agent wait lock."""
    try:
        conn.execute(text("SELECT ops.lock_input_snapshot(:run)"), {"run": run_id})
    except Exception as exc:
        if getattr(getattr(exc, "orig", None), "sqlstate", None) == "P0004":
            raise OperationConflict("packet input snapshot changed") from exc
        raise


def hold_agent_result(
    conn: Connection,
    *,
    task_id: int,
    attempt: int,
    holder: str,
    packet_hash: str,
    clean: bool,
    result: Mapping[str, JsonValue],
    prepared: PreparedRelease | None = None,
) -> HoldDecision:
    """Lock one live submission; persist only its first well-typed uncertain result."""
    import json

    try:
        held = conn.execute(
            text(
                "SELECT ops.hold_agent_result(:task,:attempt,:holder,:packet,:clean,CAST("
                ":result AS jsonb))"
            ),
            {
                "task": task_id,
                "attempt": attempt,
                "holder": holder,
                "packet": packet_hash,
                "clean": clean,
                "result": json.dumps(dict(result)),
            },
        ).scalar_one()
        from .operation_results import validate_result_dimension, validate_task_result_dimension

        disposition = "held" if held else "proceed"
        if prepared is not None:
            validate_result_dimension(
                prepared, "hold_submission", "decision", disposition, field="disposition"
            )
        else:
            validate_task_result_dimension(
                conn, task_id, "hold_submission", "decision", disposition
            )
        return HoldDecision(
            task_id=task_id,
            attempt=attempt,
            packet_hash=packet_hash,
            disposition=disposition,
        )
    except Exception as exc:
        if getattr(getattr(exc, "orig", None), "sqlstate", None) == "P0004":
            raise OperationConflict("agent submission attempt lost or run sealed") from exc
        raise


@dataclass(frozen=True)
class ReleasedClaim:
    task_id: int
    attempt: int
    reason: str


def renew_claim(conn: Connection, *, task_id: int, attempt: int, holder: str) -> None:
    """Renew only the current attempt through the protected native ownership guard."""
    try:
        conn.execute(
            text("SELECT ops.renew_claim(:task,:attempt,:holder)"),
            dict(task=task_id, attempt=attempt, holder=holder),
        ).scalar_one()
    except Exception as exc:
        if getattr(getattr(exc, "orig", None), "sqlstate", None) == "P0004":
            raise OperationConflict("task ownership changed before renewal") from exc
        raise


def release_claim(
    conn: Connection, *, task_id: int, attempt: int, holder: str, reason: str
) -> ReleasedClaim:
    """Release the current agent attempt while retaining durable held submission progress."""
    if not reason:
        raise ValueError("claim release requires a reason")
    try:
        conn.execute(
            text("SELECT ops.release_claim(:task,:attempt,:holder,:reason)"),
            dict(task=task_id, attempt=attempt, holder=holder, reason=reason),
        ).scalar_one()
    except Exception as exc:
        if getattr(getattr(exc, "orig", None), "sqlstate", None) == "P0004":
            raise OperationConflict("task ownership changed before release") from exc
        raise
    return ReleasedClaim(task_id, attempt, reason)
