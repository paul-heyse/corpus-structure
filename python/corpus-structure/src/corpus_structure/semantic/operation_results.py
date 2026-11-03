"""Typed projections of protected operation results; native/model owners enforce semantics."""

from functools import lru_cache
from typing import Literal

from ._operation_calls import ClaimedTask as ClaimedTask
from ._operation_calls import CompletionReceipt as CompletionReceipt
from ._operation_calls import CompletionResult as CompletionResult
from ._operation_ids import MethodConfigId as MethodConfigId
from ._operation_ids import ReleaseId as ReleaseId
from ._operation_ids import RunId as RunId
from ._operation_ids import TaskAttempt as TaskAttempt
from ._operation_ids import TaskId as TaskId
from .operation_value_types import HeldProgress as HeldProgress
from .operation_value_types import OperationResult


class HoldDecision(OperationResult):
    task_id: TaskId
    attempt: TaskAttempt
    packet_hash: str
    disposition: Literal["held", "proceed"]


def validate_result_dimension(
    prepared, operation: str, dimension: str, value: str, *, field: str | None = None
) -> None:
    """Validate an actual constructor's finite result against its bound release contract."""
    key = (operation, dimension, field)
    if key in prepared._result_adapters:
        prepared._result_adapters[key].validate_python(value, strict=True)
        return
    rows = [row for row in prepared.registry_rows if row.kind == "execution_model"]
    if prepared.execution_model_id is None:
        raise ValueError("operation result requires a composed execution binding")
    if len(rows) != 1 or rows[0].name != prepared.execution_model_id:
        raise ValueError("operation result requires its exact archived execution binding")
    adapter = _result_adapter(rows[0].body, operation, dimension, field)
    prepared._result_adapters[key] = adapter
    adapter.validate_python(value, strict=True)


def validate_product_result_dimension(
    content: bytes, operation: str, dimension: str, value: str, *, field: str | None = None
) -> None:
    """Native-call adapters consume the same immutable normalized product as Python owners."""
    _result_adapter(content, operation, dimension, field).validate_python(value, strict=True)


@lru_cache(maxsize=128)
def _result_adapter(
    content: bytes, operation: str, dimension: str, actual_field: str | None = None
):
    import json
    from typing import Any

    from pydantic import TypeAdapter

    product = json.loads(content)
    from .contracts import _bound_execution_model

    _bound_execution_model(content, product["model_id"])
    contract = next((item for item in product["operations"] if item["id"] == operation), None)
    if contract is None:
        raise ValueError(f"{operation}: operation is not declared by the bound execution model")
    field = next(
        (item for item in contract.get("result_dimensions", ()) if item["id"] == dimension), None
    )
    if field is None:
        raise ValueError(
            f"{operation}/{dimension}: no enforcing result contract; derive a supported release"
        )
    if actual_field is not None and field["field"] != actual_field:
        raise ValueError(
            f"{operation}/{dimension}: contract field {field['field']!r} "
            f"differs from constructor {actual_field!r}; regenerate the enforcing adapter"
        )
    domain = next(
        item for item in product["outcome_domains"] if item["id"] == field["outcome_domain"]
    )
    literal: Any = Literal
    members = (
        [v for v in contract["outcomes"] if v in domain["values"]]
        if field["outcome_domain"] == contract["outcome_domain"]
        else domain["values"]
    )
    return TypeAdapter(literal[tuple(members)])


def validate_task_result_dimension(
    conn, task_id: int, operation: str, dimension: str, value: str
) -> None:
    """Resolve the task's immutable release, never the project's current interpretation."""
    from sqlalchemy import select

    from .metadata import table

    tasks, runs, registry = table("ops.task"), table("ops.run"), table("sem.registry_row")
    content = conn.execute(
        select(registry.c.body)
        .select_from(
            tasks.join(runs, tasks.c.run_id == runs.c.id).join(
                registry, registry.c.release_id == runs.c.release_id
            )
        )
        .where(tasks.c.id == task_id, registry.c.kind == "execution_model")
    ).scalar_one_or_none()
    if content is None:
        from .outcomes import CODE_OUTCOME_DOMAINS

        if (
            operation == "hold_submission"
            and dimension == "decision"
            and value in CODE_OUTCOME_DOMAINS["hold_decision"]
        ):
            return
        raise ValueError("task has no bound operation result contract")
    validate_product_result_dimension(
        bytes(content), operation, dimension, value, field="disposition"
    )


def validate_method_dimension(prepared, method: str, dimension: str, value: str | None) -> None:
    """Consume the method's declared dimension from its archived configure-method contract."""
    from .contracts import bound_execution_model

    key = f"{method}/{dimension}"
    definitions = bound_execution_model(prepared).operation("configure_method").result_dimensions
    declared = any(item.id == key for item in definitions)
    # An absent confidence channel is distinct from an asserted provenance value.
    if value is None and (
        dimension == "observation.confidence_source"
        or (dimension == "confidence_source" and not declared)
    ):
        return
    if value is None:
        raise ValueError(f"{method}/{dimension}: a declared value is required")
    field = {"family": "family", "tier": "tier", "confidence_source": "confidence_source",
             "result.outcome": "outcome", "observation.family": "observations.family",
             "observation.outcome": "observations.outcome",
             "observation.confidence_source": "observations.confidence_source"}[dimension]
    validate_result_dimension(prepared, "configure_method", key, value, field=field)
