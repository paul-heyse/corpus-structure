"""Run-bound source operations over the trusted semantic physical model.

Database sequence IDs locate rows only. Reproducible source observations bind the immutable
release, method input and source item; task attempts and sequence IDs do not enter their keys.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, JsonValue
from sqlalchemy import Connection, cast, func, insert, literal, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert

from corpus_structure.core.method import (
    MeasurementView,
    Method,
    Reader,
    SourceObservationReference,
    SourceViewRef,
    UnitResult,
)
from corpus_structure.core.vocab import RunKind, TaskUnitType

from ._operation_calls import ReleasedClaim as ReleasedClaim
from ._operation_ids import (
    CutId,
    DocumentId,
    MethodConfigId,
    ProjectId,
    RunId,
    TaskAttempt,
    TaskId,
)
from .identity import canonical_bytes
from .metadata import table
from .operation_results import (
    ClaimedTask,
    CompletionResult,
    HoldDecision,
)
from .types import PreparedRelease

if TYPE_CHECKING:
    from .runtime_bindings import RuntimeBinding

_SOURCE_RESULT_MAX_BYTES = 64 * 1024**2


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
    prepared: PreparedRelease | None = None,
    runtime_binding: RuntimeBinding | None = None,
) -> RunId:
    from typing import cast

    from ._operation_calls import ProjectId, RealizationId, ReleaseId
    from ._operation_calls import create_run as invoke
    from .releases import open_release
    from .runtime_binding_store import persist_runtime_binding
    from .runtime_bindings import require_installed_runtime

    prepared = prepared or open_release(conn, binding.release_id)
    if prepared.release_id != binding.release_id:
        raise OperationConflict("run preparation belongs to another release")
    runtime_binding = require_installed_runtime(prepared, runtime_binding)
    runtime_id = persist_runtime_binding(conn, prepared, runtime_binding)

    try:
        return invoke(
            conn,
            project_id=ProjectId(project_id),
            release_id=ReleaseId(binding.release_id),
            runtime_id=runtime_id,
            realization_id=RealizationId(binding.input_realization_id),
            revision=binding.input_revision,
            dependencies=binding.dependencies,
            kind=kind,
            phase=phase,
            options=cast(JsonValue, dict(options)),
            guideline=guideline,
            code_commit=code_commit,
            projection_context=prepared,
        )
    except Exception as exc:
        if getattr(getattr(exc, "orig", None), "sqlstate", None) == "P0004":
            raise OperationConflict("input realization changed before run creation") from exc
        raise


def _require_run_runtime(
    conn: Connection, run_id: RunId, prepared: PreparedRelease | None = None
) -> PreparedRelease:
    """Authenticate one execution/claim boundary, independently of historical read access."""
    from .releases import open_release
    from .runtime_bindings import RuntimeBindingError, installed_runtime_id

    run = table("ops.run")
    selected = conn.execute(
        select(run.c.release_id, run.c.runtime_id).where(run.c.id == run_id)
    ).one()
    if prepared is None:
        prepared = open_release(conn, selected.release_id)
    if prepared.release_id != selected.release_id:
        raise RuntimeBindingError("run and prepared release differ")
    if selected.runtime_id is None or selected.runtime_id != installed_runtime_id(prepared):
        raise RuntimeBindingError("installed runtime differs from the archived execution pin")
    return prepared


def start_run(conn: Connection, run_id: RunId, *, prepared: PreparedRelease | None = None) -> int:
    """Start a source run through guarded DML; an exact running replay is harmless."""
    _require_run_runtime(conn, run_id, prepared)
    try:
        from ._operation_calls import start_source_run as invoke

        return invoke(conn, run_id=run_id)
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
    method: Method[Any] | OperationDescriptor,
    name: str,
    params: Mapping[str, Any],
    config_hash: str,
    *,
    prepared: PreparedRelease | None = None,
) -> MethodConfigId:
    from . import _operation_calls as calls
    from .contracts import require_bound_operation

    if prepared is None:
        raise OperationConflict("method configuration requires an explicit released binding")
    require_bound_operation(prepared, "configure_method")
    from .operation_results import validate_method_dimension

    validate_method_dimension(prepared, method.name, "family", method.family)
    validate_method_dimension(prepared, method.name, "tier", method.tier)
    validate_method_dimension(
        prepared,
        method.name,
        "confidence_source",
        method.confidence_source if method.confidence_source is not None else None,
    )
    m = table("ops.method")
    c = table("ops.method_config")
    request = calls.prepare_method_definition(
        name=method.name,
        version=method.version,
        unit_type=str(method.unit_type) if hasattr(method, "unit_type") else None,
        configuration_schema_digest=sha256(
            canonical_bytes(method.Config.model_json_schema())
        ).hexdigest()
        if hasattr(method, "Config")
        else None,
        family=method.family,
        tier=method.tier,
        confidence_source=method.confidence_source
        if method.confidence_source is not None
        else None,
        projection_context=prepared,
    )
    values = calls.values_method_definition_ops_method(request)
    expected = calls.expected_method_definition_ops_method(request)
    conn.execute(pg_insert(m).values(**values).on_conflict_do_nothing())
    declared = calls.collect_method_definition(
        conn.execute(
            select(*calls.projection_method_definition).where(
                m.c.name == request.name, m.c.version == request.version
            )
        )
    )
    actual = declared.decoded_json_fields(operation="configure_method")
    if any(
        actual[k] != value
        for k, value in expected.items()
        if not (k in {"unit_type", "configuration_schema_digest"} and actual[k] is None)
    ):
        raise OperationConflict("operation version denotes another method contract")
    configuration = calls.prepare_method_configuration(
        method_id=declared.id,
        name=name,
        params=dict(params),
        config_hash=config_hash,
        projection_context=prepared,
    )
    conn.execute(
        pg_insert(c)
        .values(**calls.values_method_configuration_ops_method_config(configuration))
        .on_conflict_do_nothing()
    )
    row = calls.collect_method_configuration(
        conn.execute(
            select(*calls.projection_method_configuration).where(
                c.c.method_id == configuration.method_id,
                c.c.config_hash == configuration.config_hash,
            )
        )
    )
    if row.decoded_json_fields(operation="configure_method")["params"] != configuration.params:
        raise OperationConflict("configuration hash denotes different parameters")
    return row.id


def create_task(
    conn: Connection,
    *,
    run_id: RunId,
    config_id: MethodConfigId,
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
) -> TaskId:
    r = table("ops.run")
    from ._operation_calls import lock_schedule_run

    run = lock_schedule_run(conn, run_id=run_id).decoded_json_fields(operation="schedule")
    if run["sealed"] or run["status"] not in {"created", "running"}:
        raise OperationConflict("run no longer accepts tasks")
    t = table("ops.task")
    old_run = r.alias("origin_run")
    config = table("ops.method_config")
    method = table("ops.method")
    twin = (
        None
        if fresh or skip_reason is not None
        else conn.execute(
            select(t.c.id)
            .join(old_run, t.c.run_id == old_run.c.id)
            .join(config, t.c.method_config_id == config.c.id)
            .join(method, config.c.method_id == method.c.id)
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
                old_run.c.runtime_id.is_not_distinct_from(run["runtime_id"]),
                old_run.c.input_realization_id == run["input_realization_id"],
                old_run.c.input_revision == run["input_revision"],
                func.ops.task_dependency_scope(
                    cast(func.convert_from(old_run.c.dependencies, "UTF8"), JSONB), method.c.name
                )
                == func.ops.task_dependency_scope(
                    cast(func.convert_from(literal(run["dependencies"]), "UTF8"), JSONB),
                    method.c.name,
                ),
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
    return TaskId(task_id)


def claim_tasks(
    conn: Connection,
    *,
    run_id: RunId,
    config_id: MethodConfigId,
    holder: str,
    limit: int = 1,
    agent: bool = False,
    prepared: PreparedRelease | None = None,
) -> tuple[ClaimedTask, ...]:
    if limit < 1:
        raise ValueError("positive claim limit required")
    if not isinstance(holder, str) or not holder:
        raise ValueError("nonempty claim holder required")
    from ._operation_calls import claim_tasks as invoke

    _require_run_runtime(conn, run_id, prepared)
    model = None
    if prepared is not None:
        from dataclasses import asdict

        from ._operation_calls import CLAIM_TASKS_CONTRACT_DIGEST
        from .contracts import bound_execution_model

        run = table("ops.run")
        release = conn.execute(select(run.c.release_id).where(run.c.id == run_id)).scalar_one()
        if release != prepared.release_id:
            raise ValueError("claim preparation differs from the run's bound release")
        if prepared.execution_model_id is not None:
            model = bound_execution_model(prepared)
            call = model.require_operation("claim").call
            if (
                call is None
                or sha256(canonical_bytes([asdict(call)])).hexdigest()
                != CLAIM_TASKS_CONTRACT_DIGEST
            ):
                raise ValueError("claim call correspondence differs from this generated adapter")
    try:
        return invoke(
            conn, run_id=run_id, config_id=config_id, holder=holder, limit=limit, agent=agent
        )
    except Exception as exc:
        if model is not None and prepared is not None:
            from .invariant_failures import InvariantViolation, classify_invariant_failure

            failure = classify_invariant_failure(
                model, "claim", exc, release_id=prepared.release_id
            )
            if failure is not None:
                raise InvariantViolation(failure) from exc
        raise


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
    task_id: TaskId,
    attempt: TaskAttempt,
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
    has_output = (
        bool(observations)
        or bool((envelope or {}).get("records"))
        or bool((envelope or {}).get("contributions"))
    )
    if (outcome == "done") != has_output:
        raise ValueError("terminal outcome contradicts source outputs")
    if (outcome == "failed") != bool(error):
        raise ValueError("failure requires explicit error")
    t = table("ops.task")
    task = conn.execute(select(t).where(t.c.id == task_id)).mappings().one()
    binding = binding_of(conn, task["run_id"])
    if prepared.release_id != binding.release_id:
        raise OperationConflict("wrong producer release")
    from .operation_results import validate_method_dimension

    method_name = conn.execute(
        select(table("ops.method").c.name)
        .join(
            table("ops.method_config"),
            table("ops.method_config").c.method_id == table("ops.method").c.id,
        )
        .where(table("ops.method_config").c.id == task["method_config_id"])
    ).scalar_one()
    rows = []
    for ordinal, raw in enumerate(observations):
        data = dict(raw)
        definition = data.pop("payload_definition")
        item = data.pop("item_key")
        payload = prepared.validate_python(definition, data.pop("payload")).model_dump(mode="json")
        if any(data.get(field) is not None for field in ("rendition_id", "segment_id", "span_id")):
            raise OperationConflict("source observations require current SourceView custody")
        if task["unit_type"] == "source_view":
            if data.get("source_view_id") not in (None, task["unit_id"]) or any(
                data.get(field) is not None for field in ("rendition_id", "segment_id", "span_id")
            ):
                raise OperationConflict("source-view observation differs from its task unit")
            data["source_view_id"] = task["unit_id"]
        supplied_key = data.pop("observation_key", None)
        if definition == "SourceObservation" and supplied_key != payload["observation_key"]:
            raise OperationConflict("source observation identity differs from bound report")
        validate_method_dimension(prepared, method_name, "observation.family", data["kind"])
        validate_method_dimension(
            prepared, method_name, "observation.outcome", data.get("outcome", "produced")
        )
        if definition == "SourceObservation":
            if payload["family"] != data["kind"] or (
                payload["outcome"] != data.get("outcome", "produced")
            ):
                raise OperationConflict("observation dimensions differ from its bound report")
            validate_method_dimension(
                prepared,
                method_name,
                "observation.confidence_source",
                payload.get("confidence_source"),
            )
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
    from typing import cast

    from ._operation_calls import TaskAttempt, TaskId
    from ._operation_calls import complete_task as invoke

    try:
        completion = invoke(
            conn,
            task_id=TaskId(task_id),
            attempt=TaskAttempt(attempt),
            holder=holder,
            rows=cast(JsonValue, rows),
            outcome=outcome,
            error=cast(JsonValue, dict(error) if error is not None else None),
            envelope=cast(JsonValue, dict(envelope) if envelope is not None else None),
        )
    except Exception as exc:
        if prepared.execution_model_id is not None:
            from .contracts import bound_execution_model
            from .invariant_failures import InvariantViolation, classify_invariant_failure

            failure = classify_invariant_failure(
                bound_execution_model(prepared), "complete", exc, release_id=prepared.release_id
            )
            if failure is not None:
                raise InvariantViolation(failure) from exc
        if getattr(getattr(exc, "orig", None), "sqlstate", None) in {"P0004", "55000"}:
            raise OperationConflict("task attempt lost or run sealed") from exc
        raise
    from .operation_results import validate_result_dimension

    validate_result_dimension(
        prepared, "complete", "protocol", completion.receipt.protocol, field="receipt.protocol"
    )
    validate_result_dimension(
        prepared, "complete", "transaction", completion.transaction, field="transaction"
    )
    return completion


def seal_cut(conn: Connection, run_id: RunId, name: str, *, final: bool = False) -> CutId:
    from ._operation_calls import capture_cut as invoke

    return invoke(conn, run_id=run_id, name=name, final=final)


def cut_observations(conn: Connection, cut_id: CutId) -> list[dict[str, Any]]:
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
) -> DocumentId:
    from . import _operation_calls as calls
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
    request = calls.prepare_document_registration(
        project_id=ProjectId(project_id),
        key=key,
        source_uri=source_uri,
        content_hash=content_hash,
        original_path=original_path,
        mime=mime,
        title=title,
        meta=dict(metadata or {}),
        projection_context=prepared,
    )
    values = calls.values_document_registration_kb_document(request)
    conn.execute(pg_insert(t).values(**values).on_conflict_do_nothing())
    row = calls.collect_document_registration(
        conn.execute(
            select(*calls.projection_document_registration).where(
                t.c.project_id == request.project_id, t.c.key == request.key
            )
        )
    )
    actual = row.decoded_json_fields(operation="register_document")
    if any(
        actual[k] != value
        for k, value in calls.expected_document_registration_kb_document(request).items()
    ):
        raise OperationConflict("source identity denotes another source descriptor")
    calls.retain_source_artifact(conn, document_id=row.id, original=original)
    return row.id


class SourceReadRefused(OperationConflict):
    """An owned source-read failure with an explicit modeled outcome."""

    def __init__(self, outcome: str, reason: str):
        self.outcome = outcome
        super().__init__(reason)


def _source_read_outcome(prepared: PreparedRelease | None, operation: str, outcome: str) -> None:
    from .operation_results import validate_result_dimension

    if prepared is None:
        raise ValueError("source reads require a composed execution binding")
    validate_result_dimension(prepared, operation, "outcome", outcome, field="outcome")


def read_original(
    conn: Connection,
    document_id: DocumentId,
    *,
    prepared: PreparedRelease | None = None,
    projection_context: PreparedRelease | None = None,
) -> bytes:
    """Read fixed physical custody; producer outcomes and consumer admission stay separate.

    The producer release supplies execution authority; a separate consumer context may
    additionally qualify the fixed projection call.
    """
    from pathlib import Path

    from . import _operation_calls as calls
    from .contracts import require_bound_operation

    if prepared is None:
        raise ValueError("source reads require a composed execution binding")
    require_bound_operation(prepared, "read_original")
    request = calls.prepare_original_descriptor(
        id=document_id, projection_context=projection_context
    )
    t = table("kb.document")
    row = calls.collect_original_descriptor(
        conn.execute(select(*calls.projection_original_descriptor).where(t.c.id == request.id))
    )
    if row is None:
        _source_read_outcome(prepared, "read_original", "missing")
        raise SourceReadRefused("missing", "retained original document is missing")
    artifact = table("kb.source_artifact")
    artifact_request = calls.prepare_original_artifact(
        artifact_digest=row.content_hash, projection_context=projection_context
    )
    retained = calls.collect_original_artifact(
        conn.execute(
            select(*calls.projection_original_artifact).where(
                artifact.c.artifact_digest == artifact_request.artifact_digest
            )
        )
    )
    if retained is not None:
        data = retained
        if sha256(data).hexdigest() != row.content_hash:
            _source_read_outcome(prepared, "read_original", "invalid")
            raise SourceReadRefused("invalid", "retained original artifact is corrupt")
        _source_read_outcome(prepared, "read_original", "source_ready")
        return data
    try:
        data = Path(row.original_path).read_bytes()
    except FileNotFoundError as exc:
        _source_read_outcome(prepared, "read_original", "missing")
        raise SourceReadRefused("missing", "retained original file is missing") from exc
    if sha256(data).hexdigest() != row.content_hash:
        _source_read_outcome(prepared, "read_original", "invalid")
        raise SourceReadRefused("invalid", "retained original content changed")
    _source_read_outcome(prepared, "read_original", "source_ready")
    return data


@dataclass(frozen=True)
class PreparedUnitCompletion:
    """Detached exact intent: large report preparation precedes the short owner fence."""

    prepared: PreparedRelease
    task_id: TaskId
    attempt: TaskAttempt
    holder: str
    run_id: RunId
    rows: tuple[Mapping[str, Any], ...]
    outcome: str
    error: Mapping[str, Any] | None
    envelope: Mapping[str, Any]
    source_views: tuple[Any, ...]

    def apply(self, conn: Connection) -> CompletionResult:
        from ._operation_calls import lock_complete_unit_run
        from .source_views import store_source_view

        lock_complete_unit_run(conn, run_id=self.run_id)
        tasks = table("ops.task")
        task = (
            conn.execute(select(tasks).where(tasks.c.id == self.task_id).with_for_update())
            .mappings()
            .one()
        )
        if task["attempt"] != self.attempt or task["claimed_by"] != self.holder:
            raise OperationConflict("recognizer attempt lost")
        if task["status"] == "running":
            for position, draft in enumerate(self.source_views):
                store_source_view(
                    conn,
                    run_id=self.run_id,
                    task_id=self.task_id,
                    attempt=self.attempt,
                    holder=self.holder,
                    draft=draft,
                    position=position,
                )
        return complete_task(
            conn,
            task_id=self.task_id,
            attempt=self.attempt,
            holder=self.holder,
            prepared=self.prepared,
            observations=self.rows,
            outcome=self.outcome,
            error=self.error,
            envelope=self.envelope,
        )


def prepare_unit_completion(
    conn: Connection,
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    prepared: PreparedRelease,
    result: UnitResult,
    method: Method[Any] | OperationDescriptor,
    configuration_hash: str,
    source: str,
    records: Sequence[Mapping[str, Any]] | None = None,
) -> PreparedUnitCompletion:
    """The actual recognizer terminal boundary: binding, source storage and one native fence."""
    from .contracts import require_bound_operation

    require_bound_operation(prepared, "complete_unit")
    from .observations import bind_result, source_python

    task_table = table("ops.task")
    task = conn.execute(select(task_table).where(task_table.c.id == task_id)).mappings().one()
    if task["attempt"] != attempt or task["claimed_by"] != holder:
        raise OperationConflict("recognizer attempt lost")
    record_coordinates = ()
    if records is not None:
        from .records import authenticated_coordinate_texts

        require_bound_operation(prepared, "bind_report")
        if (result.ref.unit_key, result.ref.unit_id) != (task["unit_key"], task["unit_id"]):
            raise OperationConflict("private record result differs from its exact task unit")
        record_coordinates = authenticated_coordinate_texts(
            conn, prepared, dict(task), source, records
        )
    contribution_coordinates = ()
    if result.contributions is not None:
        from .records import authenticated_contribution_coordinate_texts

        if (result.ref.unit_key, result.ref.unit_id) != (task["unit_key"], task["unit_id"]):
            raise OperationConflict("contribution result differs from its exact task unit")
        contribution_coordinates = authenticated_contribution_coordinate_texts(
            conn, prepared, dict(task), source, result.contributions
        )
    bound = bind_result(
        prepared,
        source=source,
        method=method.name,
        operation_version=method.version,
        configuration_hash=configuration_hash,
        input_hash=task["input_hash"],
        invocation_key=task["invocation_key"],
        result=result,
        method_confidence_source=method.confidence_source
        if method.confidence_source is not None
        else None,
        records=records,
        record_coordinate_texts=record_coordinates,
        contribution_coordinate_texts=contribution_coordinates,
    )
    # Native completion receives JSON, while complete_task admits each typed
    # observation through the Python boundary. Keep those representations separate.
    envelope = bound.model_dump(mode="json", exclude={"observations"})
    items = bound.model_dump(mode="python", include={"observations"})["observations"]
    rows = []
    for item in items:
        rows.append(
            dict(
                payload_definition="SourceObservation",
                item_key=item["item_key"],
                observation_key=item["observation_key"],
                payload=item,
                kind=item["family"],
                rendition_id=None,
                source_view_id=item.get("source_view_id"),
                segment_id=item.get("segment_id"),
                span_id=None,
                score=source_python(item["score"]) if item.get("score") is not None else None,
                outcome=item["outcome"],
            )
        )
    outcome = {"produced": "done", "empty": "empty", "failed": "failed"}[result.outcome.value]
    return PreparedUnitCompletion(
        prepared,
        task_id,
        attempt,
        holder,
        RunId(task["run_id"]),
        tuple(rows),
        outcome,
        {"message": result.error} if result.error else None,
        envelope,
        tuple(result.source_views),
    )


def complete_unit_result(
    conn: Connection,
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    prepared: PreparedRelease,
    result: UnitResult,
    method: Method[Any] | OperationDescriptor,
    configuration_hash: str,
    source: str,
    records: Sequence[Mapping[str, Any]] | None = None,
) -> CompletionResult:
    """Prepare and apply on the caller's transaction; source execution prepares before fencing."""
    return prepare_unit_completion(
        conn,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        prepared=prepared,
        result=result,
        method=method,
        configuration_hash=configuration_hash,
        source=source,
        records=records,
    ).apply(conn)


@dataclass(frozen=True)
class BoundRunView:
    run_id: int
    kind: RunKind
    phase: int
    reference_run_id: int | None
    binding: OperationBinding
    prepared: PreparedRelease
    options: Mapping[str, JsonValue]
    reader: Reader


@dataclass(frozen=True)
class SourceObservationView:
    id: int
    task_id: int
    kind: str
    rendition_id: int | None
    segment_id: int | None
    span_id: int | None
    payload: Mapping[str, JsonValue]
    payload_hash: str
    score: float | None
    outcome: str
    observation_key: str
    release_id: str
    input_refs: tuple[SourceObservationReference, ...] = ()
    source_view_id: int | None = None
    native_pointer: str | None = None
    projected_span: tuple[int, int] | None = None
    recognized_span: tuple[int, int] | None = None


def _retained_source_ref(reference):
    return dict(
        document_id=reference.document_id,
        native_task_id=reference.native_product.task_id,
        native_product_key=reference.native_product.product_key,
        native_content_digest=reference.native_product.content_digest,
        section_pointer=reference.section_pointer,
        membership=reference.membership,
        projection_digest=reference.projection_digest,
        recipe_digest=reference.recipe_digest,
        analysis_eligible=reference.analysis_eligible,
    )


def _retained_source_descriptor(view):
    return dict(
        **_retained_source_ref(view.ref),
        projection=dict(
            text=view.text,
            pieces=view.pieces,
            items=[item["self_ref"] for item in view.items],
            ancestors=[item.get("self_ref", item.get("pointer")) for item in view.ancestors],
            health=view.health,
        ),
    )


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
        read_budget: Any = None,
    ):
        self.conn, self.run_id, self.prepared, self.cut_id = conn, run_id, prepared, cut_id
        self._analysis_enabled = analysis
        self._read_budget = read_budget
        self.math_readings_batch = None
        self.source_tasks: dict[int, int] = {}

    @property
    def read_budget(self):
        return self._read_budget

    def pdf_contract(self):
        from .pdf_contracts import pdf_context_for_release

        return pdf_context_for_release(self.conn, self.prepared).boundary

    def source_record_report(self, task_id: int):
        from .records import read_private_record_report

        return read_private_record_report(self, task_id)

    def source_views(self):
        cached = getattr(self, "_native_view_refs", None)
        if cached is not None:
            return cached
        from .source_views import selected_source_views

        selected = tuple(
            v
            for v in selected_source_views(self.conn, self.run_id, read_budget=self._read_budget)
            if v.analysis_eligible
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

    def source_view_ref(self, source_view_id: int) -> SourceViewRef:
        """Authorize one selected immutable reference without hydrating its contents."""
        from .source_views import selected_source_views

        selected = selected_source_views(
            self.conn, self.run_id, read_budget=self._read_budget, source_view_id=source_view_id
        )
        if len(selected) != 1 or selected[0].id != source_view_id:
            raise OperationConflict("source view is outside bound run")
        return selected[0]

    def source_formula_metadata(
        self, source_view_id: int, pointer: str
    ) -> tuple[SourceViewRef, dict[str, str]]:
        """Read the selected formula's reference and scoped recognition health."""
        from .source_views import source_formula_metadata

        reference = self.source_view_ref(source_view_id)
        return reference, source_formula_metadata(
            self.conn, reference, pointer, read_budget=self._read_budget
        )

    def source_view(self, source_view_id: int):
        from .source_views import load_source_view

        self.source_view_ref(source_view_id)
        cache = getattr(self, "_native_views", None)
        if cache is None:
            cache = {}
            self._native_views = cache
        if source_view_id not in cache:
            cache[source_view_id] = load_source_view(
                self.conn,
                source_view_id,
                analysis=self._analysis_enabled,
                read_budget=self._read_budget,
            )
        return cache[source_view_id]

    def ancestor_source_views(self, source_view_id: int):
        from .source_views import selected_source_views

        source = self.source_view(source_view_id)
        ancestors = {a["self_ref"] for a in source.ancestors}
        selected = selected_source_views(self.conn, self.run_id, read_budget=self._read_budget)
        return tuple(
            v
            for v in selected
            if v.native_product == source.ref.native_product and v.section_pointer in ancestors
        )

    def context_sources(self, source_view_id, request, *, limit, read_budget):
        from .source_views import read_context_sources

        # The primary view has already been read by the invoking consumer. The
        # shared budget covers all new candidate metadata and owned related bodies.
        source = self.source_view(source_view_id)
        return read_context_sources(
            self.conn,
            self.run_id,
            source,
            request,
            limit=limit,
            read_budget=self._read_budget or read_budget,
        )

    def cached_contextual_vectors(self, *, profile_id, targets):
        from .contextual_storage import cached_target_vectors

        return cached_target_vectors(
            self.conn,
            run_id=self.run_id,
            profile_id=profile_id,
            targets=targets,
            read_budget=self._read_budget,
        )

    def contextual_candidates(
        self,
        *,
        occurrence_id,
        query,
        inventory,
        target_vectors,
        lexical_query,
        dimension,
        budget,
        channel_budget,
    ):
        from .contextual_retrieval import retrieve_candidates
        from .contextual_storage import transient_vector_relation

        return retrieve_candidates(
            self.conn,
            occurrence_id=occurrence_id,
            query=query,
            inventory=inventory,
            relation=transient_vector_relation(inventory, target_vectors),
            lexical_query=lexical_query,
            dimension=dimension,
            budget=budget,
            channel_budget=channel_budget,
        )

    def source_context_membership(self, source_view_id):
        from .source_views import context_membership_digest

        return context_membership_digest(
            self.conn,
            self.run_id,
            self.source_view(source_view_id),
            read_budget=self._read_budget,
        )

    def source_result(self, source_view_id, method):
        from .observations import source_python
        from .pdf_record_reader import PublishedReadBudget

        source = self.source_view(source_view_id)
        task, result, config, producer = map(
            table, ("ops.task", "ops.task_result", "ops.method_config", "ops.method")
        )
        query = (
            select(
                result.c.body,
                result.c.release_id,
                task.c.input_hash,
                task.c.unit_key,
                config.c.config_hash,
            )
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
        budget = self._read_budget or PublishedReadBudget(16, _SOURCE_RESULT_MAX_BYTES)
        budget.preflight(self.conn, query)
        rows = tuple(self.conn.execute(query).mappings())
        if not rows:
            return None
        if len(rows) != 1:
            raise OperationConflict("upstream source result is ambiguous")
        row = rows[0]
        body = row["body"]
        budget.value(body)
        if (
            row["release_id"] != self.prepared.release_id
            or body.get("release_id") != self.prepared.release_id
            or body.get("source") != source.ref.key
            or body.get("unit_key") != row["unit_key"]
            or body.get("method") != method
            or body.get("configuration_hash") != row["config_hash"]
            or body.get("input_hash") != row["input_hash"]
        ):
            raise OperationConflict("upstream source result differs from its run/task binding")
        # Return detached decoded columns; the enclosing stored envelope remains
        # the one persistence and source-product custody owner.
        return dict(body, parse_detail=source_python(body["parse_detail"]))

    def retained_source_result(self, source_view_id, task_id, method):
        """Read a named immutable producer result, never implicitly search older runs.

        Both sides are independently selected and source-authenticated. The only
        admitted relocation is a bijective logical alias over unchanged physical
        placement, product and complete projection; old task/frame bytes stay intact.
        """
        from corpus_structure.core.method import RetainedSourceResult

        from .observations import source_python
        from .pdf_record_reader import PublishedReadBudget
        from .proposals import native_source_frame
        from .releases import open_release
        from .source_contexts import NativeSourcePin
        from .source_views import selected_source_views

        if method != "extract.m1_candidates" or type(task_id) is not int or task_id < 1:
            raise OperationConflict("historical source port requires an explicit M1 producer task")
        selected_ref = self.source_view_ref(source_view_id)
        tasks, results, configs, methods, runs = map(
            table, ("ops.task", "ops.task_result", "ops.method_config", "ops.method", "ops.run")
        )
        requested = (
            self.conn.execute(
                select(tasks.c.id, tasks.c.reused_task_id, tasks.c.run_id).where(
                    tasks.c.id == task_id
                )
            )
            .mappings()
            .one_or_none()
        )
        if requested is None:
            raise OperationConflict("historical producer task is missing")
        origin_id = requested["reused_task_id"] or task_id
        metadata_query = (
            select(
                tasks.c.id,
                tasks.c.run_id,
                tasks.c.release_id,
                tasks.c.unit_type,
                tasks.c.unit_id,
                tasks.c.unit_key,
                tasks.c.input_hash,
                configs.c.config_hash,
                methods.c.name.label("method_name"),
                runs.c.project_id.label("origin_project"),
            )
            .join(results, results.c.task_id == tasks.c.id)
            .join(configs, configs.c.id == tasks.c.method_config_id)
            .join(methods, methods.c.id == configs.c.method_id)
            .join(runs, runs.c.id == tasks.c.run_id)
            .where(tasks.c.id == origin_id)
        )
        row = self.conn.execute(metadata_query).mappings().one_or_none()
        if row is None:
            raise OperationConflict("historical producer has no sealed result")
        current_project = self.conn.execute(
            select(runs.c.project_id).where(runs.c.id == self.run_id)
        ).scalar_one()
        requested_project = self.conn.execute(
            select(runs.c.project_id).where(runs.c.id == requested["run_id"])
        ).scalar_one()
        if requested_project != current_project:
            raise OperationConflict("historical task selection belongs to another project")
        if row["origin_project"] != current_project or row["method_name"] != method:
            raise OperationConflict("historical producer belongs to another project or method")
        if row["unit_type"] != "source_view" or row["unit_id"] is None:
            raise OperationConflict("historical producer does not name a source view")
        original = BoundReader(
            self.conn,
            row["run_id"],
            open_release(self.conn, row["release_id"]),
            analysis=False,
            read_budget=self._read_budget,
        )
        original_ref = original.source_view_ref(row["unit_id"])
        if _retained_source_ref(original_ref) != _retained_source_ref(selected_ref):
            raise OperationConflict(
                "historical source has no unique current physical correspondence"
            )
        view = original.source_view(row["unit_id"])
        selected = self.source_view(source_view_id)
        if _retained_source_descriptor(view) != _retained_source_descriptor(selected):
            raise OperationConflict("historical source projection or native placement changed")
        query = (
            select(results.c.body, configs.c.params.label("producer_configuration"))
            .select_from(tasks)
            .join(results, results.c.task_id == tasks.c.id)
            .join(configs, configs.c.id == tasks.c.method_config_id)
            .where(tasks.c.id == origin_id)
        )
        budget = self._read_budget or PublishedReadBudget(16, _SOURCE_RESULT_MAX_BYTES)
        budget.preflight(self.conn, query)
        payload = self.conn.execute(query).mappings().one_or_none()
        if payload is None:
            raise OperationConflict("historical producer has no sealed result")
        body = payload["body"]
        budget.value(body)
        if (
            body.get("release_id") != row["release_id"]
            or body.get("method") != method
            or body.get("input_hash") != row["input_hash"]
            or body.get("configuration_hash") != row["config_hash"]
            or body.get("unit_key") != row["unit_key"]
        ):
            raise OperationConflict("historical producer body differs from its sealed task binding")
        detail = source_python(body["parse_detail"])
        if body.get("source") != view.ref.key or detail.get("source_pin") != asdict(
            NativeSourcePin.from_source(native_source_frame(view, ()))
        ):
            raise OperationConflict("historical producer source frame differs from selected source")
        old_ids = {view.ref.id}
        for context in detail.get("contexts", ()):
            old_ids.update(identity for identity, _, _ in context.get("relationships", ()))
        old_views = tuple(original.source_view(identity) for identity in sorted(old_ids))
        candidates = selected_source_views(self.conn, self.run_id, read_budget=self._read_budget)
        bindings, used = [], set()
        for old in old_views:
            descriptor = _retained_source_descriptor(old)
            matching = [
                candidate
                for candidate in candidates
                if _retained_source_ref(candidate) == _retained_source_ref(old.ref)
            ]
            if old.ref.id == view.ref.id:
                matching = [candidate for candidate in matching if candidate.id == selected.ref.id]
            if len(matching) != 1 or matching[0].id in used:
                raise OperationConflict(
                    "historical source has no unique current physical correspondence"
                )
            current = self.source_view(matching[0].id)
            if _retained_source_descriptor(current) != descriptor:
                raise OperationConflict("historical source projection or native placement changed")
            used.add(current.ref.id)
            bindings.append(
                dict(
                    original_source_view_id=old.ref.id,
                    current_source_view_id=current.ref.id,
                    original_source=old.ref.key,
                    current_source=current.ref.key,
                    physical_digest=sha256(canonical_bytes(descriptor)).hexdigest(),
                )
            )
        return RetainedSourceResult(
            selected_task_id=task_id,
            task_id=origin_id,
            run_id=row["run_id"],
            release_id=row["release_id"],
            body_digest=sha256(canonical_bytes(body)).hexdigest(),
            prepared=original.prepared,
            configuration=payload["producer_configuration"],
            result=dict(body, parse_detail=detail),
            source_views=old_views,
            source_bindings=tuple(bindings),
        )

    def _native_product_input(self, reference):
        """Selected/input pins or this running task's exact published output custody."""
        from .contracts import require_bound_operation
        from .pdf_contracts import pdf_context_for_task
        from .pdf_record_reader import PublishedSchemaUnavailable, published_record_reader
        from .pdf_storage import (
            NativeDocumentUnavailable,
            _record_product_identity,
        )

        require_bound_operation(self.prepared, "read_pdf_product")
        context = pdf_context_for_task(self.conn, reference.task_id)
        published = published_record_reader(self.conn, reference, projection_context=self.prepared)
        if published is not None:
            identity = _record_product_identity(
                self.conn,
                reference.task_id,
                reference.product_key,
                reference.content_digest,
                published,
            )
            try:
                published._native_schema_mapping()
            except PublishedSchemaUnavailable as error:
                raise NativeDocumentUnavailable(str(error)) from error
            # PreparedPdfProduct's contract is the producer payload schema, not
            # the sealed record projection receipt. Keep their meanings distinct.
            row = dict(
                payload=None,
                contract_digest=context.contract_digest,
                schema_digest=published.revision["schema_digest"],
                recipe_digest=published.revision["recipe_digest"],
                product_kind=identity["kind"],
                original_digest=published.revision["source_digest"],
            )
        else:
            raise NativeDocumentUnavailable("current native input requires a published record")
        from .source_views import selected_source_views

        # Custody is bound to selected pins or a claimed input, before analysis-unit filtering.
        permitted = any(
            view.native_product == reference
            for view in selected_source_views(self.conn, self.run_id)
        )
        if self.source_tasks:
            task, config, run, document, source_build = (
                table("ops.task"),
                table("ops.method_config"),
                table("ops.run"),
                table("kb.document"),
                table("ops.source_build"),
            )
            declared = self.conn.execute(
                select(
                    config.c.params,
                    document.c.content_hash,
                    document.c.project_id,
                    task.c.id.label("task_id"),
                    document.c.id.label("document_id"),
                    source_build.c.artifact_digest.label("bound_original_digest"),
                )
                .join(task, task.c.method_config_id == config.c.id)
                .join(document, document.c.id == task.c.unit_id)
                .outerjoin(source_build, source_build.c.task_id == task.c.id)
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
            # A method may publish an organized/native product before selecting its
            # source views. It cannot declare this future output in its input config.
            # Only the same bound running document task gets that route. Immutable
            # product identity is attempt-independent; live claim/write fencing stays
            # with the method owner, not an invented producing-attempt read contract.
            permitted = permitted or any(
                item.get("task_id") == reference.task_id
                and self.source_tasks.get(item["document_id"]) == reference.task_id
                and item.get("bound_original_digest") == row["original_digest"]
                and item["content_hash"] == row["original_digest"]
                and item["project_id"] == project == producer_project
                for item in claims
            )
        if not permitted:
            raise OperationConflict(
                "whole-native read requires a selected source view or exact claimed "
                "method input/output pin"
            )
        if row["contract_digest"] != context.contract_digest:
            raise OperationConflict("native product archived contract differs")
        context.execution.require_operation("read_pdf_product")
        return row, context, published

    def native_document(self, reference, *, include_candidate_pages: bool = True):
        from .pdf_contracts import PreparedPdfProduct

        row, _, published = self._native_product_input(reference)
        artifact = table("kb.source_artifact")
        contents = dict(
            self.conn.execute(
                select(artifact.c.artifact_digest, artifact.c.content).where(
                    artifact.c.artifact_digest.in_(
                        [row["original_digest"], row["schema_digest"], row["recipe_digest"]]
                    )
                )
            ).all()
        )
        if row["payload"] is None:
            if published is None:
                raise OperationConflict("native product has no readable published record binding")
            values = published.native_product_values(
                include_candidate_pages=include_candidate_pages
            )
            return PreparedPdfProduct(
                canonical_bytes(values),
                bytes(contents[row["original_digest"]]),
                bytes(contents[row["schema_digest"]]),
                bytes(contents[row["recipe_digest"]]),
                row["contract_digest"],
            )
        raise OperationConflict("current native input requires a published record")

    def native_section_drafts(
        self, reference, *, document_id, selections, membership, scope, consumer_release
    ):
        from corpus_structure.ingest.pdf_section_views import published_section_drafts

        _, _, reader = self._native_product_input(reference)
        if consumer_release != self.prepared.release_id:
            raise OperationConflict("section projection consumer release differs from its reader")
        if reader is None:
            raise OperationConflict(
                "current source preparation requires a record-backed publication"
            )
        return published_section_drafts(
            reader,
            document_id=document_id,
            selections=selections,
            membership=membership,
            scope=scope,
            consumer_release=consumer_release,
        )

    def capture_pdf_candidates(self, reference, directory):
        """Detach selected-product IPC custody before releasing the database borrower."""
        from dataclasses import replace
        from pathlib import Path

        from corpus_structure.ingest.pdf_candidate_source import ReplayCandidatePageSource
        from corpus_structure.ingest.pdf_streaming import _atomic_bytes

        from .pdf_payloads import prepare_payload_family

        _, context, reader = self._native_product_input(reference)
        if reader is None:
            raise OperationConflict("selected product has no released Arrow candidate realization")
        family = prepare_payload_family(context)
        root = Path(directory)
        root.mkdir(parents=True, exist_ok=False)
        replays = {}
        for payload in reader.iter_candidate_payloads(context=context):
            if payload.page_no in replays:
                raise ValueError("duplicate published candidate page")
            replay = _atomic_bytes(
                root / f"candidate-{payload.page_no:06}.arrow",
                payload.content,
                "candidate_payload",
            )
            replays[payload.page_no] = replace(
                replay,
                rows=1,
                page_no=payload.page_no,
                schema_digest=payload.schema_digest,
                logical_digest=payload.logical_digest,
            )
        return ReplayCandidatePageSource(replays, family)

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
        return read_original(self.conn, DocumentId(permitted), prepared=self.prepared)

    def bind_source_tasks(self, tasks: Mapping[int, int]) -> None:
        """Bind one claimed batch; task identity never comes from a fabricated placeholder."""
        if any(document < 1 or task < 1 for document, task in tasks.items()):
            raise ValueError("source task binding requires real document/task identities")
        self.source_tasks = dict(tasks)

    def source_observations(self, source_view_id: int, method: str, kind: str):
        self.source_view(source_view_id)
        return self._observations(source_view_id, method, kind)

    def source_observations_for_ref(self, reference: SourceViewRef, method: str, kind: str):
        """Read observations under an exact selected reference, without view hydration."""
        if self.source_view_ref(reference.id) != reference:
            raise OperationConflict("source observation reference differs from bound run")
        return self._observations(reference.id, method, kind)

    def _observations(self, source_id: int, method: str, kind: str):
        from corpus_structure.core.method import payload_hash

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
                o.c.source_view_id == source_id,
                m.c.name == method,
                o.c.kind == kind,
            )
            .order_by(o.c.ordinal)
        )
        if self.cut_id is not None:
            cut = table("ops.cut_task")
            q = q.join(cut, cut.c.origin_task_id == o.c.task_id).where(cut.c.cut_id == self.cut_id)
        if self._read_budget is not None:
            self._read_budget.preflight(self.conn, q)
        out = []
        for row in self.conn.execute(q).mappings():
            if self._read_budget is not None:
                self._read_budget.value(row["payload"])
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
                    row["kind"],
                    row["rendition_id"],
                    row["segment_id"],
                    row["span_id"],
                    payload,
                    payload_hash(payload),
                    float(row["score"]) if row["score"] is not None else None,
                    row["outcome"],
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

    def documents(self, originals):
        from corpus_structure.core.method import UnitRef
        from corpus_structure.core.vocab import TaskUnitType

        documents, runs = table("kb.document"), table("ops.run")
        options = self.conn.execute(
            select(runs.c.options).where(runs.c.id == self.run_id)
        ).scalar_one()
        keys = (options.get("corpus") or {}).get("documents", [])
        rows = self.conn.execute(
            select(documents.c.id, documents.c.key)
            .join(runs, runs.c.project_id == documents.c.project_id)
            .where(
                runs.c.id == self.run_id,
                documents.c.key.in_(keys),
                documents.c.source_uri.in_(originals),
            )
            .order_by(documents.c.key)
        ).all()
        return tuple(UnitRef(TaskUnitType.DOCUMENT, row.id, row.key) for row in rows)

    def source_view_documents(self):
        from corpus_structure.core.method import UnitRef
        from corpus_structure.core.vocab import TaskUnitType

        ids = {view.document_id for view in self.source_views()}
        documents, runs = table("kb.document"), table("ops.run")
        rows = self.conn.execute(
            select(documents.c.id, documents.c.key)
            .join(runs, runs.c.project_id == documents.c.project_id)
            .where(runs.c.id == self.run_id, documents.c.id.in_(ids))
            .order_by(documents.c.id)
        ).all()
        return tuple(UnitRef(TaskUnitType.DOCUMENT, row.id, row.key) for row in rows)


def run_view(
    conn: Connection,
    run_id: int,
    prepared: PreparedRelease,
    *,
    cut_id: int | None = None,
    read_budget=None,
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
        BoundReader(conn, run_id, prepared, cut_id, read_budget=read_budget),
    )


def end_source_run(
    conn: Connection,
    run_id: RunId,
    *,
    failure: Mapping[str, JsonValue] | None = None,
    prepared: PreparedRelease | None = None,
) -> int:
    from ._operation_calls import end_source_run as invoke
    from .releases import open_release

    run = table("ops.run")
    release = conn.execute(select(run.c.release_id).where(run.c.id == run_id)).scalar_one()
    if prepared is None:
        prepared = open_release(conn, release)
    elif prepared.release_id != release:
        raise ValueError("end-run preparation differs from the run's bound release")
    return invoke(
        conn,
        run_id=run_id,
        failure=dict(failure) if failure is not None else None,
        projection_context=prepared,
    )


def lock_input_snapshot(conn: Connection, run_id: int) -> None:
    """Fence packet input reads until this queue/serve transaction ends; no agent wait lock."""
    try:
        from ._operation_calls import lock_input_snapshot as invoke

        invoke(conn, run_id=RunId(run_id))
    except Exception as exc:
        if getattr(getattr(exc, "orig", None), "sqlstate", None) == "P0004":
            raise OperationConflict("packet input snapshot changed") from exc
        raise


def hold_agent_result(
    conn: Connection,
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    packet_hash: str,
    clean: bool,
    result: Mapping[str, JsonValue],
    prepared: PreparedRelease | None = None,
) -> HoldDecision:
    """Lock one live submission; persist only its first well-typed uncertain result."""
    from ._operation_calls import TaskAttempt, TaskId
    from ._operation_calls import hold_agent_result as invoke

    try:
        held = invoke(
            conn,
            task_id=TaskId(task_id),
            attempt=TaskAttempt(attempt),
            holder=holder,
            packet_hash=packet_hash,
            clean=clean,
            result=dict(result),
        )
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


def renew_claim(conn: Connection, *, task_id: TaskId, attempt: TaskAttempt, holder: str) -> None:
    """Renew only the current attempt through the protected native ownership guard."""
    try:
        from ._operation_calls import TaskAttempt, TaskId
        from ._operation_calls import renew_claim as invoke

        invoke(conn, task_id=TaskId(task_id), attempt=TaskAttempt(attempt), holder=holder)
    except Exception as exc:
        if getattr(getattr(exc, "orig", None), "sqlstate", None) == "P0004":
            raise OperationConflict("task ownership changed before renewal") from exc
        raise


def release_claim(
    conn: Connection, *, task_id: TaskId, attempt: TaskAttempt, holder: str, reason: str
) -> ReleasedClaim:
    """Release the current agent attempt while retaining durable held submission progress."""
    if not reason:
        raise ValueError("claim release requires a reason")
    try:
        from ._operation_calls import TaskAttempt, TaskId
        from ._operation_calls import release_claim as invoke

        released = invoke(
            conn,
            task_id=TaskId(task_id),
            attempt=TaskAttempt(attempt),
            holder=holder,
            reason=reason,
        )
    except Exception as exc:
        if getattr(getattr(exc, "orig", None), "sqlstate", None) == "P0004":
            raise OperationConflict("task ownership changed before release") from exc
        raise
    return released
