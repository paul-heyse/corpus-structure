"""Run-bound source operations over the trusted semantic physical model.

Database sequence IDs locate rows only. Reproducible source observations bind the immutable
release, method input and source item; task attempts and sequence IDs do not enter their keys.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from pydantic import JsonValue
from sqlalchemy import Connection, cast, func, insert, literal, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert

from corpus_structure.core.method import (
    Method,
    UnitResult,
)

from ._operation_ids import (
    CutId,
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
from .refusals import OperationConflict
from .types import PreparedRelease

if TYPE_CHECKING:
    from .data_operation_runtime import RuntimeBinding

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


def record_method(
    conn: Connection,
    method: Method[Any],
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
    method: Method[Any],
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
    method: Method[Any],
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
