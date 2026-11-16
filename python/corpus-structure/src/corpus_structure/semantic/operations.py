"""Run-bound source operations over the trusted semantic physical model.

Database sequence IDs locate rows only. Reproducible source observations bind the immutable
release, method input and source item; task attempts and sequence IDs do not enter their keys.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, JsonValue
from sqlalchemy import Connection, cast, func, insert, literal, select, text
from sqlalchemy.dialects.postgresql import JSONB, JSONPATH
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql import ColumnElement

from corpus_structure.core.method import (
    MeasurementView,
    Method,
    SourceViewRef,
    UnitResult,
)
from corpus_structure.core.vocab import TaskUnitType

from ._operation_ids import (
    CutId,
    DocumentId,
    MethodConfigId,
    RunId,
    TaskAttempt,
    TaskId,
)
from .identity import canonical_bytes
from .metadata import table
from .operation_results import (
    ClaimedTask,
    CompletionResult,
)
from .refusals import OperationConflict, SourceReadRefused
from .types import PreparedRelease

if TYPE_CHECKING:
    from .data_operation_runtime import RuntimeBinding

_SOURCE_RESULT_MAX_BYTES = 64 * 1024**2


@dataclass(frozen=True)
class BoundSourceProducer:
    task_id: TaskId
    origin_task_id: TaskId


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

    from ._operation_calls import ProjectId, RealizationId, ReleaseId, RuntimeId
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
            runtime_id=RuntimeId(runtime_id),
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
    from .data_operation_runtime import RuntimeBindingError
    from .releases import open_release
    from .runtime_bindings import installed_runtime_id

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
                model.invariants,
                "claim",
                exc,
                model_id=model.model_id,
                release_id=prepared.release_id,
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
        or bool((envelope or {}).get("structural_product"))
    )
    if (outcome == "done") != has_output:
        raise ValueError("terminal outcome contradicts source outputs")
    if (outcome == "failed") != bool(error):
        raise ValueError("failure requires explicit error")
    t = table("ops.task")
    task = (
        conn.execute(
            select(
                t.c.run_id,
                t.c.method_config_id,
                t.c.unit_type,
                t.c.unit_id,
                t.c.input_hash,
                t.c.invocation_key,
            ).where(t.c.id == task_id)
        )
        .mappings()
        .one()
    )
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

            model = bound_execution_model(prepared)
            model.require_operation("complete")
            failure = classify_invariant_failure(
                model.invariants,
                "complete",
                exc,
                model_id=model.model_id,
                release_id=prepared.release_id,
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
    characterization_layer: Any = None
    characterization_view: Any = None

    def apply(self, conn: Connection) -> CompletionResult:
        from ._operation_calls import lock_complete_unit_run
        from .source_views import store_source_view

        if self.characterization_layer is not None or self.characterization_view is not None:
            from .characterization_store import _publish

            wire = _publish(
                conn,
                task_id=self.task_id,
                attempt=self.attempt,
                holder=self.holder,
                layer=self.characterization_layer,
                view=self.characterization_view,
                cost=self.envelope.get("cost"),
            )
            return CompletionResult.model_validate_json(
                canonical_bytes({key: wire[key] for key in ("transaction", "receipt")})
            )
        lock_complete_unit_run(conn, run_id=self.run_id)
        tasks = table("ops.task")
        task = (
            conn.execute(
                select(tasks.c.attempt, tasks.c.claimed_by, tasks.c.status)
                .where(tasks.c.id == self.task_id)
                .with_for_update()
            )
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
    from .observations import bind_result, source_python, source_value

    task_table = table("ops.task")
    task = (
        conn.execute(
            select(
                task_table.c.attempt,
                task_table.c.claimed_by,
                task_table.c.unit_type,
                task_table.c.unit_key,
                task_table.c.unit_id,
                task_table.c.run_id,
                task_table.c.input_hash,
                task_table.c.invocation_key,
            ).where(task_table.c.id == task_id)
        )
        .mappings()
        .one()
    )
    if task["attempt"] != attempt or task["claimed_by"] != holder:
        raise OperationConflict("recognizer attempt lost")
    if result.characterization_layer is not None or result.characterization_view is not None:
        from .characterization import validate_layer, validate_view
        from .characterization_store import read_layer

        if (result.ref.unit_key, result.ref.unit_id) != (task["unit_key"], task["unit_id"]):
            raise OperationConflict("characterization differs from exact producing task unit")
        layer = result.characterization_layer
        view = result.characterization_view
        from .product_reference import ProductReference

        layers = {}
        releases = {prepared.release_id: prepared}
        from .releases import open_release

        if layer is None and view is not None:
            from .characterization import validate_published_view
            from .characterization_store import read_layer_manifest

            manifests = {
                ProductReference(**value): read_layer_manifest(
                    conn, ProductReference(**value), run_id=task["run_id"]
                )
                for value in view.payload["layers"]
            }
            view = validate_published_view(prepared, view.payload, manifests)
        else:
            producing_layer = layer.reference(task_id) if layer is not None else None
            pending = [
                ProductReference(**pin)
                for report in (layer, view)
                if report is not None
                for pin in report.payload.get("dependencies" if report is layer else "layers", ())
                if ProductReference(**pin) != producing_layer
            ]
            while pending:
                reference = pending.pop()
                if reference in layers:
                    continue
                retained = read_layer(conn, reference, run_id=task["run_id"])
                layers[reference] = retained
                release_id = retained.payload["release_id"]
                if release_id not in releases:
                    releases[release_id] = open_release(conn, release_id)
                pending.extend(
                    ProductReference(**pin) for pin in retained.payload.get("dependencies", ())
                )
            if layer is not None:
                layer = validate_layer(
                    prepared, layer.payload, dependencies=layers, releases=releases
                )
                layers[layer.reference(task_id)] = layer
            if view is not None:
                view = validate_view(prepared, view.payload, layers, releases=releases)
        return PreparedUnitCompletion(
            prepared,
            task_id,
            attempt,
            holder,
            RunId(task["run_id"]),
            (),
            "done",
            None,
            {"cost": source_value(result.cost.model_dump(mode="json"))}
            if result.cost is not None
            else {},
            (),
            layer,
            view,
        )
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
        cpu_execution=None,
    ):
        self.cpu_execution = cpu_execution
        self.provider_execution: Any = None
        self.conn, self.run_id, self.prepared, self.cut_id = conn, run_id, prepared, cut_id
        self._analysis_enabled = analysis
        self._read_budget = read_budget
        self.source_tasks: dict[int, int] = {}
        self.source_producers: Mapping[tuple[int, str], BoundSourceProducer] = {}
        self.characterization_selection: tuple[Any, ...] = ()

    @property
    def read_budget(self):
        return self._read_budget

    def characterization_release(self, release_id):
        from .releases import open_release

        return open_release(self.conn, release_id)

    def characterization_layers(self, references):
        from .characterization_store import read_layer

        return {
            reference: read_layer(self.conn, reference, run_id=self.run_id)
            for reference in references
        }

    def characterization_manifests(self, references):
        from .characterization_store import read_layer_manifest

        return {
            reference: read_layer_manifest(self.conn, reference, run_id=self.run_id)
            for reference in references
        }

    def primary_characterization(self, source_view_id, *, families):
        from .characterization import select_primary_layers
        from .characterization_store import read_primary_layers

        return select_primary_layers(
            read_primary_layers(
                self.conn, self.run_id, source_view_id, self.characterization_selection
            ),
            self.source_view(source_view_id),
            families=families,
        )

    def characterization_view(self, reference):
        from .characterization_store import read_view

        return read_view(self.conn, reference, run_id=self.run_id)

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
                analysis_context=self.prepared,
                read_budget=self._read_budget,
            )
        return cache[source_view_id]

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
            analysis_context=self.prepared,
        )

    def retained_definition_component(self, reference):
        """Read original component and source manifest through their native custody owner."""
        import json

        return self.conn.execute(
            text("SELECT ops.resolve_retained_component(CAST(:reference AS jsonb))"),
            {"reference": json.dumps(reference.model_dump(mode="json"))},
        ).scalar_one()

    def resolve_definition_component(self, reference):
        """Resolve original retained component content for a selected applicability edge."""
        import json

        result = self.conn.execute(
            text("SELECT ops.resolve_retained_component(CAST(:reference AS jsonb))"),
            {"reference": json.dumps(reference.model_dump(mode="json"))},
        ).scalar_one()
        return result["component"]

    def retained_source_contribution(self, reference):
        """Resolve immutable selected producer output and all endpoint source evidence."""
        import json

        from corpus_structure.methods.pm2_products import (
            PARSER_PROVIDER,
            validate_parser_input,
            validate_parser_members,
        )

        from .contributions import contribution_payload_contracts
        from .releases import load_release
        from .retained_contributions import RetainedContributionRef

        ref = RetainedContributionRef.model_validate(reference)
        retained = self.conn.execute(
            text("SELECT ops.resolve_retained_source_contribution(CAST(:reference AS jsonb))"),
            {"reference": json.dumps(ref.model_dump(mode="json"))},
        ).scalar_one()
        parser_rows = [
            row for row in retained["contributions"] if row["semantic_type"] in PARSER_PROVIDER
        ]
        if parser_rows:
            prepared = (
                self.prepared
                if ref.release_id == self.prepared.release_id
                else load_release(self.conn, ref.release_id)
            )
            payload_contracts = contribution_payload_contracts(prepared.definitions)
            population = {row["contribution_id"]: row for row in retained["contributions"]}
            for row in parser_rows:
                validate_parser_input(prepared, row, payload_contracts=payload_contracts)
                if row["semantic_type"] in payload_contracts:
                    validate_parser_members(row, population)
        return retained

    def prepare_table_correspondence(self, source_view_id, contributions, weight_scale):
        """Detach the canonical finite questions for an exact selected native view."""
        from .identity import canonical_bytes

        self.source_view_ref(source_view_id)
        return self.conn.execute(
            text(
                "SELECT ops.prepare_table_correspondence("
                ":run, :view, CAST(:rows AS jsonb), "
                "CAST(:scale AS numeric), CAST(:layers AS jsonb))"
            ),
            {
                "run": self.run_id,
                "view": source_view_id,
                "rows": canonical_bytes(contributions).decode(),
                "scale": weight_scale,
                "layers": canonical_bytes(
                    [pin.values() for pin in self.characterization_selection]
                ).decode(),
            },
        ).scalar_one()

    def retained_component_section(self, reference, work_digest):
        """Read a native section designator from the original component's own source."""
        import json

        return self.conn.execute(
            text(
                "SELECT ops.contextual_component_section(CAST(:reference AS jsonb), "
                ":digest, :run, CAST(:layers AS jsonb))"
            ),
            {
                "reference": json.dumps(reference.model_dump(mode="json")),
                "digest": work_digest,
                "run": self.run_id,
                "layers": canonical_bytes(
                    [pin.values() for pin in self.characterization_selection]
                ).decode(),
            },
        ).scalar_one()

    def retained_component_alias(self, reference, edge):
        """Resolve an exact retained naming relation against a component term occurrence."""
        return self.conn.execute(
            text(
                "SELECT ops.contextual_definition_alias(CAST(:ref AS jsonb), "
                "CAST(:edge AS jsonb), :run, CAST(:layers AS jsonb))"
            ),
            {
                "ref": reference.model_dump_json(),
                "edge": edge.model_dump_json(),
                "run": self.run_id,
                "layers": canonical_bytes(
                    [pin.values() for pin in self.characterization_selection]
                ).decode(),
            },
        ).scalar_one()

    def contextual_section_headings(self, sources, source_view_id, scope, effective_version):
        """Resolve a complete heading population against the consuming release."""
        return self.conn.execute(
            text(
                "SELECT ops.contextual_section_headings(:release, CAST(:sources AS jsonb), "
                ":source_view, :scope, :effective_version, :run, CAST(:layers AS jsonb))"
            ),
            {
                "release": self.prepared.release_id,
                "sources": canonical_bytes(
                    [source.model_dump(mode="json") for source in sources]
                ).decode(),
                "source_view": source_view_id,
                "scope": scope,
                "effective_version": effective_version,
                "run": self.run_id,
                "layers": canonical_bytes(
                    [pin.values() for pin in self.characterization_selection]
                ).decode(),
            },
        ).scalar_one()

    def retained_structural_report(self, reference):
        """Authenticate one completed original report and its separately published support."""
        import json

        return self.conn.execute(
            text("SELECT ops.resolve_retained_structural_report(CAST(:reference AS jsonb))"),
            {"reference": json.dumps(reference.model_dump(mode="json"))},
        ).scalar_one()

    def retained_relationship_decision(self, reference):
        """Read one exact completed selected edge through the native custody owner."""
        import json

        return self.conn.execute(
            text("SELECT ops.resolve_retained_relationship_decision(CAST(:reference AS jsonb))"),
            {"reference": json.dumps(reference.model_dump(mode="json"))},
        ).scalar_one()

    def component_semantic_targets(self, targets):
        """Hydrate source-resolved target meanings once within one short owned read."""
        import json

        payload = json.dumps([target.model_dump(mode="json") for target in targets])
        self.conn.execute(
            text("SELECT ops.validate_component_targets(CAST(:targets AS jsonb))"),
            {"targets": payload},
        ).scalar_one()
        rows = self.conn.execute(
            text(
                "SELECT target->'reference'->>'component_id', "
                "ops.component_semantic_target(target->'reference') "
                "FROM jsonb_array_elements(CAST(:targets AS jsonb)) target"
            ),
            {"targets": payload},
        )
        return {row[0]: row[1] for row in rows}

    def contextual_mutual_neighbors(self, report):
        from sqlalchemy import text

        from .identity import canonical_bytes

        return self.conn.execute(
            text(
                "SELECT ops.contextual_mutual_neighbors("
                "CAST(:inventory AS jsonb),CAST(:profile AS jsonb),CAST(:vectors AS jsonb))"
            ),
            {
                "inventory": canonical_bytes(report["inventories"][0]).decode(),
                "profile": canonical_bytes(report["profiles"][0]).decode()
                if report["profiles"]
                else None,
                "vectors": canonical_bytes(report["vectors"]).decode(),
            },
        ).scalar_one()

    def validate_structural_inputs(self, inputs):
        from sqlalchemy import text

        from .identity import canonical_bytes

        raw = canonical_bytes(inputs.model_dump(mode="json", exclude_none=True)).decode()
        self.prepared.validate_json("StructuralInput", raw)
        self.conn.execute(
            text("SELECT ops.validate_structural_input(CAST(:inputs AS jsonb))"), {"inputs": raw}
        )

    def structural_source_frame(self, inputs, source_ref):
        from .proposals import native_source_frame
        from .source_views import load_source_view

        self.validate_structural_inputs(inputs)
        source = next((s for s in inputs.sources if s.identity == source_ref), None)
        if source is None:
            raise ValueError("structural source lies outside authenticated inputs")
        return native_source_frame(
            load_source_view(
                self.conn, source.source_view_id, analysis=False, read_budget=self._read_budget
            ),
            (),
        )

    def structural_source_annotations(self, inputs, source_ref, profile):
        from corpus_structure.methods.native_evidence_layers import (
            SPACY_FAMILIES,
            retained_annotation_products,
        )

        from .source_views import load_source_view
        from .structural_sources import PreparedStructuralAnnotations

        self.validate_structural_inputs(inputs)
        source = next((s for s in inputs.sources if s.identity == source_ref), None)
        if source is None:
            raise ValueError("structural annotations require an exact selected source")
        frame = self.structural_source_frame(inputs, source_ref)
        view = load_source_view(
            self.conn, source.source_view_id, analysis=False, read_budget=self._read_budget
        )
        layers = self.primary_characterization(
            source.source_view_id, families=(*SPACY_FAMILIES, "construction.source_readings")
        )
        products = retained_annotation_products(layers, view, profile)
        native = [
            (pin, layer)
            for pin, layer in layers.items()
            if layer.payload["operation"]["key"] == "text.native_evidence"
        ]
        if len(native) != 1:
            raise ValueError(
                "structural annotations require one explicitly selected native producer"
            )
        # These products come directly from their exact primary layers. They are
        # not an M1 summary task, so do not relabel the native producer as one.
        return PreparedStructuralAnnotations(frame, products, (), None, None)

    def source_context_membership(self, source_view_id):
        from .source_views import context_membership_digest

        return context_membership_digest(
            self.conn,
            self.run_id,
            self.source_view(source_view_id),
            read_budget=self._read_budget,
        )

    def source_result(self, source_view_id, method, *, occurrence_ids=(), semantic_types=()):
        from .observations import source_python
        from .pdf_record_reader import PublishedReadBudget

        source = self.source_view(source_view_id)
        task, result, config, producer = map(
            table, ("ops.task", "ops.task_result", "ops.method_config", "ops.method")
        )
        body_expr: ColumnElement[Any] = result.c.body
        if occurrence_ids:
            if len(occurrence_ids) > 256 or len(set(occurrence_ids)) != len(occurrence_ids):
                raise ValueError("upstream occurrence selection requires distinct bounded ids")
            selector = "$.contributions[*] ? (@.occurrence_id == $ids[*]"
            if semantic_types:
                selector += " && @.semantic_type == $types[*]"
            projected = func.jsonb_path_query_array(
                body_expr,
                cast(literal(selector + ")"), JSONPATH),
                literal({"ids": list(occurrence_ids), "types": list(semantic_types)}, type_=JSONB),
            )
            binding = (
                "release_id",
                "source",
                "unit_key",
                "method",
                "configuration_hash",
                "input_hash",
            )
            body_expr = func.jsonb_build_object(
                *(item for key in binding for item in (key, body_expr[key])),
                "contributions",
                projected,
            ).label("body")
        query = (
            select(
                body_expr,
                result.c.task_id.label("origin_task_id"),
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
        query = self._source_producer_query(query, task, result, source_view_id, method)
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
        body = dict(body)
        if method in {"extract.m1_annotations", "structure.scoped_relations"}:
            body["origin_task_id"] = row["origin_task_id"]
        if body.get("parse_detail") is not None:
            body["parse_detail"] = source_python(body["parse_detail"])
        return body

    def _source_producer_query(self, query, task, output, source_view_id: int, method: str):
        """Use the exact ordinary dependency when preparing or running a declared consumer."""
        producer = self.source_producers.get((source_view_id, method))
        if producer is not None:
            query = query.where(
                task.c.id == producer.task_id,
                task.c.unit_type == "source_view",
                task.c.unit_id == source_view_id,
                task.c.release_id == self.prepared.release_id,
                output.c.task_id == producer.origin_task_id,
                output.c.release_id == self.prepared.release_id,
            )
        if self.cut_id is not None:
            cut = table("ops.cut_task")
            query = query.join(cut, cut.c.origin_task_id == output.c.task_id).where(
                cut.c.cut_id == self.cut_id
            )
            if producer is not None:
                query = query.where(cut.c.task_id == producer.task_id)
        return query

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


def renew_claim(conn: Connection, *, task_id: int, attempt: int, holder: str) -> None:
    """Renew only the current attempt through the protected native ownership guard."""
    try:
        from ._operation_calls import TaskAttempt, TaskId
        from ._operation_calls import renew_claim as invoke

        invoke(conn, task_id=TaskId(task_id), attempt=TaskAttempt(attempt), holder=holder)
    except Exception as exc:
        if getattr(getattr(exc, "orig", None), "sqlstate", None) == "P0004":
            raise OperationConflict("task ownership changed before renewal") from exc
        raise
